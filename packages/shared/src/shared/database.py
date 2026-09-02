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
