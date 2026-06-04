import asyncio
import sys
from pathlib import Path

# Add backend dir to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from db.connection import AsyncSessionLocal

async def seed():
    async with AsyncSessionLocal() as session:
        # 1. Scholarship
        await session.execute(text("""
            INSERT INTO opportunities 
            (source_url, title, description, opportunity_type, funding_type, country, organization, deadline, source_name, status, first_seen_at, url_hash) 
            VALUES 
            ('https://example.com/oxford', 'Clarendon Fund Scholarships', 'The Clarendon Fund offers fully-funded scholarships at the University of Oxford for outstanding graduate students from all around the world.', 'scholarship', 'fully_funded', 'United Kingdom', 'University of Oxford', '2026-10-15', 'OpportunitiesCorners', 'active', NOW(), 'hash1')
            ON CONFLICT (url_hash) DO NOTHING;
        """))
        
        # 2. Fellowship
        await session.execute(text("""
            INSERT INTO opportunities 
            (source_url, title, description, opportunity_type, funding_type, country, organization, deadline, source_name, status, first_seen_at, url_hash) 
            VALUES 
            ('https://example.com/schmidt', 'Schmidt Science Fellows', 'A post-doctoral fellowship for scientists wanting to pivot into a new discipline.', 'fellowship', 'fully_funded', 'Global', 'Schmidt Futures', '2026-06-01', 'OpportunitiesCircle', 'active', NOW(), 'hash2')
            ON CONFLICT (url_hash) DO NOTHING;
        """))
        
        # 3. Exchange Program
        await session.execute(text("""
            INSERT INTO opportunities 
            (source_url, title, description, opportunity_type, funding_type, country, organization, deadline, source_name, status, first_seen_at, url_hash) 
            VALUES 
            ('https://example.com/fulbright', 'Fulbright Foreign Student Program', 'Enables graduate students, young professionals and artists from abroad to study and conduct research in the United States.', 'exchange_program', 'fully_funded', 'United States', 'US Department of State', '2026-05-30', 'OpportunitiesCorners', 'active', NOW(), 'hash3')
            ON CONFLICT (url_hash) DO NOTHING;
        """))

        # 4. Internship
        await session.execute(text("""
            INSERT INTO opportunities 
            (source_url, title, description, opportunity_type, funding_type, country, organization, deadline, source_name, status, first_seen_at, url_hash) 
            VALUES 
            ('https://example.com/cern', 'CERN Technical Student Programme', 'If you are an undergraduate or Master student in applied physics, engineering or computing, this is your chance to spend 4 to 12 months at CERN.', 'internship', 'paid', 'Switzerland', 'CERN', '2026-06-15', 'OpportunitiesCircle', 'active', NOW(), 'hash4')
            ON CONFLICT (url_hash) DO NOTHING;
        """))

        # 5. Conference
        await session.execute(text("""
            INSERT INTO opportunities 
            (source_url, title, description, opportunity_type, funding_type, country, organization, deadline, source_name, status, first_seen_at, url_hash) 
            VALUES 
            ('https://example.com/oneyoungworld', 'One Young World Summit 2026', 'The annual One Young World Summit convenes the brightest young talent from every country and sector.', 'conference', 'partially_funded', 'Japan', 'One Young World', '2026-05-28', 'OpportunitiesCorners', 'active', NOW(), 'hash5')
            ON CONFLICT (url_hash) DO NOTHING;
        """))

        await session.commit()
        print("Successfully seeded 5 sample opportunities!")

if __name__ == "__main__":
    asyncio.run(seed())
