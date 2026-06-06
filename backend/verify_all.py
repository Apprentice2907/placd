import subprocess
import datetime
import sys

scrapers = [
    "scrapers.google.adapter",
    "scrapers.amazon.adapter",
    "scrapers.microsoft.adapter",
    "scrapers.meta.adapter",
    "scrapers.apple.adapter",
    "scrapers.netflix.adapter",
    "scrapers.greenhouse.adapter",
    "scrapers.lever.adapter",
    "scrapers.ashby.adapter",
    "scrapers.himalayas.adapter",
    "scrapers.remoteok.adapter",
    "scrapers.cutshort.adapter",
    "scrapers.naukri.adapter",
    "scrapers.internshala.adapter",
    "scrapers.jobspy.adapter",
    "scrapers.weworkremotely.adapter",
    "scrapers.bamboohr.adapter",
    "scrapers.recruitee.adapter",
    "scrapers.wellfound.adapter",
    "scrapers.workday.company_scraper"
]

with open("scraper_results.txt", "w", encoding="utf-8") as f:
    f.write(f"SCRAPER VERIFICATION — {datetime.datetime.now()}\n")
    f.write("================================\n")

for s in scrapers:
    print(f"Running {s}...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", s], 
            capture_output=True, 
            text=True, 
            timeout=1200
        )
        with open("scraper_results.txt", "a", encoding="utf-8") as f:
            f.write(f"\n--- {s} ---\n")
            f.write(result.stdout)
            if result.stderr:
                f.write(f"STDERR:\n{result.stderr}")
    except Exception as e:
        with open("scraper_results.txt", "a", encoding="utf-8") as f:
            f.write(f"\n--- {s} ---\n")
            f.write(f"FAILED TO RUN: {e}\n")
    
print("All done.")
