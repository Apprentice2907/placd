import asyncio
import datetime
import importlib
import traceback

scrapers = [
    ("scrapers.google.adapter", "GoogleAdapter"),
    ("scrapers.amazon.adapter", "AmazonAdapter"),
    ("scrapers.microsoft.adapter", "MicrosoftAdapter"),
    ("scrapers.meta.adapter", "MetaAdapter"),
    ("scrapers.apple.adapter", "AppleAdapter"),
    ("scrapers.netflix.adapter", "NetflixAdapter"),
    ("scrapers.greenhouse.adapter", "GreenhouseAdapter"),
    ("scrapers.lever.adapter", "LeverAdapter"),
    ("scrapers.ashby.adapter", "AshbyAdapter"),
    ("scrapers.himalayas.adapter", "HimalayasAdapter"),
    ("scrapers.remoteok.adapter", "RemoteOKAdapter"),
    ("scrapers.cutshort.adapter", "CutshortAdapter"),
    ("scrapers.naukri.adapter", "NaukriAdapter"),
    ("scrapers.internshala.adapter", "InternshalaAdapter"),
    ("scrapers.jobspy.adapter", "JobSpyAdapter"),
    ("scrapers.weworkremotely.adapter", "WeWorkRemotelyAdapter"),
    ("scrapers.bamboohr.adapter", "BambooHRAdapter"),
    ("scrapers.recruitee.adapter", "RecruiteeAdapter"),
    ("scrapers.wellfound.adapter", "WellfoundAdapter"),
    ("scrapers.workday.company_scraper", "WorkdayCompanyScraper")
]

results = {}

async def run_scraper(module_name, cls_name):
    try:
        mod = importlib.import_module(module_name)
        if hasattr(mod, cls_name):
            adapter_cls = getattr(mod, cls_name)
        else:
            adapter_cls = None
            # fallback if it's named something else
            for name, obj in vars(mod).items():
                if isinstance(obj, type) and hasattr(obj, 'fetch_jobs') and name != 'UnifiedAdapter':
                    adapter_cls = obj
                    break
        
        if not adapter_cls:
            return f"FAILED: Could not find adapter class in {module_name}"
            
        adapter = adapter_cls()
        jobs = await adapter.fetch_jobs()
        
        out = f"{adapter.source}: {len(jobs)} jobs\n"
        if jobs:
            j = jobs[0]
            out += f"  Title: {j.get('title')}\n"
            out += f"  Company: {j.get('company')}\n"
            out += f"  Location: {j.get('location')}\n"
            out += f"  URL: {j.get('apply_url')}\n"
            desc = str(j.get('description', ''))[:150]
            out += f"  Desc preview: {desc}\n"
        return out
    except Exception as e:
        return f"FAILED: {e}\n{traceback.format_exc()}"

async def main():
    print("Starting fast verification...")
    with open("scraper_results.txt", "w", encoding="utf-8") as f:
        f.write(f"SCRAPER VERIFICATION — {datetime.datetime.now()}\n")
        f.write("================================\n")
        
    tasks = []
    for mod, cls in scrapers:
        tasks.append(run_scraper(mod, cls))
        
    outputs = await asyncio.gather(*tasks, return_exceptions=True)
    
    with open("scraper_results.txt", "a", encoding="utf-8") as f:
        for (mod, _), out in zip(scrapers, outputs):
            f.write(f"\n--- {mod} ---\n")
            if isinstance(out, Exception):
                f.write(f"UNHANDLED EXCEPTION: {out}\n")
            else:
                f.write(str(out) + "\n")
                
    print("Done writing to scraper_results.txt")

if __name__ == "__main__":
    asyncio.run(main())
