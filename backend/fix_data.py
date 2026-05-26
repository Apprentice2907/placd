import asyncio
from sqlalchemy import text
from db.connection import AsyncSessionLocal

async def fix_data():
    async with AsyncSessionLocal() as session:
        # Update Figma's logo URL
        await session.execute(text("UPDATE companies SET logo_url = 'https://logo.clearbit.com/figma.com' WHERE domain = 'figma.com'"))
        
        # Link existing orphaned jobs to Figma
        await session.execute(text("""
            UPDATE jobs 
            SET company_id = (SELECT id FROM companies WHERE domain = 'figma.com') 
            WHERE company_id IS NULL
        """))
        
        await session.commit()
        print("Data fixed!")

if __name__ == "__main__":
    asyncio.run(fix_data())
