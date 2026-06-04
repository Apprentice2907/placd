"""
Placd — Cutshort Adapter

Fetches jobs from Cutshort.io by extracting data from the server-rendered
__NEXT_DATA__ JSON embedded in the /jobs pages.

Cutshort is a Next.js SPA with no public REST API. Job data is server-side
rendered into React Query dehydrated state. We paginate via ?page=N.

Indian market scraper — salary in INR, multi-city locations,
experience ranges.
"""

import asyncio
import json
import re
import logging
from typing import List, Dict, Any, Optional

from scrapers.shared.base_adapter import UnifiedAdapter

logger = logging.getLogger(__name__)

_NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)


class CutshortAdapter(UnifiedAdapter):
    source = "cutshort"
    rpm = 20
    api_domain = "cutshort.io"

    def __init__(self, company_config: dict = None):
        super().__init__(company_config)
        self._max_pages = self.company_config.get("max_pages", 5)

    def _build_probe_url(self) -> str:
        return "https://cutshort.io/jobs"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch jobs from Cutshort by parsing __NEXT_DATA__ from /jobs pages.
        Extracts from the `featuredJobListData` dehydrated query.
        """
        all_jobs: List[Dict[str, Any]] = []
        seen_ids: set = set()

        async with self.get_client() as client:
            for page in range(1, self._max_pages + 1):
                url = f"https://cutshort.io/jobs?page={page}"

                try:
                    resp = await self._fetch_with_retry(client, url)
                except Exception as e:
                    logger.warning(f"cutshort_page_error page={page} error={e}")
                    break

                html = resp.text
                match = _NEXT_DATA_RE.search(html)
                if not match:
                    logger.warning(f"cutshort_no_next_data page={page}")
                    break

                try:
                    next_data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    logger.warning(f"cutshort_json_parse_error page={page}")
                    break

                queries = (
                    next_data
                    .get("props", {})
                    .get("pageProps", {})
                    .get("dehydratedState", {})
                    .get("queries", [])
                )

                page_jobs = []
                for q in queries:
                    qkey = str(q.get("queryKey", ""))
                    if "featuredJobListData" in qkey:
                        featured = (
                            q.get("state", {})
                            .get("data", {})
                            .get("data", {})
                            .get("pageData", {})
                            .get("jobs", [])
                        )
                        page_jobs.extend(featured)

                if not page_jobs:
                    break

                for item in page_jobs:
                    job_id = item.get("_id", "")
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    job = self._parse_job(item)
                    if job:
                        all_jobs.append(job)

        return all_jobs

    def _parse_job(self, item: dict) -> Optional[Dict[str, Any]]:
        """Parse a single Cutshort job from the dehydrated query."""
        title = item.get("headline", "").strip()
        if not title:
            return None

        # ── Company ──────────────────────────────────────────────
        company_obj = item.get("companyDetails", {})
        company_name = company_obj.get("name", "") if isinstance(company_obj, dict) else ""

        # ── Location ─────────────────────────────────────────────
        locations = item.get("locations", [])
        if isinstance(locations, list):
            location = ", ".join(str(loc) for loc in locations if loc) or ""
        else:
            location = str(locations) if locations else ""
        # Also check locationsText
        if not location:
            location = item.get("locationsText", "")

        remote_type = item.get("remoteType", "")
        is_remote = remote_type in ("remote_okay", "remote_only", "hybrid") or "remote" in location.lower()
        if not location and is_remote:
            location = "Remote"

        # ── Skills ───────────────────────────────────────────────
        skills_raw = item.get("allSkills", []) or item.get("allSkillsObj", [])
        skill_names = []
        for s in skills_raw:
            if isinstance(s, dict):
                skill_names.append(s.get("name", str(s)))
            else:
                skill_names.append(str(s))
        skills_str = ", ".join(skill_names)

        # ── Salary (INR) ─────────────────────────────────────────
        salary_range = item.get("salaryRange", {}) or {}
        salary_min = _safe_int(salary_range.get("min"))
        salary_max = _safe_int(salary_range.get("max"))
        salary_currency = salary_range.get("currency", "INR")
        salary_display = item.get("salaryRangeText", "")
        if not salary_display and (salary_min or salary_max):
            # Convert from raw INR to LPA for display
            min_lpa = (salary_min or 0) / 100000
            max_lpa = (salary_max or 0) / 100000
            salary_display = f"₹{min_lpa:.1f} - ₹{max_lpa:.1f} LPA"

        # ── Experience ───────────────────────────────────────────
        exp_range = item.get("expRange", {}) or {}
        exp_min = _safe_int(exp_range.get("min") or exp_range.get("minVanity"))
        exp_max = _safe_int(exp_range.get("max") or exp_range.get("maxVanity"))

        # ── Job type ─────────────────────────────────────────────
        role_types = item.get("roleTypes", [])
        job_type = _normalize_job_type(role_types, title)

        # ── Apply URL ────────────────────────────────────────────
        apply_url = item.get("publicUrl", "") or item.get("authApplyUrl", "")
        if not apply_url:
            apply_url = f"https://cutshort.io/job/{item.get('_id', '')}"

        # ── Description ──────────────────────────────────────────
        description = item.get("sanitizedComment", "") or item.get("description", "") or ""

        return {
            "title": title,
            "company": company_name,
            "location": location,
            "description": description,
            "url": apply_url,
            "apply_url": apply_url,
            "source": self.source,
            "job_type": job_type,
            "is_remote": is_remote,
            "skills": skills_str,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "salary_display": salary_display,
            "experience_min": exp_min,
            "experience_max": exp_max,
            "source_priority": self.priority,
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(float(str(val).replace(",", "")))
    except (ValueError, TypeError):
        return None


def _normalize_job_type(role_types: list, title: str = "") -> str:
    if isinstance(role_types, list):
        rt_str = " ".join(str(r) for r in role_types).lower()
    else:
        rt_str = str(role_types).lower()
    title_lower = (title or "").lower()

    if "intern" in rt_str or "intern" in title_lower:
        return "internship"
    if "part" in rt_str:
        return "part-time"
    if "contract" in rt_str or "freelance" in rt_str:
        return "contract"
    return "full-time"


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    adapter = CutshortAdapter({"name": "cutshort", "max_pages": 3})
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"Fetched {len(jobs)} jobs from Cutshort")
    for j in jobs[:5]:
        sal = j.get("salary_display", "")
        exp = f"{j.get('experience_min', '?')}-{j.get('experience_max', '?')} yrs" if j.get("experience_min") else ""
        print(f"  {j['title']} @ {j['company']} — {j['location']} — {sal} — {exp}")
        print(f"    Skills: {j.get('skills', '')[:80]}")
        print(f"    URL: {j['apply_url']}")
