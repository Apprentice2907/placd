import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from utils.minhash_lsh import deduplicator

async def main():
    jobs = [
        {'title': 'Software Engineer', 'company': 'Stripe', 'location': 'Remote', 'external_id': '1'},
        {'title': 'software engineer', 'company': 'stripe', 'location': 'remote', 'external_id': '2'},
        {'title': 'Senior Engineer', 'company': 'Stripe', 'location': 'Remote', 'external_id': '3'}
    ]
    
    unique = await deduplicator.bulk_deduplicate(jobs)
    print(f"Unique IDs: {[j.get('external_id') for j in unique]}")
    print(f"Modified jobs: {jobs}")

if __name__ == "__main__":
    asyncio.run(main())
