import asyncio
import asyncpg
import os

async def run():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_Ki9wP2nSAkzs@ep-orange-cake-at8squfa.c-9.us-east-1.aws.neon.tech/neondb')
    
    with open('db/migrations/014_resume_builder_enhancements.sql', 'r') as f:
        sql = f.read()
        
    await conn.execute(sql)
    print("Migration applied successfully!")
    await conn.close()

asyncio.run(run())
