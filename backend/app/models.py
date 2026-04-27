from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
import re as _re


# ==========================================
# 1. Models for Initial Search (Step 1)
# ==========================================

class AIAnalysis(BaseModel):
    product_category: Optional[str] = Field("", description="Detected product category")
    required_features: List[str] = Field(default_factory=list)
    brand: Optional[str] = Field(None, description="Preferred brand if mentioned")
    budget_range: Optional[Dict] = Field(None, description="Budget range as {min, max}")
    usage_scenario: Optional[str] = Field("", description="How user will use the product")
    buying_advice: Optional[str] = Field("", description="Short buying advice")
    ai_explanation: Optional[str] = Field("", description="Why these products are recommended")

    @validator("required_features", pre=True)
    def ensure_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @validator("budget_range", pre=True)
    def parse_budget(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            nums = _re.findall(r'\d+', v)
            if len(nums) >= 2:
                return {"min": int(nums[0]), "max": int(nums[1])}
            elif len(nums) == 1:
                return {"min": 0, "max": int(nums[0])}
            return None
        if isinstance(v, dict):
            return v
        return None

# ==========================================
# 2. Models for Advanced AI Phase (Step 2)
# ==========================================

class ParsedUserIntent(BaseModel):
    category: str = ""
    budget: Union[str, int, float] = "Flexible"
    room_size: str = ""
    preferences: List[str] = Field(default_factory=list)
    energy_efficiency: str = ""

    @validator("budget", pre=True)
    def validate_budget(cls, v):
        if v is None or (isinstance(v, (int, float)) and v != v):  # Handle None and NaN
            return "Flexible"
        return v

class Recommendation(BaseModel):
    name: str = ""
    price: Union[str, int, float] = 0.0
    match_score: Union[str, float] = 0.0
    reason: str = ""
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)

class AdvancedAdvisorResponse(BaseModel):
    parsed_user_intent: ParsedUserIntent = Field(default_factory=ParsedUserIntent)
    recommendations: List[Recommendation] = Field(default_factory=list)
    follow_up_question: str = ""

# --- New Advanced Comparison Models ---

class SideBySideAnalysis(BaseModel):
    name: str = ""
    verdict: str = ""
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)

class AdvancedComparisonResponse(BaseModel):
    comparison_summary: str = ""
    best_product_name: str = ""
    best_product_reason: str = ""
    side_by_side_analysis: List[SideBySideAnalysis] = Field(default_factory=list)
    overall_recommendation: str = ""



# ==========================================
# 3. Models for Frontend / Legacy Compatibility
# ==========================================

class Product(BaseModel):
    name: str
    price_inr: int
    rating: Optional[float] = None
    review_count: Optional[int] = None
    image_url: Optional[str] = None
    product_link: Optional[str] = None
    store: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    key_features: List[str] = Field(default_factory=list)
    match_score: Optional[float] = Field(None, description="Feature match score 0-100")
    ai_reason: Optional[str] = Field(None, description="AI explanation for why this product fits")
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)

class AdvisorResponse(BaseModel):
    # This structure is sent to the frontend
    ai_analysis: ParsedUserIntent
    recommended_products: List[Product] = Field(default_factory=list)
    best_overall_product: Optional[Product] = None
    best_overall_reason: Optional[str] = None
    follow_up_question: str = ""

class CompareRequest(BaseModel):
    products: List[Dict] = Field(..., min_length=2, max_length=6)

class CompareResponse(BaseModel):
    products: List[Product]
    comparison_summary: Optional[str] = None
    best_product: Optional[Product] = None
    best_product_reason: Optional[str] = None
    score_breakdown: List[Dict] = Field(default_factory=list)
