import asyncio
from workers.enricher import _enrich_job_async
from db.connection import AsyncSessionLocal
from sqlalchemy import text

async def run():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT id FROM jobs WHERE company_id = (SELECT id FROM companies WHERE name='Stripe' LIMIT 1) AND salary_min IS NULL LIMIT 3"))
        rows = result.fetchall()
    
    if not rows:
        print("No unenriched Stripe jobs found")
        return
        
    for row in rows:
        job_id = str(row[0])
        print(f"enriching {job_id}")
        await _enrich_job_async(job_id)
        await asyncio.sleep(6)
    
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT title, salary_min, salary_max, salary_currency FROM jobs WHERE id = :id"), {"id": job_id})
        row = res.fetchone()
        print(f"Result: {row}")

if __name__ == '__main__':
    asyncio.run(run())
