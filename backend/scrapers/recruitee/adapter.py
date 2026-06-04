"""
Placd — Recruitee Adapter

Fetches jobs from Recruitee's public offers API.
Endpoint: GET https://{company}.recruitee.com/api/offers
"""

import asyncio
from typing import List, Dict, Any

from scrapers.shared.base_adapter import UnifiedAdapter


class RecruiteeAdapter(UnifiedAdapter):
    source = "recruitee"
    rpm = 30
    api_domain = "recruitee.com"

    def _build_probe_url(self) -> str:
        return f"https://{self.company}.recruitee.com/api/offers"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch jobs from Recruitee public offers API."""
        url = f"https://{self.company}.recruitee.com/api/offers"
        jobs: List[Dict[str, Any]] = []

        async with self.get_client() as client:
            resp = await self._fetch_with_retry(client, url)
            data = resp.json()

            for offer in data.get("offers", []):
                title = offer.get("title", "")

                # ── Location ─────────────────────────────────────────
                location = offer.get("location", "")
                is_remote = offer.get("remote", False)
                if not location and is_remote:
                    location = "Remote"
                if isinstance(location, str) and "remote" in location.lower():
                    is_remote = True

                # ── Job type ─────────────────────────────────────────
                job_type = _normalize_job_type(
                    offer.get("employment_type_code", ""),
                    title,
                )

                # ── Tags ─────────────────────────────────────────────
                tags = offer.get("tags", [])
                if not isinstance(tags, list):
                    tags = []

                # ── Description ──────────────────────────────────────
                description = offer.get("description", "") or ""

                # ── Apply URL ────────────────────────────────────────
                slug = offer.get("slug", offer.get("id", ""))
                apply_url = f"https://{self.company}.recruitee.com/o/{slug}"

                # ── Salary ───────────────────────────────────────────
                salary_min = offer.get("min_salary") or offer.get("salary_min")
                salary_max = offer.get("max_salary") or offer.get("salary_max")
                salary_currency = offer.get("salary_currency", "USD")

                jobs.append({
                    "title": title,
                    "company": self.company,
                    "location": location,
                    "description": description,
                    "url": apply_url,
                    "apply_url": apply_url,
                    "source": self.source,
                    "job_type": job_type,
                    "is_remote": is_remote,
                    "tags": tags,
                    "salary_min": _safe_int(salary_min),
                    "salary_max": _safe_int(salary_max),
                    "salary_currency": salary_currency,
                    "source_priority": self.priority,
                    "company_tags": self._format_tags(),
                    "company_type": self.company_type,
                })

        return jobs


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


def _safe_int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":
    adapter = RecruiteeAdapter({"name": "personio"})
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"Fetched {len(jobs)} jobs from Recruitee (personio)")
    if jobs:
        j = jobs[0]
        print(f"  Title:    {j['title']}")
        print(f"  Location: {j['location']}")
        print(f"  Type:     {j['job_type']}")
        print(f"  Remote:   {j['is_remote']}")
        print(f"  URL:      {j['apply_url']}")
        print(f"  Tags:     {j.get('tags', [])}")

