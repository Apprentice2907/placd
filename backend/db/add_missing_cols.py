import asyncio
from sqlalchemy import text
from db.connection import engine

async def add_cols():
    queries = [
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS trust_score FLOAT DEFAULT 0.0;",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_spam BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS spam_reason TEXT;",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS company_tier INTEGER DEFAULT 3;",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_faang BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_internship BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_hybrid BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS work_mode TEXT;",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_student_eligible BOOLEAN DEFAULT FALSE;"
    ]
    async with engine.connect() as conn:
        for q in queries:
            try:
                await conn.execute(text(q))
                await conn.commit()
                print(f"Executed: {q}")
            except Exception as e:
                print(f"Error executing {q}: {e}")
                await conn.rollback()

if __name__ == "__main__":
    asyncio.run(add_cols())
