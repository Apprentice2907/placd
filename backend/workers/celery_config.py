"""
Placd — Centralized Celery Configuration

Defines all queues, task routing, and shared settings in one place.
Every worker module imports `app` from here instead of creating its own Celery instance.
"""

import os
from celery import Celery
from celery.schedules import crontab
from kombu import Queue

# ── Broker / Backend ─────────────────────────────────────────────────────────

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

app = Celery(
    "placd",
    broker=redis_url,
    backend=redis_url,
    include=[
        "workers.crawlers",
        "workers.enricher",
        "workers.liveness",
        "workers.opportunity_tasks",
        "workers.playwright_tasks",
        "workers.calendar_tasks",
    ],
)

# ── Queues ───────────────────────────────────────────────────────────────────

QUEUES = [
    Queue("crawl_tier_a"),   # Fast API-based ATS scrapers
    Queue("crawl_tier_b"),   # Slower / HTML-parsing scrapers
    Queue("crawl_tier_c"),   # Playwright-based scrapers (LinkedIn, Wellfound)
    Queue("enrich"),         # AI enrichment pipeline
    Queue("liveness"),       # URL liveness checks
    Queue("opportunities"),  # Opportunity & calendar tasks
    Queue("default"),        # Fallback
]

# ── Task Routing ─────────────────────────────────────────────────────────────
# Maps each task name → the queue it should land on.

TASK_ROUTES = {
    # crawl_tier_a: fast API-based ATS scrapers
    "crawl_company_task":           {"queue": "crawl_tier_a"},
    "crawl_all_companies_task":     {"queue": "crawl_tier_a"},
    "crawl_bamboohr_task":          {"queue": "crawl_tier_a"},
    "crawl_recruitee_task":         {"queue": "crawl_tier_a"},
    "crawl_himalayas_task":         {"queue": "crawl_tier_a"},
    # greenhouse, lever, ashby, workable handled by crawl_company_task
    # remoteok also tier_a
    "crawl_remoteok_task":          {"queue": "crawl_tier_a"},

    # crawl_tier_b: slower / HTML-parsing / anti-bot scrapers
    "crawl_naukri_task":            {"queue": "crawl_tier_b"},
    "crawl_internshala_task":       {"queue": "crawl_tier_b"},
    "crawl_instahyre_task":         {"queue": "crawl_tier_b"},
    "crawl_cutshort_task":          {"queue": "crawl_tier_b"},
    "crawl_amazon_task":            {"queue": "crawl_tier_b"},
    "crawl_google_task":            {"queue": "crawl_tier_b"},
    "crawl_meta_task":              {"queue": "crawl_tier_b"},
    "crawl_microsoft_task":         {"queue": "crawl_tier_b"},
    "crawl_weworkremotely_task":    {"queue": "crawl_tier_b"},

    # crawl_tier_c: playwright-based scrapers
    "scrape_linkedin_task":         {"queue": "crawl_tier_c"},
    "scrape_wellfound_task":        {"queue": "crawl_tier_c"},

    # enrich: AI enrichment tasks
    "enrich_job_task":              {"queue": "enrich"},
    "batch_enrich_task":            {"queue": "enrich"},

    # liveness: URL verification tasks
    "verify_new_jobs_task":         {"queue": "liveness"},
    "daily_liveness_sweep_task":    {"queue": "liveness"},
    "mark_stale_jobs_task":         {"queue": "liveness"},
    "reactivate_reopened_jobs_task": {"queue": "liveness"},

    # opportunities: opportunity + calendar tasks
    "crawl_opportunities_corners":  {"queue": "opportunities"},
    "crawl_opportunities_circle":   {"queue": "opportunities"},
    "crawl_all_opportunities":      {"queue": "opportunities"},
    "sweep_expired_opportunities":  {"queue": "opportunities"},
    "refresh_calendar_from_jobs":   {"queue": "opportunities"},

    # batch dispatch for new adapters (lightweight coordinator)
    "crawl_all_new_adapters_task":  {"queue": "crawl_tier_a"},
}

# ── App Settings ─────────────────────────────────────────────────────────────

app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Results
    result_expires=3600,

    # Queues & routing
    task_queues=QUEUES,
    task_routes=TASK_ROUTES,
    task_default_queue="default",

    # Important for long-running scrape tasks: fetch one task at a time
    worker_prefetch_multiplier=1,

    # Acknowledge after task completes (not before) — prevents lost tasks on crash
    task_acks_late=True,

    # Default retry policy (individual tasks can override)
    task_default_retry_delay=60,
    task_annotations={
        "*": {
            "max_retries": 3,
        },
    },

    # Beat Schedule for periodic background runs
    beat_schedule={
        "scrape-himalayas-hourly": {
            "task": "workers.crawlers.crawl_himalayas_task",
            "schedule": crontab(minute="0"),
            "options": {"queue": "crawl_tier_a"}
        },
        "scrape-remoteok-hourly": {
            "task": "workers.crawlers.crawl_remoteok_task",
            "schedule": crontab(minute="15"),
            "options": {"queue": "crawl_tier_a"}
        },
        "scrape-weworkremotely-hourly": {
            "task": "workers.crawlers.crawl_weworkremotely_task",
            "schedule": crontab(minute="30"),
            "options": {"queue": "crawl_tier_b"}
        },
        "scrape-cutshort-2hourly": {
            "task": "workers.crawlers.crawl_cutshort_task",
            "schedule": crontab(minute="45", hour="*/2"),
            "options": {"queue": "crawl_tier_b"}
        },
        "scrape-all-tier-a-6h": {
            "task": "workers.crawlers.scrape_all_discovered_companies",
            "schedule": crontab(minute="0", hour="*/6"),
            "options": {"queue": "crawl_tier_a"}
        },
        "run-full-discovery-weekly": {
            "task": "workers.crawlers.run_full_discovery",
            "schedule": crontab(minute="0", hour="1", day_of_week="sun"),
            "options": {"queue": "crawl_tier_a"}
        },
        "scrape-naukri-2hourly": {
            "task": "workers.crawlers.crawl_naukri_task",
            "schedule": crontab(minute="10", hour="*/2"),
            "options": {"queue": "crawl_tier_b"}
        },
        "scrape-internshala-4hourly": {
            "task": "workers.crawlers.crawl_internshala_task",
            "schedule": crontab(minute="20", hour="*/4"),
            "options": {"queue": "crawl_tier_b"}
        },
        "scrape-linkedin-daily": {
            "task": "workers.crawlers.scrape_linkedin_task",
            "schedule": crontab(minute="0", hour="2"),
            "options": {"queue": "crawl_tier_c"}
        }
    }
)

# ── Default Retry Helper ─────────────────────────────────────────────────────

def default_retry_countdown(retries: int) -> int:
    """Exponential backoff: 60s → 120s → 240s → …"""
    return 60 * (2 ** retries)
