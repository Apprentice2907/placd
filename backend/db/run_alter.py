import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://neondb_owner:npg_Ki9wP2nSAkzs@ep-orange-cake-at8squfa.c-9.us-east-1.aws.neon.tech/neondb")
    with open("db/alter.sql", "r") as f:
        sql = f.read()
    await conn.execute(sql)
    await conn.close()
    print("SQL executed successfully")

asyncio.run(main())
