import os
from dotenv import load_dotenv

load_dotenv()

import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    with open("db/alter.sql", "r") as f:
        sql = f.read()
    await conn.execute(sql)
    await conn.close()
    print("SQL executed successfully")

asyncio.run(main())
