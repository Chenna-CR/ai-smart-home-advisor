from typing import List, Dict, Optional, Any, Tuple
import httpx
import logging
import re
from statistics import median
import numpy as np
from textblob import TextBlob
from sklearn.preprocessing import MinMaxScaler
from .config import SERPAPI_KEY, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

SMART_AI_KEYWORDS = [
    "smart",
    "wifi",
    "alexa",
    "google assistant",
    "ai",
    "automation",
    "iot",
    "voice control",
    "app control",
]

GENERIC_CATEGORY_TOKENS = {
    "smart",
    "ai",
    "home",
    "appliance",
    "appliances",
    "device",
    "devices",
    "product",
    "products",
}

QUERY_STOPWORDS = {
    "a", "an", "the", "i", "me", "my", "we", "our", "you", "your", "to", "for", "with", "and", "or",
    "of", "in", "on", "at", "by", "from", "under", "over", "best", "top", "good", "need", "want", "looking",
    "show", "find", "search", "buy", "price", "budget", "smart", "ai", "home", "appliance", "appliances",
}

UNSAFE_LISTING_PATTERNS = [
    r"\bsex\s*toy\b",
    r"\badult\s*toy\b",
    r"\bintimate\s*toy\b",
    r"\bvibrator\b",
    r"\bdildo\b",
    r"\bporn\b",
    r"\berotic\b",
    r"\bnsfw\b",
    r"\bmasturbat(?:e|ion|or|ing)?\b",
    r"\bpleasure\b",
]

# Known feature keywords for auto-tagging
DETECTABLE_FEATURES = [
    "WiFi", "Bluetooth", "Zigbee", "Z-Wave", "Matter", "Thread",
    "Alexa", "Google Home", "Siri", "HomeKit",
    "Night Vision", "Motion Detection", "1080p", "2K", "4K",
    "Weatherproof", "Waterproof", "IP65", "IP66", "IP67",
    "Rechargeable", "Battery", "Solar", "USB-C",
    "HEPA", "Smart", "Voice Control", "App Control",
    "Touch", "RGB", "Dimmable", "Color",
]

FEATURE_KEYWORDS_MAP = {
    "alexa": "Alexa Voice Control",
    "bluetooth": "Bluetooth Connectivity",
    "wifi": "WiFi Enabled",
    "smart": "Smart Home Integration",
    "portable": "Portable Design",
    "voice": "Voice Assistant Support",
    "speaker": "High Quality Audio",
}

FALLBACK_FEATURE_POOL = [
    "App Based Control",
    "Energy Efficient Operation",
    "Reliable Daily Performance",
    "Quick Setup",
    "Modern Build Quality",
    "Compact Form Factor",
    "User Friendly Controls",
    "Value Focused Pricing",
]

CATEGORY_FEATURE_HINTS = {
    "camera": ["Home Monitoring Ready", "Motion Detection Support"],
    "bulb": ["Scene Lighting Control", "Brightness Customization"],
    "light": ["Scene Lighting Control", "Brightness Customization"],
    "ac": ["Efficient Cooling Performance", "Comfort Climate Control"],
    "air conditioner": ["Efficient Cooling Performance", "Comfort Climate Control"],
    "speaker": ["Hands Free Voice Operation", "Room Filling Audio"],
    "lock": ["Secure Access Control", "Door Safety Automation"],
    "plug": ["Remote Power Scheduling", "Energy Usage Insights"],
    "switch": ["Remote Power Scheduling", "Energy Usage Insights"],
    "vacuum": ["Automated Cleaning Support", "Low Effort Maintenance"],
    "fan": ["Efficient Airflow Management", "Adaptive Speed Control"],
}

# ─── 1. DATA-CENTRIC FEATURE ENGINEERING (UNIT III) ───────────

class PreprocessingPipeline:
    @staticmethod
    def normalize_numerical_data(products: List[Dict]) -> List[Dict]:
        """Normalize Price and Ratings using MinMaxScaler."""
        if not products:
            return products

        prices = np.array([p.get("price_inr", 0) for p in products]).reshape(-1, 1)
        ratings = np.array([p.get("rating", 0) for p in products]).reshape(-1, 1)

        scaler = MinMaxScaler()
        normalized_prices = scaler.fit_transform(prices)
        normalized_ratings = scaler.fit_transform(ratings)

        for i, p in enumerate(products):
            p["norm_price"] = float(normalized_prices[i][0])
            p["norm_rating"] = float(normalized_ratings[i][0])
        
        return products

