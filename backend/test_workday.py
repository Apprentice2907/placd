import asyncio
import httpx

async def run():
    async with httpx.AsyncClient() as client:
        r = await client.post('https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/nvidiaexternalcareersite/jobs', json={'appliedFacets':{},'limit':20,'offset':20,'searchText':''})
        data = r.json()
        print("Keys:", list(data.keys()))
        print("Total:", data.get('total'))

asyncio.run(run())
