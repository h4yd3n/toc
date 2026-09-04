import pytest
import json
from datetime import datetime, timezone
from shared.database import create_engine, async_session_factory, init_db
from shared.db_models import LedgerEventRow
from shared.ledger import AsyncDatabaseEventLedger
import pytest_asyncio

@pytest_asyncio.fixture
async def async_session():
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    session_factory = async_session_factory(engine)
    yield session_factory
    await engine.dispose()

@pytest.mark.asyncio
async def test_async_ledger_persistence(async_session):
    ledger = AsyncDatabaseEventLedger(async_session)
    content_id = "test-content-1"
    
    evt1 = await ledger.append_event(
        content_id=content_id,
        event_type="create",
        actor_type="user",
        actor_id="user1"
    )
    
    evt2 = await ledger.append_event(
        content_id=content_id,
        event_type="report",
        actor_type="user",
        actor_id="user2"
    )
    
    evt3 = await ledger.append_event(
        content_id=content_id,
        event_type="moderate",
        actor_type="admin",
        actor_id="admin1",
        new_state="removed"
    )
    
    history = await ledger.get_content_history(content_id)
    assert len(history) == 3
    
    assert history[0].event_id == evt1.event_id
    assert history[1].event_id == evt2.event_id
    assert history[2].event_id == evt3.event_id
    
    assert history[0].prev_hash is None
    assert history[1].prev_hash is not None
    assert history[2].prev_hash is not None
    
    assert history[1].prev_hash == evt2.prev_hash
    assert history[2].prev_hash == evt3.prev_hash
    
    assert await ledger.verify_chain_integrity(content_id)

@pytest.mark.asyncio
async def test_ledger_event_row_roundtrip(async_session):
    async with async_session() as session:
        row = LedgerEventRow(
            event_id="test-event-1",
            content_id="test-content-1",
            event_type="create",
            actor_type="user",
            actor_id="user1",
            metadata_json=json.dumps({"key": "value"}),
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        session.add(row)
        await session.commit()
        
        from sqlalchemy import select
        stmt = select(LedgerEventRow).where(LedgerEventRow.event_id == "test-event-1")
        result = await session.execute(stmt)
        fetched_row = result.scalar_one()
        
        assert fetched_row.content_id == "test-content-1"
        assert fetched_row.actor_id == "user1"
