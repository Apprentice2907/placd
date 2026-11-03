"""
Placd — Job Retention
Keeps the free Neon database small: jobs store a link plus minimal details,
and old jobs are deleted based on how important the company is.

Usage:
    python main.py cleanup --dry-run     Show what would change, change nothing
    python main.py cleanup --trim-only   Shrink stored details, delete nothing
    python main.py cleanup               Trim, then delete old jobs
    python main.py cleanup --compact     Also give freed space back to Neon
"""

import html
import logging
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from db.connection import DATABASE_URL, engine
from utils.company_trust import TIER_1_COMPANIES, TIER_2_COMPANIES, _normalise_company
from utils.job_tagger import INDIA_PLACES, is_student_eligible
from utils.scam_check import check_job

logger = logging.getLogger(__name__)

# Characters of description stored per job. The full text lives behind apply_url.
MAX_DESCRIPTION_CHARS = 300

# Days a job is kept after the scraper last saw it, by company tier.
RETENTION_DAYS = {1: 150, 2: 60, 0: 30}

_INDIA_LOCATION = re.compile(rf"\b({'|'.join(INDIA_PLACES)})\b")

# Hard limit on stored jobs. Hidden jobs go first, then lowest-priority, longest-unseen ones.
MAX_JOBS = 20000

# Age-based deletes only apply to sources whose scraper succeeded this recently.
# Job dates can't prove this, because the link checker also updates last_verified_at.
SCRAPER_RECENT_DAYS = 3

BATCH_SIZE = 500


def _company_pattern(companies: Iterable[str]) -> re.Pattern:
    names = sorted(companies, key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(re.escape(n) for n in names) + r")\b")


_TIER_1_PATTERN = _company_pattern(TIER_1_COMPANIES)
_TIER_2_PATTERN = _company_pattern(TIER_2_COMPANIES)


def retention_tier(company: Optional[str]) -> int:
    """Whole-word company match, so 'Nicola Labs' is not treated as 'ola'."""
    if not company:
        return 0
    name = _normalise_company(company)
    if _TIER_1_PATTERN.search(name):
        return 1
    if _TIER_2_PATTERN.search(name):
        return 2
    return 0


def minimize_description(raw: Optional[str], limit: int = MAX_DESCRIPTION_CHARS) -> str:
    """Plain-text summary of a job description, cut at a word boundary."""
    if not raw:
        return ""
    # Some ATS feeds escape their HTML, so unescape before stripping tags
    plain = BeautifulSoup(html.unescape(raw), "html.parser").get_text(" ")
    plain = " ".join(html.unescape(plain).split())
    if len(plain) <= limit:
        return plain
    cut = plain[: limit - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-") + "…"


def parse_deadline(job: dict) -> Optional[date]:
    """Read an application deadline from a scraped job, if the source gave one."""
    for key in ("application_close_date", "deadline", "last_date"):
        value = job.get(key)
        if not value:
            continue
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            # Internshala writes dates like "29 Aug' 26"
            parsed = date_parser.parse(str(value).replace("'", " "), dayfirst=True).date()
        except (ValueError, OverflowError):
            continue
        # A date far from today is a misread, not a real deadline
        if abs((parsed - date.today()).days) <= 730:
            return parsed
    return None


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _keep_rank(tier: int, row: dict) -> int:
    """Lower is kept longer. Jobs people can see always outrank hidden ones."""
    if row.get("status") != "active":
        return {1: 4, 2: 5, 0: 6}[tier]
    if tier == 1:
        return 0
    location = (row.get("location") or "").lower()
    if row.get("is_internship") or _INDIA_LOCATION.search(location):
        return 1
    return 2 if tier == 2 else 3


def plan_deletions(
    rows: Iterable[dict],
    now: datetime,
    scrape_health: dict,
    max_jobs: int = MAX_JOBS,
) -> tuple[dict, bool]:
    """
    Decide which jobs to delete. Returns ({reason: [ids]}, scraper_recent).

    Each row needs: id, source, company_name, status, last_seen, deadline.
    scrape_health maps each attempted source to its last successful scrape, or None.
    A job with a future deadline is kept until that deadline, whatever its age.
    A job from a failing scraper is not aged out, because it can't be seen as still open.
    A source with no entry is no longer scraped, so its jobs age out normally.
    An 'expired' status is not grounds for deletion: it comes from automated link
    checks that can be wrong, and a later scrape can show the job is still open.
    """
    rows = [dict(r, last_seen=_as_utc(r.get("last_seen"))) for r in rows]
    cutoff = now - timedelta(days=SCRAPER_RECENT_DAYS)
    healthy = {
        source for source, last_success in scrape_health.items()
        if last_success and _as_utc(last_success) >= cutoff
    }
    scraper_recent = bool(healthy)

    def can_age_out(source: Optional[str]) -> bool:
        return scraper_recent and (source in healthy or source not in scrape_health)

    plan = {"deadline_passed": [], "too_old": [], "over_limit": []}
    kept = []
    for row in rows:
        tier = retention_tier(row.get("company_name"))
        deadline = row.get("deadline")
        last_seen = row["last_seen"]
        if deadline and deadline < now.date():
            plan["deadline_passed"].append(row["id"])
        elif (
            can_age_out(row.get("source"))
            and not deadline
            and (last_seen is None or last_seen < now - timedelta(days=RETENTION_DAYS[tier]))
        ):
            plan["too_old"].append(row["id"])
        else:
            kept.append((tier, row))

    if scraper_recent and len(kept) > max_jobs:
        oldest = datetime.min.replace(tzinfo=timezone.utc)
        # Newest first, then a stable sort by priority: best jobs stay at the front
        kept.sort(key=lambda item: item[1]["last_seen"] or oldest, reverse=True)
        kept.sort(key=lambda item: _keep_rank(item[0], item[1]))
        plan["over_limit"] = [row["id"] for _, row in kept[max_jobs:]]

    return plan, scraper_recent


async def ensure_retention_schema(conn) -> None:
    await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS application_close_date DATE"))
    await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS scrape_health (
            source TEXT PRIMARY KEY,
            last_attempt TIMESTAMPTZ NOT NULL,
            last_success TIMESTAMPTZ
        )
    """))
    await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS scam_flags TEXT[] DEFAULT '{}'"))
    await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS stipend_text TEXT"))
    await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS duration_months INT"))
    await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS job_reports (
            job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            reporter_hash TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (job_id, reporter_hash, reason)
        )
    """))


