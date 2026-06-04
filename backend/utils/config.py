"""
Placd — Configuration
Loads environment variables and defines project-wide constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ─── Project Paths ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
RESUMES_DIR = BASE_DIR / "resumes"

# Ensure directories exist
OUTPUTS_DIR.mkdir(exist_ok=True)
RESUMES_DIR.mkdir(exist_ok=True)

# ─── Database ────────────────────────────────────────────────────────────────
# PostgreSQL connection is configured in db/connection.py via DATABASE_URL env var.
# No local file-based database is used.

# ─── API Keys ────────────────────────────────────────────────────────────────
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")

# ─── Scraping Settings ──────────────────────────────────────────────────────
REQUEST_TIMEOUT = 30       # seconds
REQUEST_DELAY = (2, 5)     # random delay range between requests (seconds)
MAX_PAGES = 5              # max pages to scrape per source
MAX_RETRIES = 3            # retry attempts for transient HTTP errors
RETRY_BACKOFF = 2.0        # exponential backoff base in seconds
NAUKRI_RESULTS_PER_PAGE = 20  # listings per API page (max ~50 before Naukri rejects)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# ─── Concurrency Settings (Semaphores) ──────────────────────────────────────
INTERNSHALA_CONCURRENCY = 5
NAUKRI_CONCURRENCY = 3
GOOGLE_CONCURRENCY = 10
PLAYWRIGHT_MAX_CONCURRENCY = 2

# ─── Filter Defaults ────────────────────────────────────────────────────────
DEFAULT_SKILLS = [
    "python", "javascript", "react", "flask", "django",
    "sql", "machine learning", "data science", "api",
    "html", "css", "git", "docker", "pandas", "numpy",
]
MIN_MATCH_SCORE = 0.3  # minimum overlap ratio to consider a job relevant

# ─── Google Sheets ───────────────────────────────────────────────────────────
GOOGLE_SHEETS_CREDS = BASE_DIR / "credentials.json"
SPREADSHEET_NAME = "Placd Job Tracker"

# ─── ATS Configuration ─────────────────────────────────────────────────────────
ATS_COMPANIES = {
    "greenhouse": [
        {"name": "Stripe", "board_token": "stripe", "priority": 10, "company_type": "fintech", "tags": ["Fintech", "Unicorn"]},
        {"name": "OpenAI", "board_token": "openai", "priority": 10, "company_type": "ai_company", "tags": ["AI", "Unicorn", "Research"]},
        {"name": "Anthropic", "board_token": "anthropic", "priority": 10, "company_type": "ai_company", "tags": ["AI", "Unicorn", "Research"]},
        {"name": "Scale AI", "board_token": "scaleai", "priority": 10, "company_type": "ai_company", "tags": ["AI", "Unicorn"]},
        {"name": "HuggingFace", "board_token": "huggingface", "priority": 9, "company_type": "ai_company", "tags": ["AI", "OpenSource"]},
        {"name": "Notion", "board_token": "notion", "priority": 10, "company_type": "startup", "tags": ["Productivity", "Unicorn"]},
        {"name": "Canva", "board_token": "canva", "priority": 9, "company_type": "unicorn", "tags": ["Design", "Unicorn"]},
        {"name": "Figma", "board_token": "figma", "priority": 9, "company_type": "startup", "tags": ["Design", "Unicorn"]},
    ],
    "lever": [
        {"name": "Netflix", "board_token": "netflix", "priority": 10, "company_type": "faang", "tags": ["FAANG", "Entertainment"]},
        {"name": "Postman", "board_token": "postman", "priority": 9, "company_type": "developer_tools", "tags": ["DevTools", "Unicorn"]},
        {"name": "Miro", "board_token": "miro", "priority": 9, "company_type": "remote", "tags": ["Collaboration", "Unicorn", "Remote"]},
        {"name": "Rippling", "board_token": "rippling", "priority": 10, "company_type": "startup", "tags": ["HRTech", "Unicorn"]},
    ],
    "workday": [
        {"name": "Databricks", "url": "https://databricks.wd1.myworkdayjobs.com/databricks_careers", "tenant": "databricks", "priority": 10, "company_type": "bigdata", "tags": ["BigData", "Unicorn"]},
        {"name": "NVIDIA", "url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite", "tenant": "nvidia", "priority": 10, "company_type": "faang", "tags": ["FAANG", "AI", "BigTech"]}
    ],
    "ashby": [
        {"name": "Notion", "board_token": "notion", "priority": 9, "company_type": "startup", "tags": ["Productivity", "Unicorn"]}
    ],
    "smartrecruiters": [
        {"name": "Square", "board_token": "Square", "priority": 9, "company_type": "fintech", "tags": ["Fintech", "BigTech"]}
    ]
}

# ─── Ranking ────────────────────────────────────────────────────────────────
SOURCE_WEIGHTS = {
    "greenhouse": 1.0,
    "lever": 1.0,
    "workday": 1.0,
    "ashby": 1.0,
    "smartrecruiters": 1.0,
    "remoteok": 0.9,
    "weworkremotely": 0.9,
    "linkedin": 0.8,
    "linkedin_apify": 0.85,
    "wellfound": 0.8,
    "google_jobs": 0.8,
    "naukri": 0.6,
    "internshala": 0.4
}
