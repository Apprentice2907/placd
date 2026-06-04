import asyncio
from sqlalchemy import text
from db.connection import AsyncSessionLocal

async def run_migration():
    async with AsyncSessionLocal() as session:
        await session.execute(text('''
            CREATE TABLE IF NOT EXISTS profiles (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id TEXT NOT NULL UNIQUE,
                full_name TEXT,
                email TEXT,
                phone TEXT,
                location TEXT,
                linkedin_url TEXT,
                github_url TEXT,
                portfolio_url TEXT,
                professional_summary TEXT,
                education JSONB,
                experiences JSONB,
                projects JSONB,
                skills JSONB,
                certifications JSONB,
                achievements JSONB,
                languages JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        '''))
        
        await session.commit()
        print('Profiles table created successfully!')

if __name__ == '__main__':
    asyncio.run(run_migration())
