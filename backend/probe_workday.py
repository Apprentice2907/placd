import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        # Netflix
        try:
            r = await client.post('https://netflix.wd1.myworkdayjobs.com/wday/cxs/netflix/Netflix/jobs', json={'appliedFacets':{},'limit':1,'offset':0,'searchText':''}, headers=headers)
            print("Netflix:", r.status_code)
        except Exception as e: print(e)
        
        # Databricks
        try:
            r = await client.post('https://databricks.wd1.myworkdayjobs.com/wday/cxs/databricks/databricks/jobs', json={'appliedFacets':{},'limit':1,'offset':0,'searchText':''}, headers=headers)
            print("Databricks:", r.status_code)
        except Exception as e: print(e)
        
        # Snowflake
        try:
            r = await client.post('https://snowflake.wd1.myworkdayjobs.com/wday/cxs/snowflake/Careers/jobs', json={'appliedFacets':{},'limit':1,'offset':0,'searchText':''}, headers=headers)
            print("Snowflake:", r.status_code)
        except Exception as e: print(e)

if __name__ == "__main__":
    asyncio.run(main())
