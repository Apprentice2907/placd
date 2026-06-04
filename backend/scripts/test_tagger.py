"""
Quick unit test for utils/job_tagger.py — no DB required.
Run from backend/:  python scripts/test_tagger.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.job_tagger import is_faang, classify_work_mode, is_internship, tag_job

PASS = 0
FAIL = 0

def check(name, actual, expected):
    global PASS, FAIL
    if actual == expected:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name}  got={actual!r}  want={expected!r}")
        FAIL += 1

print("\n-- FAANG --------------------------------------------------")
check("Google India Pvt Ltd",      is_faang("Google India Pvt Ltd"),      True)
check("Microsoft Corporation",     is_faang("Microsoft Corporation"),     True)
check("Amazon Web Services",       is_faang("Amazon Web Services"),       True)
check("AWS",                       is_faang("AWS"),                       True)
check("OpenAI",                    is_faang("OpenAI"),                    True)
check("Flipkart",                  is_faang("Flipkart"),                  True)
check("GitHub Inc",                is_faang("GitHub Inc"),                True)
check("Some Random Startup",       is_faang("Some Random Startup"),       False)
check("ABC Pvt Ltd",               is_faang("ABC Pvt Ltd"),               False)
check("empty string",              is_faang(""),                          False)

print("\n-- WORK MODE ----------------------------------------------")
check("Remote",                        classify_work_mode("Remote"),                            "remote")
check("Work From Home",                classify_work_mode("Work From Home"),                    "remote")
check("WFH",                           classify_work_mode("WFH"),                              "remote")
check("Remote - India",                classify_work_mode("Remote - India"),                    "remote")
check("Fully Remote",                  classify_work_mode("Fully Remote"),                      "remote")
check("100% Remote",                   classify_work_mode("100% Remote"),                       "remote")
check("Bangalore onsite",              classify_work_mode("Bangalore"),                         "onsite")
check("Mumbai onsite",                 classify_work_mode("Mumbai"),                            "onsite")
check("Hybrid - Bangalore",            classify_work_mode("Hybrid - Bangalore"),                "hybrid")
check("no loc + desc fully remote",    classify_work_mode("", "This is a fully remote role."), "remote")
check("no loc + desc hybrid",          classify_work_mode("Delhi", "hybrid work arrangement"),  "hybrid")

print("\n-- INTERNSHIP ---------------------------------------------")
check("intern title",
      is_internship({"title": "Software Engineer Intern", "description": "x" * 200}), True)
check("summer analyst",
      is_internship({"title": "Summer Analyst", "description": "x" * 200}), True)
check("graduate trainee",
      is_internship({"title": "Graduate Trainee", "description": "x" * 200}), True)
check("employment_type=internship",
      is_internship({"employment_type": "internship", "title": "SDE", "description": "x"}), True)
check("desc signals 2+",
      is_internship({"title": "SDE-1",
                     "description": "We offer a stipend and pre-placement offer for final year students."}), True)
check("SWE senior false-positive",
      is_internship({"title": "Senior Software Engineer", "description": "x" * 200}), False)
check("desc only 1 signal -> false",
      is_internship({"title": "Data Analyst", "description": "stipend negotiable"}), False)

print("\n-- tag_job INTEGRATION ------------------------------------")
job = {
    "title": "Software Engineer Intern",
    "company": "Google India Pvt Ltd",
    "location": "Remote",
    "description": "We offer a stipend and pre-placement offer for final year students.",
}
t = tag_job(job)
check("is_faang=True",      t["is_faang"],      True)
check("is_remote=True",     t["is_remote"],     True)
check("work_mode=remote",   t["work_mode"],     "remote")
check("is_internship=True", t["is_internship"], True)
check("is_hybrid=False",    t["is_hybrid"],     False)

job2 = {"title": "Backend Engineer", "company": "Startup Inc", "location": "Bangalore", "description": "x" * 200}
t2 = tag_job(job2)
check("not faang",     t2["is_faang"],      False)
check("not remote",    t2["is_remote"],     False)
check("onsite",        t2["work_mode"],     "onsite")
check("not internship",t2["is_internship"], False)

print(f"\n{'=' * 55}")
print(f"  Results:  {PASS} passed,  {FAIL} failed")
if FAIL == 0:
    print("  ALL TESTS PASSED")
else:
    print("  SOME TESTS FAILED -- fix before deploying")
print()
sys.exit(0 if FAIL == 0 else 1)