async def record_scrape_result(source: str, success: bool) -> None:
    """A failed attempt keeps the source's previous last_success."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            INSERT INTO scrape_health (source, last_attempt, last_success)
            VALUES (:source, NOW(), CASE WHEN CAST(:success AS boolean) THEN NOW() END)
            ON CONFLICT (source) DO UPDATE SET
                last_attempt = EXCLUDED.last_attempt,
                last_success = COALESCE(EXCLUDED.last_success, scrape_health.last_success)
        """), {"source": source, "success": success})


async def _table_exists(conn, name: str) -> bool:
    result = await conn.execute(text("SELECT to_regclass(:name) IS NOT NULL"), {"name": f"public.{name}"})
    return bool(result.scalar())


async def _report_size(conn, label: str) -> None:
    result = await conn.execute(text("""
        SELECT pg_size_pretty(pg_database_size(current_database())) AS db,
               pg_size_pretty(pg_total_relation_size('jobs')) AS jobs,
               (SELECT COUNT(*) FROM jobs) AS job_count
    """))
    row = result.fetchone()
    logger.info(f"[{label}] database={row.db} jobs_table={row.jobs} job_rows={row.job_count}")


async def _refresh_safety_labels(engine, dry_run: bool) -> None:
    """Applies the current scam and student rules to jobs saved before they existed."""
    async with engine.connect() as conn:
        rows = (await conn.execute(text("""
            SELECT id, title, company_name, description, apply_url, job_type,
                   is_internship, is_student_eligible, scam_flags
            FROM jobs
            WHERE is_spam = FALSE
        """))).fetchall()

    hide, student_off, flag_updates = [], [], []
    for row in rows:
        job = dict(row._mapping)
        high_risk_reason, flags = check_job(job)
        if high_risk_reason:
            hide.append({"id": job["id"], "reason": high_risk_reason})
            continue
        if flags != (job["scam_flags"] or []):
            flag_updates.append({"id": job["id"], "flags": flags})
        if job["is_student_eligible"] and not is_student_eligible(job):
            student_off.append({"id": job["id"]})

    logger.info(
        f"Safety labels: {len(hide)} risky jobs to hide, {len(flag_updates)} warnings to update, "
        f"{len(student_off)} jobs no longer student friendly"
    )
    if dry_run:
        return

    async with engine.begin() as conn:
        if hide:
            await conn.execute(
                text("UPDATE jobs SET is_spam = TRUE, spam_reason = :reason WHERE id = :id"), hide
            )
        if flag_updates:
            await conn.execute(text("UPDATE jobs SET scam_flags = :flags WHERE id = :id"), flag_updates)
        if student_off:
            await conn.execute(text("UPDATE jobs SET is_student_eligible = FALSE WHERE id = :id"), student_off)


