from typing import Optional, Dict, Any, List
import json
import httpx
import logging
import re
from string import Template

from .config import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL, REQUEST_TIMEOUT
from .models import AIAnalysis, AdvancedAdvisorResponse, AdvancedComparisonResponse

logger = logging.getLogger(__name__)

PRODUCT_ANALYST_PROMPT = """You are an expert smart home product analyst.

You will receive product details. Some fields may be missing or incomplete.

Your task:
Generate realistic and specific pros and cons for the product.

Product Details:
- Name: {name}
- Price: {price}
- Rating: {rating}
- Features: {features}
- Category: {category}
- SerpAPI Context: {serpapi_context}

IMPORTANT RULES:
- Do NOT ask for more data
- Do NOT mention missing data
- If any field is missing, intelligently assume typical values based on similar products
- Pros must highlight strengths (features, usability, performance, value)
- Cons must highlight realistic drawbacks (price, limitations, compatibility, etc.)
- Avoid generic phrases like "good product" or "nice design"
- Keep points short and practical
- Generate 3-5 pros and 2-4 cons

Output format (STRICT JSON):
{
    "pros": [
        "point 1",
        "point 2",
        "point 3"
    ],
    "cons": [
        "point 1",
        "point 2"
    ]
}"""

PRODUCT_ANALYST_PROMPT_TEMPLATE = Template(PRODUCT_ANALYST_PROMPT)

# ─── New Advanced Prompt (Recommendation Phase - v3.1.0 CoT) ─────
ADVANCED_SYSTEM_PROMPT = """You are a Senior AI Smart Home Decision Assistant.
You are part of a Hybrid AI Architecture (v3.1.0).

Context:
1. A local Python Heuristic Search Engine has already identified the top products based on A* search and Euclidean distance metrics.
2. The "Match Score" provided in the input is the GROUND TRUTH calculated via local Machine Learning (normalization + sentiment analysis).

Task:
Perform a Chain-of-Thought (CoT) analysis to explain the trade-offs between the top 3 products.

--------------------------------------------------
🔹 STEP 1: REASONING (THINK STEP-BY-STEP)
--------------------------------------------------
1. Identify the core user intent (extracted from query).
2. Look at the top 3 products provided in the list.
3. Compare them based on:
   - Price vs. Feature Density.
   - Sentiment-adjusted Match Score.
   - Specific pros/cons mentioned in the product data.
4. Formulate an explanation of WHY the #1 product is superior for this specific user.

--------------------------------------------------
🔹 STEP 2: OUTPUT FORMAT (STRICT JSON)
--------------------------------------------------
Always return response in this exact JSON format:

{
  "parsed_user_intent": {
    "category": "",
    "budget": "Flexible or Specified",
    "room_size": "",
    "preferences": [],
    "energy_efficiency": ""
  },
  "recommendations": [
    {
      "name": "",
      "price": "",
      "match_score": "Use the PROVIDED score",
      "reason": "Chain-of-thought trade-off explanation",
      "pros": [],
      "cons": []
    }
  ],
  "follow_up_question": "A relevant question to refine the next state-space search"
}

--------------------------------------------------
🔹 INPUT DATA
--------------------------------------------------
User Query: "{user_input}"
Top Ranked Products (via Python Heuristic Engine): {products_json}

--------------------------------------------------
🔹 FINAL INSTRUCTIONS
--------------------------------------------------
- Do NOT recalculate scores. Use the ones provided.
- Focus heavily on 'Reasoning' for trade-offs.
- Acknowledge the mathematical precision of the Python engine.
- Only output clean JSON."""

