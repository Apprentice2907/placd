# Contributing to Placd

Thank you for contributing to Placd! We rely on community contributions to maintain our vast network of ATS and job board integrations.

## Setting up your local dev environment

Placd uses Docker to orchestrate PostgreSQL, Redis, FastAPI, and Celery.
1. Clone the repository and configure your `.env` file from `.env.example`.
2. Start the local stack:
   ```bash
   docker compose up -d
   ```
3. Run the initial database migration and seeding (if setting up fresh):
   ```bash
   docker compose exec api alembic upgrade head
   docker compose exec api python scripts/seed_calendar.py
   ```

## Branch naming convention
When submitting a pull request, please follow these branch naming conventions:
- `feature/your-feature-name`
- `fix/issue-description`
- `scraper/company-or-ats-name`

## PR requirements
When submitting your pull request, please ensure:
- You include a description of what you scraped and the ATS you integrated with.
- You state how many real jobs the scraper returned during your local test run.
- **NO MOCK DATA**: We only accept real, live job listings. Mock data PRs will be rejected.
- You verify that rate-limiting and delays are respected (no aggressive crawling).

## Adding a new Tier A scraper
Tier A scrapers rely on public JSON APIs (e.g., Lever, Greenhouse). To add a new Tier A scraper:
1. Create a new adapter in `backend/scrapers/`.
2. Inherit from the base crawler configuration.
3. Review `backend/scrapers/greenhouse_adapter.py` for the standard pattern and data normalization rules.

## Adding a new Tier B scraper
Tier B scrapers pull from structured XML feeds or job postings (e.g., Workday).
1. Create a new module in `backend/scrapers/structured/`.
2. Review `backend/scrapers/structured/workday.py` for guidance on XML parsing and handling pagination.
