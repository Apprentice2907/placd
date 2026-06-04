from scrapers.himalayas.adapter import HimalayasAdapter
from scrapers.remoteok.adapter import scrape_remoteok  
from utils.async_utils import run_async
from db.database import async_save_jobs
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def run():
    print("Testing Himalayas...")
    jobs = await HimalayasAdapter().fetch_jobs()
    print(f'Himalayas: {len(jobs)} jobs')
    await async_save_jobs(jobs)

    print("Testing RemoteOK...")
    jobs2 = await scrape_remoteok()
    print(f'RemoteOK: {len(jobs2)} jobs')
    await async_save_jobs(jobs2)

run_async(run())
