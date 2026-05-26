import asyncio
import json
import os
import sys

from db.connection import AsyncSessionLocal
from sqlalchemy import text
from datetime import datetime

async def seed_calendar():
    seed_file = os.path.join(os.path.dirname(__file__), 'calendar_seed.json')
    if not os.path.exists(seed_file):
        print(f"Seed file not found: {seed_file}")
        return

    with open(seed_file, 'r') as f:
        data = json.load(f)

    print(f"Seeding {len(data)} calendar events...")

    async with AsyncSessionLocal() as session:
        for item in data:
            dt = datetime.strptime(item['event_date'], '%Y-%m-%d').date()
            year = dt.year
            
            # Simple check if exists
            check_sql = """
                SELECT 1 FROM company_hiring_windows 
                WHERE company_name = :company_name 
                AND window_type = :window_type 
                AND event_date = :event_date
            """
            result = await session.execute(text(check_sql), {
                "company_name": item['company'],
                "window_type": item['window_type'],
                "event_date": dt
            })
            exists = result.scalar()
            
            if not exists:
                insert_sql = """
                    INSERT INTO company_hiring_windows (
                        company_name, category, event_date, window_type, 
                        year, source_url, notes, verified
                    ) VALUES (
                        :company_name, :category, :event_date, :window_type, 
                        :year, :source_url, :notes, :verified
                    )
                """
                await session.execute(text(insert_sql), {
                    "company_name": item['company'],
                    "category": item.get('category'),
                    "event_date": dt,
                    "window_type": item['window_type'],
                    "year": year,
                    "source_url": item.get('source_url'),
                    "notes": item.get('notes'),
                    "verified": item.get('verified', False)
                })
                print(f"Inserted: {item['company']} {item['window_type']} on {item['event_date']}")
            else:
                print(f"Skipped (already exists): {item['company']} {item['window_type']} on {item['event_date']}")
                
        await session.commit()
    print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_calendar())
