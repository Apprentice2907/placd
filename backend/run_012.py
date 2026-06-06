import asyncio
from pathlib import Path
from sqlalchemy import text
from db.connection import engine

async def run():
    sql = Path('db/migrations/012_student_eligible.sql').read_text()
    async with engine.begin() as conn:
        await conn.execute(text(sql))
    print('Migration 012 done')

if __name__ == '__main__':
    asyncio.run(run())
