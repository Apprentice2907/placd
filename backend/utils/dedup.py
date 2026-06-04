import sys
import os
"""
Placd — Deduplication & Normalization Module
Handles normalizing job metadata, generating deterministic fingerprints,
and fuzzy matching duplicate jobs.
"""

import hashlib
import re
from rapidfuzz import fuzz

def normalize_title(title: str) -> str:
    """Normalize job title for fingerprinting and fuzzy matching."""
    if not title:
        return ""
    # Lowercase and strip
    t = title.lower().strip()
    # Remove common extra labels like "(Remote)", " - India", etc.
    t = re.sub(r'\(.*?\)', '', t)
    t = re.sub(r'\[.*?\]', '', t)
    # Remove some common punctuation
    t = re.sub(r'[^\w\s]', ' ', t)
    # Collapse whitespace
    t = re.sub(r'\s+', ' ', t)
    # Standardize common terms
    t = t.replace("sr ", "senior ")
    t = t.replace("jr ", "junior ")
    return t.strip()

def normalize_company(company: str) -> str:
    """Normalize company name to group branches/legal entities."""
    if not company:
        return ""
    c = company.lower().strip()
    # Remove non-alphanumeric except spaces
    c = re.sub(r'[^\w\s]', '', c)
    # Strip common corporate suffixes
    suffixes = [
        r'\binc\b', r'\bllc\b', r'\bltd\b', r'\blimited\b',
        r'\bpvt\b', r'\bprivate\b', r'\bcorp\b', r'\bcorporation\b'
    ]
    for suffix in suffixes:
        c = re.sub(suffix, '', c)
    # Collapse whitespace
    c = re.sub(r'\s+', ' ', c)
    return c.strip()

def normalize_location(location: str) -> str:
    """Normalize location strings."""
    if not location:
        return ""
    loc = location.lower().strip()
    # If it contains remote, wfh, etc, just map to "remote"
    if any(x in loc for x in ("remote", "work from home", "wfh")):
        return "remote"
        
    # Remove non-alphanumeric except spaces
    loc = re.sub(r'[^\w\s]', '', loc)
    
    # Common mappings
    mapping = {
        "bangalore": "bengaluru",
        "gurugram": "gurgaon",
        "ncr": "delhi ncr",
        "new delhi": "delhi"
    }
    for old, new in mapping.items():
        loc = loc.replace(old, new)
        
    # Collapse whitespace
    loc = re.sub(r'\s+', ' ', loc)
    return loc.strip()

def generate_fingerprint(title: str, company: str, location: str) -> str:
    """
    Generate a deterministic SHA-256 fingerprint for a job.
    Uses normalized fields to group exact matches.
    """
    nt = normalize_title(title)
    nc = normalize_company(company)
    nl = normalize_location(location)
    
    # We combine them with a pipe separator
    raw = f"{nt}|{nc}|{nl}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def is_fuzzy_duplicate(title1: str, title2: str, threshold: float = 85.0) -> bool:
    """
    Check if two titles are fuzzy duplicates using RapidFuzz.
    We assume the company is already an exact (normalized) match before calling this,
    to avoid O(N^2) global checks.
    """
    t1 = normalize_title(title1)
    t2 = normalize_title(title2)
    
    if not t1 or not t2:
        return False
        
    # token_sort_ratio ignores word order ("Python Developer" vs "Developer Python")
    score = fuzz.token_sort_ratio(t1, t2)
    return score >= threshold

def run_batch_dedup():
    """
    Periodic cleanup pipeline.
    Finds fuzzy duplicates across the entire database, grouped by normalized company name
    to prevent O(N^2) global comparisons.
    Uses async PostgreSQL via db.connection.
    """
    import asyncio
    import logging
    from rich.console import Console
    from sqlalchemy import text as sa_text
    from db.connection import AsyncSessionLocal

    console = Console()

    async def _run():
        async with AsyncSessionLocal() as session:
            # Fetch all canonical jobs
            res = await session.execute(sa_text(
                "SELECT id, title, source, location FROM jobs WHERE status = 'active' ORDER BY created_at DESC"
            ))
            rows = res.fetchall()

        jobs = [dict(r._mapping) for r in rows]

        # Block by normalized company name
        company_blocks = {}
        for j in jobs:
            nc = normalize_company(j.get('source', ''))
            if nc not in company_blocks:
                company_blocks[nc] = []
            company_blocks[nc].append(j)

        merged_count = 0

        for nc, block in company_blocks.items():
            if len(block) < 2:
                continue

            canonicals = []
            for job in block:
                is_dup = False
                for canon in canonicals:
                    if is_fuzzy_duplicate(job.get('title', ''), canon.get('title', '')):
                        if normalize_location(job.get('location', '')) == normalize_location(canon.get('location', '')):
                            is_dup = True
                            break

                if not is_dup:
                    canonicals.append(job)
                else:
                    merged_count += 1

        console.print(f"[bold green]Batch Deduplication Complete: Found {merged_count} potential duplicates![/bold green]")
        return merged_count

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, _run()).result()
    else:
        return asyncio.run(_run())

