from workers.opportunity_tasks import scrape_opportunities_task

print("Triggering scrape_opportunities_task...")
res = scrape_opportunities_task.delay("https://opportunitiescorners.com/")
print(f"Task queued with ID: {res.id}")
