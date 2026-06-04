"""
Tag Backfill Script
===================
Re-tags all existing active jobs in the database using the current
job_tagger.py logic (is_faang, work_mode, is_remote, is_hybrid, is_internship).

Run this once after deploying migration 011_job_tags.sql:

    python backend/scripts/backfill_tags.py

Process jobs in batches of 500 to avoid memory spikes.
Estimated time: ~1–2 minutes per 100k jobs.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import AsyncSessionLocal
from sqlalchemy import text
from utils.job_tagger import tag_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BATCH_SIZE = 500


async def backfill():
    log.info("Starting tag backfill...")
    total_updated = 0
    offset = 0

    while True:
        async with AsyncSessionLocal() as session:
            rows = (await session.execute(
                text("""
                    SELECT 
                        j.id, j.title, c.name as company, j.location, 
                        j.description, j.job_type 
                    FROM jobs j
                    LEFT JOIN companies c ON j.company_id = c.id
                    WHERE j.status = 'active' 
                    ORDER BY j.created_at DESC 
                    LIMIT :lim OFFSET :off
                """),
                {"lim": BATCH_SIZE, "off": offset}
            )).fetchall()

            if not rows:
                break

            updates = []
            for row in rows:
                job = dict(row._mapping)
                tag_job(job)
                updates.append({
                    "id":            str(job["id"]),
                    "is_faang":      job["is_faang"],
                    "is_internship": job["is_internship"],
                    "is_remote":     job["is_remote"],
                    "is_hybrid":     job["is_hybrid"],
                    "work_mode":     job["work_mode"],
                })

            # Batch update
            for upd in updates:
                await session.execute(
                    text("""
                        UPDATE jobs SET
                            is_faang      = :is_faang,
                            is_internship = :is_internship,
                            is_remote     = :is_remote,
                            is_hybrid     = :is_hybrid,
                            work_mode     = :work_mode
                        WHERE id = :id
                    """),
                    upd
                )

            await session.commit()

        total_updated += len(rows)
        offset += BATCH_SIZE
        log.info(f"  Backfilled {total_updated:,} jobs...")

        if len(rows) < BATCH_SIZE:
            break

    log.info(f"✅ Backfill complete — {total_updated:,} jobs re-tagged.")


if __name__ == "__main__":
    asyncio.run(backfill())
