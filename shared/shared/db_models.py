from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

class LedgerEventRow(Base):
    __tablename__ = "ledger_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String, unique=True)
    content_id: Mapped[str] = mapped_column(String, index=True)
    event_type: Mapped[str] = mapped_column(String)
    actor_type: Mapped[str] = mapped_column(String)
    actor_id: Mapped[str] = mapped_column(String)
    policy_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    old_state: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    new_state: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prev_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class ModerationDecisionRow(Base):
    __tablename__ = "moderation_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[str] = mapped_column(String, unique=True)
    content_id: Mapped[str] = mapped_column(String, index=True)
    policy_id: Mapped[str] = mapped_column(String)
    policy_version: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float)
    action: Mapped[str] = mapped_column(String)
    new_visibility: Mapped[str] = mapped_column(String)
    rationale: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String)
    decided_at: Mapped[datetime] = mapped_column(DateTime)

class ContentStateRow(Base):
    __tablename__ = "content_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    author_id: Mapped[str] = mapped_column(String)
    current_visibility: Mapped[str] = mapped_column(String, default='visible')
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
