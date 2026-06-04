"""
Placd — PostgreSQL Schema Migration Runner

Applies the schema from schema.sql to ensure all tables and indexes exist.
This replaces the old run_migration.py which operated on jobs.db (removed).
"""
import asyncio
from pathlib import Path
from sqlalchemy import text
from db.connection import engine


async def run_pg_migration():
    """Apply schema.sql to the PostgreSQL database."""
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    
    print(f"Applying schema from: {schema_path}")
    
    async with engine.begin() as conn:
        for statement in schema_sql.split(";"):
            stmt = statement.strip()
            if stmt and not stmt.startswith("--"):
                try:
                    await conn.execute(text(stmt))
                except Exception as e:
                    print(f"  Note: {e}")
    
    print("PostgreSQL migration complete!")


if __name__ == "__main__":
    asyncio.run(run_pg_migration())
