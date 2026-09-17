"""§5.10b Phase 4 (LOE 5) — sources beyond the feeds: liaison reporting, graded by the analyst over time.

Our own people report at A; a liaison source — host-nation police, a venue's security office, a partner company's
guard force — is a source the analyst grades. A new source starts at F (reliability cannot be judged) and every
report it files carries the source's grade at the time of filing. The track record is derived from what the analyst
did with its reports: corroborated, linked, promoted, dismissed. The grade is the analyst's call, informed by that
record; the record never sets it."""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base
from . import requirements as R
from .cases import ReportRow

RELIABILITY = ("A", "B", "C", "D", "E", "F")   # NATO source reliability: A reliable … E unreliable, F cannot be judged
KINDS = ("host_nation", "police", "venue", "partner", "military", "other")


class LiaisonSourceRow(Base):
    __tablename__ = "s2_liaison_sources"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[str] = mapped_column(String, default="other")
    reliability: Mapped[str] = mapped_column(String, default="F")
    notes: Mapped[str] = mapped_column(Text, default="")
    history_json: Mapped[str] = mapped_column(Text, default="[]")   # [{at, by, reliability, note}]
    created_by: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    graded_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


def source_tag(src: LiaisonSourceRow) -> str:
    return f"liaison:{src.id}"


async def find_or_create(session: AsyncSession, name: str, kind: str, by: str, now: datetime) -> LiaisonSourceRow:
    """A liaison report names its source; an unknown name becomes a new source at F until the analyst grades it."""
    name = " ".join(name.split())
    rows = (await session.execute(select(LiaisonSourceRow))).scalars().all()
    hit = next((r for r in rows if r.name.lower() == name.lower()), None)
    if hit: return hit
    row = LiaisonSourceRow(id=f"lsn_{uuid.uuid4().hex[:8]}", name=name, kind=kind if kind in KINDS else "other", reliability="F", created_by=by, created_at=now)
    session.add(row)
    await session.flush()
    return row


def track_record(reports: List[ReportRow]) -> Dict[str, Any]:
    by = {"filed": 0, "corroborated": 0, "linked": 0, "promoted": 0, "dismissed": 0}
    for r in reports:
        by[r.status] = by.get(r.status, 0) + 1
    disposed = by["corroborated"] + by["linked"] + by["promoted"] + by["dismissed"]
    return {"reports": len(reports), **by, "disposed": disposed, "borne_out": by["corroborated"] + by["linked"] + by["promoted"],
            "last_report_at": R.iso(max((r.filed_at for r in reports), default=None))}


def to_dict(src: LiaisonSourceRow, reports: Optional[List[ReportRow]] = None) -> Dict[str, Any]:
    return {"id": src.id, "name": src.name, "kind": src.kind, "reliability": src.reliability, "notes": src.notes, "history": json.loads(src.history_json or "[]"),
            "created_by": src.created_by, "created_at": R.iso(src.created_at), "graded_by": src.graded_by, "graded_at": R.iso(src.graded_at),
            "record": track_record(reports or [])}


async def reports_of(session: AsyncSession, src: LiaisonSourceRow) -> List[ReportRow]:
    return (await session.execute(select(ReportRow).where(ReportRow.source == source_tag(src)).order_by(ReportRow.filed_at))).scalars().all()


def grade(src: LiaisonSourceRow, reliability: str, by: str, now: datetime, note: str = "") -> None:
    hist = json.loads(src.history_json or "[]")
    hist.append({"at": R.iso(now), "by": by, "from": src.reliability, "reliability": reliability, "note": note})
    src.history_json = json.dumps(hist)
    src.reliability = reliability
    src.graded_by, src.graded_at = by, now
