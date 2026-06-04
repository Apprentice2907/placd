import uuid
from sqlalchemy import Column, String, Text, Date, DateTime, func, JSON, text
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TIMESTAMP, JSONB
from sqlalchemy.orm import declarative_base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback if pgvector not installed locally, use a custom type
    from sqlalchemy.types import UserDefinedType
    class Vector(UserDefinedType):
        def __init__(self, dim):
            self.dim = dim
        def get_col_spec(self):
            return f"vector({self.dim})"

Base = declarative_base()

class Opportunity(Base):
    __tablename__ = 'opportunities'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url = Column(Text, unique=True, nullable=False)
    url_hash = Column(Text, unique=True, nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text)
    opportunity_type = Column(Text)  # 'scholarship', 'fellowship', etc.
    funding_type = Column(Text)      # 'fully_funded', 'paid', etc.
    country = Column(Text)
    region = Column(Text)
    organization = Column(Text)
    deadline = Column(Date)
    start_date = Column(Date)
    tags = Column(ARRAY(Text))       # GIN index added via alembic or raw sql
    source_name = Column(Text)
    source_site = Column(Text)
    first_seen_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_verified_at = Column(TIMESTAMP(timezone=True))
    status = Column(Text, server_default=text("'active'"))
    description_embedding = Column(Vector(1536))

class Profile(Base):
    __tablename__ = "profiles"
    
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id      = Column(Text, unique=True, nullable=False)
    
    # Personal info
    full_name       = Column(Text)
    email           = Column(Text)
    phone           = Column(Text)
    location        = Column(Text)
    linkedin_url    = Column(Text, nullable=True)
    github_url      = Column(Text, nullable=True)
    portfolio_url   = Column(Text, nullable=True)
    
    # Summary
    professional_summary = Column(Text)
    
    # JSONB Arrays
    education       = Column(JSONB)
    experiences     = Column(JSONB)
    projects        = Column(JSONB)
    skills          = Column(JSONB)
    certifications  = Column(JSONB, nullable=True)
    achievements    = Column(JSONB, nullable=True)
    languages       = Column(JSONB, nullable=True)
    
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
