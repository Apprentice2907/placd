from datetime import datetime
from pydantic import BaseModel, Field

class JobData(BaseModel):
    external_id: str
    title: str
    description: str
    apply_url: str
    source: str
    job_type: str
    location: str
    is_remote: bool
    company_slug: str
    company_name: str
    raw_data: dict = Field(default_factory=dict)
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
