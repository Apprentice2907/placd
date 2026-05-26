"""
Placd — Database Module
SQLite database with FTS5 full-text search for job listings.
"""

import sqlite3
from datetime import datetime
from typing import Optional

from utils.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """Create tables and FTS5 virtual table if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # ── Main jobs table ──────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            title          TEXT    NOT NULL,
            company        TEXT    NOT NULL,
            location       TEXT    DEFAULT '',
            job_type       TEXT    DEFAULT '',       -- full-time, internship, etc.
            salary         TEXT    DEFAULT '',
            description    TEXT    DEFAULT '',
            url            TEXT    UNIQUE NOT NULL,
            source         TEXT    NOT NULL,         -- google_jobs, internshala, naukri, amazon
            skills         TEXT    DEFAULT '',       -- comma-separated extracted skills
            match_score    REAL    DEFAULT 0.0,
            status         TEXT    DEFAULT 'new',    -- new, applied, rejected, interview, offer
            scraped_at     TEXT    NOT NULL,
            applied_at     TEXT    DEFAULT NULL,
            notes          TEXT    DEFAULT '',
            apply_url      TEXT    DEFAULT '',       -- direct application link
            hiring_status  TEXT    DEFAULT '',       -- actively hiring / closed / ''
            duration       TEXT    DEFAULT '',       -- internship duration e.g. '3 Months'
            experience     TEXT    DEFAULT '',       -- required experience e.g. '0-1 Yrs'
            posted_date    TEXT    DEFAULT '',       -- ISO date or relative string
            is_enriched    BOOLEAN DEFAULT 0,
            enrichment_timestamp TEXT DEFAULT NULL,
            last_seen_at   TEXT    DEFAULT NULL,
            source_priority INTEGER DEFAULT 0,
            is_remote      BOOLEAN DEFAULT 0,
            is_hybrid      BOOLEAN DEFAULT 0,
            is_fulltime    BOOLEAN DEFAULT 0,
            is_internship  BOOLEAN DEFAULT 0,
            is_fresher     BOOLEAN DEFAULT 0,
            fingerprint_hash TEXT DEFAULT '',
            canonical_job_id INTEGER DEFAULT NULL,
            merged_sources TEXT DEFAULT '',
            source_count   INTEGER DEFAULT 1,
            final_score    REAL DEFAULT 0.0,
            ranking_breakdown TEXT DEFAULT '{}',
            recency_score  REAL DEFAULT 0.0,
            posted_date_normalized TEXT DEFAULT NULL,
            company_tags   TEXT DEFAULT '',
            is_paid        INTEGER DEFAULT NULL,
            company_type   TEXT DEFAULT '',
            is_research    BOOLEAN DEFAULT 0,
            is_new_grad    BOOLEAN DEFAULT 0
        );
    """)

    # ── User Profile table ───────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1), -- Single-tenant architecture
            education_year INTEGER DEFAULT NULL,
            degree TEXT DEFAULT '',
            skills TEXT DEFAULT '',
            preferred_roles TEXT DEFAULT '',
            remote_preference BOOLEAN DEFAULT 0,
            expected_salary TEXT DEFAULT '',
            is_fresher_seeking BOOLEAN DEFAULT 0,
            is_internship_seeking BOOLEAN DEFAULT 0,
            updated_at TEXT DEFAULT NULL
        );
    """)

    # ── Source Health table ──────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS source_health (
            source TEXT PRIMARY KEY,
            last_successful_scrape TEXT DEFAULT NULL,
            jobs_added INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'unknown'
        );
    """)

    # ── Scraping State table ──────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scraping_state (
            source TEXT PRIMARY KEY,
            state_data TEXT DEFAULT '{}',
            updated_at TEXT DEFAULT NULL
        );
    """)

    # ── Non-breaking Migrations ──────────────────────────────────────────
    _migrate_db(cursor)

    # ── Indexes for deduplication ────────────────────────────────────────
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs(fingerprint_hash);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_external ON jobs(external_job_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_canonical ON jobs(canonical_job_id);")

    # ── Indexes for API filtering ────────────────────────────────────────
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON jobs(match_score);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at ON jobs(scraped_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_removed_at ON jobs(removed_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_remote ON jobs(is_remote);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_internship ON jobs(is_internship);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_fulltime ON jobs(is_fulltime);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_fresher ON jobs(is_fresher);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_hybrid ON jobs(is_hybrid);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_final_score ON jobs(final_score);")

    # ── FTS5 full-text search index ──────────────────────────────────────
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
            title, company, location, description, skills,
            content='jobs',
            content_rowid='id'
        );
    """)

    # ── Triggers to keep FTS in sync ─────────────────────────────────────
    cursor.executescript("""
        CREATE TRIGGER IF NOT EXISTS jobs_ai AFTER INSERT ON jobs BEGIN
            INSERT INTO jobs_fts(rowid, title, company, location, description, skills)
            VALUES (new.id, new.title, new.company, new.location, new.description, new.skills);
        END;

        CREATE TRIGGER IF NOT EXISTS jobs_ad AFTER DELETE ON jobs BEGIN
            INSERT INTO jobs_fts(jobs_fts, rowid, title, company, location, description, skills)
            VALUES ('delete', old.id, old.title, old.company, old.location, old.description, old.skills);
        END;

        CREATE TRIGGER IF NOT EXISTS jobs_au AFTER UPDATE ON jobs BEGIN
            INSERT INTO jobs_fts(jobs_fts, rowid, title, company, location, description, skills)
            VALUES ('delete', old.id, old.title, old.company, old.location, old.description, old.skills);
            INSERT INTO jobs_fts(rowid, title, company, location, description, skills)
            VALUES (new.id, new.title, new.company, new.location, new.description, new.skills);
        END;
    """)

    conn.commit()
    conn.close()