# ─── New Advanced Comparison Prompt ───────────────────────────
COMPARISON_SYSTEM_PROMPT = """You are an advanced AI Smart Home Comparison Assistant.
Your goal is to perform a deep, side-by-side analysis of 2-6 products.

Analyze each product in the context of:
1. Value for Money (Price vs Features/Quality)
2. Performance & Reliability (Ratings/Reviews)
3. Energy Efficiency & Smart Integration
4. Unique Standout Features

Return a detailed, contrasting summary of our comparison and nominate the 'Best Overall Buy' with a clear reasoning.

Always return high-quality JSON content.

Format your response in this exact JSON:

{
  "comparison_summary": "A 2-3 sentence overview of how these products contrast.",
  "best_product_name": "The exact name of the winner",
  "best_product_reason": "Detailed 2-3 sentence explanation of why this product won.",
  "side_by_side_analysis": [
    {
      "name": "Product Name",
      "verdict": "Short 1-sentence verdict (e.g. Best for Budget, Most Advanced)",
      "pros": ["Pro 1", "Pro 2"],
      "cons": ["Con 1"]
    }
  ],
  "overall_recommendation": "Final recommendation based on usage scenario."
}

--------------------------------------------------
🔹 PRODUCTS TO COMPARE
--------------------------------------------------
{products_json}
"""

# ─── System prompt (exact training instructions) ──────────────
SYSTEM_PROMPT = """You are an AI product advisor for smart home devices.

Your task is to analyze the user query and extract structured information.

Return ONLY valid JSON.

Extract the following fields:

product_category: the type of product (camera, smart bulb, robot vacuum, smart lock, etc)

required_features: a list of important features mentioned by the user

brand: if the user mentions a brand

budget_range: minimum and maximum price in INR

usage_scenario: where the product will be used (home security, apartment lighting, etc)

buying_advice: short helpful advice (1-2 sentences)

ai_explanation: 1-2 sentence explanation of why the recommended product type fits the user's needs

Example:

User query:
"I need a security camera under 5000 with night vision"

Response:

{
 "product_category": "security camera",
 "required_features": ["night vision"],
 "brand": null,
 "budget_range": {"min":0,"max":5000},
 "usage_scenario": "home security monitoring",
 "buying_advice": "Look for cameras with night vision and mobile alerts for effective home monitoring.",
 "ai_explanation": "A security camera with night vision is ideal for round-the-clock home surveillance."
}

Rules:
- budget_range must be an object with min and max as integers (INR currency)
- If no budget mentioned, use {"min": 0, "max": 999999}
- required_features should include connectivity (WiFi, Bluetooth, Zigbee), capabilities (night vision, motion detection), and compatibility (Alexa, Google Home) when relevant
- brand should be null if not specifically mentioned

Only return JSON.
Do not include explanations."""


def _build_contextual_user_prompt(text: str, previous_queries: Optional[List[str]] = None) -> str:
    history = [q.strip() for q in (previous_queries or []) if str(q).strip()]
    if not history:
        return text

    lines = ["Previous conversations:"]
    for idx, query in enumerate(history[:3], 1):
        lines.append(f"{idx}. User: {query}")
    lines.append("")
    lines.append("Current query:")
    lines.append(text)
    return "\n".join(lines)


