"""
Placd — Scam checks and plain-language trust labels

Checks a job for the scams students actually run into: fee requests, hiring
over WhatsApp or Telegram, unrealistic pay and disguised apply links.

  - High risk: the job is rejected, the same as spam
  - Caution: the job stays on the site with a visible warning

No check can prove a job is real, so nothing here says it does.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from urllib.parse import urlparse

# Jobs from these sources come straight from the company's own hiring system.
# Marketplaces like Internshala let anyone post, so they do not count.
DIRECT_SOURCES = (
    "greenhouse", "lever", "ashby", "workday", "smartrecruiters", "bamboohr",
    "recruitee", "amazon", "google", "microsoft", "meta", "apple",
)
VERIFIED_WITHIN_DAYS = 14

CAUTION_MESSAGES = {
    "personal_email": "Asks you to apply through a personal email address",
    "phone_contact": "Asks you to call or message a phone number",
    "google_form": "Applications go through a Google Form",
    "apply_link_mismatch": "Apply link is not on this company's website",
    "commission_sales": "May be commission-only sales work",
    "recruiting_agency": "Posted by a recruiting agency, not the employer",
}

_NEGATION = re.compile(r"\b(no|not|never|without|free of|zero|don'?t|doesn'?t|won'?t|nor)\b")

_FEE_PATTERNS = [
    re.compile(
        r"\b(registration|security|training|joining|processing|enrol?lment|"
        r"certificate|certification|onboarding|kit|interview)\s+(fees?|deposit|charges?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\brefundable\s+(amount|deposit|fees?)\b", re.IGNORECASE),
    re.compile(r"\bpay\s+(a\s+|the\s+|an\s+)?(small\s+)?(fees?|deposit)\b", re.IGNORECASE),
]

# Only hiring over a messenger counts. "Contact clients on WhatsApp" is a normal duty.
_MESSENGER_PATTERNS = [
    re.compile(
        r"\b(apply|send|share|submit|forward)\b.{0,60}\b(on|via|through|over)\s+(whatsapp|telegram)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(contact|message|ping|text|dm)\s+(us|hr|me)\b.{0,30}\b(whatsapp|telegram)\b", re.IGNORECASE),
    re.compile(r"\bjoin\b.{0,30}\b(whatsapp|telegram)\b", re.IGNORECASE),
    re.compile(r"\b(whatsapp|telegram)\b.{0,30}\b(your\s+cv|your\s+resume)\b", re.IGNORECASE),
]

_PAY_PATTERNS = [
    re.compile(
        r"\bearn\w*\s+(up\s*to\s+)?(₹|rs\.?\s*|inr\s*|\$)?\s*[\d,]+\s*(k\s*)?(per|/|a|every)\s*(day|week|hour)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(daily|weekly)\s+(payout|payment|income|earning)s?\b", re.IGNORECASE),
    re.compile(r"\bguaranteed\s+(income|earning|job|placement|salary)s?\b", re.IGNORECASE),
    re.compile(r"\bwork\s+from\s+mobile\b", re.IGNORECASE),
    re.compile(r"\b(refer\s+and\s+earn|pay\s+after\s+placement)\b", re.IGNORECASE),
]

_PERSONAL_EMAIL = re.compile(
    r"[\w.+-]+@(gmail|yahoo|hotmail|outlook|rediffmail|ymail|proton|protonmail)\.[a-z.]{2,6}",
    re.IGNORECASE,
)
_PHONE_CONTACT = re.compile(
    r"\b(call|contact|whatsapp|message|text)\b.{0,30}(\+91[\s-]?)?\b[6-9]\d{4}[\s-]?\d{5}\b",
    re.IGNORECASE,
)
_COMMISSION = re.compile(
    r"\b(commission[- ](only|based)|field sales executive|insurance advisor|financial advisor)\b",
    re.IGNORECASE,
)
_AGENCY = re.compile(
    r"\b(consultancy|consultants|staffing|recruitment|placement|manpower)\b.*\b(pvt|ltd|llp|inc|services|solutions|agency|firm)\b"
    r"|\bhr\s?(consultancy|solutions|services)\b",
    re.IGNORECASE,
)

_LINK_SHORTENERS = {
    "bit.ly", "tinyurl.com", "cutt.ly", "rb.gy", "is.gd", "goo.gl", "t.co", "shorturl.at", "ow.ly",
}
_MESSENGER_HOSTS = {"wa.me", "chat.whatsapp.com", "api.whatsapp.com", "t.me", "telegram.me"}
_GOOGLE_FORM_HOSTS = {"forms.gle", "docs.google.com", "forms.google.com"}

# Hiring systems and job boards, where the host never contains the company name
_TRUSTED_APPLY_HOSTS = (
    "greenhouse.io", "lever.co", "ashbyhq.com", "myworkdayjobs.com", "workday.com",
    "smartrecruiters.com", "bamboohr.com", "recruitee.com", "icims.com", "taleo.net",
    "successfactors.com", "jobvite.com", "breezy.hr", "workable.com", "teamtailor.com",
    "internshala.com", "naukri.com", "linkedin.com", "indeed.com", "wellfound.com",
    "himalayas.app", "remoteok.com", "weworkremotely.com", "ycombinator.com",
    "workatastartup.com", "cutshort.io", "instahyre.com",
)


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _has_unnegated_match(pattern: re.Pattern, text: str) -> bool:
    """Skips "no registration fee" and "we never charge a security deposit"."""
    for match in pattern.finditer(text):
        before = text[max(0, match.start() - 40):match.start()].lower()
        if not _NEGATION.search(before):
            return True
    return False


def _apply_link_matches_company(host: str, company: str) -> bool:
    words = re.findall(r"[a-z0-9]+", company.lower())
    squashed = host.replace("-", "").replace(".", "")
    if "".join(words) and "".join(words) in squashed:
        return True
    return any(len(word) >= 4 and word in squashed for word in words)


def check_job(job: dict) -> Tuple[Optional[str], list]:
    """
    Returns (high_risk_reason, caution_flags).
    high_risk_reason is None when the job can be kept.
    """
    title = job.get("title") or ""
    description = job.get("description") or ""
    company = job.get("company") or job.get("company_name") or ""
    apply_url = job.get("apply_url") or job.get("url") or ""
    text = f"{title}\n{description}"
    host = _host(apply_url) if apply_url else ""

    if any(_has_unnegated_match(p, text) for p in _FEE_PATTERNS):
        return "asks_for_money", []
    if any(p.search(text) for p in _MESSENGER_PATTERNS):
        return "hires_over_messenger", []
    if any(_has_unnegated_match(p, text) for p in _PAY_PATTERNS):
        return "unrealistic_pay_promise", []
    if host in _MESSENGER_HOSTS:
        return "apply_link_is_messenger", []
    if host in _LINK_SHORTENERS:
        return "apply_link_is_disguised", []

    flags = []
    if _PERSONAL_EMAIL.search(description):
        flags.append("personal_email")
    if _PHONE_CONTACT.search(description):
        flags.append("phone_contact")
    if _COMMISSION.search(text):
        flags.append("commission_sales")
    if _AGENCY.search(company):
        flags.append("recruiting_agency")

    if host in _GOOGLE_FORM_HOSTS:
        flags.append("google_form")
    elif (
        host
        and company
        and not any(host == h or host.endswith("." + h) for h in _TRUSTED_APPLY_HOSTS)
        and not _apply_link_matches_company(host, company)
    ):
        flags.append("apply_link_mismatch")

    return None, flags


def _parse_time(value) -> Optional[datetime]:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def describe_trust(job: dict, now: Optional[datetime] = None) -> dict:
    """Plain-language reasons shown to users. Only states what was actually checked."""
    now = now or datetime.now(timezone.utc)
    source = (job.get("source") or "").lower()
    flags = job.get("scam_flags") or []
    last_confirmed = _parse_time(job.get("last_verified_at"))

    is_direct = source in DIRECT_SOURCES
    is_recent = bool(last_confirmed) and now - last_confirmed <= timedelta(days=VERIFIED_WITHIN_DAYS)

    reasons = []
    if is_direct:
        reasons.append("Apply link goes to the company's own hiring page")
    if is_recent:
        reasons.append(f"Last confirmed live on {last_confirmed.day} {last_confirmed:%b %Y}")

    warnings = [CAUTION_MESSAGES[f] for f in flags if f in CAUTION_MESSAGES]
    if not is_direct:
        warnings.append("Posted on a public job site. We have not checked the employer")

    return {
        "verified": is_direct and is_recent and not flags,
        "reasons": reasons,
        "warnings": warnings,
    }