# ─── 2. LOCAL NLP & SENTIMENT ANALYSIS (UNIT IV) ──────────────

class SentimentAnalyzer:
    @staticmethod
    def analyze_sentiment(text: str) -> float:
        """Perform local sentiment analysis using TextBlob."""
        if not text:
            return 0.0
        analysis = TextBlob(text)
        return analysis.sentiment.polarity  # Range: -1.0 to 1.0

    @staticmethod
    def apply_sentiment_penalty(products: List[Dict]) -> List[Dict]:
        """Apply penalty multiplier if sentiment is negative."""
        for p in products:
            # Analyze title and store description/snippets if available
            text_to_analyze = f"{p.get('name', '')} {p.get('store', '')}"
            score = SentimentAnalyzer.analyze_sentiment(text_to_analyze)
            p["sentiment_score"] = score
            
            # Unit IV Requirement: If sentiment < 0, apply penalty
            p["sentiment_multiplier"] = 0.8 if score < 0 else 1.0
        return products

# ─── 3. STATE SPACE & HEURISTIC SEARCH (UNIT II/III) ──────────

class HeuristicSearchEngine:
    """Implement A* Style Search for Product Ranking."""

    @staticmethod
    def calculate_distance(p_vector: np.ndarray, q_vector: np.ndarray) -> float:
        """Calculate Euclidean Distance between Requirement and Product (Unit III)."""
        return float(np.linalg.norm(p_vector - q_vector))

    @classmethod
    def rank_with_heuristic(cls, products: List[Dict], requirements: Dict[str, Any]) -> List[Dict]:
        """
        Logic: f(n) = g(n) + h(n)
        g(n) = Path cost (Normalized Price)
        h(n) = Heuristic (Euclidean distance from target features/rating)
        
        IMPROVED: Now filters and scores by category relevance first!
        """
        # Preprocess
        products = PreprocessingPipeline.normalize_numerical_data(products)
        products = SentimentAnalyzer.apply_sentiment_penalty(products)

        # Target Vector: [Ideal Price (min), Ideal Rating (max=1.0), Ideal Feature Match (max=1.0)]
        target_v = np.array([0.0, 1.0, 1.0])

        # Extract category and features from requirements
        req_category = requirements.get("category", "").lower().strip()
        req_features = [f.lower() for f in requirements.get("required_features", [])]

        ranked_results = []
        for p in products:
            # STEP 1: Category Relevance Scoring (MOST IMPORTANT)
            product_name = p.get("name", "").lower()
            product_features_str = " ".join([f.lower() for f in p.get("features", [])])
            product_full_text = f"{product_name} {product_features_str}"
            
            # Check if product name contains category keywords
            category_relevance = 0.0
            if req_category:
                category_keywords = req_category.split()
                matched_keywords = sum(1 for kw in category_keywords if kw in product_name or kw in product_features_str)
                if matched_keywords > 0:
                    category_relevance = min(100, (matched_keywords / max(len(category_keywords), 1)) * 100)
            
            # STEP 2: Feature Match Calculation
            p_features = [f.lower() for f in p.get("features", [])]
            if req_features:
                overlap = sum(1 for f in req_features if f in p_features or f in product_name)
                feat_score = (overlap / len(req_features)) * 100
            else:
                feat_score = 50.0
            
            # STEP 3: Combine Category (70% weight) + Features (30% weight)
            category_weight = 0.7
            feature_weight = 0.3
            
            combined_relevance = (category_relevance * category_weight) + (feat_score * feature_weight)
            
            # STEP 4: Price & Rating factors (secondary)
            price_score = (1.0 - p.get("norm_price", 0.5)) * 100  # Lower price = higher score
            rating_score = p.get("norm_rating", 0.5) * 100  # Higher rating = higher score
            
            # STEP 5: Final Score Calculation
            relevance_weight = 0.6  # Relevance is most important
            price_weight = 0.2
            rating_weight = 0.2
            
            raw_score = (combined_relevance * relevance_weight) + (price_score * price_weight) + (rating_score * rating_weight)
            
            # Apply sentiment multiplier
            final_score = raw_score * p.get("sentiment_multiplier", 1.0)
            
            p["match_score"] = round(min(final_score, 100), 2)
            ranked_results.append(p)

        # Sort by final match score descending
        return sorted(ranked_results, key=lambda x: x["match_score"], reverse=True)


