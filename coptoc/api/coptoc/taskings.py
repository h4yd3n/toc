"""§5.10 taskings (2026-09-05): the object that moves work between staff sections. One section raises it, another accepts,
schedules, and completes it — S2 asks S3 for a collection asset over an area (a drone over the FARP during the rotation);
S3 asks S6 to confirm comms for an operation; S3 asks S4 for fuel at a site; S6 tells S3 a net will be down for a changeover.
A tasking carries who asked, who owes, what for (an operation, event, requirement, or site), the asset or capability wanted,
the window, a priority, and a status: requested → accepted → scheduled → complete, or declined. Every step is on the ledger;
open taskings ride into the handover brief per section."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base

KINDS = ("collection", "comms", "supply", "movement", "coverage", "other")
STATUSES = ("requested", "accepted", "scheduled", "complete", "declined")
SECTIONS = ("S1", "S2", "S3", "S4", "S6")
PRIORITIES = ("routine", "priority", "urgent")


class TaskingRow(Base):
    __tablename__ = "cop_taskings"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, default="other")
    title: Mapped[str] = mapped_column(String)
    from_section: Mapped[str] = mapped_column(String)
    to_section: Mapped[str] = mapped_column(String, index=True)
    subject_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # operation | event | requirement | location | trip
    subject_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subject_name: Mapped[str] = mapped_column(String, default="")
    asset: Mapped[str] = mapped_column(String, default="")  # what is wanted: "RQ-7 Shadow, 4 h on station", "TACSAT + HF check", "JP-8 10,000 gal"
    window_from: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    window_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    priority: Mapped[str] = mapped_column(String, default="routine")
    status: Mapped[str] = mapped_column(String, default="requested")
    notes: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="")  # what the owing section did or why it declined
    requested_by: Mapped[str] = mapped_column(String, default="")
    requested_at: Mapped[datetime] = mapped_column(DateTime)
    owned_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # who accepted it
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    # §5.10a what accepting it created: an operation (collection), a shipment (supply), or a task on the subject's operation (comms, coverage)
    created_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)   # operation | shipment | task
    created_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_parent: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # the operation a task belongs to
    created_name: Mapped[str] = mapped_column(String, default="")


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def out(t: TaskingRow, now: datetime) -> Dict[str, Any]:
    overdue = t.status in ("requested", "accepted", "scheduled") and t.window_from is not None and t.window_from < now
    age_h = round((now - t.requested_at).total_seconds() / 3600, 1)
    return {"id": t.id, "kind": t.kind, "title": t.title, "from_section": t.from_section, "to_section": t.to_section,
            "subject_type": t.subject_type, "subject_id": t.subject_id, "subject_name": t.subject_name, "asset": t.asset,
            "window_from": _iso(t.window_from), "window_to": _iso(t.window_to), "priority": t.priority, "status": t.status,
            "notes": t.notes, "result": t.result, "requested_by": t.requested_by, "requested_at": _iso(t.requested_at), "age_h": age_h,
            "owned_by": t.owned_by, "updated_at": _iso(t.updated_at), "open": t.status in ("requested", "accepted", "scheduled"),
            "created_type": t.created_type, "created_id": t.created_id, "created_parent": t.created_parent, "created_name": t.created_name,
            "overdue": overdue, "health": "red" if (overdue or (t.priority == "urgent" and t.status == "requested" and age_h > 4)) else ("amber" if t.status == "requested" and age_h > 12 else "green")}


def summarize(rows: List[TaskingRow], now: datetime) -> Dict[str, Any]:
    items = sorted((out(t, now) for t in rows), key=lambda x: (not x["open"], {"red": 0, "amber": 1, "green": 2}[x["health"]], x["requested_at"] or ""))
    per: Dict[str, Dict[str, int]] = {s: {"inbox": 0, "outbox": 0, "overdue": 0} for s in SECTIONS}
    for x in items:
        if x["open"]:
            per[x["to_section"]]["inbox"] += 1
            per[x["from_section"]]["outbox"] += 1
            if x["overdue"]: per[x["to_section"]]["overdue"] += 1
    return {"items": items, "open": sum(1 for x in items if x["open"]), "overdue": sum(1 for x in items if x["overdue"]), "per_section": per}


def seed(dataset: str, now: datetime) -> List[TaskingRow]:
    from datetime import timedelta
    d = lambda x: now + timedelta(days=x); h = lambda x: now + timedelta(hours=x)
    def T(i, kind, title, frm, to, st, si, sn, asset, wf, wt, pri, status, notes="", result="", by="", owner=None, age=6):
        return TaskingRow(id=f"tsk_{i:03d}", kind=kind, title=title, from_section=frm, to_section=to, subject_type=st, subject_id=si, subject_name=sn, asset=asset,
                          window_from=wf, window_to=wt, priority=pri, status=status, notes=notes, result=result, requested_by=by, requested_at=h(-age), owned_by=owner, updated_at=h(-age + 1))
    if dataset == "cab":
        return [
            T(1, "collection", "UAS coverage of FARP Eagle, D-3 to D-1", "S2", "S3", "location", "loc_farp", "FARP Eagle", "RQ-7 Shadow · 4 h on station per night, dusk to 0200", d(18), d(21), "priority", "accepted",
              "PIR 1: hostile or nuisance UAS over the FARP. Coverage requested for the establishment window.", by="S2 Intelligence", owner="S3 Operations", age=20),
            T(2, "comms", "Confirm PACE for the Brigade FTX", "S3", "S6", "event", "evt_ftx", "Brigade FTX — JRTC Rotation", "TACSAT + HF check at FOB Warrior and FARP Eagle; retrans plan for Peason Ridge", d(19), d(21), "priority", "requested",
              "Comms card due D-2.", by="S3 Operations", age=30),
            T(3, "supply", "JP-8 at FARP Eagle before the attack battalions arrive", "S3", "S4", "location", "loc_farp", "FARP Eagle", "JP-8 20,000 gal on hand by D-2", d(19), d(19), "urgent", "scheduled",
              "Tanker convoy CONV-0912 in transit; second lift booked.", by="S3 Operations", owner="S4 Logistics", age=14),
            T(4, "coverage", "Gate security for the change of command", "S3", "S1", "event", "evt_change", "Change of Command — 4th GSAB", "ACP team ×2, 0600–1400", d(12), d(12), "routine", "requested", by="S3 Operations", age=3),
            T(5, "comms", "SIPR at FOB Warrior before the TOC jumps", "S3", "S6", "location", "loc_fob", "FOB Warrior — JRTC", "SIPRNET terminal re-pointed and validated", h(-6), h(2), "urgent", "scheduled",
              "Terminal re-pointing in progress.", by="S3 Operations", owner="S6 Signal", age=8),
            T(6, "collection", "Route recon, MSR to Peason Ridge", "S2", "S3", "event", "evt_gunnery", "Aerial Gunnery — Table VI, 2nd Attack", "One AH-64 pair, route recon on the day before", d(4), d(4), "routine", "complete",
              result="Flown 0700–0830; route clear, one bridge weight-posted.", by="S2 Intelligence", owner="S3 Operations", age=40),
        ]
    return [
        T(1, "collection", "Advance look at the Riyadh venue and hotel", "S2", "S3", "trip", "trip_001", "Board meeting — Riyadh", "Local security partner walk-through, 48 h before arrival", h(-30), h(-20), "priority", "complete",
          result="Walk-through done; hotel approach and loading dock noted.", by="S2 Analyst", owner="Executive Assistant", age=50),
        T(2, "coverage", "Two agents for the Q4 board dinner", "S3", "S1", "event", "evt_001", "Q4 Board Meeting", "Lead + 1, day 2 evening", d(36), d(36), "routine", "requested", by="Executive Assistant", age=5),
        T(3, "comms", "Check-in path for London travelers during the transit strike", "S3", "S6", "location", "loc_ldn", "London Office", "SMS + chat check-in test to all London travelers", h(-2), h(6), "priority", "accepted",
          by="Executive Assistant", owner="Battle Captain", age=4),
    ]


# ---- what accepting a tasking creates, and what finishing the created thing does to the tasking ------------------------
# The tasking is the ask; the thing the owing section makes to answer it lives on that section's board, where the work is
# done. Accepting a collection tasking opens an S3 operation with a collection skeleton; accepting a supply tasking books a
# shipment on the S4 board; accepting a comms or coverage tasking adds a task, owned by the answering section, to the
# operation its subject already has. Each is linked both ways: complete the tasking and the thing closes; arrive the
# shipment, finish the task, close the operation, and the tasking completes with the result on it.

COLLECTION_TASKS = [
    {"title": "Assign the asset and crew for the window", "section": "S3"},
    {"title": "Confirm the window, the airspace, and the route", "section": "S3"},
    {"title": "Brief the collection requirement and the reporting criteria", "section": "S2"},
    {"title": "Fly / run the mission and report what was collected to S2", "section": "S3"},
]

def _supply_category(text: str) -> str:
    t = text.lower()
    for cat, words in (("fuel", ("jp-8", "jp8", "fuel", "diesel", "mogas")), ("ammunition", ("hellfire", "rds", "ammo", "ammunition", "hydra", "30 mm", "30mm")),
                       ("water", ("water",)), ("rations", ("mre", "ration", "class i ")), ("medical", ("class viii", "medical", "cls bag")), ("parts", ("engine", "blade", "apu", "class ix", "part"))):
        if any(w in t for w in words): return cat
    return "other"


async def on_accept(session, t: TaskingRow, actor: str, now: datetime) -> Optional[Dict[str, Any]]:
    """Create what the accepted tasking calls for. Returns {type, id, name} or None when the ask creates nothing."""
    from datetime import timedelta
    from .operations import OperationRow, OpTaskRow, new_task
    from .sections import ShipmentRow
    from .db_models import EventRow, LocationRow, TripRow
    from sqlalchemy import select
    if t.created_id:
        return None
    if t.kind == "collection" and t.subject_type in ("location", "event", "trip") and t.subject_id:
        op = OperationRow(id=f"op_{uuid.uuid4().hex[:8]}", title=f"COLLECTION — {t.title}", subject_type=t.subject_type, subject_id=t.subject_id, subject_name=t.subject_name,
                          from_product_type="tasking", from_product_id=t.id, opened_by=actor, opened_at=now, notes=(t.asset + ("\n" + t.notes if t.notes else "")).strip())
        session.add(op); await session.flush()
        session.add_all([new_task(op.id, spec["title"], spec["section"], "", i, t.window_from if i < 2 else t.window_to) for i, spec in enumerate(COLLECTION_TASKS)])
        t.created_type, t.created_id, t.created_name = "operation", op.id, op.title
        return {"type": "operation", "id": op.id, "name": op.title}
    if t.kind == "supply":
        loc = await session.get(LocationRow, t.subject_id) if t.subject_type == "location" and t.subject_id else None
        eta = t.window_from or t.window_to or (now + timedelta(hours=24))
        sh = ShipmentRow(id=f"shp_{uuid.uuid4().hex[:8]}", description=t.asset or t.title, category=_supply_category(t.asset + " " + t.title), quantity=t.asset, from_name="",
                         to_location_id=loc.id if loc else None, to_name=loc.name if loc else t.subject_name, eta=eta, status="planned", priority=t.priority, carrier="", ref=t.id,
                         note=f"From tasking {t.id}: {t.title}", updated_by=actor, updated_at=now, source="tasking")
        session.add(sh); await session.flush()
        t.created_type, t.created_id, t.created_name = "shipment", sh.id, sh.description
        return {"type": "shipment", "id": sh.id, "name": sh.description}
    if t.kind in ("comms", "coverage", "movement", "other"):
        op = None
        if t.subject_type == "operation" and t.subject_id:
            op = await session.get(OperationRow, t.subject_id)
        elif t.subject_type in ("event", "trip", "location") and t.subject_id:
            op = (await session.execute(select(OperationRow).where(OperationRow.subject_type == t.subject_type, OperationRow.subject_id == t.subject_id, OperationRow.status.in_(("planned", "active"))).order_by(OperationRow.opened_at.desc()))).scalars().first()
        if op:
            n = len((await session.execute(select(OpTaskRow.id).where(OpTaskRow.operation_id == op.id))).scalars().all())
            task = new_task(op.id, t.title, t.to_section, t.owned_by or "", n, t.window_from); task.note = t.asset
            session.add(task); await session.flush()
            t.created_type, t.created_id, t.created_parent, t.created_name = "task", task.id, op.id, f"{op.title}: {t.title}"
            return {"type": "task", "id": task.id, "parent": op.id, "name": t.created_name}
    return None


async def on_complete(session, t: TaskingRow, actor: str, now: datetime) -> Optional[str]:
    """The tasking is complete: close what it created, if that is still open. Returns a phrase for the ledger."""
    from .operations import OperationRow, OpTaskRow
    from .sections import ShipmentRow
    if t.created_type == "operation":
        op = await session.get(OperationRow, t.created_id)
        if op and op.status in ("planned", "active"):
            op.status, op.closed_at = "complete", now; return f"closed {op.title}"
    if t.created_type == "shipment":
        sh = await session.get(ShipmentRow, t.created_id)
        if sh and sh.status not in ("arrived", "cancelled"):
            sh.status, sh.updated_by, sh.updated_at = "arrived", actor, now; return f"{sh.description} marked arrived"
    if t.created_type == "task":
        task = await session.get(OpTaskRow, t.created_id)
        if task and task.status != "done":
            task.status, task.updated_by, task.updated_at = "done", actor, now; return f"task done on {t.created_parent}"
    return None


async def complete_from(session, created_type: str, created_id: str, actor: str, now: datetime, result: str) -> Optional[TaskingRow]:
    """The created thing finished on its own board: the tasking behind it completes, with the result on it."""
    from sqlalchemy import select
    t = (await session.execute(select(TaskingRow).where(TaskingRow.created_type == created_type, TaskingRow.created_id == created_id))).scalars().first()
    if not t or t.status not in ("requested", "accepted", "scheduled"):
        return None
    t.status, t.result, t.updated_at = "complete", (t.result + " · " if t.result else "") + result, now
    if not t.owned_by: t.owned_by = actor
    return t
