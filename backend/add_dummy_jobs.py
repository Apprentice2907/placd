import sqlite3
import json
from datetime import datetime

db = sqlite3.connect('d:/Job Searcher/Placd/backend/placd.db')

# Insert some fake jobs
fake_jobs = [
    (
        "id_1",
        "Frontend Developer",
        "TechNova",
        "San Francisco, CA",
        "We are looking for a skilled Frontend Developer to join our team and build amazing UI components.",
        "https://technova.com/jobs/frontend-developer",
        "https://technova.com/jobs/frontend-developer",
        "custom_script",
        "custom_script",
        "full_time",
        "Engineering",
        datetime.now().isoformat(),
        1, # is_remote
        0, # is_hybrid
        0, # is_sponsored
        0, # is_student_eligible
        85, # trust_score
        "technova.com",
        "https://logo.clearbit.com/technova.com",
        1, # company_tier
        json.dumps(["React", "TypeScript", "TailwindCSS"]),
        100000,
        150000,
        "USD",
        None,
        datetime.now().isoformat(),
        datetime.now().isoformat()
    ),
    (
        "id_2",
        "Backend Engineer",
        "DataCore",
        "Remote",
        "Join DataCore to build highly scalable microservices in Python and Go.",
        "https://datacore.com/careers/backend-engineer",
        "https://datacore.com/careers/backend-engineer",
        "custom_script",
        "custom_script",
        "full_time",
        "Engineering",
        datetime.now().isoformat(),
        1, # is_remote
        0, # is_hybrid
        0, # is_sponsored
        0, # is_student_eligible
        90, # trust_score
        "datacore.com",
        "https://logo.clearbit.com/datacore.com",
        2, # company_tier
        json.dumps(["Python", "Go", "Kubernetes"]),
        120000,
        160000,
        "USD",
        None,
        datetime.now().isoformat(),
        datetime.now().isoformat()
    ),
    (
        "id_3",
        "UI/UX Designer",
        "DesignStudio",
        "New York, NY",
        "Looking for a creative UI/UX designer with a strong portfolio.",
        "https://designstudio.com/jobs/uiux",
        "https://designstudio.com/jobs/uiux",
        "custom_script",
        "custom_script",
        "contract",
        "Design",
        datetime.now().isoformat(),
        0, # is_remote
        1, # is_hybrid
        0, # is_sponsored
        1, # is_student_eligible
        80, # trust_score
        "designstudio.com",
        "https://logo.clearbit.com/designstudio.com",
        3, # company_tier
        json.dumps(["Figma", "Sketch", "Prototyping"]),
        80000,
        110000,
        "USD",
        None,
        datetime.now().isoformat(),
        datetime.now().isoformat()
    ),
    (
        "id_4",
        "Data Scientist",
        "AI Dynamics",
        "London, UK",
        "Help us build the next generation of AI models.",
        "https://aidynamics.com/jobs/data-scientist",
        "https://aidynamics.com/jobs/data-scientist",
        "custom_script",
        "custom_script",
        "full_time",
        "Data Science",
        datetime.now().isoformat(),
        0, # is_remote
        0, # is_hybrid
        1, # is_sponsored
        0, # is_student_eligible
        95, # trust_score
        "aidynamics.com",
        "https://logo.clearbit.com/aidynamics.com",
        1, # company_tier
        json.dumps(["Machine Learning", "Python", "TensorFlow"]),
        130000,
        180000,
        "GBP",
        None,
        datetime.now().isoformat(),
        datetime.now().isoformat()
    )
]

# We need to find the column names first
c = db.cursor()
c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='jobs';")
print("TABLE SCHEMA:")
print(c.fetchone()[0])
