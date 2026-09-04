"""§5.10 #4 — dissemination is tracked. "Right people, right time" is a measurable: who a product went to, when, and
whether they acknowledged it. Latency from the product's creation → sent → acknowledged is on the record, and a
warning nobody read is a failure the ledger and the INTSUM show."""
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base
from . import requirements as R

PRODUCT_TYPES = ("assessment", "area", "intsum")
ROLES = ("battle_captain", "ep", "security", "analyst", "ea")
STALE_HOURS = 2  # unacknowledged this long is a failure worth showing


class DistributionRow(Base):
    __tablename__ = "s2_distribution"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    product_type: Mapped[str] = mapped_column(String, index=True)
    product_id: Mapped[str] = mapped_column(String, index=True)
    product_title: Mapped[str] = mapped_column(String, default="")
    recipient: Mapped[str] = mapped_column(String)  # a role, a person id, or a name
    channel: Mapped[str] = mapped_column(String, default="wall")  # wall | chat
    delivery: Mapped[str] = mapped_column(String, default="recorded")  # recorded | sent | simulated | failed
    sent_at: Mapped[datetime] = mapped_column(DateTime)
    sent_by: Mapped[str] = mapped_column(String)
    product_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")


def _mins(a: Optional[datetime], b: Optional[datetime]) -> Optional[int]:
    return round((b - a).total_seconds() / 60) if a and b else None


def row_dict(r: DistributionRow, now: datetime) -> Dict[str, Any]:
    return {"id": r.id, "product_type": r.product_type, "product_id": r.product_id, "product_title": r.product_title, "recipient": r.recipient, "channel": r.channel,
            "delivery": r.delivery, "sent_at": R.iso(r.sent_at), "sent_by": r.sent_by, "acknowledged_at": R.iso(r.acknowledged_at), "acknowledged_by": r.acknowledged_by,
            "latency": {"created_to_sent_min": _mins(r.product_created_at, r.sent_at), "sent_to_ack_min": _mins(r.sent_at, r.acknowledged_at),
                        "outstanding_min": None if r.acknowledged_at else _mins(r.sent_at, now)},
            "stale": (not r.acknowledged_at) and (now - r.sent_at) > timedelta(hours=STALE_HOURS), "note": r.note}


async def for_product(session: AsyncSession, ptype: str, pid: str, now: datetime) -> Dict[str, Any]:
    rows = (await session.execute(select(DistributionRow).where(DistributionRow.product_type == ptype, DistributionRow.product_id == pid).order_by(DistributionRow.sent_at))).scalars().all()
    out = [row_dict(r, now) for r in rows]
    return {"product_type": ptype, "product_id": pid, "recipients": out, "sent": len(out), "acknowledged": sum(1 for r in out if r["acknowledged_at"]),
            "unacknowledged": [r["recipient"] for r in out if not r["acknowledged_at"]], "stale": [r["recipient"] for r in out if r["stale"]]}


async def unacknowledged(session: AsyncSession, now: datetime, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """For the INTSUM: everything sent (in the period, or ever) that nobody acknowledged and that is past the stale line."""
    q = select(DistributionRow).where(DistributionRow.acknowledged_at.is_(None))
    if since is not None: q = q.where(DistributionRow.sent_at > since)
    rows = (await session.execute(q)).scalars().all()
    return [row_dict(r, now) for r in rows if (now - r.sent_at) > timedelta(hours=STALE_HOURS)]


def new_row(ptype: str, pid: str, title: str, recipient: str, channel: str, delivery: str, sent_by: str, now: datetime, created_at: Optional[datetime]) -> DistributionRow:
    return DistributionRow(id=f"dist_{uuid.uuid4().hex[:8]}", product_type=ptype, product_id=pid, product_title=title, recipient=recipient, channel=channel,
                           delivery=delivery, sent_at=now, sent_by=sent_by, product_created_at=created_at)
