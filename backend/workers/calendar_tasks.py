import structlog
from celery import shared_task
from sqlalchemy import text
from db.connection import AsyncSessionLocal
from utils.async_utils import run_async

logger = structlog.get_logger(__name__)

async def _refresh_calendar():
    """
    Extract open and close dates from recently scraped jobs to auto-populate the hiring calendar.
    """
    logger.info("refresh_calendar_started")
    try:
        async with AsyncSessionLocal() as session:
            sql = """
                WITH job_events AS (
                    SELECT 
                        c.name as company_name,
                        c.ats_slug as company_slug,
                        'opens' as window_type,
                        MIN(COALESCE(j.application_open_date, j.first_seen_at::date)) as event_date,
                        EXTRACT(YEAR FROM MIN(COALESCE(j.application_open_date, j.first_seen_at::date))) as year
                    FROM jobs j JOIN companies c ON j.company_id = c.id
                    WHERE j.first_seen_at >= NOW() - INTERVAL '30 days'
                    GROUP BY c.name, c.ats_slug
                    HAVING MIN(COALESCE(j.application_open_date, j.first_seen_at::date)) IS NOT NULL
                    
                    UNION ALL
                    
                    SELECT 
                        c.name as company_name,
                        c.ats_slug as company_slug,
                        'closes' as window_type,
                        MAX(j.application_close_date) as event_date,
                        EXTRACT(YEAR FROM MAX(j.application_close_date)) as year
                    FROM jobs j JOIN companies c ON j.company_id = c.id
                    WHERE j.first_seen_at >= NOW() - INTERVAL '30 days' 
                    GROUP BY c.name, c.ats_slug
                    HAVING MAX(j.application_close_date) IS NOT NULL
                )
                INSERT INTO company_hiring_windows (
                    company_name, company_slug, window_type, event_date, year, verified, notes
                )
                SELECT 
                    je.company_name, je.company_slug, je.window_type, je.event_date, je.year, false, 'Auto-derived from recent jobs'
                FROM job_events je
                WHERE NOT EXISTS (
                    SELECT 1 FROM company_hiring_windows w 
                    WHERE w.company_name = je.company_name 
                      AND w.window_type = je.window_type 
                      AND w.event_date = je.event_date
                );
            """
            result = await session.execute(text(sql))
            await session.commit()
            logger.info("refresh_calendar_completed", rows_inserted=result.rowcount)
    except Exception as e:
        logger.error("refresh_calendar_error", error=str(e))

@shared_task(name='refresh_calendar_from_jobs')
def refresh_calendar_from_jobs():
    """
    Runs nightly. For each job scraped in the last 30 days:
    - If application_close_date is set, ensure a company_hiring_windows row exists.
    - Group jobs by company, find earliest first_seen_at as proxy open date.
    - Insert/upsert into company_hiring_windows.
    """
    run_async(_refresh_calendar())