async def analyze_text_with_groq(text: str, previous_queries: Optional[List[str]] = None) -> Optional[AIAnalysis]:
    """Call Groq API to extract structured JSON from user text. Falls back to simple parsing if API not available."""
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not configured, using keyword extraction")
        return _fallback_keyword_analysis(text)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    contextual_text = _build_contextual_user_prompt(text, previous_queries)

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": contextual_text},
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(GROQ_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            response_data = resp.json()

            content = response_data["choices"][0]["message"]["content"]
            if not content:
                logger.warning("Groq returned empty content, using fallback")
                return _fallback_keyword_analysis(text)

            data = json.loads(content.strip())
            return AIAnalysis(**data)

    except Exception as e:
        logger.error(f"Error in analyze_text_with_groq: {e}, using keyword extraction fallback")
        # Use smart fallback based on actual user query
        return _fallback_keyword_analysis(text)


def _fallback_keyword_analysis(text: str) -> AIAnalysis:
    """Intelligent fallback that extracts product info from user query text itself."""
    text_lower = text.lower()
    
    # CATEGORY DETECTION: Look for product type keywords
    category_map = {
        "bulb": ["bulb", "light", "lamp"],
        "AC": ["ac", "air conditioner", "cooling"],
        "fan": ["fan", "ceiling fan", "exhaust"],
        "washing machine": ["washing", "wash", "machine", "laundry"],
        "refrigerator": ["fridge", "refrigerator", "cooler"],
        "plug": ["plug", "socket", "outlet", "switch"],
        "camera": ["camera", "cctv", "security"],
        "door lock": ["lock", "door lock", "smart lock"],
        "speaker": ["speaker", "echo", "alexa", "nest"],
        "purifier": ["purifier", "air purifier", "humidifier"],
        "vacuum": ["vacuum", "robot vacuum", "cleaner"],
    }
    
    detected_category = "Smart Appliance"
    for category, keywords in category_map.items():
        if any(kw in text_lower for kw in keywords):
            detected_category = category
            break
    
    # FEATURES DETECTION
    feature_keywords = {
        "WiFi": ["wifi", "wireless", "connected"],
        "Voice": ["voice", "alexa", "google", "assistant"],
        "Energy Monitor": ["energy", "power", "monitor"],
        "Smart": ["smart", "intelligent", "automated"],
        "Dimmable": ["dimmable", "brightness"],
        "Color": ["color", "rgb", "colorful"],
    }
    
    features = []
    for feature, keywords in feature_keywords.items():
        if any(kw in text_lower for kw in keywords):
            features.append(feature)
    
    # BUDGET DETECTION: Look for price mentions (prioritize "under" keyword)
    budget_max = 999999
    import re as re_module
    
    # First try to find "under/below AMOUNT" pattern
    under_match = re_module.search(r'(?:under|below|less than|max|<)\s*₹?\s*(\d+)', text_lower)
    if under_match:
        budget_max = int(under_match.group(1))
    else:
        # Fall back to any large number (likely price)
        numbers = re_module.findall(r'\d+', text_lower)
        if numbers:
            # Use the largest number (usually the budget) or the last one mentioning price
            for num in reversed(numbers):
                val = int(num)
                if val > 100:  # Likely a price, not quantity
                    budget_max = val
                    break
    
    # BRAND DETECTION
    brand = None
    brand_keywords = ["philips", "halonix", "tp-link", "mi", "amazon", "google", "lg", "daikin", "whirlpool"]
    for brand_name in brand_keywords:
        if brand_name in text_lower:
            brand = brand_name.title()
            break
    
    return AIAnalysis(
        product_category=detected_category,
        required_features=features if features else ["Smart", "WiFi"],
        brand=brand,
        budget_range={"min": 0, "max": budget_max},
        usage_scenario="Smart home automation",
        buying_advice=f"Looking for {detected_category.lower()} with intelligent features.",
        ai_explanation=f"A {detected_category.lower()} matching your requirements."
    )


async def generate_advanced_recommendations(user_query: str, products: List[Dict]) -> Optional[AdvancedAdvisorResponse]:
    """Call Groq API using the Advanced AI-powered Prompt with User Query and Available Products."""
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not configured")
        return None

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    products_json_str = json.dumps(products[:12], ensure_ascii=False)
    prompt_content = ADVANCED_SYSTEM_PROMPT.replace("{user_input}", user_query).replace("{products_json}", products_json_str)

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "user", "content": prompt_content},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(GROQ_API_URL, json=payload, headers=headers)
            resp.raise_for_status()

            content = resp.json()["choices"][0]["message"]["content"]
            
            # JSON extraction
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                content = content[start:end+1]
            
            data = json.loads(content)
            return AdvancedAdvisorResponse(**data)

    except Exception as e:
        logger.error(f"Error in generate_advanced_recommendations: {e}")
        return None


