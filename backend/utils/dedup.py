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
    """
    from db.database import get_connection, merge_jobs, init_db
    import logging
    from rich.console import Console

    console = Console()
    init_db()
    conn = get_connection()
    
    # We only want to deduplicate jobs that are currently considered canonical
    rows = conn.execute("SELECT id, title, company, location, fingerprint_hash, source_priority, length(description) as desc_len FROM jobs WHERE canonical_job_id IS NULL ORDER BY source_priority DESC, desc_len DESC").fetchall()
    conn.close()
    
    jobs = [dict(row) for row in rows]
    
    # Block by normalized company name
    company_blocks = {}
    for j in jobs:
        nc = normalize_company(j['company'])
        if nc not in company_blocks:
            company_blocks[nc] = []
        company_blocks[nc].append(j)
        
    merged_count = 0
    
    for nc, block in company_blocks.items():
        if len(block) < 2:
            continue
            
        # Compare every pair in the block.
        # Since we sorted by priority DESC, the first item in a duplicate pair 
        # should become the canonical one.
        canonicals = [] # List of jobs that have been established as canonical in this block
        
        for job in block:
            is_dup = False
            for canon in canonicals:
                # First check exact fingerprint
                if job['fingerprint_hash'] == canon['fingerprint_hash']:
                    is_dup = True
                # Next check fuzzy
                elif is_fuzzy_duplicate(job['title'], canon['title']):
                    # Check location fuzzy (or just exact normalized match)
                    if normalize_location(job['location']) == normalize_location(canon['location']):
                        is_dup = True
                        
                if is_dup:
                    # Merge job into canon
                    merge_jobs(canonical_id=canon['id'], duplicate_id=job['id'])
                    merged_count += 1
                    break
            
            if not is_dup:
                canonicals.append(job)
                
    console.print(f"[bold green]Batch Deduplication Complete: Merged {merged_count} jobs![/bold green]")
    return merged_count