def _migrate_db(cursor: sqlite3.Cursor) -> None:
    """
    Non-breaking schema migration: add new columns to existing databases.
    Silently skips columns that already exist (catches OperationalError).
    """
    new_columns = [
        ("apply_url",     "TEXT DEFAULT ''"),
        ("hiring_status", "TEXT DEFAULT ''"),
        ("duration",      "TEXT DEFAULT ''"),
        ("experience",    "TEXT DEFAULT ''"),
        ("posted_date",   "TEXT DEFAULT ''"),
        ("is_enriched",   "BOOLEAN DEFAULT 0"),
        ("enrichment_timestamp", "TEXT DEFAULT NULL"),
        ("last_seen_at",  "TEXT DEFAULT NULL"),
        ("source_priority", "INTEGER DEFAULT 0"),
        ("is_remote",     "BOOLEAN DEFAULT 0"),
        ("is_hybrid",     "BOOLEAN DEFAULT 0"),
        ("is_fulltime",   "BOOLEAN DEFAULT 0"),
        ("is_internship", "BOOLEAN DEFAULT 0"),
        ("is_fresher",    "BOOLEAN DEFAULT 0"),
        ("fingerprint_hash", "TEXT DEFAULT ''"),
        ("canonical_job_id", "INTEGER DEFAULT NULL"),
        ("merged_sources", "TEXT DEFAULT ''"),
        ("source_count",  "INTEGER DEFAULT 1"),
        ("final_score",   "REAL DEFAULT 0.0"),
        ("ranking_breakdown", "TEXT DEFAULT '{}'"),
        ("recency_score", "REAL DEFAULT 0.0"),
        ("posted_date_normalized", "TEXT DEFAULT NULL"),
        ("company_tags", "TEXT DEFAULT ''"),
        ("is_paid", "INTEGER DEFAULT NULL"),
        ("company_type", "TEXT DEFAULT ''"),
        ("is_senior",     "BOOLEAN DEFAULT 0"),
        ("removed_at",    "TEXT DEFAULT NULL"),
        ("external_job_id", "TEXT DEFAULT NULL"),
        ("is_research",   "BOOLEAN DEFAULT 0"),
        ("is_new_grad",   "BOOLEAN DEFAULT 0"),
        ("city",          "TEXT DEFAULT ''"),
        ("state",         "TEXT DEFAULT ''"),
        ("country",       "TEXT DEFAULT ''"),
        ("locations",     "TEXT DEFAULT ''"),
        ("compact_summary", "TEXT DEFAULT ''"),
    ]
    for col_name, col_def in new_columns:
        try:
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_def}")
        except sqlite3.OperationalError:
            pass  # Column already exists — skip silently


