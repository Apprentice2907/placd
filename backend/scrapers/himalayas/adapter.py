"""
Placd — Himalayas Adapter

Fetches jobs from the Himalayas.app global remote job feed.
Endpoint: GET https://himalayas.app/jobs/api?limit=100&offset=N
Paginated — keeps fetching until response "jobs" array is empty.
"""

import asyncio
import re
from typing import List, Dict, Any, Optional

from scrapers.shared.base_adapter import UnifiedAdapter


class HimalayasAdapter(UnifiedAdapter):
    source = "himalayas"
    rpm = 20
    api_domain = "himalayas.app"

    def __init__(self, company_config: dict = None):
        super().__init__(company_config)
        # Max jobs to fetch per run (safety cap)
        self._max_jobs = self.company_config.get("max_jobs", 500)

    def _build_probe_url(self) -> str:
        return "https://himalayas.app/jobs/api"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch paginated global remote job feed from Himalayas."""
        jobs: List[Dict[str, Any]] = []
        offset = 0
        page_size = 100

        async with self.get_client() as client:
            while len(jobs) < self._max_jobs:
                url = f"https://himalayas.app/jobs/api?limit={page_size}&offset={offset}"

                resp = await self._fetch_with_retry(client, url)
                data = resp.json()

                page_jobs = data.get("jobs", [])
                if not page_jobs:
                    break

                for item in page_jobs:
                    title = item.get("title", "")

                    # ── Company ───────────────────────────────────────
                    company_name = item.get("companyName", "") or item.get("company_name", "")

                    # ── Location ──────────────────────────────────────
                    location = item.get("location", "") or "Remote"
                    is_remote = True  # Himalayas is a remote-first board

                    # ── Job type ──────────────────────────────────────
                    job_type = _normalize_job_type(
                        item.get("jobType", "") or item.get("job_type", ""),
                        title,
                    )

                    # ── Salary ────────────────────────────────────────
                    salary_min, salary_max, salary_currency = _parse_salary(
                        item.get("salary", ""),
                        item.get("salaryCurrency", "USD"),
                    )
                    # Also check explicit fields
                    if salary_min is None:
                        salary_min = _safe_int(item.get("salaryMin") or item.get("salary_min"))
                    if salary_max is None:
                        salary_max = _safe_int(item.get("salaryMax") or item.get("salary_max"))

                    # ── Description ───────────────────────────────────
                    description = item.get("description", "") or ""

                    # ── Apply URL ─────────────────────────────────────
                    apply_url = item.get("applyUrl", "") or item.get("apply_url", "") or item.get("url", "")

                    # ── Tags / Categories ─────────────────────────────
                    tags = item.get("tags", [])
                    if not isinstance(tags, list):
                        tags = []
                    categories = item.get("categories", [])
                    if not isinstance(categories, list):
                        categories = []

                    jobs.append({
                        "title": title,
                        "company": company_name,
                        "location": location,
                        "description": description,
                        "url": apply_url,
                        "apply_url": apply_url,
                        "source": self.source,
                        "job_type": job_type,
                        "is_remote": is_remote,
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "salary_currency": salary_currency or "USD",
                        "tags": tags,
                        "categories": categories,
                        "source_priority": self.priority,
                    })

                offset += page_size

        return jobs


# ── Helpers ──────────────────────────────────────────────────────────────────

def _normalize_job_type(raw: str, title: str = "") -> str:
    raw_lower = (raw or "").lower()
    title_lower = (title or "").lower()
    if "intern" in raw_lower or "intern" in title_lower:
        return "internship"
    if "part" in raw_lower:
        return "part-time"
    if "contract" in raw_lower or "freelance" in raw_lower:
        return "contract"
    return "full-time"


def _safe_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


_SALARY_RE = re.compile(r"[\$€£₹]?\s*([\d,]+)")


def _parse_salary(salary_str: str, default_currency: str = "USD"):
    """
    Best-effort parse of a free-text salary string like "$120,000 - $150,000".
    Returns (min, max, currency).
    """
    if not salary_str:
        return None, None, default_currency

    numbers = _SALARY_RE.findall(salary_str)
    nums = []
    for n in numbers:
        try:
            nums.append(int(n.replace(",", "")))
        except ValueError:
            pass

    salary_min = nums[0] if len(nums) >= 1 else None
    salary_max = nums[1] if len(nums) >= 2 else salary_min

    # Detect currency symbol
    currency = default_currency
    if "€" in salary_str:
        currency = "EUR"
    elif "£" in salary_str:
        currency = "GBP"
    elif "₹" in salary_str:
        currency = "INR"

    return salary_min, salary_max, currency


if __name__ == "__main__":
    adapter = HimalayasAdapter({"name": "himalayas", "max_jobs": 200})
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"Fetched {len(jobs)} jobs from Himalayas")
    if jobs:
        j = jobs[0]
        print(f"  Title:    {j['title']}")
        print(f"  Company:  {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  Type:     {j['job_type']}")
        print(f"  Salary:   {j.get('salary_min')}-{j.get('salary_max')} {j.get('salary_currency')}")
        print(f"  URL:      {j['apply_url']}")
