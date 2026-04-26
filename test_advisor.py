import asyncio
import httpx
import json

async def main():
    payload = {"query": "I want a budget smart bulb"}
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://127.0.0.1:8000/advisor", json=payload, timeout=30.0)
        print("Status Code:", resp.status_code)
        try:
            data = resp.json()
            print("Response:", json.dumps(data, indent=2))
        except Exception as e:
            print("Failed to decode JSON:", e)
            print("Raw Content:", resp.text)

if __name__ == "__main__":
    asyncio.run(main())
