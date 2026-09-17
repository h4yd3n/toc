import os
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

def create_engine(url: str = None) -> AsyncEngine:
    if url is None:
        url = os.environ.get('DATABASE_URL', 'sqlite+aiosqlite:///./toc.db')
    return create_async_engine(url, echo=False)

def async_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)

async def init_db(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await add_missing_columns(engine)


# create_all makes tables that are missing; it never adds a column to a table that already exists. A deployment
# carrying live data would otherwise fail on the first SELECT after a model grew a field, so the columns added since
# the first release are listed here and added if absent. SQLite only, which is what every deployment runs today.
ADDED_COLUMNS = [
    ("toc_ai_assignments", "location_id", "VARCHAR"),
    ("toc_ai_runs", "instruction", "TEXT DEFAULT ''"),
    ("toc_ai_runs", "retry_at", "DATETIME"),
    ("cop_locations", "is_toc", "BOOLEAN DEFAULT 0"),   # §3.1 the CP the TOC is running from
    ("cop_graphics", "confidence", "TEXT DEFAULT 'confirmed'"),
    ("cop_graphics", "basis", "TEXT DEFAULT ''"),
    ("s2_reports", "status", "TEXT DEFAULT 'filed'"),
    ("s2_reports", "disposition", "TEXT"),
    ("s2_reports", "disposition_target_type", "TEXT"),
    ("s2_reports", "disposition_target_id", "TEXT"),
    ("s2_reports", "disposed_by", "TEXT"),
    ("s2_reports", "disposed_at", "DATETIME"),
    ("s2_reports", "disposition_note", "TEXT"),
    ("cop_taskings", "created_type", "VARCHAR"),
    ("cop_taskings", "created_id", "VARCHAR"),
    ("cop_taskings", "created_parent", "VARCHAR"),
    ("cop_taskings", "created_name", "VARCHAR DEFAULT ''"),
    ("toc_ai_assignments", "subject_type", "VARCHAR"),   # §5.12 an assignment scoped to an operation or a requirement
    ("toc_ai_assignments", "subject_id", "VARCHAR"),
    ("cop_intake_submissions", "kind", "VARCHAR DEFAULT 'shipment'"),   # §5.13 intake beyond S4
    ("toc_users", "password_hash", "VARCHAR"),          # the sign-in layer in front of the profile picker
    ("toc_users", "password_set_at", "DATETIME"),
    ("cop_supply", "daily_use", "FLOAT"),               # §7 days of supply, from the rate S4 enters
]


async def add_missing_columns(engine: AsyncEngine):
    if engine.dialect.name != "sqlite":
        return
    from sqlalchemy import text
    async with engine.begin() as conn:
        for table, column, decl in ADDED_COLUMNS:
            rows = (await conn.execute(text(f"PRAGMA table_info({table})"))).fetchall()
            if rows and not any(r[1] == column for r in rows):
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {decl}"))