async def _fix_internship_labels(engine, dry_run: bool) -> None:
    # Word boundaries in the regex, so "Internal Auditor" does not match
    match = """
        FROM jobs
        WHERE (is_internship = TRUE OR title ~* '\\mintern(ship)?s?\\M')
          AND LOWER(COALESCE(job_type, '')) <> 'internship'
    """
    async with engine.begin() as conn:
        if dry_run:
            result = await conn.execute(text("SELECT COUNT(*)" + match))
            logger.info(f"Internship labels to fix: {result.scalar()}")
            return
        result = await conn.execute(text(
            "UPDATE jobs SET job_type = 'Internship' WHERE id IN (SELECT id" + match + ")"
        ))
        logger.info(f"Internship labels fixed: {result.rowcount}")


async def _trim_details(engine, dry_run: bool) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT COUNT(*) FILTER (WHERE LENGTH(description) > :limit) AS long_descriptions,
                   COUNT(description_embedding) AS embeddings
            FROM jobs
        """), {"limit": MAX_DESCRIPTION_CHARS})
        row = result.fetchone()
    logger.info(f"Trim: {row.long_descriptions} long descriptions, {row.embeddings} embeddings")
    if dry_run:
        return

    async with engine.begin() as conn:
        await conn.execute(text("UPDATE jobs SET description_embedding = NULL WHERE description_embedding IS NOT NULL"))

    # Each trimmed row stops matching the filter, so this loop always finishes
    while True:
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT id, LEFT(description, 20000) AS description
                FROM jobs WHERE LENGTH(description) > :limit LIMIT :batch
            """), {"limit": MAX_DESCRIPTION_CHARS, "batch": BATCH_SIZE})
            batch = result.fetchall()
            if not batch:
                return
            await conn.execute(
                text("UPDATE jobs SET description = :description WHERE id = :id"),
                [{"id": r.id, "description": minimize_description(r.description)} for r in batch],
            )


async def _delete_old_jobs(engine, dry_run: bool) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT id, source, company_name, status, is_internship, location,
                   application_close_date AS deadline,
                   COALESCE(last_verified_at, created_at) AS last_seen
            FROM jobs
        """))
        rows = [dict(r._mapping) for r in result.fetchall()]

        result = await conn.execute(text("SELECT source, last_success FROM scrape_health"))
        scrape_health = {r.source: r.last_success for r in result.fetchall()}

    now = datetime.now(timezone.utc)
    plan, scraper_recent = plan_deletions(rows, now, scrape_health)
    logger.info(f"Delete plan: { {reason: len(ids) for reason, ids in plan.items()} } of {len(rows)} jobs")
    if not scraper_recent:
        logger.warning("No recent successful scrape recorded, so age-based deletes were skipped.")
    failing = sorted(
        source for source, last_success in scrape_health.items()
        if not last_success or _as_utc(last_success) < now - timedelta(days=SCRAPER_RECENT_DAYS)
    )
    if failing:
        logger.warning(f"Not aging out jobs from failing scrapers: {', '.join(failing)}")
    if dry_run:
        return

    ids = [job_id for reason_ids in plan.values() for job_id in reason_ids]
    for start in range(0, len(ids), BATCH_SIZE):
        chunk = ids[start:start + BATCH_SIZE]
        async with engine.begin() as conn:
            # sources.job_id references jobs(id) without ON DELETE CASCADE
            if await _table_exists(conn, "sources"):
                await conn.execute(text("DELETE FROM sources WHERE job_id = ANY(CAST(:ids AS uuid[]))"), {"ids": chunk})
            await conn.execute(text("DELETE FROM jobs WHERE id = ANY(CAST(:ids AS uuid[]))"), {"ids": chunk})

    async with engine.begin() as conn:
        if await _table_exists(conn, "crawl_log"):
            await conn.execute(text("DELETE FROM crawl_log WHERE crawled_at < NOW() - INTERVAL '30 days'"))


async def run_cleanup(dry_run: bool = False, trim_only: bool = False, compact: bool = False) -> None:
    # Own engine: bulk work must not inherit the API's short statement timeouts
    engine = create_async_engine(
        DATABASE_URL,
        poolclass=NullPool,
        connect_args={"command_timeout": 3600, "server_settings": {"statement_timeout": "0"}},
    )
    try:
        async with engine.begin() as conn:
            await ensure_retention_schema(conn)
        async with engine.connect() as conn:
            await _report_size(conn, "before")

        await _trim_details(engine, dry_run)
        await _fix_internship_labels(engine, dry_run)
        await _refresh_safety_labels(engine, dry_run)
        if not trim_only:
            await _delete_old_jobs(engine, dry_run)

        if not dry_run:
            # A plain VACUUM makes space reusable. Only VACUUM FULL returns it to
            # Neon, but it locks the table while it runs, so it is opt-in.
            vacuum = "VACUUM FULL ANALYZE jobs" if compact else "VACUUM ANALYZE jobs"
            async with engine.connect() as conn:
                autocommit = await conn.execution_options(isolation_level="AUTOCOMMIT")
                await autocommit.execute(text(vacuum))
                await _report_size(autocommit, "after")
    finally:
        await engine.dispose()
