"""§5.10 taskings (2026-09-05): the object that moves work between staff sections. One section raises it, another accepts,
schedules, and completes it — S2 asks S3 for a collection asset over an area (a drone over the FARP during the rotation);
S3 asks S6 to confirm comms for an operation; S3 asks S4 for fuel at a site; S6 tells S3 a net will be down for a changeover.
A tasking carries who asked, who owes, what for (an operation, event, requirement, or site), the asset or capability wanted,
the window, a priority, and a status: requested → accepted → scheduled → complete, or declined. Every step is on the ledger;
open taskings ride into the handover brief per section."""
from __future__ import annotations

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
