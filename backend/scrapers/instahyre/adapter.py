"""
Placd — Instahyre Adapter

Fetches jobs from Instahyre's jobseeker API with curl_cffi TLS impersonation.
"""

import asyncio
import re
import random
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from scrapers.shared.base_adapter import UnifiedAdapter

logger = logging.getLogger(__name__)

_HEADERS: Dict[str, str] = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Referer": "https://www.instahyre.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

_PRIMARY_URL = "https://www.instahyre.com/jobseeker/api/jobs/"
_FALLBACK_URL = "https://www.instahyre.com/api/v1/jobs/"

_NUM_RE = re.compile(r"[\d,.]+")
_EXP_RE = re.compile(r"(\d+)\s*[-–—to]+\s*(\d+)", re.IGNORECASE)
_EXP_SINGLE_RE = re.compile(r"(\d+)\s*\+?\s*(?:year|yr|yrs)", re.IGNORECASE)

def _safe_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(float(str(val).replace(",", "")))
    except (ValueError, TypeError):
        return None

def _parse_salary_inr(item: dict) -> tuple:
    salary_range = item.get("salary_range", {}) or item.get("salary", {})
    if isinstance(salary_range, dict):
        raw_min = salary_range.get("min") or salary_range.get("minimum") or salary_range.get("lower")
        raw_max = salary_range.get("max") or salary_range.get("maximum") or salary_range.get("upper")
        sal_min = _safe_int(raw_min)
        sal_max = _safe_int(raw_max)
        if sal_min or sal_max:
            return sal_min, sal_max
    if isinstance(salary_range, str) and salary_range.strip():
        nums = _NUM_RE.findall(salary_range.replace(",", ""))
        parsed = [_safe_int(n) for n in nums]
        parsed = [n for n in parsed if n is not None]
        sal_min = parsed[0] if len(parsed) >= 1 else None
        sal_max = parsed[1] if len(parsed) >= 2 else sal_min
        return sal_min, sal_max
    sal_min = _safe_int(item.get("salary_min") or item.get("min_salary"))
    sal_max = _safe_int(item.get("salary_max") or item.get("max_salary"))
    if sal_min or sal_max:
        return sal_min, sal_max
    return None, None

def _parse_experience(item: dict) -> tuple:
    exp_raw = item.get("experience_range", "") or item.get("experience", "") or item.get("min_experience", "")
    if isinstance(exp_raw, dict):
        return _safe_int(exp_raw.get("min")), _safe_int(exp_raw.get("max"))
    exp_str = str(exp_raw)
    m = _EXP_RE.search(exp_str)
    if m:
        return _safe_int(m.group(1)), _safe_int(m.group(2))
    m = _EXP_SINGLE_RE.search(exp_str)
    if m:
        val = _safe_int(m.group(1))
        return val, val
    exp_min = _safe_int(item.get("min_experience") or item.get("experience_min"))
    exp_max = _safe_int(item.get("max_experience") or item.get("experience_max"))
    if exp_min is not None or exp_max is not None:
        return exp_min, exp_max
    return None, None

def _normalize_job_type(raw: str, title: str = "") -> str:
    raw_lower = (raw or "").lower()
    title_lower = (title or "").lower()
    if "intern" in raw_lower or "intern" in title_lower:
        return "internship"
    if "part" in raw_lower:
        return "part-time"
    if "contract" in raw_lower or "freelance" in raw_lower:
        return "contract"
    return "full_time"

def _strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&[a-z]+;", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

class InstahyreAdapter(UnifiedAdapter):
    source = "instahyre"
    company = "Instahyre"
    rpm = 20
    api_domain = "instahyre.com"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        import httpx
        
        jobs: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=30) as session:
                use_fallback = False
                max_pages = 5

                for page in range(1, max_pages + 1):
                    if not use_fallback:
                        url = f"{_PRIMARY_URL}?page={page}"
                    else:
                        url = f"{_FALLBACK_URL}?format=json&page={page}"

                    data = await self._fetch_page(session, url)

                    if data is None and not use_fallback:
                        logger.warning("Instahyre primary API returned 403. Falling back to /api/v1/jobs/")
                        use_fallback = True
                        url = f"{_FALLBACK_URL}?format=json&page={page}"
                        data = await self._fetch_page(session, url)

                    if data is None:
                        break

                    page_jobs = []
                    if isinstance(data, dict):
                        page_jobs = data.get("results", data.get("data", data.get("jobs", [])))
                        has_next = data.get("next") is not None
                    elif isinstance(data, list):
                        page_jobs = data
                        has_next = len(data) > 0
                    else:
                        break

                    if not page_jobs:
                        break

                    for item in page_jobs:
                        job = self._parse_job(item)
                        if job:
                            jobs.append(job)

                    if not has_next:
                        break

                    await asyncio.sleep(random.uniform(1.0, 3.0))

        except Exception as e:
            logger.error(f"Instahyre error: {e}")

        return jobs

    async def _fetch_page(self, session, url: str) -> Optional[dict]:
        max_retries = 3
        base_wait = 2.0

        for attempt in range(max_retries + 1):
            try:
                resp = await session.get(url, headers=_HEADERS)

                if resp.status_code == 403:
                    return None

                if resp.status_code == 429:
                    if attempt < max_retries:
                        wait = base_wait * (2 ** attempt) + random.uniform(0.5, 2.0)
                        await asyncio.sleep(wait)
                        continue
                    return None

                if resp.status_code >= 500:
                    if attempt < max_retries:
                        await asyncio.sleep(base_wait * (2 ** attempt))
                        continue
                    return None

                return resp.json()

            except Exception as e:
                if attempt < max_retries:
                    await asyncio.sleep(base_wait * (2 ** attempt))
                else:
                    logger.error(f"Instahyre fetch failed for {url}: {e}")
                    return None
        return None

    def _parse_job(self, item: dict) -> Optional[Dict[str, Any]]:
        title = (item.get("designation", "") or item.get("title", "")).strip()
        if not title:
            return None

        company = (item.get("company_name", "") or item.get("company", "")).strip()

        location_raw = item.get("location", "") or item.get("locations", "")
        if isinstance(location_raw, list):
            location = ", ".join(str(loc) for loc in location_raw if loc) or ""
        else:
            location = str(location_raw)

        is_remote = "remote" in location.lower() or item.get("is_remote", False)

        skills_raw = item.get("skills_required", []) or item.get("skills", [])
        skill_names = []
        if isinstance(skills_raw, list):
            for s in skills_raw:
                if isinstance(s, dict):
                    skill_names.append(s.get("name", str(s)))
                else:
                    skill_names.append(str(s))

        salary_min, salary_max = _parse_salary_inr(item)
        exp_min, exp_max = _parse_experience(item)

        job_type = _normalize_job_type(
            item.get("employment_type", "") or item.get("type", ""),
            title,
        )

        job_id = item.get("id", "")
        apply_url = item.get("url", "") or item.get("apply_url", "")
        if not apply_url and job_id:
            apply_url = f"https://www.instahyre.com/job-{job_id}/"

        description = _strip_html(item.get("description", "") or "")

        return {
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "apply_url": apply_url,
            "url": apply_url,
            "source": self.source,
            "source_platform": self.source,
            "job_type": job_type,
            "department": "General",
            "date_posted": datetime.now().isoformat(),
            "is_remote": is_remote,
            "is_hybrid": False,
            "trust_score": 60,
            "company_domain": "",
            "company_logo_url": None,
            "company_tier": 3,
            "skills": skill_names,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": "INR" if salary_min else None,
        }

if __name__ == "__main__":
    adapter = InstahyreAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
