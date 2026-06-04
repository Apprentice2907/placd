from workers.celery_config import app

print("--- Celery Beat Schedule ---")
beat_schedule = app.conf.beat_schedule
for name, config in beat_schedule.items():
    print(f'{name}: {config["schedule"]}')
