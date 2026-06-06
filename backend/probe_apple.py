import asyncio
import httpx

async def test():
    url = "https://jobs.apple.com/api/v1/jobDetails/search"
    payload = {
        "query": "",
        "filters": {"locations": {"location": [{"locationNodeId": "1/1", "type": "0"}]}},
        "page": 1
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Test POST
        r = await client.post(url, json=payload, headers=headers)
        print("Apple POST:", r.status_code)
        
        # Test GET
        r = await client.get(url, params={"page": 1}, headers=headers)
        print("Apple GET:", r.status_code)

if __name__ == "__main__":
    asyncio.run(test())
