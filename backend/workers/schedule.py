from celery.schedules import crontab

# This configuration should be loaded into your Celery application instance (e.g., celery_app.conf.beat_schedule)
beat_schedule = {
    'crawl-all-companies-every-6-hours': {
        'task': 'crawl_all_companies_task',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    'liveness-sweep-every-24-hours': {
        'task': 'liveness_sweep_task',
        'schedule': crontab(minute=0, hour=3), # Run at 3 AM daily
    },
    'discover-companies-every-7-days': {
        'task': 'discover_companies_task',
        'schedule': crontab(minute=0, hour=0, day_of_week=0), # Run every Sunday at midnight
    },
    'crawl-opportunities-daily': {
        'task': 'crawl_all_opportunities',
        'schedule': crontab(hour=6, minute=0),  # Daily at 06:00 UTC
    },
    'sweep-expired-opportunities': {
        'task': 'sweep_expired_opportunities',
        'schedule': crontab(hour='*/6', minute=0),  # Every 6 hours
    },
    'refresh-calendar-from-jobs': {
        'task': 'refresh_calendar_from_jobs',
        'schedule': crontab(hour=2, minute=0),      # Nightly at 02:00 UTC
    },
}
