import asyncio
import json
from base64 import b64encode
import os
import sys

from backend.app.ai_service import generate_advanced_recommendations
from backend.app.models import AdvancedAdvisorResponse

async def debug_call():
    products = [{"name": "Halonix 12W Smart Bulb", "price_inr": 800, "rating": 4.2}]
    res = await generate_advanced_recommendations("I want a budget smart bulb", products)
    print("Result:", res)

if __name__ == "__main__":
    
    # insert path to Python can resolve it
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))
    
    asyncio.run(debug_call())
