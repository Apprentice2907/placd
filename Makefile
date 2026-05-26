.PHONY: up down logs migrate seed crawl-now stats shell

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

migrate:
	docker-compose exec api python -m db.migrate # Adjust this to your migration script path

seed:
	docker-compose exec celery-worker celery -A workers.crawlers call workers.crawlers.seed_companies_task # Replace with correct seed task/script

crawl-now:
	docker-compose exec celery-worker celery -A workers.crawlers call workers.crawlers.trigger_crawlers_task # Replace with correct crawl trigger task/script

stats:
	docker-compose exec api curl -s http://localhost:8000/api/stats | grep -o '{"total_jobs":[^}]*}' # Or run a quick python script

shell:
	docker-compose exec api bash
