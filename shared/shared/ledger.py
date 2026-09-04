import hashlib
import uuid
import json
from datetime import timezone
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from shared.models import LedgerEvent
from shared.db_models import LedgerEventRow

class ImmutableEventLedger:
    """
    Append-only immutable audit ledger.
    Every detection, visibility transition, reach gate trip, and human decision
    is recorded sequentially.
    Provides complete EU DSA 'statement of reasons' compliance and QA traceability.
    """

    def __init__(self):
        # Maps content_id -> list of LedgerEvents
        self._ledger: Dict[str, List[LedgerEvent]] = {}
        self._last_hash: Dict[str, str] = {}

    def append_event(
        self,
        content_id: str,
        event_type: str,
        actor_type: str,
        actor_id: str,
        policy_version: Optional[str] = None,
        old_state: Optional[str] = None,
        new_state: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> LedgerEvent:
        prev_hash = self._last_hash.get(content_id)
        event = LedgerEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:12]}",
            content_id=content_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            policy_version=policy_version,
            old_state=old_state,
            new_state=new_state,
            reason=reason,
            metadata=metadata or {},
            prev_hash=prev_hash,
        )
        if content_id not in self._ledger:
            self._ledger[content_id] = []
        self._ledger[content_id].append(event)
        self._last_hash[content_id] = hashlib.sha256(event.model_dump_json().encode('utf-8')).hexdigest()
        return event

    def get_content_history(self, content_id: str) -> List[LedgerEvent]:
        return list(self._ledger.get(content_id, []))

    def verify_chain_integrity(self, content_id: str) -> bool:
        history = self.get_content_history(content_id)
        if not history:
            return True
            
        expected_prev_hash = None
        for event in history:
            if event.prev_hash != expected_prev_hash:
                return False
            expected_prev_hash = hashlib.sha256(event.model_dump_json().encode('utf-8')).hexdigest()
        return True

class AsyncDatabaseEventLedger:
    """
    Async database-backed append-only immutable audit ledger.
    """

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def get_content_history(self, content_id: str) -> List[LedgerEvent]:
        async with self.session_factory() as session:
            stmt = select(LedgerEventRow).where(LedgerEventRow.content_id == content_id).order_by(LedgerEventRow.id)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            
            events = []
            for row in rows:
                metadata = json.loads(row.metadata_json) if row.metadata_json else {}
                event = LedgerEvent(
                    event_id=row.event_id,
                    content_id=row.content_id,
                    event_type=row.event_type,
                    actor_type=row.actor_type,
                    actor_id=row.actor_id,
                    policy_version=row.policy_version,
                    old_state=row.old_state,
                    new_state=row.new_state,
                    reason=row.reason,
                    metadata=metadata,
                    timestamp=row.timestamp.replace(tzinfo=timezone.utc) if row.timestamp.tzinfo is None else row.timestamp,
                    prev_hash=row.prev_hash
                )
                events.append(event)
            return events

    async def append_event(
        self,
        content_id: str,
        event_type: str,
        actor_type: str,
        actor_id: str,
        policy_version: Optional[str] = None,
        old_state: Optional[str] = None,
        new_state: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> LedgerEvent:
        history = await self.get_content_history(content_id)
        prev_hash = None
        if history:
            prev_event = history[-1]
            prev_hash = hashlib.sha256(prev_event.model_dump_json().encode('utf-8')).hexdigest()

        metadata_dict = metadata or {}
        event_id = f"EVT-{uuid.uuid4().hex[:12]}"
        
        event = LedgerEvent(
            event_id=event_id,
            content_id=content_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            policy_version=policy_version,
            old_state=old_state,
            new_state=new_state,
            reason=reason,
            metadata=metadata_dict,
            prev_hash=prev_hash,
        )

        row = LedgerEventRow(
            event_id=event.event_id,
            content_id=event.content_id,
            event_type=event.event_type,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            policy_version=event.policy_version,
            old_state=event.old_state,
            new_state=event.new_state,
            reason=event.reason,
            prev_hash=event.prev_hash,
            metadata_json=json.dumps(event.metadata),
            timestamp=event.timestamp.replace(tzinfo=None)
        )

        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            
        return event

    async def verify_chain_integrity(self, content_id: str) -> bool:
        history = await self.get_content_history(content_id)
        if not history:
            return True
            
        expected_prev_hash = None
        for event in history:
            if event.prev_hash != expected_prev_hash:
                return False
            expected_prev_hash = hashlib.sha256(event.model_dump_json().encode('utf-8')).hexdigest()
        return True
