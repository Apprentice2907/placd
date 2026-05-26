"""
Placd — PostgreSQL Connection Setup
Async SQLAlchemy 2.0 configuration with asyncpg.
"""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from dotenv import load_dotenv

# Load from .env if present
load_dotenv()

# Read DATABASE_URL from environment or fallback to default compose setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/placd")

from sqlalchemy.pool import NullPool

# Create Async Engine
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        yield session

async def close_db_connection():
    """Close engine connection pool."""
    await engine.dispose()
