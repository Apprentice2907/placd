import asyncio
from db.connection import AsyncSessionLocal

from sqlalchemy import text
from scrapers.amazon.adapter import scrape_amazon_jobs

async def main():
    print("Scraping Amazon Internships...")
    jobs = await scrape_amazon_jobs("Intern", "")
    print(f"Fetched {len(jobs)} internships from Amazon!")
    
    if jobs:
        async with AsyncSessionLocal() as session:
            query = text("""
                INSERT INTO jobs (
                    external_id, title, description, apply_url, source, 
                    job_type, location, is_remote, status, url_hash
                ) VALUES (
                    :external_id, :title, :description, :apply_url, :source,
                    'internship', :location, :is_remote, 'active', :url_hash
                )
                ON CONFLICT (url_hash) DO NOTHING
            """)
            
            params = []
            for j in jobs:
                url_hash = str(hash(j['apply_url']))
                params.append({
                    "external_id": j['external_job_id'],
                    "title": j['title'],
                    "description": j['description'],
                    "apply_url": j['apply_url'],
                    "source": j['source'],
                    "location": j['location'],
                    "is_remote": False,
                    "url_hash": url_hash
                })
                
            await session.execute(query, params)
            await session.commit()
            print(f"Inserted {len(jobs)} internships into DB.")

if __name__ == "__main__":
    asyncio.run(main())
