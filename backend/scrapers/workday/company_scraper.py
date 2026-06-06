import asyncio
import logging
import httpx
from typing import List, Dict, Any

from scrapers.shared.base_adapter import UnifiedAdapter

log = logging.getLogger(__name__)

WORKDAY_COMPANIES = [
    {
        "company": "Nvidia",
        "slug": "nvidia",
        "tenant": "nvidiaexternalcareersite",
        "base_url": "https://nvidia.wd5.myworkdayjobs.com",
        "domain": "nvidia.com",
        "tier": 1,
        "trust_score": 100,
    },
    {
        "company": "Salesforce",
        "slug": "salesforce",
        "tenant": "External_Career_Site",
        "base_url": "https://salesforce.wd1.myworkdayjobs.com",
        "domain": "salesforce.com",
        "tier": 1,
        "trust_score": 100,
    },
    {
        "company": "Adobe",
        "slug": "adobe",
        "tenant": "external_experienced",
        "base_url": "https://adobe.wd5.myworkdayjobs.com",
        "domain": "adobe.com",
        "tier": 1,
        "trust_score": 100,
    },
    {
        "company": "Uber",
        "slug": "uber",
        "tenant": "ATG_External_Site",
        "base_url": "https://uber.wd5.myworkdayjobs.com",
        "domain": "uber.com",
        "tier": 1,
        "trust_score": 100,
    },
    {
        "company": "Intel",
        "slug": "intel",
        "tenant": "External",
        "base_url": "https://intel.wd1.myworkdayjobs.com",
        "domain": "intel.com",
        "tier": 1,
        "trust_score": 100,
    },
    {
        "company": "Cisco",
        "slug": "cisco",
        "tenant": "External",
        "base_url": "https://cisco.wd5.myworkdayjobs.com",
        "domain": "cisco.com",
        "tier": 1,
        "trust_score": 100,
    },
    {
        "company": "Oracle",
        "slug": "oracle",
        "tenant": "OracleCareers",
        "base_url": "https://oracle.wd1.myworkdayjobs.com",
        "domain": "oracle.com",
        "tier": 1,
        "trust_score": 90,
    },
    {
        "company": "SAP",
        "slug": "sap",
        "tenant": "SAP",
        "base_url": "https://sap.wd3.myworkdayjobs.com",
        "domain": "sap.com",
        "tier": 1,
        "trust_score": 90,
    },
    {
        "company": "Intuit",
        "slug": "intuit",
        "tenant": "jobs",
        "base_url": "https://intuit.wd5.myworkdayjobs.com",
        "domain": "intuit.com",
        "tier": 1,
        "trust_score": 100,
    },
    {
        "company": "PayPal",
        "slug": "paypal",
        "tenant": "jobs",
        "base_url": "https://paypal.wd1.myworkdayjobs.com",
        "domain": "paypal.com",
        "tier": 1,
        "trust_score": 100,
    },
    {
        "company": "Qualcomm",
        "slug": "qualcomm",
        "tenant": "External",
        "base_url": "https://qualcomm.wd5.myworkdayjobs.com",
        "domain": "qualcomm.com",
        "tier": 1,
        "trust_score": 100,
    },
    {
        "company": "VMware",
        "slug": "vmware",
        "tenant": "VMware",
        "base_url": "https://vmware.wd5.myworkdayjobs.com",
        "domain": "vmware.com",
        "tier": 1,
        "trust_score": 90,
    },
    {
        "company": "ServiceNow",
        "slug": "servicenow",
        "tenant": "ServiceNow",
        "base_url": "https://servicenow.wd5.myworkdayjobs.com",
        "domain": "servicenow.com",
        "tier": 1,
        "trust_score": 100,
    },
    {
        "company": "Workday",
        "slug": "workday",
        "tenant": "workdaydevjobs",
        "base_url": "https://workday.wd5.myworkdayjobs.com",
        "domain": "workday.com",
        "tier": 1,
        "trust_score": 90,
    },
]

class WorkdayCompanyScraper(UnifiedAdapter):
    source = "workday_direct"
    rpm = 20

    async def fetch_all_companies(self) -> list[dict]:
        all_jobs = []
        sem = asyncio.Semaphore(5)  # max 5 companies concurrent

        async def fetch_company(config: dict) -> list[dict]:
            async with sem:
                jobs = []
                seen_paths = set()
                offset = 0
                total_jobs = 0
                api_url = f"{config['base_url']}/wday/cxs/{config['slug']}/{config['tenant']}/jobs"

                async with httpx.AsyncClient(timeout=30) as client:
                    while True:
                        try:
                            resp = await client.post(
                                api_url,
                                json={
                                    "appliedFacets": {},
                                    "limit": 20,
                                    "offset": offset,
                                    "searchText": ""
                                },
                                headers={
                                    "Content-Type": "application/json",
                                    "Accept": "application/json",
                                }
                            )

                            if resp.status_code in [403, 404]:
                                break

                            if resp.status_code == 429:
                                await asyncio.sleep(30)
                                continue

                            data = resp.json()
                            if offset == 0:
                                total_jobs = data.get("total", 0)
                            postings = data.get("jobPostings", [])

                            if not postings or offset >= total_jobs:
                                break

                            for p in postings:
                                job_path = p.get("externalPath", "")
                                if not job_path or job_path in seen_paths:
                                    continue
                                seen_paths.add(job_path)
                                jobs.append({
                                    "title": p.get("title", ""),
                                    "company": config["company"],
                                    "location": p.get("locationsText", ""),
                                    "description": p.get("jobDescription", {}).get("descriptor", ""),
                                    "apply_url": f"{config['base_url']}{job_path}",
                                    "url": f"{config['base_url']}{job_path}",
                                    "source": "workday_direct",
                                    "source_platform": "workday_direct",
                                    "job_type": p.get("timeType", "full_time"),
                                    "department": p.get("jobFamilyGroup", "General"),
                                    "date_posted": p.get("postedOn", ""),
                                    "is_remote": "remote" in p.get("locationsText", "").lower(),
                                    "is_hybrid": False,
                                    "trust_score": config["trust_score"],
                                    "company_domain": config["domain"],
                                    "company_logo_url": f"https://logo.clearbit.com/{config['domain']}",
                                    "company_tier": config["tier"],
                                    "skills": [],
                                    "salary_min": None,
                                    "salary_max": None,
                                    "salary_currency": None,
                                })

                            offset += 20
                            if len(postings) < 20:
                                break

                            await asyncio.sleep(1)

                        except Exception as e:
                            log.error(f"Workday {config['company']} error: {e}")
                            break

                log.info(f"Workday {config['company']}: {len(jobs)} jobs")
                return jobs

        tasks = [fetch_company(c) for c in WORKDAY_COMPANIES]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)

        return all_jobs

    async def fetch_jobs(self) -> list[dict]:
        return await self.fetch_all_companies()


if __name__ == "__main__":
    adapter = WorkdayCompanyScraper()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"\nWorkday Companies Total: {len(jobs)} jobs")
    from collections import Counter
    counts = Counter(j["company"] for j in jobs)
    for company, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {company}: {count}")
