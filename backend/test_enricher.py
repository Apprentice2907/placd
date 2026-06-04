import asyncio
import json
import logging
import os
from workers.enricher import extract_jobs_batch

logging.basicConfig(level=logging.INFO)

async def test_enrich():
    jobs = [
        {
            "id": "mock_id_1",
            "title": "Senior Frontend Engineer",
            "company_name": "Stripe",
            "location": "San Francisco, CA (Remote)",
            "description": "We are looking for a Senior Frontend Engineer with 5+ years of React experience. You will work on our dashboard, using React, TypeScript, and GraphQL. We offer a competitive salary of $150,000 - $200,000 + equity. Full remote work allowed. Visa sponsorship available for the right candidate."
        },
        {
            "id": "mock_id_2",
            "title": "Machine Learning Intern",
            "company_name": "OpenAI",
            "location": "San Francisco",
            "description": "Join our 12-week summer internship! You must have experience in Python and PyTorch. Preferred skills include CUDA and C++. No visa sponsorship for interns. Onsite required."
        }
    ]
    
    # We use generate_content which is synchronous in our code, so no await
    results, cost = extract_jobs_batch(jobs)
    
    print(f"Cost: ${cost:.4f}")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    if "GEMINI_API_KEY" not in os.environ:
        print("Set GEMINI_API_KEY to test.")
    else:
        # even though we call it async test_enrich, extract_jobs_batch is sync
        asyncio.run(test_enrich())
