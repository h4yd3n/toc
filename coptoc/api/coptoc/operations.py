"""§5.10 #3 — a product hands off to an operation. Target package → OPORD: an approved assessment (or area assessment)
on a subject becomes an Operation with tasks (who does what by when, by staff section), and resource asks for S4.
The wall shows the operation's status against its event or trip."""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class OperationRow(Base):
    __tablename__ = "cop_operations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    subject_type: Mapped[str] = mapped_column(String)  # event | trip | location
    subject_id: Mapped[str] = mapped_column(String, index=True)
    subject_name: Mapped[str] = mapped_column(String, default="")
    from_product_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # assessment | area
    from_product_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="planned")  # planned | active | complete | cancelled
    opened_by: Mapped[str] = mapped_column(String)
    opened_at: Mapped[datetime] = mapped_column(DateTime)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class OpTaskRow(Base):
    __tablename__ = "cop_op_tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    operation_id: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    section: Mapped[str] = mapped_column(String, default="S3")  # S1..S6 — who owns it
    owner: Mapped[str] = mapped_column(String, default="")  # a person, a team, a vendor — free text
    status: Mapped[str] = mapped_column(String, default="todo")  # todo | doing | done | blocked
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    updated_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")


class OpResourceRow(Base):
    """S4 — the resource ask: vehicles, kit, a local vendor. Requested by S3, answered by S4."""
    __tablename__ = "cop_op_resources"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    operation_id: Mapped[str] = mapped_column(String, index=True)
    item: Mapped[str] = mapped_column(String)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String, default="requested")  # requested | approved | issued | denied
    note: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# The standard tasks an operation starts with, by subject kind — the OPORD skeleton. All editable; none pre-assigned.
DEFAULT_TASKS: Dict[str, List[Dict[str, str]]] = {
    "event": [
        {"title": "Advance the venue — access, egress, safe room, medical", "section": "S3"},
        {"title": "Vet transport and routes; alternates for each leg", "section": "S3"},
        {"title": "Brief the principal(s) on the assessment and the plan", "section": "S2"},
        {"title": "Coordinate with venue security and local police", "section": "S3"},
        {"title": "Comms plan: check-in cadence, roll-call trigger, contact tree", "section": "S6"},
        {"title": "Confirm attendee list and travel against the roster", "section": "S1"},
    ],
    "trip": [
        {"title": "Vet transport and routes; alternates for each leg", "section": "S3"},
        {"title": "Brief the principal on the assessment and the plan", "section": "S2"},
        {"title": "Hotel and venue advance; safe room and medical", "section": "S3"},
        {"title": "Comms plan: check-in cadence and contact tree", "section": "S6"},
    ],
    "location": [
        {"title": "Adjust access control and guard posture for the window", "section": "S3"},
        {"title": "Brief site leads on the assessment", "section": "S2"},
        {"title": "Comms plan and roll-call trigger", "section": "S6"},
    ],
}


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


def task_dict(t: OpTaskRow) -> Dict[str, Any]:
    return {"id": t.id, "title": t.title, "section": t.section, "owner": t.owner, "status": t.status, "due_at": iso(t.due_at), "order": t.order, "updated_by": t.updated_by, "updated_at": iso(t.updated_at), "note": t.note}

def resource_dict(r: OpResourceRow) -> Dict[str, Any]:
    return {"id": r.id, "item": r.item, "qty": r.qty, "status": r.status, "note": r.note, "updated_by": r.updated_by, "updated_at": iso(r.updated_at)}

def op_dict(o: OperationRow, tasks: List[OpTaskRow], resources: List[OpResourceRow]) -> Dict[str, Any]:
    done = sum(1 for t in tasks if t.status == "done")
    return {"id": o.id, "title": o.title, "subject_type": o.subject_type, "subject_id": o.subject_id, "subject_name": o.subject_name,
            "from_product_type": o.from_product_type, "from_product_id": o.from_product_id, "status": o.status, "opened_by": o.opened_by, "opened_at": iso(o.opened_at),
            "closed_at": iso(o.closed_at), "notes": o.notes, "tasks": [task_dict(t) for t in sorted(tasks, key=lambda t: (t.order, t.id))],
            "resources": [resource_dict(r) for r in resources], "tasks_total": len(tasks), "tasks_done": done, "blocked": sum(1 for t in tasks if t.status == "blocked"),
            "resources_open": sum(1 for r in resources if r.status == "requested"), "pct": round(100 * done / len(tasks)) if tasks else 0}


async def load_all(session: AsyncSession) -> List[Dict[str, Any]]:
    ops = (await session.execute(select(OperationRow).order_by(OperationRow.opened_at.desc()))).scalars().all()
    tasks = (await session.execute(select(OpTaskRow))).scalars().all()
    res = (await session.execute(select(OpResourceRow))).scalars().all()
    return [op_dict(o, [t for t in tasks if t.operation_id == o.id], [r for r in res if r.operation_id == o.id]) for o in ops]


def new_task(op_id: str, title: str, section: str, owner: str = "", order: int = 0, due_at: Optional[datetime] = None) -> OpTaskRow:
    return OpTaskRow(id=f"task_{uuid.uuid4().hex[:8]}", operation_id=op_id, title=title, section=section, owner=owner, order=order, due_at=due_at)