def insert_jobs_bulk(jobs: list[dict]) -> int:
    """
    High-speed bulk insert of scraped jobs.
    Generates fingerprint_hash. If fingerprint already exists, merges the sources.
    Otherwise inserts a new canonical job.
    Uses UPSERT to update `last_seen_at` and reset `removed_at` to NULL if the exact URL already exists.
    Returns the number of *new* rows inserted.
    """
    from utils.dedup import generate_fingerprint
    if not jobs:
        return 0

    now_iso = datetime.now().isoformat()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        old_count = cursor.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

        # Process each job
        for job in jobs:
            fp = generate_fingerprint(
                job.get("title", ""),
                job.get("company", ""),
                job.get("location", "")
            )
            
            # Check if fingerprint or external_job_id already exists
            canon = None
            if job.get("external_job_id"):
                canon = cursor.execute("SELECT id, merged_sources FROM jobs WHERE external_job_id = ? AND canonical_job_id IS NULL LIMIT 1", (job["external_job_id"],)).fetchone()
            
            if not canon:
                canon = cursor.execute("SELECT id, merged_sources FROM jobs WHERE fingerprint_hash = ? AND canonical_job_id IS NULL LIMIT 1", (fp,)).fetchone()
            
            if canon:
                # Group under this canonical job
                canon_id = canon['id']
                existing_sources = set((canon['merged_sources'] or "").split(","))
                existing_sources.add(job["source"])
                existing_sources.discard("")
                merged_str = ",".join(sorted(existing_sources))
                
                # We insert the new URL, but set canonical_job_id
                cursor.execute("""
                    INSERT INTO jobs
                        (title, company, location, job_type, salary,
                         description, url, source, skills, match_score,
                         apply_url, hiring_status, duration,
                         experience, posted_date, scraped_at, last_seen_at, source_priority,
                         fingerprint_hash, canonical_job_id, merged_sources, source_count, company_tags, company_type, external_job_id, removed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    ON CONFLICT(url) DO UPDATE SET
                        last_seen_at = excluded.last_seen_at,
                        removed_at = NULL
                """, (
                    job.get("title", ""), job.get("company", ""), job.get("location", ""),
                    job.get("job_type", ""), job.get("salary", ""), job.get("description", ""),
                    job["url"], job["source"], job.get("skills", ""), job.get("match_score", 0.0),
                    job.get("apply_url", ""), job.get("hiring_status", ""), job.get("duration", ""),
                    job.get("experience", ""), job.get("posted_date", ""), now_iso, now_iso,
                    job.get("source_priority", 0), fp, canon_id, "", 1, job.get("company_tags", ""), job.get("company_type", ""), job.get("external_job_id")
                ))
                
                # Update canonical record's merged sources
                cursor.execute(
                    "UPDATE jobs SET merged_sources = ?, source_count = ?, last_seen_at = ?, removed_at = NULL WHERE id = ?",
                    (merged_str, len(existing_sources), now_iso, canon_id)
                )
            else:
                # No existing canonical job, insert as a new canonical job
                cursor.execute("""
                    INSERT INTO jobs
                        (title, company, location, job_type, salary,
                         description, url, source, skills, match_score,
                         apply_url, hiring_status, duration,
                         experience, posted_date, scraped_at, last_seen_at, source_priority,
                         fingerprint_hash, canonical_job_id, merged_sources, source_count, company_tags, company_type, external_job_id, removed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 1, ?, ?, ?, NULL)
                    ON CONFLICT(url) DO UPDATE SET
                        last_seen_at = excluded.last_seen_at,
                        removed_at = NULL
                """, (
                    job.get("title", ""), job.get("company", ""), job.get("location", ""),
                    job.get("job_type", ""), job.get("salary", ""), job.get("description", ""),
                    job["url"], job["source"], job.get("skills", ""), job.get("match_score", 0.0),
                    job.get("apply_url", ""), job.get("hiring_status", ""), job.get("duration", ""),
                    job.get("experience", ""), job.get("posted_date", ""), now_iso, now_iso,
                    job.get("source_priority", 0), fp, job["source"], job.get("company_tags", ""), job.get("company_type", ""), job.get("external_job_id")
                ))
        
        conn.commit()
        new_count = cursor.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        return new_count - old_count
    finally:
        conn.close()

def merge_jobs(canonical_id: int, duplicate_id: int) -> None:
    """
    Merge a duplicate job into a canonical job.
    Updates merged_sources and source_count on the canonical job,
    and sets canonical_job_id on the duplicate job so it can be filtered out.
    """
    conn = get_connection()
    try:
        # Get duplicate details
        dup = conn.execute("SELECT source, merged_sources FROM jobs WHERE id = ?", (duplicate_id,)).fetchone()
        canon = conn.execute("SELECT source, merged_sources FROM jobs WHERE id = ?", (canonical_id,)).fetchone()
        if not dup or not canon:
            return
            
        dup_sources = {s.strip() for s in (dup['merged_sources'] or dup['source']).split(',') if s.strip()}
        canon_sources = {s.strip() for s in (canon['merged_sources'] or canon['source']).split(',') if s.strip()}
        
        all_sources = canon_sources | dup_sources
        merged_str = ",".join(sorted(all_sources))
        count = len(all_sources)
        
        # Update Canonical
        conn.execute(
            "UPDATE jobs SET merged_sources = ?, source_count = ? WHERE id = ?",
            (merged_str, count, canonical_id)
        )
        # Update Duplicate to point to Canonical
        conn.execute(
            "UPDATE jobs SET canonical_job_id = ? WHERE id = ?",
            (canonical_id, duplicate_id)
        )
        conn.commit()
    finally:
        conn.close()


