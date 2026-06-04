"""
Tag Audit Script
================
Verifies the distribution of job tags in the database.
Run after deploying migration 011 and backfill_tags.py.

    python backend/scripts/audit_tags.py

Expected healthy ranges:
  FAANG        3 – 8%
  Remote      15 – 35%
  Hybrid       5 – 20%
  Internships  5 – 15%
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure backend/ is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import AsyncSessionLocal
from sqlalchemy import text


async def audit():
    async with AsyncSessionLocal() as db:
        def q(sql: str) -> int:
            return db.execute(text(sql))

        total_res    = await db.execute(text("SELECT COUNT(*) FROM jobs WHERE status = 'active'"))
        faang_res    = await db.execute(text("SELECT COUNT(*) FROM jobs WHERE status = 'active' AND is_faang = TRUE"))
        remote_res   = await db.execute(text("SELECT COUNT(*) FROM jobs WHERE status = 'active' AND is_remote = TRUE"))
        hybrid_res   = await db.execute(text("SELECT COUNT(*) FROM jobs WHERE status = 'active' AND is_hybrid = TRUE"))
        onsite_res   = await db.execute(text("SELECT COUNT(*) FROM jobs WHERE status = 'active' AND work_mode = 'onsite'"))
        intern_res   = await db.execute(text("SELECT COUNT(*) FROM jobs WHERE status = 'active' AND is_internship = TRUE"))
        untagged_res = await db.execute(text("SELECT COUNT(*) FROM jobs WHERE status = 'active' AND work_mode IS NULL"))

        total    = total_res.scalar()    or 0
        faang    = faang_res.scalar()    or 0
        remote   = remote_res.scalar()   or 0
        hybrid   = hybrid_res.scalar()   or 0
        onsite   = onsite_res.scalar()   or 0
        intern   = intern_res.scalar()   or 0
        untagged = untagged_res.scalar() or 0

    def pct(n: int) -> str:
        if total == 0:
            return "N/A"
        return f"{n / total * 100:.1f}%"

    W = 48
    print(f"\n{'-' * W}")
    print(f"  TAG AUDIT REPORT")
    print(f"{'-' * W}")
    print(f"  Total active jobs : {total:>10,}")
    print(f"{'-' * W}")
    print(f"  FAANG             : {faang:>10,}  ({pct(faang):<6})  [target: 3-8%]")
    print(f"  Remote            : {remote:>10,}  ({pct(remote):<6})  [target: 15-35%]")
    print(f"  Hybrid            : {hybrid:>10,}  ({pct(hybrid):<6})  [target: 5-20%]")
    print(f"  Onsite            : {onsite:>10,}  ({pct(onsite):<6})")
    print(f"  Internships       : {intern:>10,}  ({pct(intern):<6})  [target: 5-15%]")
    print(f"  Untagged (NULL)   : {untagged:>10,}")
    print(f"{'-' * W}")

    # Sanity warnings
    issues = []
    if total > 0:
        if faang / total < 0.01:
            issues.append("! FAANG < 1% - is_faang tagger may be broken")
        if faang / total > 0.20:
            issues.append("! FAANG > 20% - FAANG_CANONICAL list too broad")
        if remote / total < 0.05:
            issues.append("! Remote < 5% - classify_work_mode may not be running")
        if remote / total > 0.60:
            issues.append("! Remote > 60% - remote detection too aggressive")
        if intern / total < 0.01 and total > 500:
            issues.append("! Internships < 1% - is_internship tagger may be broken")
        if untagged > 0:
            issues.append(f"! {untagged:,} jobs have NULL work_mode - run backfill_tags.py")

    if issues:
        print(f"\n  ISSUES DETECTED:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print(f"\n  OK: All tag distributions look healthy.\n")

    print()


if __name__ == "__main__":
    asyncio.run(audit())