async def generate_advanced_comparison(products: List[Dict]) -> Optional[AdvancedComparisonResponse]:
    """Call Groq API using the Comparison Prompt with selected Products."""
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not configured")
        return None

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    products_json_str = json.dumps(products, ensure_ascii=False)
    prompt_content = COMPARISON_SYSTEM_PROMPT.replace("{products_json}", products_json_str)

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "user", "content": prompt_content},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(GROQ_API_URL, json=payload, headers=headers)
            resp.raise_for_status()

            content = resp.json()["choices"][0]["message"]["content"]
            
            # JSON extraction
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                content = content[start:end+1]
            
            data = json.loads(content)
            return AdvancedComparisonResponse(**data)

    except Exception as e:
        logger.error(f"Error in generate_advanced_comparison: {e}")
        return None


async def generate_product_analysis(product: Dict[str, Any]) -> Optional[Dict[str, List[str]]]:
    """Call Groq to generate realistic product pros and cons in strict JSON."""
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not configured")
        return None

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    prompt_content = PRODUCT_ANALYST_PROMPT_TEMPLATE.safe_substitute(
        name=product.get("name", "Unknown"),
        price=product.get("price_inr", product.get("price", "Unknown")),
        rating=product.get("rating", "Unknown"),
        features=json.dumps(product.get("features", []), ensure_ascii=False),
        category=product.get("category", product.get("product_category", "Unknown")),
        serpapi_context=json.dumps({
            "raw_title": product.get("raw_title", ""),
            "source": product.get("source", ""),
            "snippet": product.get("snippet", ""),
            "extensions": product.get("extensions", []),
            "delivery": product.get("delivery", ""),
            "rating_count": product.get("rating_count", 0),
            "review_count": product.get("review_count", 0),
            "price_text": product.get("price_text", ""),
        }, ensure_ascii=False),
    )

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt_content,
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(GROQ_API_URL, json=payload, headers=headers)
            resp.raise_for_status()

            content = resp.json()["choices"][0]["message"]["content"]
            if not content:
                return None

            data = json.loads(content.strip())
            pros = data.get("pros", [])
            cons = data.get("cons", [])
            if isinstance(pros, str):
                pros = [pros]
            if isinstance(cons, str):
                cons = [cons]
            return {
                "pros": [str(item).strip() for item in pros if str(item).strip()][:5],
                "cons": [str(item).strip() for item in cons if str(item).strip()][:4],
            }

    except Exception as e:
        logger.error(f"Error in generate_product_analysis: {e}")
        return None


def build_search_query(ai: AIAnalysis) -> str:
    """Build an optimized SerpAPI search query from AI analysis."""
    parts = []
    if ai.product_category:
        parts.append(ai.product_category)
    if ai.brand:
        parts.append(ai.brand)
    if ai.required_features:
        parts.extend(ai.required_features[:3])
    return " ".join(parts) if parts else ""


def generate_product_reason(product_name: str, ai: AIAnalysis) -> str:
    """Fallback reason generator (legacy)."""
    return f"Matches your search for {ai.product_category or 'smart appliance'}."


def compute_match_score(
    product_name: str,
    ai: AIAnalysis,
    product_features: Optional[List[str]] = None,
    product_description: str = "",
) -> float:
    """Compute a dynamic 0-100 feature alignment score using keyword overlap."""
    user_phrases: List[str] = []
    if ai.required_features:
        user_phrases.extend([str(feature) for feature in ai.required_features if str(feature).strip()])
    if ai.product_category:
        user_phrases.append(str(ai.product_category))
    if ai.brand:
        user_phrases.append(str(ai.brand))

    user_keywords: List[str] = []
    for phrase in user_phrases:
        user_keywords.extend([token for token in re.findall(r"[a-z0-9]+", phrase.lower()) if len(token) >= 3])
    user_keywords = list(dict.fromkeys(user_keywords))

    if not user_keywords:
        return 50.0

    product_blob = " ".join(
        [
            product_name or "",
            " ".join(product_features or []),
            product_description or "",
        ]
    ).lower()

    matched = sum(1 for keyword in user_keywords if keyword in product_blob)
    total = max(len(user_keywords), 1)
    feature_score = int((matched / total) * 100)
    return float(max(0, min(feature_score, 100)))