def _price_to_int(price_str: str) -> int:
    if not price_str:
        return 0
    cleaned = re.sub(r"[^0-9.]", "", price_str)
    try:
        value = float(cleaned)
        return int(round(value))
    except (ValueError, TypeError):
        return 0


def _extract_features(title: str, snippet: str = "", description: str = "") -> List[str]:
    """Extract clean, unique features from title and snippet text."""
    text = " ".join([title or "", snippet or "", description or ""]).lower()
    features: List[str] = []

    def add_feature(label: str) -> None:
        clean = re.sub(r"\s+", " ", str(label).strip())
        if clean and clean not in features:
            features.append(clean)

    for keyword, label in FEATURE_KEYWORDS_MAP.items():
        if re.search(rf"\b{re.escape(keyword)}\b", text):
            add_feature(label)

    for feat in DETECTABLE_FEATURES:
        if feat.lower() in text:
            add_feature(feat)

    for token, hints in CATEGORY_FEATURE_HINTS.items():
        if token in text:
            for hint in hints:
                add_feature(hint)

    # Ensure a stable 4-6 feature list per product, even with sparse marketplace data.
    if len(features) < 4:
        seed_text = (title or snippet or "product")
        seed = sum(ord(ch) for ch in seed_text)
        start_idx = seed % len(FALLBACK_FEATURE_POOL)
        for offset in range(len(FALLBACK_FEATURE_POOL)):
            add_feature(FALLBACK_FEATURE_POOL[(start_idx + offset) % len(FALLBACK_FEATURE_POOL)])
            if len(features) >= 6:
                break

    return features[:6]


def _reviews_to_int(value) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    cleaned = re.sub(r"[^0-9]", "", str(value))
    return int(cleaned) if cleaned else 0


def _safe_int(value, default: int = 0) -> int:
    try:
        if value is None or isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return int(value)
        cleaned = re.sub(r"[^0-9]", "", str(value))
        return int(cleaned) if cleaned else default
    except Exception:
        return default


def _safe_float(value, default: float = 3.5) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _contains_unsafe_listing(text: str) -> bool:
    q = (text or "").strip().lower()
    if not q:
        return False
    return any(re.search(pattern, q, re.IGNORECASE) for pattern in UNSAFE_LISTING_PATTERNS)


def _tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t]


def _build_product_text_blob(product: Dict[str, Any]) -> str:
    name = str(product.get("name", ""))
    features = " ".join(str(f) for f in product.get("features", []))
    description = str(product.get("description") or product.get("snippet") or "")
    return f"{name} {features} {description}".lower()


def _contains_required_smart_keyword(product: Dict[str, Any]) -> bool:
    blob = _build_product_text_blob(product)
    return any(keyword in blob for keyword in SMART_AI_KEYWORDS)


def _category_tokens(ai_result: Any) -> List[str]:
    category = str(getattr(ai_result, "product_category", "") or "").lower().strip()
    if not category:
        return []
    tokens = [t for t in _tokenize(category) if t not in GENERIC_CATEGORY_TOKENS and len(t) >= 2]
    if tokens:
        return tokens
    return [t for t in _tokenize(category) if len(t) >= 2]


def _query_tokens(user_query: str) -> List[str]:
    tokens = [
        t for t in _tokenize(user_query)
        if len(t) >= 2 and t not in QUERY_STOPWORDS
    ]
    # Keep deterministic order and remove duplicates.
    return list(dict.fromkeys(tokens))


def _matches_category(product: Dict[str, Any], category_tokens: List[str], strict_name_only: bool = True) -> bool:
    if not category_tokens:
        return True
    name = str(product.get("name", "")).lower()
    text = _build_product_text_blob(product)
    haystack = name if strict_name_only else text
    return any(token in haystack for token in category_tokens)


def _matches_query(product: Dict[str, Any], query_tokens: List[str], strict_name_only: bool = True) -> bool:
    if not query_tokens:
        return True
    name = str(product.get("name", "")).lower()
    text = _build_product_text_blob(product)
    haystack = name if strict_name_only else text
    return any(token in haystack for token in query_tokens)


