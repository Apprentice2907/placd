from dotenv import load_dotenv

load_dotenv()

import asyncio
import asyncpg
import os

async def run():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    
    with open('db/migrations/014_resume_builder_enhancements.sql', 'r') as f:
        sql = f.read()
        
    await conn.execute(sql)
    print("Migration applied successfully!")
    await conn.close()

asyncio.run(run())
