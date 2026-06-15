"""
Placd — Spam & Fake Job Detection

Detects spam, MLM, and low-quality job postings using:
  - Title pattern matching (regex)
  - Company pattern matching (regex)
  - Description signal detection (keyword)
  - Minimum quality thresholds (length, URL validity)
"""

import re
from typing import Tuple


# ── Spam Title Patterns ──────────────────────────────────────────────────────

SPAM_TITLE_PATTERNS: list[re.Pattern] = [
    re.compile(r"work from home.*earn.*\d+", re.IGNORECASE),
    re.compile(r"earn \$?\d+.*per (day|hour)", re.IGNORECASE),
    re.compile(r"no experience.*required.*\d+k", re.IGNORECASE),
    re.compile(r"(mlm|multi.?level|network marketing)", re.IGNORECASE),
    re.compile(r"(urgent|immediate).*(hiring|joiners).*\d{4,}", re.IGNORECASE),
    re.compile(r"data entry.*work from home", re.IGNORECASE),
    re.compile(r"part time.*\d+ (lakh|lac|lpa)", re.IGNORECASE),
    re.compile(r"home based.*job", re.IGNORECASE),
    re.compile(r"(telecaller|bpo).*night shift.*lakh", re.IGNORECASE),
    re.compile(r"earn.*lakhs?.*month", re.IGNORECASE),
    re.compile(r"form filling.*home", re.IGNORECASE),
    re.compile(r"copy paste.*job", re.IGNORECASE),
    re.compile(r"typing.*job.*\d+", re.IGNORECASE),
]

# ── Spam Company Patterns ────────────────────────────────────────────────────

SPAM_COMPANY_PATTERNS: list[re.Pattern] = [
    re.compile(r"^[A-Z]{2,5}\s?(pvt|ltd|llp|inc)\.?$", re.IGNORECASE),
    re.compile(r"(consultancy|consultants|solutions|services)\s?(pvt|ltd)", re.IGNORECASE),
    re.compile(r"hr\s?(consultancy|solutions|services)", re.IGNORECASE),
    re.compile(r"^(hiring|recruitment|staffing)\s?(agency|firm|company)$", re.IGNORECASE),
]

# ── Spam Description Signals ─────────────────────────────────────────────────

SPAM_DESCRIPTION_SIGNALS: list[str] = [
    "whatsapp us",
    "call hr",
    "send cv on whatsapp",
    "contact: +91",
    "immediate joining",
    "10th pass",
    "12th pass",
    "no target",
    "weekly payout",
    "daily payout",
    "tele caller",
    "field sales executive",
    "insurance advisor",
    "financial advisor",
    "mlm",
    "network marketing",
    "refer and earn",
    "work from mobile",
    "just give missed call",
    "sms sending job",
    "ad posting job",
    "captcha typing",
]

# ── Quality Thresholds ───────────────────────────────────────────────────────

MINIMUM_QUALITY_THRESHOLDS = {
    "min_description_length": 30,  # Reduced from 100 — many real jobs have brief descriptions
    "min_title_length": 5,
    "max_title_length": 150,
    "must_have_apply_url": True,
    "apply_url_not_email": True,
    "no_phone_in_apply_url": True,
}


def is_spam(job: dict) -> Tuple[bool, str]:
    """
    Returns (is_spam: bool, reason: str).
    If is_spam is True, reason explains why.
    """
    title = job.get("title", "") or ""
    description = job.get("description", "") or ""
    company = job.get("company", "") or ""
    apply_url = job.get("apply_url", "") or ""

    # ── Title patterns ───────────────────────────────────────────────────
    for pattern in SPAM_TITLE_PATTERNS:
        if pattern.search(title):
            return True, f"spam_title_pattern: {pattern.pattern}"

    # ── Company patterns ─────────────────────────────────────────────────
    for pattern in SPAM_COMPANY_PATTERNS:
        if pattern.search(company):
            return True, f"spam_company_pattern: {pattern.pattern}"

    # ── Description signals ──────────────────────────────────────────────
    desc_lower = description.lower()
    for signal in SPAM_DESCRIPTION_SIGNALS:
        if signal in desc_lower:
            return True, f"spam_description_signal: {signal}"

    # ── Quality thresholds ───────────────────────────────────────────────
    if len(description) < MINIMUM_QUALITY_THRESHOLDS["min_description_length"]:
        return True, "description_too_short"

    if len(title) < MINIMUM_QUALITY_THRESHOLDS["min_title_length"]:
        return True, "title_too_short"

    if len(title) > MINIMUM_QUALITY_THRESHOLDS["max_title_length"]:
        return True, "title_too_long"

    # Apply URL validation
    if not apply_url:
        return True, "missing_apply_url"
    if apply_url.startswith("mailto:"):
        return True, "apply_url_is_email"
    if apply_url.startswith("tel:"):
        return True, "apply_url_is_phone"

    return False, ""
