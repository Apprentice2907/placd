"""
Placd — Company Trust Tier System

Three tiers of company trust for quality scoring.
Tier 1 = FAANG + Big Tech + Top Indian startups (trust_score bonus: 100)
Tier 2 = Series B+ startups, known brands (trust_score bonus: 70)
Unranked = everything else (no bonus, but can still score well on data quality)
"""

import re
from datetime import datetime, timezone
from typing import Optional

# ── Tier 1: Blue-chip companies ──────────────────────────────────────────────

TIER_1_COMPANIES: set[str] = {
    # FAANG + Big Tech
    "google", "microsoft", "amazon", "apple", "meta", "netflix",
    "nvidia", "intel", "amd", "qualcomm", "broadcom",
    # Top Product Companies India
    "flipkart", "razorpay", "phonepe", "paytm", "swiggy", "zomato",
    "meesho", "cred", "groww", "zerodha", "freshworks", "zoho",
    "byju", "unacademy", "sharechat", "dream11", "ola",
    # Top Global Tech
    "stripe", "airbnb", "uber", "lyft", "twitter", "linkedin",
    "salesforce", "oracle", "sap", "ibm", "accenture", "deloitte",
    "openai", "anthropic", "deepmind", "mistral", "cohere",
    "databricks", "snowflake", "cloudflare", "datadog", "hashicorp",
    "figma", "notion", "airtable", "asana", "slack", "zoom",
    "shopify", "square", "twilio", "sendgrid", "okta", "auth0",
    "mongodb", "elastic", "confluent", "dbt", "fivetran",
    # Top Indian IT
    "tcs", "infosys", "wipro", "hcl", "tech mahindra", "cognizant",
    "capgemini", "mphasis", "hexaware", "mindtree", "l&t technology",
    # Additional well-known
    "adobe", "atlassian", "github", "gitlab", "vercel", "supabase",
    "postman", "docker", "red hat", "vmware", "dell", "hp",
    "samsung", "sony", "siemens", "bosch", "continental",
    "jpmorgan", "goldman sachs", "morgan stanley", "barclays",
    "visa", "mastercard", "paypal", "robinhood", "coinbase",
    "tesla", "spacex", "palantir", "anduril",
}

# ── Tier 2: Known Series B+ / established companies ─────────────────────────

TIER_2_COMPANIES: set[str] = {
    # Well-known startups & mid-stage companies
    "razorpay", "lenskart", "nykaa", "policybazaar", "cars24",
    "vedantu", "upgrad", "scaler", "coding ninjas",
    "dunzo", "rapido", "jupiter", "slice", "fi",
    "hasura", "postman", "browserstack", "druva", "icertis",
    "chargebee", "clevertap", "leadsquared", "darwinbox",
    "delhivery", "shiprocket", "licious", "bigbasket",
    "cure.fit", "practo", "1mg", "pharmeasy",
    # Global mid-stage
    "canva", "miro", "linear", "retool", "vercel",
    "render", "fly.io", "planetscale", "turso", "neon",
    "resend", "clerk", "inngest", "temporal",
    "wiz", "snyk", "lacework", "sentry",
    # YC-backed well-known
    "stripe", "airbnb", "dropbox", "instacart", "doordash",
    "gusto", "plaid", "brex", "ramp", "mercury",
}

# ── Scoring Weights ──────────────────────────────────────────────────────────

TRUST_SCORE_WEIGHTS = {
    "tier_1_company": 100,
    "tier_2_company": 70,
    "has_description_gt_200_chars": 20,
    "has_salary": 15,
    "has_skills": 10,
    "source_is_direct_ats": 20,     # greenhouse/lever/ashby = direct from ATS
    "source_is_aggregator": 0,      # indeed/jobspy = aggregator
    "posted_within_7_days": 15,
    "posted_within_30_days": 5,
    "has_apply_url_not_email": 10,
    "description_has_tech_keywords": 10,
    "no_spam_signals": 20,
}

# Direct ATS sources (higher quality signal)
DIRECT_ATS_SOURCES = frozenset({
    "greenhouse", "lever", "ashby", "workday", "bamboohr",
    "recruitee", "smartrecruiters",
})

