from sqlalchemy import text as sa_text

def build_query(job_type):
    status = "active"
    trust_min = 30
    where_parts = [f"status = '{status}'", "is_spam = FALSE", f"trust_score >= {trust_min}"]
    params = {}

    if job_type:
        types = [t.strip() for t in job_type.split(',')]
        type_conditions = []
        for i, t in enumerate(types):
            if "intern" in t.lower():
                type_conditions.append("is_internship = TRUE")
            elif "full" in t.lower():
                type_conditions.append("job_type ILIKE '%full%'")
            elif "part" in t.lower():
                type_conditions.append("job_type ILIKE '%part%'")
            else:
                type_conditions.append(f"job_type ILIKE :job_type_{i}")
                params[f"job_type_{i}"] = f"%{t}%"
        
        if type_conditions:
            where_parts.append("(" + " OR ".join(type_conditions) + ")")
    
    where_sql = " AND ".join(where_parts)
    print("SQL:", f"SELECT COUNT(*) FROM jobs WHERE {where_sql}")
    print("Params:", params)

build_query("internship")