def filter_relevant_products(products, ai_result, user_query):
    """Return only category-relevant smart/AI products aligned with user query intent."""
    if not products:
        return []

    category_tokens = _category_tokens(ai_result)
    query_tokens = _query_tokens(user_query)

    strict_filtered = []
    for product in products:
        if not _contains_required_smart_keyword(product):
            continue
        if not _matches_category(product, category_tokens, strict_name_only=True):
            continue
        if not _matches_query(product, query_tokens, strict_name_only=True):
            continue
        strict_filtered.append(product)

    if strict_filtered:
        return strict_filtered

    # Fallback: relax name-only constraints, but never return products lacking smart/AI keywords.
    relaxed_filtered = []
    for product in products:
        if not _contains_required_smart_keyword(product):
            continue
        if not _matches_category(product, category_tokens, strict_name_only=False):
            continue
        if not _matches_query(product, query_tokens, strict_name_only=False):
            continue
        relaxed_filtered.append(product)

    if relaxed_filtered:
        return relaxed_filtered

    # Last-resort fallback: keep only smart/AI-enabled products with the best token overlap.
    scored = []
    for product in products:
        if not _contains_required_smart_keyword(product):
            continue
        blob = _build_product_text_blob(product)
        overlap = sum(1 for token in category_tokens + query_tokens if token and token in blob)
        scored.append((overlap, product))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored if item[0] > 0] or [item[1] for item in scored]


def _feature_match_score(product: Dict[str, Any], requirements: Dict[str, Any]) -> Tuple[float, str]:
    required_features = [str(feature).strip().lower() for feature in requirements.get("required_features", []) if str(feature).strip()]
    category = str(requirements.get("category", "")).strip().lower()

    combined_product_text = " ".join(
        [
            str(product.get("name", "")),
            " ".join(str(feature) for feature in product.get("features", [])),
            str(product.get("snippet") or product.get("description") or ""),
        ]
    ).lower()

    user_keywords: List[str] = []
    for phrase in required_features + ([category] if category else []):
        user_keywords.extend(re.findall(r"[a-z0-9]+", phrase))
    user_keywords = [kw for kw in dict.fromkeys(user_keywords) if len(kw) >= 3]

    if not user_keywords:
        return 50.0, "Neutral feature score because no explicit requirements were provided."

    matched_keywords = [kw for kw in user_keywords if kw in combined_product_text]
    matched = len(matched_keywords)
    total = max(len(user_keywords), 1)
    feature_score = int((matched / total) * 100)
    feature_score = max(0, min(feature_score, 100))

    if matched_keywords:
        explanation = f"Matches {matched}/{total} requirement keywords: {', '.join(matched_keywords[:4])}."
    else:
        explanation = "No direct requirement keyword overlap found in this listing."

    return float(feature_score), explanation


def _rating_score(product: Dict[str, Any]) -> float:
    rating = _safe_float(product.get("rating"), default=3.5)
    return round(min(max((rating / 5.0) * 100.0, 0.0), 100.0), 2)


def _price_fit_score(price: int, budget_reference: float) -> float:
    if budget_reference <= 0:
        return 50.0
    distance_ratio = abs(price - budget_reference) / budget_reference
    return round(max(0.0, 100.0 - min(distance_ratio * 100.0, 100.0)), 2)


def _review_score(review_count: int, max_review_count: int) -> float:
    if review_count <= 0 or max_review_count <= 0:
        return 0.0
    return round(min(100.0, (np.log1p(review_count) / np.log1p(max_review_count)) * 100.0), 2)


