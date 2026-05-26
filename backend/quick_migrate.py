import asyncio
from sqlalchemy import text
from db.connection import AsyncSessionLocal

async def run_migration():
    async with AsyncSessionLocal() as session:
        # Add columns
        await session.execute(text('ALTER TABLE jobs ADD COLUMN IF NOT EXISTS application_open_date DATE;'))
        await session.execute(text('ALTER TABLE jobs ADD COLUMN IF NOT EXISTS application_close_date DATE;'))
        await session.execute(text('ALTER TABLE jobs ADD COLUMN IF NOT EXISTS hiring_cycle TEXT;'))
        
        # Create table
        await session.execute(text('''
            CREATE TABLE IF NOT EXISTS company_hiring_windows (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                company_name TEXT NOT NULL,
                company_slug TEXT,
                category TEXT,
                window_type TEXT,
                event_date DATE NOT NULL,
                year INTEGER,
                is_recurring BOOLEAN DEFAULT FALSE,
                recurrence_rule TEXT,
                source_url TEXT,
                notes TEXT,
                verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        '''))
        
        # Create indexes
        await session.execute(text('CREATE INDEX IF NOT EXISTS idx_company_hiring_windows_name ON company_hiring_windows(company_name);'))
        await session.execute(text('CREATE INDEX IF NOT EXISTS idx_company_hiring_windows_date ON company_hiring_windows(event_date);'))
        
        await session.commit()
        print('Migration applied successfully!')

if __name__ == '__main__':
    asyncio.run(run_migration())
