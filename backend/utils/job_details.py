"""Small, cleaned-up job details kept in the database: skills and posting date."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from dateutil import parser as date_parser

MAX_SKILLS = 15
MAX_SKILL_LENGTH = 40


def clean_skills(skills) -> Optional[list]:
    if isinstance(skills, str):
        skills = skills.split(",")
    if not isinstance(skills, (list, tuple)):
        return None
    cleaned = []
    for skill in skills:
        skill = str(skill).strip()
        if skill and len(skill) <= MAX_SKILL_LENGTH and skill.lower() not in (s.lower() for s in cleaned):
            cleaned.append(skill)
    return cleaned[:MAX_SKILLS] or None


# Other scrapers fill the date with the time they ran, or with the last edit
# (Greenhouse's updated_at), which would make old jobs look new
SOURCES_WITH_REAL_POSTING_DATES = {"internshala", "ashby", "lever", "amazon", "indeed", "jobspy", "linkedin"}


def parse_posted_at(job: dict, source: Optional[str] = None, now: Optional[datetime] = None) -> Optional[datetime]:
    """The date the employer posted the job, when a source gives one we can trust."""
    if (source or job.get("source") or "").lower() not in SOURCES_WITH_REAL_POSTING_DATES:
        return None
    now = now or datetime.now(timezone.utc)
    value = job.get("posted_date") or job.get("date_posted")
    if not value:
        return None
    try:
        posted = value if isinstance(value, datetime) else date_parser.parse(str(value))
    except (ValueError, OverflowError, TypeError):
        return None
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)
    # Some scrapers fill in the scrape time; a date in the future or years ago is not real
    if posted > now + timedelta(days=1) or posted < now - timedelta(days=365):
        return None
    return posted