# Tech keywords that indicate a real tech job posting
_TECH_KEYWORDS = frozenset({
    "api", "backend", "frontend", "database", "cloud", "aws", "gcp", "azure",
    "python", "java", "javascript", "typescript", "react", "node", "docker",
    "kubernetes", "microservices", "agile", "scrum", "ci/cd", "git",
    "machine learning", "deep learning", "data pipeline", "sql", "nosql",
    "rest", "graphql", "terraform", "ansible", "linux", "devops",
})


def _normalise_company(name: str) -> str:
    """Lowercase and strip common suffixes for matching."""
    name = name.lower().strip()
    for suffix in (" inc.", " inc", " ltd.", " ltd", " pvt.", " pvt",
                    " llp", " corp.", " corp", " technologies",
                    " technology", " solutions", " services",
                    " private limited", " limited"):
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
    return name


def get_company_tier(company_name: str) -> int:
    """Returns 1, 2, or 0 (unranked)."""
    norm = _normalise_company(company_name)
    if norm in TIER_1_COMPANIES:
        return 1
    if norm in TIER_2_COMPANIES:
        return 2
    # Fuzzy check — see if any tier-1 company is a substring of the name
    for t1 in TIER_1_COMPANIES:
        if t1 in norm or norm in t1:
            return 1
    for t2 in TIER_2_COMPANIES:
        if t2 in norm or norm in t2:
            return 2
    return 0


def calculate_trust_score(job: dict) -> int:
    """
    Returns 0-200. Jobs below 30 should be filtered. Above 80 are featured.
    """
    score = 0
    company = job.get("company", "")
    tier = get_company_tier(company)

    if tier == 1:
        score += TRUST_SCORE_WEIGHTS["tier_1_company"]
    elif tier == 2:
        score += TRUST_SCORE_WEIGHTS["tier_2_company"]

    # Description quality
    desc = job.get("description", "") or ""
    if len(desc) > 200:
        score += TRUST_SCORE_WEIGHTS["has_description_gt_200_chars"]

    # Salary data present
    if job.get("salary_min") or job.get("salary_max") or job.get("salary"):
        score += TRUST_SCORE_WEIGHTS["has_salary"]

    # Skills present
    skills = job.get("skills", "")
    if skills and (isinstance(skills, list) and len(skills) > 0) or (isinstance(skills, str) and len(skills) > 3):
        score += TRUST_SCORE_WEIGHTS["has_skills"]

    # Source quality
    source = (job.get("source_platform") or job.get("source") or "").lower()
    if source in DIRECT_ATS_SOURCES:
        score += TRUST_SCORE_WEIGHTS["source_is_direct_ats"]

    # Freshness
    date_posted = job.get("date_posted") or job.get("posted_date")
    if date_posted:
        try:
            if isinstance(date_posted, str):
                # Handle ISO format
                posted_dt = datetime.fromisoformat(date_posted.replace("Z", "+00:00"))
            elif isinstance(date_posted, datetime):
                posted_dt = date_posted
            else:
                posted_dt = None

            if posted_dt:
                now = datetime.now(timezone.utc)
                if posted_dt.tzinfo is None:
                    posted_dt = posted_dt.replace(tzinfo=timezone.utc)
                age_days = (now - posted_dt).days
                if age_days <= 7:
                    score += TRUST_SCORE_WEIGHTS["posted_within_7_days"]
                elif age_days <= 30:
                    score += TRUST_SCORE_WEIGHTS["posted_within_30_days"]
        except (ValueError, TypeError):
            pass

    # Apply URL quality
    apply_url = job.get("apply_url", "")
    if apply_url and not apply_url.startswith("mailto:") and not apply_url.startswith("tel:"):
        score += TRUST_SCORE_WEIGHTS["has_apply_url_not_email"]

    # Tech keyword check in description
    desc_lower = desc.lower()
    if any(kw in desc_lower for kw in _TECH_KEYWORDS):
        score += TRUST_SCORE_WEIGHTS["description_has_tech_keywords"]

    # Spam check bonus (applied externally — if spam_filter says clean)
    # This is added by the pipeline, not here. We leave room for it.

    return score
