import asyncio
import uuid
from sqlalchemy import text
from db.connection import AsyncSessionLocal
from workers.crawlers import crawl_company_task

COMPANIES = [
    {"name": "Stripe", "domain": "stripe.com", "ats_type": "workday", "ats_slug": "stripe", "logo_url": "https://logo.clearbit.com/stripe.com", "size_tier": "enterprise"},
    {"name": "Airbnb", "domain": "airbnb.com", "ats_type": "greenhouse", "ats_slug": "airbnb", "logo_url": "https://logo.clearbit.com/airbnb.com", "size_tier": "enterprise"},
    {"name": "Vercel", "domain": "vercel.com", "ats_type": "greenhouse", "ats_slug": "vercel", "logo_url": "https://logo.clearbit.com/vercel.com", "size_tier": "startup"},
    {"name": "Notion", "domain": "notion.so", "ats_type": "greenhouse", "ats_slug": "notion", "logo_url": "https://logo.clearbit.com/notion.so", "size_tier": "startup"},
    {"name": "OpenAI", "domain": "openai.com", "ats_type": "greenhouse", "ats_slug": "openai", "logo_url": "https://logo.clearbit.com/openai.com", "size_tier": "enterprise"},
    {"name": "Anthropic", "domain": "anthropic.com", "ats_type": "greenhouse", "ats_slug": "anthropic", "logo_url": "https://logo.clearbit.com/anthropic.com", "size_tier": "startup"},
    {"name": "Dropbox", "domain": "dropbox.com", "ats_type": "greenhouse", "ats_slug": "dropbox", "logo_url": "https://logo.clearbit.com/dropbox.com", "size_tier": "enterprise"},
    {"name": "Plaid", "domain": "plaid.com", "ats_type": "greenhouse", "ats_slug": "plaid", "logo_url": "https://logo.clearbit.com/plaid.com", "size_tier": "startup"},
    {"name": "Discord", "domain": "discord.com", "ats_type": "greenhouse", "ats_slug": "discord", "logo_url": "https://logo.clearbit.com/discord.com", "size_tier": "enterprise"},
    {"name": "Robinhood", "domain": "robinhood.com", "ats_type": "greenhouse", "ats_slug": "robinhood", "logo_url": "https://logo.clearbit.com/robinhood.com", "size_tier": "enterprise"},
    {"name": "Coinbase", "domain": "coinbase.com", "ats_type": "greenhouse", "ats_slug": "coinbase", "logo_url": "https://logo.clearbit.com/coinbase.com", "size_tier": "enterprise"},
    {"name": "Databricks", "domain": "databricks.com", "ats_type": "greenhouse", "ats_slug": "databricks", "logo_url": "https://logo.clearbit.com/databricks.com", "size_tier": "enterprise"},
    {"name": "Snowflake", "domain": "snowflake.com", "ats_type": "greenhouse", "ats_slug": "snowflake", "logo_url": "https://logo.clearbit.com/snowflake.com", "size_tier": "enterprise"},
]

async def seed():
    async with AsyncSessionLocal() as session:
        for comp in COMPANIES:
            # Check if exists
            res = await session.execute(text("SELECT id FROM companies WHERE domain = :domain"), {"domain": comp["domain"]})
            row = res.fetchone()
            
            if not row:
                comp_id = str(uuid.uuid4())
                await session.execute(text("""
                    INSERT INTO companies (id, name, domain, ats_type, ats_slug, logo_url, size_tier, country)
                    VALUES (:id, :name, :domain, :ats_type, :ats_slug, :logo_url, :size_tier, 'US')
                """), {
                    "id": comp_id,
                    "name": comp["name"],
                    "domain": comp["domain"],
                    "ats_type": comp["ats_type"],
                    "ats_slug": comp["ats_slug"],
                    "logo_url": comp["logo_url"],
                    "size_tier": comp["size_tier"]
                })
                print(f"Inserted {comp['name']}")
            else:
                comp_id = str(row.id)
                print(f"Skipped {comp['name']} (already exists)")
                
            # Queue Celery task for the company
            print(f"Queueing scrape task for {comp['name']}...")
            crawl_company_task.delay(comp_id)

        await session.commit()
        print("Done seeding and queueing!")

if __name__ == "__main__":
    asyncio.run(seed())