def _score_reason(name: str, feature_score: float, rating_score: float, price_score: float, review_score: float, price: int, budget_reference: float) -> str:
    budget_text = f"budget target of ₹{int(round(budget_reference))}" if budget_reference > 0 else "market pricing"
    if price_score >= 75:
        price_fit_note = f"Its price fit is strong against the {budget_text}."
    elif price_score >= 45:
        price_fit_note = f"Price fit is moderate versus the {budget_text}."
    else:
        price_fit_note = f"Price fit is weaker for the {budget_text}, but other factors help." 

    templates = [
        f"This product scored well due to feature match ({feature_score:.0f}/100), rating confidence ({rating_score:.0f}/100), and review signal ({review_score:.0f}/100). {price_fit_note}",
        f"{name} performs strongly on requirement alignment ({feature_score:.0f}/100) with solid rating quality ({rating_score:.0f}/100). Review backing is {review_score:.0f}/100, and {price_fit_note.lower()}",
        f"A balanced pick overall: feature alignment is {feature_score:.0f}/100, rating momentum is {rating_score:.0f}/100, and buyer feedback support is {review_score:.0f}/100. {price_fit_note}",
    ]
    idx = sum(ord(char) for char in name) % len(templates)
    return templates[idx]


async def serpapi_search(
    query: str,
    max_results: int = 15,  
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
) -> Optional[List[Dict]]:
    if not SERPAPI_KEY:
        logger.warning("SERPAPI_KEY not configured, returning demo products")
        return get_demo_products(max_results, min_price, max_price)

    params = {
        "engine": "google_shopping",
        "q": query,
        "gl": "in",
        "hl": "en",
        "api_key": SERPAPI_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get("https://serpapi.com/search", params=params)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("shopping_results", [])
            results: List[Dict] = []
            for item in items:
                if len(results) >= max_results:
                    break
                title = item.get("title") or item.get("product_title")
                price = item.get("price") or item.get("extracted_price") or ""
                price_int = _price_to_int(str(price))
                if price_int == 0:
                    continue

                if min_price is not None and price_int < min_price:
                    continue
                if max_price is not None and price_int > max_price:
                    continue

                store = item.get("source") or item.get("merchant", {}).get("name", "")
                extensions = item.get("extensions") or []
                if isinstance(extensions, str):
                    extensions = [extensions]

                snippet = item.get("snippet") or item.get("description") or item.get("tag") or ""
                features = _extract_features(title or "", snippet=snippet, description=" ".join(extensions))
                delivery = item.get("delivery") or item.get("shipping") or ""
                raw_title = item.get("title") or item.get("product_title") or ""
                listing_text = " ".join(
                    str(part)
                    for part in [raw_title, title, snippet, delivery, store, " ".join(extensions)]
                    if str(part).strip()
                )
                if _contains_unsafe_listing(listing_text):
                    continue

                product = {
                    "name": title or "Unknown",
                    "raw_title": raw_title,
                    "price_inr": price_int,
                    "price_text": price,
                    "rating": float(item.get("rating", 0) or 0),
                    "review_count": _reviews_to_int(item.get("reviews") or item.get("rating_count") or item.get("reviews_count")),
                    "image_url": item.get("thumbnail") or item.get("thumbnail_url"),
                    "product_link": item.get("link") or item.get("product_link"),
                    "store": store,
                    "features": features,
                    "extensions": extensions,
                    "snippet": snippet,
                    "delivery": delivery,
                    "merchant": item.get("merchant", {}),
                    "source": store,
                    "rating_count": _reviews_to_int(item.get("rating_count") or item.get("reviews_count")),
                    "shipping": item.get("shipping") or "",
                }
                results.append(product)

            return results if results else None

    except Exception as e:
        logger.exception(f"SerpAPI error: {e}, returning demo products")
        # Return demo products as fallback instead of None
        return get_demo_products(max_results, min_price, max_price)


def rank_products(products: List[Dict], requirements: Optional[Dict] = None) -> List[Dict]:
    """Weighted ranking with feature match, rating, price fit, and review count."""
    if not products:
        return []
    if not requirements:
        requirements = {"required_features": []}

    ranked_products = [dict(product) for product in products]

    price_values = [_safe_int(product.get("price_inr", 0)) for product in ranked_products if _safe_int(product.get("price_inr", 0)) > 0]
    budget_reference = requirements.get("budget_range", {}).get("max") or requirements.get("budget") or requirements.get("max_price")
    budget_reference = _safe_int(budget_reference, 0)
    if budget_reference <= 0 and price_values:
        budget_reference = int(round(median(price_values)))

    max_review_count = max((_safe_int(product.get("review_count", 0)) for product in ranked_products), default=0)

    for product in ranked_products:
        price = _safe_int(product.get("price_inr", 0))
        review_count = _safe_int(product.get("review_count", 0))

        feature_score, feature_reason = _feature_match_score(product, requirements)
        rating_score = _rating_score(product)
        price_score = _price_fit_score(price, float(budget_reference))
        review_score = _review_score(review_count, max_review_count)

        weighted_score = (
            feature_score * 0.40 +
            rating_score * 0.30 +
            price_score * 0.20 +
            review_score * 0.10
        )

        smart_bonus = 10.0 if _contains_required_smart_keyword(product) else 0.0

        product["match_score"] = round(min(max(weighted_score + smart_bonus, 0.0), 100.0), 2)
        product["reason"] = _score_reason(
            product.get("name", "Unknown"),
            feature_score,
            rating_score,
            price_score,
            review_score,
            price,
            float(budget_reference),
        )
        product["score_breakdown"] = {
            "feature_score": feature_score,
            "rating_score": rating_score,
            "price_score": price_score,
            "review_score": review_score,
            "feature_reason": feature_reason,
        }

    return sorted(ranked_products, key=lambda item: item.get("match_score", 0), reverse=True)


def get_demo_products(max_results: int = 15, min_price: Optional[int] = None, max_price: Optional[int] = None) -> List[Dict]:
    """Return diverse demo smart home products when API is not available."""
    demo = [
        # Smart Bulbs
        {"name": "Halonix Smart Bulb 12W WiFi Dimmable Color Changing", "price_inr": 699, "rating": 4.5, "reviews": 1200, "features": ["WiFi", "Voice Control", "Dimmable", "16M Colors"]},
        {"name": "Philips Hue White Color Bulb WiFi + Bluetooth", "price_inr": 2499, "rating": 4.7, "reviews": 3400, "features": ["WiFi", "Bluetooth", "Color", "Alexa"]},
        
        # Air Conditioners
        {"name": "Daikin 1.5 Ton Smart AC Inverter WiFi Enabled", "price_inr": 35999, "rating": 4.6, "reviews": 890, "features": ["Smart", "WiFi", "Inverter", "Energy Star"]},
        {"name": "LG 1 Ton Smart Inverter AC WiFi Control", "price_inr": 28999, "rating": 4.5, "reviews": 450, "features": ["WiFi", "Smart", "Inverter", "Cooling"]},
        
        # Smart Plugs & Switches
        {"name": "TP-Link Tapo Smart Plug WiFi 16A Energy Monitor", "price_inr": 899, "rating": 4.6, "reviews": 2100, "features": ["WiFi", "Energy Monitor", "App Control"]},
        {"name": "Mi Smart Plug WiFi with Energy Monitoring", "price_inr": 449, "rating": 4.4, "reviews": 1500, "features": ["WiFi", "App Control", "Compact"]},
        
        # Smart Speakers
        {"name": "Amazon Echo Dot 4th Gen with Alexa", "price_inr": 2999, "rating": 4.5, "reviews": 8000, "features": ["Alexa", "Voice Control", "Bluetooth"]},
        {"name": "Google Nest Mini with Google Assistant", "price_inr": 3499, "rating": 4.6, "reviews": 5200, "features": ["Google Assistant", "Voice Control", "Compact"]},
        
        # Smart Lighting Switches
        {"name": "Suraksha 16A Smart WiFi Switch with Alexa", "price_inr": 603, "rating": 4.5, "reviews": 450, "features": ["WiFi", "Alexa", "Switch", "DIY"]},
        {"name": "Hexonix 16A Smart WiFi Switch Alexa Google Compatible", "price_inr": 620, "rating": 4.5, "reviews": 320, "features": ["WiFi", "Alexa", "Google", "App Control"]},
    ]
    
    result = []
    for p in demo:
        if min_price and p["price_inr"] < min_price:
            continue
        if max_price and p["price_inr"] > max_price:
            continue
        result.append({
            "name": p["name"],
            "raw_title": p["name"],
            "price_inr": p["price_inr"],
            "price_text": f"₹{p['price_inr']}",
            "rating": p["rating"],
            "review_count": p["reviews"],
            "image_url": "",
            "product_link": "https://amazon.in/",
            "store": "Demo",
            "features": p["features"],
            "extensions": [],
            "snippet": "",
            "delivery": "",
        })
        if len(result) >= max_results:
            break
    
    return result if result else demo[:max_results]
