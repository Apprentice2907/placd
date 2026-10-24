"""
Offline test for the Apify path in scrapers/linkedin/adapter.py.

The Apify client is replaced with a stub, so nothing here calls Apify or LinkedIn.
Run from backend/:  python -m pytest test_linkedin_adapter.py
"""

import asyncio
from types import SimpleNamespace

import apify_client

from scrapers.linkedin import adapter as linkedin_adapter

# Dataset items in the shape johnvc/linkedin-jobs-api returns: two job rows,
# then an error row and a notice row, neither of which has a jobUrl.
DATASET_ITEMS = [
    {
        "result_type": "job",
        "jobId": "4300000001",
        "jobUrl": "https://www.linkedin.com/jobs/view/4300000001",
        "title": "Backend Engineer",
        "companyName": "Example Labs",
        "companyUrl": "https://www.linkedin.com/company/example-labs",
        "location": "Bengaluru, Karnataka, India",
        "description": "<p>Build and run Python services.</p>",
        "seniorityLevel": "Entry level",
        "employmentType": "Full-time",
        "jobFunction": "Engineering and Information Technology",
        "industries": ["Software Development"],
        "postedDate": "2026-10-22T00:00:00.000Z",
        "postedAgo": "1 day ago",
        "numApplicants": 25,
        "countryCode": "IN",
        "summary": "Backend Engineer, at Example Labs, Bengaluru, Karnataka, India, Full-time",
        "fromCache": False,
        "fetched_at": "2026-10-23T06:00:00+00:00",
    },
    {
        # LinkedIn listed no employment type, so the Actor leaves the key out
        "result_type": "job",
        "jobId": "4300000002",
        "jobUrl": "https://www.linkedin.com/jobs/view/4300000002",
        "title": "Data Engineer",
        "companyName": "Sample Analytics",
        "location": "India",
        "description": "Work on data pipelines.",
        "postedDate": "2026-10-23T00:00:00.000Z",
        "summary": "Data Engineer, at Sample Analytics, India",
        "fromCache": False,
        "fetched_at": "2026-10-23T06:00:00+00:00",
    },
    {
        "result_type": "error",
        "sourceUrl": "software engineer",
        "error_message": "The data source returned no jobs for this search.",
        "error_type": "CollectionError",
        "fetched_at": "2026-10-23T06:00:00+00:00",
    },
    {
        "free_tier_notice": True,
        "notice": "free_tier_limit_reached",
        "message": "Free monthly allowance reached for this Actor.",
    },
]


def _fake_client_class(calls):
    class FakeDataset:
        async def iterate_items(self):
            for item in DATASET_ITEMS:
                yield item

    class FakeActor:
        def __init__(self, actor_id):
            self.actor_id = actor_id

        async def call(self, run_input=None, **kwargs):
            calls.append((self.actor_id, run_input))
            # apify-client 3.x returns a Run model, not a dict
            return SimpleNamespace(default_dataset_id="dataset-1")

    class FakeApifyClientAsync:
        def __init__(self, token):
            assert token == "test-token"

        def actor(self, actor_id):
            return FakeActor(actor_id)

        def dataset(self, dataset_id):
            assert dataset_id == "dataset-1"
            return FakeDataset()

    return FakeApifyClientAsync


def test_apify_path_calls_live_actor_and_maps_fields(monkeypatch):
    calls = []
    monkeypatch.setattr(apify_client, "ApifyClientAsync", _fake_client_class(calls))
    monkeypatch.setattr(
        linkedin_adapter,
        "LINKEDIN_SEARCHES",
        [{"keywords": "software engineer", "location": "India"}],
    )
    monkeypatch.setenv("APIFY_TOKEN", "test-token")

    jobs = asyncio.run(linkedin_adapter.LinkedinAdapter().fetch_jobs())

    assert calls == [
        (
            "johnvc/linkedin-jobs-api",
            {
                "keyword": "software engineer",
                "location": "India",
                "timeRange": "past-day",
                "maxJobs": 100,
            },
        )
    ]

    # The error row and the notice row are dropped
    assert [job["apply_url"] for job in jobs] == [
        "https://www.linkedin.com/jobs/view/4300000001",
        "https://www.linkedin.com/jobs/view/4300000002",
    ]

    first = jobs[0]
    assert first["title"] == "Backend Engineer"
    assert first["company"] == "Example Labs"
    assert first["location"] == "Bengaluru, Karnataka, India"
    assert first["description"] == "Build and run Python services."
    assert first["url"] == "https://www.linkedin.com/jobs/view/4300000001"
    assert first["posted_date"] == "2026-10-22T00:00:00.000Z"
    assert first["job_type"] == "Full-time"
    assert first["source"] == "linkedin"
    assert first["source_priority"] == 1

    # No employmentType on the row: the adapter's existing default applies
    assert jobs[1]["job_type"] == "full-time"
