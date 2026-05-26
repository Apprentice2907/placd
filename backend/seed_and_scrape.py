import asyncio
from sqlalchemy import text
from db.connection import AsyncSessionLocal
from workers.crawlers import crawl_company_task

async def trigger_scrape():
    async with AsyncSessionLocal() as session:
        # Check if Figma exists
        res = await session.execute(text("SELECT id FROM companies WHERE domain = 'figma.com'"))
        company = res.fetchone()
        if not company:
            print("Seeding Figma...")
            insert_query = text("""
                INSERT INTO companies (name, domain, ats_type, ats_slug, careers_url, size_tier, country)
                VALUES ('Figma', 'figma.com', 'greenhouse', 'figma', 'https://figma.com/careers', 'enterprise', 'US')
                RETURNING id
            """)
            res = await session.execute(insert_query)
            company_id = str(res.scalar())
            await session.commit()
            print(f"Inserted Figma with ID {company_id}")
        else:
            company_id = str(company[0])

        print(f"Queueing scrape task for figma with ID {company_id}...")
        crawl_company_task.apply_async(args=[company_id], queue='crawl')

if __name__ == "__main__":
    asyncio.run(trigger_scrape())
