import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

async def test():
    print(f"Testing Semantic Scholar connectivity with API Key: {api_key is not None}")
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {"query": "attention mechanisms", "limit": 1}
    headers = {"x-api-key": api_key} if api_key else {}
    
    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0, headers=headers) as client:
            print(f"Requesting {url}...")
            response = await client.get(url, params=params)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text[:100]}...")
    except Exception as e:
        print(f"Connection Failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test())
