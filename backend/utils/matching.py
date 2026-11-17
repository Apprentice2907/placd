"""
Placd — Interest matching and chance labels for internships

Interests are matched on the job title first, then on related titles and the
job's skills. Titles that only mention a field in passing ("AI Content Writing",
"AI Video Creator") are sales, marketing or content roles, so they never count.

Chance labels describe competition, not a prediction:
  - Stretch: a well-known company, where many people apply
  - Strong chance: a smaller company with few applicants so far, or a new post
  - Good fit: everything else
"""

import re
from datetime import datetime, timezone
from typing import Optional

from utils.company_trust import TIER_1_COMPANIES, TIER_2_COMPANIES

INTERESTS = {
    "ai": {
        "label": "AI & ML",
        "core": r"artificial intelligence|\mai\M|machine learning|\mml\M|deep learning|\mllms?\M|gen ?ai|generative"
                r"|\mnlp\M|natural language|computer vision|reinforcement learning|ai agents?|prompt engineer",
        "related": r"data scien|data analy|analytics|\mpython\M|automation|data engineer|statistic|research intern",
    },
    "data": {
        "label": "Data",
        "core": r"data scien|data analy|analytics|data engineer|business intelligence|\mbi\M|statistic",
        "related": r"machine learning|\mml\M|\msql\M|\mpython\M|power ?bi|tableau|excel",
    },
    "web": {
        "label": "Web",
        "core": r"web develop|full ?stack|front ?end|back ?end|\mreact|\mnode|javascript|django|\mmern\M|\mphp\M"
                r"|software develop|software engineer",
        "related": r"app develop|\mpython\M|\mjava\M|typescript|\mapi\M|ui/ux|programming",
    },
    "mobile": {
        "label": "Mobile apps",
        "core": r"android|\mios\M|flutter|react native|mobile app|app develop|kotlin|swift",
        "related": r"web develop|software develop|software engineer|front ?end|full ?stack",
    },
    "cloud": {
        "label": "Cloud & DevOps",
        "core": r"devops|\mcloud|\maws\M|azure|\mgcp\M|kubernetes|docker|site reliability|\msre\M|infrastructure",
        "related": r"\mlinux\M|back ?end|network|system admin|security",
    },
    "security": {
        "label": "Cybersecurity",
        "core": r"cyber ?security|information security|ethical hack|penetration|\msoc\M|network security|security (analyst|research|engineer)",
        "related": r"network|\mlinux\M|cloud|devops",
    },
    "design": {
        "label": "UI/UX Design",
        "core": r"ui/ux|ui ux|\mux\M|\mui\M|user experience|product design|interaction design|figma",
        "related": r"graphic design|visual design|motion graphics|creative design|web design",
    },
}

# Titles in these fields are never counted as a match for a tech interest
NOT_TECH_TITLES = (
    r"marketing|\msales\M|content|writ|video|film|creator|editor|influencer|social media|telecall"
    r"|business development|human resources|\mhr\M|recruit|talent acquisition|annotation|data entry"
    r"|campus ambassador|customer (service|support)|fundraising|lead generation"
)

BIG_COMPANY_SOURCES = ["google", "microsoft", "amazon", "apple", "meta"]

# Whole words only: a substring match would treat "WhatsApp Tools" as HP
WELL_KNOWN_COMPANIES = r"\m(" + "|".join(
    re.escape(name) for name in sorted(TIER_1_COMPANIES | TIER_2_COMPANIES, key=len, reverse=True)
) + r")\M"

STRONG_CHANCE_MAX_APPLICANTS = 50
STRONG_CHANCE_MAX_AGE_DAYS = 3

LEVEL_LABELS = {"strong": "Strong chance", "good": "Good fit", "stretch": "Stretch"}


def well_known_sql() -> str:
    return "(source = ANY(:big_sources) OR is_faang OR COALESCE(company_name, '') ~* :well_known_companies)"


def interest_level_sql() -> str:
    """2 when the title matches the interest, 1 for a related title or skill, else 0."""
    return """(CASE
        WHEN title ~* :not_tech_titles THEN 0
        WHEN title ~* :interest_core THEN 2
        WHEN (title || ' ' || COALESCE(array_to_string(tags, ' '), '')) ~* :interest_related THEN 1
        ELSE 0 END)"""


def interest_params(interest: str) -> dict:
    spec = INTERESTS[interest]
    return {
        "not_tech_titles": NOT_TECH_TITLES,
        "interest_core": spec["core"],
        "interest_related": f"{spec['core']}|{spec['related']}",
    }


def _as_utc(value) -> Optional[datetime]:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def describe_chance(job: dict, interest: Optional[str] = None, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    reasons = []

    level_of_match = job.get("interest_level") or 0
    if interest in INTERESTS and level_of_match:
        word = "Matches" if level_of_match == 2 else "Related to"
        reasons.append(f"{word} {INTERESTS[interest]['label']}")

    posted = _as_utc(job.get("posted_at"))
    found = _as_utc(job.get("created_at"))
    age_days = None
    if posted or found:
        age_days = max(0, (now - (posted or found)).days)
        verb = "Posted" if posted else "Found by Placd"
        when = "today" if age_days == 0 else f"{age_days} day{'s' if age_days != 1 else ''} ago"
        age_reason = f"{verb} {when}"

    applicants = job.get("applicants")

    if job.get("well_known"):
        reasons.append("Well-known company, so many people apply")
        level = "stretch"
    else:
        reasons.append("Smaller company or startup")
        few_applicants = applicants is not None and applicants <= STRONG_CHANCE_MAX_APPLICANTS
        is_new = age_days is not None and age_days <= STRONG_CHANCE_MAX_AGE_DAYS
        if applicants == 0:
            reasons.append("Be an early applicant")
        elif applicants is not None:
            reasons.append(f"{applicants} applicants so far")
        level = "strong" if few_applicants or is_new else "good"

    if age_days is not None:
        reasons.append(age_reason)

    return {"level": level, "label": LEVEL_LABELS[level], "reasons": reasons}
