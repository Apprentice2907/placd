# Placd

> Internet-scale job aggregation platform for Indian developers.
> 50,000+ real listings from Greenhouse, Lever, Ashby, Workday, LinkedIn, and more.

![Python](https://img.shields.io/badge/python-3.12-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?style=flat-square)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Docker](https://img.shields.io/badge/docker-compose-2496ED?style=flat-square)

---

## What it does
Placd is a massive-scale job and opportunity aggregator built for software engineers, specifically tuned for the Indian market and global remote roles. It systematically extracts, standardizes, and normalizes real job data from fragmented ATS platforms and job boards. Leveraging semantic search via pgvector and AI enrichment via Gemini 2.5 Flash, it allows developers to quickly find relevant roles, track hiring open/close dates, and discover international fellowships or scholarships.

## Features
- Three-tier crawler: JSON APIs (Greenhouse/Lever/Ashby) → structured XML (Workday/iCIMS/SmartRecruiters) → Playwright fallback (LinkedIn/Naukri/Wellfound)
- Company discovery via CommonCrawl CDX API and seed lists
- Liveness sweeper: HEAD checks every 24h, auto-expires dead links
- AI enrichment: Gemini 2.5 Flash for job classification, skills, salary extraction
- Semantic search: pgvector (text-embedding-004) + full-text search cached in Redis
- International opportunities: scholarships, fellowships, exchange programs
- Hiring calendar: application open/close dates plotted by company
- Celery + Redis for all async crawling, enrichment, and freshness sweeping
- React 19 dashboard with category filters, infinite scroll, job detail panels

## Architecture

```text
Tier A — Public JSON APIs (no auth, high volume):
  Greenhouse · Lever · Ashby · Workable

Tier B — Structured scraping (httpx + lxml, no browser):
  Workday XML · iCIMS XML · SmartRecruiters · schema.org JobPosting

Tier C — Playwright (last resort, bot-protected sites):
  LinkedIn · Wellfound · Naukri · Internshala


React frontend → FastAPI → PostgreSQL + pgvector
                         → Redis (cache + queue)
                         → Celery workers (crawl / enrich / sweep)
                         → Playwright pool (Tier C)
```

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async, asyncpg |
| Database | PostgreSQL 16, pgvector, Redis |
| Task queue | Celery, Celery Beat, Flower |
| Scraping | httpx, BeautifulSoup, Playwright, extruct |
| AI | Gemini 2.5 Flash, text-embedding-004 |
| Frontend | React 19, Vite, TypeScript, Tailwind CSS, shadcn/ui |
| Infra | Docker, Docker Compose |

## Getting started

### Prerequisites
- Docker and Docker Compose
- A Gemini API key (for enrichment — scrapers work without it)

### Quick start
```bash
git clone https://github.com/YOUR_USERNAME/placd.git
cd placd
cp .env.example .env
# Edit .env — add your GEMINI_API_KEY and DATABASE_URL
docker compose up -d
```

Then open http://localhost:5173 for the dashboard,
http://localhost:8000/docs for the API,
http://localhost:5555 for Flower (task monitor).

### Run your first crawl
```bash
# Crawl a single company (Greenhouse)
docker compose exec celery-worker python -c \
  "from scrapers.greenhouse_adapter import GreenhouseCrawler; \
   import asyncio; asyncio.run(GreenhouseCrawler().crawl_company('stripe'))"

# Trigger full crawl via Celery
docker compose exec celery-worker celery call tasks.crawl_all_companies_task
```

### Seed the company list
Run the discovery pipeline to fetch seeded companies or run the CommonCrawl CDX discovery process:
```bash
docker compose exec celery-worker celery -A workers.crawlers call workers.crawlers.seed_companies_task
```

## Project structure
```text
.
├── backend/
│   ├── alembic/                # Database migrations
│   ├── api/                    # FastAPI routers and app configuration
│   ├── db/                     # PostgreSQL models and connection pool
│   ├── scrapers/               # Tier A, B, and C crawler implementations
│   ├── workers/                # Celery tasks (crawling, liveness, enriching)
│   └── Dockerfile              # Backend and Celery container definition
├── frontend/
│   ├── src/                    # React 19 dashboard UI and components
│   └── Dockerfile              # Frontend container definition
├── scripts/                    # Utility scripts (e.g., seed_calendar.py)
├── docker-compose.yml          # Local infrastructure orchestration
└── Makefile                    # Make targets for local dev shortcuts
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| DATABASE_URL | Yes | PostgreSQL connection string |
| REDIS_URL | Yes | Redis connection string |
| SERPAPI_KEY | No | Key for SERP API searches |
| GEMINI_API_KEY | No | Required only for AI enrichment |
| OPENAI_API_KEY | No | Alternative AI provider key |
| SECRET_KEY | Yes | Application security secret |
| CORS_ORIGINS | Yes | Allowed CORS origins for the frontend |
| PLAYWRIGHT_ENABLED | No | Toggle to run Tier C headless browsers |
| PROXY_LIST | No | Proxies for Playwright fallback |
| LOG_LEVEL | No | Application logging level (e.g., INFO, DEBUG) |

## Data sources

| Source | Tier | Type | Notes |
|---|---|---|---|
| Greenhouse | A | Jobs API | ~8,000 companies |
| Lever | A | Jobs API | ~3,000 companies |
| Ashby | A | Jobs API | Growing, AI-native startups |
| Workday | B | XML feed | Enterprise, FAANG |
| iCIMS | B | XML feed | Mid-market |
| SmartRecruiters | B | Structured | Global |
| LinkedIn | C | Playwright | Rate-limited, supplemental |
| Wellfound | C | Playwright | Startup-focused |
| Naukri | C | Playwright | India-specific |
| Internshala | C | Playwright | India internships |
| OpportunitiesCorners | B | Scraper | Scholarships/fellowships |
| OpportunitiesCircle | B | Scraper | International opportunities |

## Roadmap
- [ ] Resume builder (Gemini 2.5 Pro)
- [ ] ATS keyword optimizer per job description  
- [ ] Email/Telegram alerts for new matching jobs
- [ ] More Tier A sources (Rippling, Workable, Personio)
- [ ] Mobile app

## Contributing
- Fork → branch → PR
- Run tests before submitting
- No mock/fake data PRs accepted

## License
MIT
