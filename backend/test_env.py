from dotenv import load_dotenv
import os

load_dotenv()

groq_key = os.getenv('GROQ_API_KEY')
serpapi_key = os.getenv('SERPAPI_KEY')

print(f"GROQ_API_KEY loaded: {bool(groq_key)}")
print(f"GROQ_API_KEY length: {len(groq_key) if groq_key else 0}")
print(f"GROQ_API_KEY starts with: {groq_key[:15] if groq_key else 'None'}...")
print(f"\nSERPAPI_KEY loaded: {bool(serpapi_key)}")
print(f"SERPAPI_KEY length: {len(serpapi_key) if serpapi_key else 0}")
