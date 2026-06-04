import sys
import asyncio
import os

# Add backend to path so we can import properly when run from anywhere
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from discovery import enumerator
from discovery import public_lists
from db.connection import AsyncSessionLocal
from sqlalchemy import text

async def main():
    print("Starting full discovery run...")
    platforms = ["greenhouse", "lever", "ashby", "workday", "bamboohr", "recruitee"]
    
    # Run them sequentially to avoid rate limiting
    for p in platforms:
        await enumerator.discover_platform(p)
        await asyncio.sleep(2)
        
    print("Running public lists...")
    await public_lists.run_public_lists()
    
    # Load seeds too
    print("Loading seeds...")
    from discovery.seed_lists import ALL_SEED_LISTS
    seeds = []
    for lst in ALL_SEED_LISTS:
        for comp in lst:
            seeds.append({
                "name": comp["name"],
                "ats_type": comp["ats_type"],
                "ats_slug": comp["ats_slug"],
                "source": "seed_list"
            })
    await enumerator.save_companies_batch(seeds)
    
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("""
            SELECT platform, COUNT(*) FROM discovered_companies GROUP BY platform
        """))
        print("\n--- Discovery Totals ---")
        for row in res.fetchall():
            print(f"Discovered {row[1]} {row[0].capitalize()} slugs")
            
    print("\nDiscovery run complete!")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
