from datetime import datetime

SOURCE_MULTIPLIERS = {
    "greenhouse": 1.0,
    "lever": 1.0,
    "ashby": 1.0,
    "workable": 1.0,
    "recruitee": 1.0,
    "bamboohr": 0.95,
    "himalayas": 0.95,
    "cutshort": 0.95,
    "remoteok": 0.95,
    "internshala": 0.9,
    "wellfound": 0.9,
    "weworkremotely": 0.9,
    "naukri": 0.85,
    "instahyre": 0.85,
    "linkedin": 0.8,
}

def freshness_score(created_at: datetime, updated_at: datetime, source: str) -> float:
    """
    Calculates a freshness score (0.0 to 1.0) based on how old the job is and the reliability of its source.
    """
    now = datetime.utcnow()
    
    # We use created_at to determine true age (if available), otherwise fallback to updated_at or now
    base_date = created_at or updated_at or now
    
    # Strip timezone for age calculation if 'now' is naive and base_date is timezone aware
    if base_date.tzinfo is not None:
        base_date = base_date.replace(tzinfo=None)
        
    age_days = (now - base_date).days
    
    # Linear decay over 30 days. Cap between 0 and 1
    base_score = max(0.0, 1.0 - (age_days / 30.0))
    
    # Apply source multiplier
    multiplier = SOURCE_MULTIPLIERS.get(source.lower() if source else "", 0.9)
    
    return float(base_score * multiplier)