def search_jobs(query: str, limit: int = 50) -> list[dict]:
    """Full-text search across job listings using FTS5."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT jobs.*
        FROM jobs_fts
        JOIN jobs ON jobs.id = jobs_fts.rowid
        WHERE jobs_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_jobs(source: Optional[str] = None, status: Optional[str] = None,
                 limit: int = 100) -> list[dict]:
    """Retrieve canonical jobs with optional filtering by source and status."""
    conn = get_connection()
    # Only return jobs that are canonical (canonical_job_id IS NULL)
    query = "SELECT * FROM jobs WHERE canonical_job_id IS NULL"
    params: list = []

    if source:
        query += " AND source = ?"
        params.append(source)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY scraped_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_job_stats() -> dict:
    """Return summary statistics about the jobs database."""
    conn = get_connection()
    stats = {}

    stats["total"] = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    for row in conn.execute("SELECT source, COUNT(*) as cnt FROM jobs GROUP BY source"):
        stats[f"source_{row['source']}"] = row["cnt"]

    for row in conn.execute("SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"):
        stats[f"status_{row['status']}"] = row["cnt"]

    stats["avg_match_score"] = conn.execute(
        "SELECT COALESCE(AVG(match_score), 0) FROM jobs"
    ).fetchone()[0]

    conn.close()
    return stats


def update_job_status(job_id: int, status: str) -> None:
    """Update the status of a job listing."""
    conn = get_connection()
    now = datetime.now().isoformat() if status == "applied" else None
    conn.execute(
        "UPDATE jobs SET status = ?, applied_at = COALESCE(?, applied_at) WHERE id = ?",
        (status, now, job_id),
    )
    conn.commit()
    conn.close()


def update_job_enrichment(job_id: int, fields: dict) -> None:
    """
    Update enriched fields and classification for a job.
    """
    if not fields:
        return
        
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]
    
    conn = get_connection()
    try:
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()

def update_job_fields(job_id: int, fields: dict) -> None:
    """
    Backfill specific fields for an existing job row.
    Only updates keys whose values are non-empty strings or non-zero numbers.
    The existing jobs_au trigger keeps the FTS index in sync automatically.
    """
    if not fields:
        return

    # Only write non-empty, non-None values
    updates = {
        k: v for k, v in fields.items()
        if v is not None and v != "" and v != 0 and v != 0.0
    }
    if not updates:
        return

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [job_id]

    conn = get_connection()
    try:
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def get_unenriched_jobs(limit: int = 100) -> list[dict]:
    """
    Fetch jobs from the queue that haven't been enriched yet.
    """
    conn = get_connection()
    query = "SELECT * FROM jobs WHERE is_enriched = 0 ORDER BY scraped_at DESC LIMIT ?"
    rows = conn.execute(query, (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_jobs_missing_description(source: Optional[str] = None) -> list[dict]:
    """
    Return jobs where description is empty — useful for a future --refresh flag.
    Returns minimal dicts with keys: id, url, source.
    """
    conn = get_connection()
    query = "SELECT id, url, source FROM jobs WHERE (description = '' OR description IS NULL)"
    params: list = []
    if source:
        query += " AND source = ?"
        params.append(source)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_user_profile() -> Optional[dict]:
    """Retrieve the single user profile."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_user_profile(profile_data: dict) -> None:
    """Upsert the single user profile."""
    conn = get_connection()
    now_iso = datetime.now().isoformat()
    
    # Extract known keys to prevent SQL injection
    fields = [
        "education_year", "degree", "skills", "preferred_roles",
        "remote_preference", "expected_salary", "is_fresher_seeking",
        "is_internship_seeking"
    ]
    
    columns = ["id"]
    values = [1]
    placeholders = ["?"]
    
    for f in fields:
        if f in profile_data:
            columns.append(f)
            values.append(profile_data[f])
            placeholders.append("?")
            
    columns.append("updated_at")
    values.append(now_iso)
    placeholders.append("?")
    
    col_str = ", ".join(columns)
    val_str = ", ".join(placeholders)
    
    set_str = ", ".join([f"{c} = excluded.{c}" for c in columns if c != "id"])
    
    query = f"""
        INSERT INTO user_profile ({col_str})
        VALUES ({val_str})
        ON CONFLICT(id) DO UPDATE SET {set_str}
    """
    
    conn.execute(query, values)
    conn.commit()
    conn.close()


def get_scraping_state(source: str) -> dict:
    import json
    """Retrieve the last scraping cursor/state for a source."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT state_data FROM scraping_state WHERE source = ?", (source,)).fetchone()
        if row and row['state_data']:
            return json.loads(row['state_data'])
        return {}
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


def save_scraping_state(source: str, state: dict):
    import json
    """Save the scraping cursor/state for a source."""
    conn = get_connection()
    try:
        now_iso = datetime.now().isoformat()
        conn.execute(
            "INSERT INTO scraping_state (source, state_data, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(source) DO UPDATE SET state_data = excluded.state_data, updated_at = excluded.updated_at",
            (source, json.dumps(state), now_iso)
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"[OK] Database initialized at {DB_PATH}")
