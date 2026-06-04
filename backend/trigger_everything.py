from workers.crawlers import crawl_all_companies_task
from workers.playwright_tasks import scrape_linkedin_task, scrape_wellfound_task
from workers.opportunity_tasks import crawl_all_opportunities_task

print("Triggering crawl_all_companies_task...")
crawl_all_companies_task.delay()

print("Triggering scrape_wellfound_task...")
scrape_wellfound_task.delay()

print("Triggering scrape_linkedin_task...")
scrape_linkedin_task.delay("software engineer", "United States")

print("Triggering crawl_all_opportunities_task...")
crawl_all_opportunities_task.delay()

print("All top-level scrapers have been triggered!")
