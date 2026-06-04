"""
Placd — BambooHR Adapter

Fetches jobs from BambooHR's public careers API.
Endpoint: GET https://{company}.bamboohr.com/careers/list
"""

import asyncio
from typing import List, Dict, Any

from scrapers.shared.base_adapter import UnifiedAdapter


class BambooHRAdapter(UnifiedAdapter):
    source = "bamboohr"
    rpm = 30
    api_domain = "bamboohr.com"

    def _build_probe_url(self) -> str:
        return f"https://{self.company}.bamboohr.com/careers/list"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch jobs from BambooHR public careers JSON endpoint."""
        url = f"https://{self.company}.bamboohr.com/careers/list"
        jobs: List[Dict[str, Any]] = []

        async with self.get_client() as client:
            # BambooHR returns JSON when Accept header is set
            client.headers["Accept"] = "application/json"
            resp = await self._fetch_with_retry(client, url)
            data = resp.json()

            for item in data.get("result", []):
                # ── Title ────────────────────────────────────────────
                title_obj = item.get("title", {})
                title = title_obj.get("label", "") if isinstance(title_obj, dict) else str(title_obj)

                # ── Location ─────────────────────────────────────────
                loc_obj = item.get("location", {})
                if isinstance(loc_obj, dict):
                    city = loc_obj.get("city", "")
                    country = loc_obj.get("country", "")
                    location = f"{city}, {country}".strip(", ") if city or country else ""
                else:
                    location = str(loc_obj) if loc_obj else ""

                is_remote = "remote" in location.lower() or "remote" in title.lower()

                # ── Job type ─────────────────────────────────────────
                emp_obj = item.get("employmentType", {})
                job_type_raw = emp_obj.get("label", "") if isinstance(emp_obj, dict) else str(emp_obj)
                job_type = _normalize_job_type(job_type_raw, title)

                # ── Department ───────────────────────────────────────
                dept_obj = item.get("department", {})
                department = dept_obj.get("label", "") if isinstance(dept_obj, dict) else str(dept_obj)

                # ── Apply URL ────────────────────────────────────────
                job_id = item.get("id", "")
                apply_url = f"https://{self.company}.bamboohr.com/careers/{job_id}"

                # ── Description ──────────────────────────────────────
                description = item.get("description", "")
                if isinstance(description, dict):
                    description = description.get("label", "")

                jobs.append({
                    "title": title,
                    "company": self.company,
                    "location": location,
                    "description": description or "",
                    "url": apply_url,
                    "apply_url": apply_url,
                    "source": self.source,
                    "job_type": job_type,
                    "is_remote": is_remote,
                    "department": department,
                    "source_priority": self.priority,
                    "company_tags": self._format_tags(),
                    "company_type": self.company_type,
                })

        return jobs


def _normalize_job_type(raw: str, title: str = "") -> str:
    """Map BambooHR employment type labels to our schema values."""
    raw_lower = (raw or "").lower()
    title_lower = (title or "").lower()
    if "intern" in raw_lower or "intern" in title_lower:
        return "internship"
    if "part" in raw_lower:
        return "part-time"
    if "contract" in raw_lower:
        return "contract"
    return "full-time"


if __name__ == "__main__":
    # Try multiple known BambooHR customers
    for company in ["zapier", "asana", "greenhouse"]:
        adapter = BambooHRAdapter({"name": company})
        jobs = asyncio.run(adapter.fetch_jobs())
        print(f"[{company}] Fetched {len(jobs)} jobs from BambooHR")
        if jobs:
            j = jobs[0]
            print(f"  Title:    {j['title']}")
            print(f"  Location: {j['location']}")
            print(f"  Type:     {j['job_type']}")
            print(f"  URL:      {j['apply_url']}")
            break

