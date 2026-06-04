from workers.opportunity_tasks import crawl_all_opportunities_task

print("Triggering crawl_all_opportunities_task...")
res = crawl_all_opportunities_task.delay()
print(f"Task queued with ID: {res.id}")
