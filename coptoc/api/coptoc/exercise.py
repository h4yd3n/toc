"""§3.7 The exercise — a scenario driven against the wall, the way a TOC rehearses.

A command post exercise runs off a **MSEL**: a master scenario events list, written in advance, each inject timed
against STARTEX. Exercise control fires them, the staff works them, and the log says what the staff did. Everything
here is that, and nothing here is a simulation of the staff — the injects change the picture and the humans respond.

**Three rules, decided by the author:**

1. **The exercise has its own profile.** A third profile beside Military and Corporate (§11.2) with its own dataset.
   Nothing an inject does can touch the live wall, because entering the exercise profile loads exercise data and
   leaving it loads the deployment's own again. An exercise refuses to start on any other profile, and the wall
   wears an EXERCISE banner the whole time it is running — a CPX message that is not marked EXERCISE is how a drill
   becomes a real alert by accident.
2. **The real clock, a compressed schedule.** Nothing fakes the time. Every inject carries an offset in minutes from
   STARTEX and fires when that offset has really passed; a 72-hour scenario runs in twenty minutes because the
   injects are packed together, not because the clock lies. `speed` divides the offsets and nothing else, so the
   watch strip, the Zulu clock, the staleness rules and the sun times all stay true.
3. **An inject writes what a person would have written.** It sets a system down, drops a supply line, takes an
   airframe NMC, files a SPOTREP, opens a roll call — into the same rows and through the same rules as the staff's
   own actions, with `EXERCISE CONTROL` as the actor on every ledger line. A target it cannot resolve **fails
   loudly** on the board rather than quietly doing nothing.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import DateTime, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base

ACTOR = "EXERCISE CONTROL"
STATUSES = ("planned", "running", "ended")
INJECT_STATUSES = ("pending", "fired", "failed", "skipped")
KINDS = ("message", "spotrep", "system", "supply", "equipment", "position", "posture", "rollcall", "tasking")
MAX_SPEED = 60


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


class ExerciseRow(Base):
    """One run of one scenario. STARTEX and ENDEX are real times; the injects hang off STARTEX."""
    __tablename__ = "cop_exercises"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    scenario: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="planned")   # planned | running | ended
    speed: Mapped[float] = mapped_column(Float, default=1.0)         # divides every offset; the clock itself is never touched
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_by: Mapped[str] = mapped_column(String, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)


class InjectRow(Base):
    """One MSEL line: what happens, how long after STARTEX, and what it did when it fired."""
    __tablename__ = "cop_exercise_injects"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    exercise_id: Mapped[str] = mapped_column(String, index=True)
    seq: Mapped[int] = mapped_column(Integer)
    offset_min: Mapped[float] = mapped_column(Float)
    kind: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    section: Mapped[str] = mapped_column(String, default="")          # the section the inject lands on, for the MSEL read-out
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String, default="pending")    # pending | fired | failed | skipped
    fired_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    result: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")


# ---------------------------------------------------------------- the scenarios on the shelf
#
# A MSEL is written in advance by an exercise planner. These two are written the way one is: an inject is a thing
# that happens in the world, not an instruction to the software, and each one names its target the way a person
# would — by site name, by unit, by supply class — so the scenario survives a reseed that changes every id.

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "farp_eagle": {
        "name": "FARP EAGLE under pressure",
        "summary": "Unidentified UAS over a forward arming and refuelling point, comms degraded, fuel short, and an "
                   "accountability requirement, inside twenty minutes. Trips four of the brigade's CCIR lines.",
        "profile": "military",
        "injects": [
            (0,  "message",   "STARTEX — this is an exercise", "", {"text": "EXERCISE EXERCISE EXERCISE. All injects are exercise traffic. Nothing on this wall is real."}),
            (1,  "spotrep",   "Two quadcopters orbiting the FARP", "S2", {"text": "Two unidentified quadcopters observed orbiting FARP Eagle at approximately 400 feet, holding east of the fuel point.", "place": "FARP Eagle", "reported_by": "FARP Eagle guard post", "reporter_role": "security"}),
            (3,  "system",    "FARP Eagle primary net degraded", "S6", {"site": "FARP Eagle", "status": "degraded", "note": "EXERCISE — jamming suspected on the primary net"}),
            (5,  "posture",   "FARP Eagle to HIGH", "S3", {"site": "FARP Eagle", "posture": "high"}),
            (7,  "equipment", "Two AH-64E go NMC", "S4", {"model": "AH-64E", "count": 2, "status": "nmc", "fault": "EXERCISE — battle damage to the tail rotor drive"}),
            (9,  "rollcall",  "Roll call at FARP Eagle", "S1", {"site": "FARP Eagle", "title": "EXERCISE — roll call, FARP Eagle"}),
            (12, "supply",    "Class III at the FARP drops to half a day", "S4", {"class": "III", "site": "FARP Eagle", "days": 0.5, "note": "EXERCISE — fuel bag holed"}),
            (14, "spotrep",   "Small arms fire east of the perimeter", "S2", {"text": "Small arms fire heard from the treeline east of the FARP perimeter, two bursts, no casualties reported.", "place": "FARP Eagle", "reported_by": "FARP Eagle guard post", "reporter_role": "security"}),
            (16, "tasking",   "S3 asks S2 to find the launch point", "S2", {"from": "S3", "to": "S2", "kind": "collection", "title": "EXERCISE — confirm the UAS launch point east of FARP Eagle", "asset": "RQ-7 Shadow, 2 h on station", "priority": "urgent"}),
            (18, "position",  "1 ATK reports in", "S1", {"unit": "1 ATK", "site": "FARP Eagle", "note": "EXERCISE — position report after comms restored"}),
            (20, "message",   "ENDEX on the controller's call", "", {"text": "EXERCISE — last scheduled inject. Exercise control ends the exercise when the staff has worked the picture."}),
        ],
    },
    "accountability_drill": {
        "name": "Accountability and comms drill",
        "summary": "The short one: a site loses its primary net and has to account for everyone on it. Six minutes.",
        "profile": "military",
        "injects": [
            (0, "message",  "STARTEX — this is an exercise", "", {"text": "EXERCISE EXERCISE EXERCISE. Accountability drill. Nothing on this wall is real."}),
            (1, "system",   "Primary net down at the FOB", "S6", {"site": "FOB Warrior", "status": "down", "note": "EXERCISE — primary net down"}),
            (2, "rollcall", "Roll call at FOB Warrior", "S1", {"site": "FOB Warrior", "title": "EXERCISE — roll call, FOB Warrior"}),
            (5, "message",  "ENDEX on the controller's call", "", {"text": "EXERCISE — account for everyone, then end the exercise."}),
        ],
    },
}


def scenario_catalog() -> List[Dict[str, Any]]:
    return [{"id": k, "name": v["name"], "summary": v["summary"], "profile": v["profile"],
             "injects": len(v["injects"]), "runs_min": max(i[0] for i in v["injects"])} for k, v in SCENARIOS.items()]


# ---------------------------------------------------------------- the board

def inject_dict(row: InjectRow, ex: Optional[ExerciseRow], now: datetime) -> Dict[str, Any]:
    due = due_at(ex, row) if ex else None
    return {"id": row.id, "seq": row.seq, "offset_min": row.offset_min, "kind": row.kind, "title": row.title,
            "section": row.section, "status": row.status, "fired_at": iso(row.fired_at), "result": row.result,
            "error": row.error, "due_at": iso(due), "payload": json.loads(row.payload_json or "{}"),
            "in_min": round((due - now).total_seconds() / 60, 1) if due and row.status == "pending" else None}


def due_at(ex: ExerciseRow, row: InjectRow) -> Optional[datetime]:
    """When this inject really fires: STARTEX plus its offset, divided by the speed. The clock is never touched."""
    if not ex.started_at:
        return None
    return ex.started_at + timedelta(minutes=row.offset_min / max(0.1, ex.speed))


def board(ex: Optional[ExerciseRow], injects: List[InjectRow], now: datetime) -> Dict[str, Any]:
    """What the wall needs to wear the banner and read the MSEL out."""
    if not ex:
        return {"running": False, "exercise": None, "injects": [], "scenarios": scenario_catalog()}
    rows = [inject_dict(i, ex, now) for i in sorted(injects, key=lambda i: i.seq)]
    pending = [r for r in rows if r["status"] == "pending"]
    return {
        "running": ex.status == "running",
        "exercise": {
            "id": ex.id, "name": ex.name, "scenario": ex.scenario, "status": ex.status, "speed": ex.speed,
            "started_at": iso(ex.started_at), "ended_at": iso(ex.ended_at), "started_by": ex.started_by, "notes": ex.notes,
            "elapsed_min": round((now - ex.started_at).total_seconds() / 60, 1) if ex.started_at else None,
            "fired": sum(1 for r in rows if r["status"] == "fired"), "failed": sum(1 for r in rows if r["status"] == "failed"),
            "pending": len(pending), "total": len(rows),
            "next": pending[0] if pending else None,
        },
        "injects": rows,
        "scenarios": scenario_catalog(),
    }


# ---------------------------------------------------------------- writing and running

async def current(session: AsyncSession) -> Optional[ExerciseRow]:
    """The running exercise, else the most recent one — the board shows the last run until a new one is created."""
    running = (await session.execute(select(ExerciseRow).where(ExerciseRow.status == "running"))).scalars().first()
    if running:
        return running
    return (await session.execute(select(ExerciseRow).order_by(ExerciseRow.created_at.desc()).limit(1))).scalars().first()


async def create(session: AsyncSession, scenario_id: str, actor: str, speed: float = 1.0, name: str = "") -> ExerciseRow:
    spec = SCENARIOS.get(scenario_id)
    if not spec:
        raise ValueError(f"scenario is one of {list(SCENARIOS)}")
    if (await session.execute(select(ExerciseRow).where(ExerciseRow.status == "running"))).scalars().first():
        raise ValueError("an exercise is already running; end it before starting another")
    ex = ExerciseRow(id=f"ex_{uuid.uuid4().hex[:8]}", name=name or spec["name"], scenario=scenario_id, status="planned",
                     speed=min(MAX_SPEED, max(0.1, float(speed))), created_at=now_utc(), started_by=actor)
    session.add(ex)
    await session.flush()
    for seq, (offset, kind, title, section, payload) in enumerate(spec["injects"], start=1):
        session.add(InjectRow(id=f"inj_{uuid.uuid4().hex[:8]}", exercise_id=ex.id, seq=seq, offset_min=float(offset),
                              kind=kind, title=title, section=section, payload_json=json.dumps(payload)))
    await session.commit()
    return ex


async def start(session: AsyncSession, ex: ExerciseRow, actor: str) -> ExerciseRow:
    if ex.status == "ended":
        raise ValueError("this exercise has ended; create another")
    ex.status, ex.started_at, ex.started_by = "running", now_utc(), actor
    await session.commit()
    return ex


async def end(session: AsyncSession, ex: ExerciseRow, actor: str, notes: str = "") -> Tuple[ExerciseRow, int]:
    """ENDEX. Injects that never fired are skipped and say so — an exercise cut short is a fact about the exercise."""
    ex.status, ex.ended_at = "ended", now_utc()
    if notes:
        ex.notes = notes
    skipped = 0
    for row in (await session.execute(select(InjectRow).where(InjectRow.exercise_id == ex.id, InjectRow.status == "pending"))).scalars():
        row.status, row.result = "skipped", "ENDEX before this inject was due"
        skipped += 1
    await session.commit()
    return ex, skipped


async def due(session: AsyncSession, ex: ExerciseRow, now: datetime) -> List[InjectRow]:
    rows = (await session.execute(select(InjectRow).where(InjectRow.exercise_id == ex.id, InjectRow.status == "pending")
                                  .order_by(InjectRow.seq))).scalars().all()
    return [r for r in rows if (d := due_at(ex, r)) is not None and d <= now]


async def tick(session: AsyncSession, ledger, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Fire whatever is due. Called by the clock every few seconds, and by the controller's TICK on demand."""
    now = now or now_utc()
    ex = (await session.execute(select(ExerciseRow).where(ExerciseRow.status == "running"))).scalars().first()
    if not ex:
        return []
    fired = []
    for row in await due(session, ex, now):
        fired.append(await fire(session, ex, row, ledger, now))
    return fired


async def fire(session: AsyncSession, ex: ExerciseRow, row: InjectRow, ledger, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Apply one inject and record what it did. A target that cannot be resolved fails on the board, loudly."""
    now = now or now_utc()
    payload = json.loads(row.payload_json or "{}")
    try:
        result = await APPLY[row.kind](session, payload, now)
        row.status, row.result, row.error = "fired", result, ""
    except Exception as e:  # noqa: BLE001 — a failed inject is exercise data, not a crash
        row.status, row.result, row.error = "failed", "", str(e)[:500]
    row.fired_at = now
    await session.commit()
    await ledger.append_event(content_id=ex.id, event_type="cop.exercise.inject", actor_type="system", actor_id=ACTOR,
                              new_state=row.status,
                              reason=f"EXERCISE inject {row.seq} — {row.title}" + (f": {row.result}" if row.result else "") + (f" — FAILED: {row.error}" if row.error else ""),
                              metadata={"exercise": ex.id, "inject": row.id, "kind": row.kind, "section": row.section, "offset_min": row.offset_min})
    return {"id": row.id, "seq": row.seq, "title": row.title, "kind": row.kind, "status": row.status,
            "result": row.result, "error": row.error}


# ---------------------------------------------------------------- what each kind of inject does
#
# Every one writes the row a person would have written, through the same model the staff's own action uses, so the
# picture reacts exactly as it would in earnest. None of them invents a fact the scenario did not state.

async def _site(session: AsyncSession, name: str):
    from .db_models import LocationRow
    rows = (await session.execute(select(LocationRow))).scalars().all()
    hit = next((l for l in rows if name.lower() in l.name.lower()), None)
    if not hit:
        raise ValueError(f"no site matching {name!r} — the scenario names a place this dataset does not have")
    return hit


async def _apply_message(session: AsyncSession, payload: Dict[str, Any], now: datetime) -> str:
    """Controller narrative. It changes nothing: the ledger line *is* the inject."""
    return payload.get("text", "")


async def _apply_spotrep(session: AsyncSession, payload: Dict[str, Any], now: datetime) -> str:
    from sigtoc.cases import ReportRow
    lat = lon = None
    place = payload.get("place", "")
    if place:
        try:
            site = await _site(session, place)
            lat, lon, place = site.lat, site.lon, site.name
        except ValueError:
            pass  # a report may name a place we do not hold a site for; it still gets filed, without a position
    r = ReportRow(id=f"rpt_{uuid.uuid4().hex[:8]}", kind="spot", reported_by=payload.get("reported_by", ACTOR),
                  reporter_role=payload.get("reporter_role", "security"), at=now, lat=lat, lon=lon, place=place or None,
                  text=f"EXERCISE — {payload['text']}", credibility=int(payload.get("credibility", 2)),
                  source="exercise", filed_at=now)
    session.add(r)
    await session.commit()
    return f"SPOTREP filed: {r.text[:80]}"


async def _apply_system(session: AsyncSession, payload: Dict[str, Any], now: datetime) -> str:
    from .sections import SystemRow
    site = await _site(session, payload["site"])
    rows = (await session.execute(select(SystemRow).where(SystemRow.location_id == site.id))).scalars().all()
    pace = payload.get("pace", "primary")
    hit = next((s for s in rows if s.pace == pace), None) or next(iter(rows), None)
    if not hit:
        raise ValueError(f"{site.name} holds no system to degrade")
    old, hit.status = hit.status, payload.get("status", "degraded")
    hit.since, hit.updated_by, hit.updated_at, hit.note = now, ACTOR, now, payload.get("note", "")
    await session.commit()
    return f"{hit.name} at {site.name}: {old.upper()} → {hit.status.upper()}"


async def _apply_supply(session: AsyncSession, payload: Dict[str, Any], now: datetime) -> str:
    """Set a line to the days of supply the scenario states, by moving what is on hand. The rate is not touched:
    days of supply stays on-hand over the rate S4 entered, and the inject moves the thing that really moves."""
    from .sections import SupplyRow
    site = await _site(session, payload["site"])
    cls = str(payload.get("class", "")).lower()
    rows = (await session.execute(select(SupplyRow).where(SupplyRow.location_id == site.id))).scalars().all()
    hit = next((s for s in rows if cls in (s.category + " " + s.item).lower()), None)
    if not hit:
        raise ValueError(f"{site.name} holds no supply line matching {payload.get('class')!r}")
    if not hit.daily_use:
        raise ValueError(f"{hit.item} at {site.name} has no use rate, so it has no days of supply to set")
    old = hit.on_hand
    hit.on_hand = round(float(payload["days"]) * hit.daily_use, 2)
    hit.updated_by, hit.updated_at, hit.note = ACTOR, now, payload.get("note", "")
    await session.commit()
    return f"{hit.item} at {site.name}: {old:g} → {hit.on_hand:g} {hit.unit} ({payload['days']} days)"


async def _apply_equipment(session: AsyncSession, payload: Dict[str, Any], now: datetime) -> str:
    from .readiness import EquipmentRow
    model = str(payload.get("model", "")).lower()
    want = int(payload.get("count", 1))
    rows = [e for e in (await session.execute(select(EquipmentRow))).scalars()
            if model in (e.model + " " + e.category).lower() and e.status == "fmc"]
    if len(rows) < want:
        raise ValueError(f"only {len(rows)} FMC {payload.get('model')} available, scenario wants {want}")
    hit = rows[:want]
    for e in hit:
        e.status, e.fault, e.since, e.updated_by, e.updated_at = payload.get("status", "nmc"), payload.get("fault", ""), now, ACTOR, now
    await session.commit()
    return f"{', '.join(e.bumper_number for e in hit)}: {payload.get('status', 'nmc').upper()}"


async def _apply_position(session: AsyncSession, payload: Dict[str, Any], now: datetime) -> str:
    from .db_models import TeamRow
    from .readiness import report_position
    site = await _site(session, payload["site"])
    unit = str(payload.get("unit", "")).lower()
    teams = (await session.execute(select(TeamRow))).scalars().all()
    hit = next((t for t in teams if unit in (t.name + " " + (t.short or "")).lower()), None)
    if not hit:
        raise ValueError(f"no unit matching {payload.get('unit')!r}")
    await report_position(session, hit.id, lat=site.lat, lon=site.lon, at=now, source="radio",
                          speed_kph=None, heading=None, note=payload.get("note", ""), reported_by=ACTOR)
    return f"{hit.name} reported at {site.name}"


async def _apply_posture(session: AsyncSession, payload: Dict[str, Any], now: datetime) -> str:
    site = await _site(session, payload["site"])
    old, site.posture = site.posture, payload["posture"]
    await session.commit()
    return f"{site.name}: posture {old.upper()} → {site.posture.upper()}"


async def _apply_rollcall(session: AsyncSession, payload: Dict[str, Any], now: datetime) -> str:
    """The same roster rule the Battle Captain's own roll call uses (Decision A): everyone present, everyone within
    the radius, and everyone assigned to the site wherever they are."""
    from .db_models import AccountabilityRow, IncidentRow, PersonRow
    from .service import build_snapshot, haversine_km
    site = await _site(session, payload["site"])
    radius = float(payload.get("radius_km", 5))
    snap = await build_snapshot(session, include_restricted=True)
    members = []
    for p in snap["people"]:
        if p["location_id"] == site.id:
            members.append((p["id"], "present"))
        elif haversine_km(p["lat"], p["lon"], site.lat, site.lon) <= radius:
            members.append((p["id"], "in_area"))
        elif p["home_location_id"] == site.id:
            members.append((p["id"], "assigned"))
    inc = IncidentRow(id=f"inc_{uuid.uuid4().hex[:8]}", title=payload.get("title", f"EXERCISE — roll call, {site.name}"),
                      kind="site", location_id=site.id, threat_id=None, lat=site.lat, lon=site.lon, radius_km=radius,
                      status="open", opened_by=ACTOR, opened_at=now, notes="EXERCISE")
    session.add(inc)
    await session.flush()
    session.add_all([AccountabilityRow(incident_id=inc.id, person_id=pid, status="unaccounted", basis=basis) for pid, basis in members])
    await session.commit()
    return f"roll call opened at {site.name}: {len(members)} to account for"


async def _apply_tasking(session: AsyncSession, payload: Dict[str, Any], now: datetime) -> str:
    from .taskings import TaskingRow
    t = TaskingRow(id=f"tk_{uuid.uuid4().hex[:8]}", kind=payload.get("kind", "other"), title=payload["title"],
                   from_section=payload.get("from", "S3"), to_section=payload.get("to", "S2"),
                   asset=payload.get("asset", ""), priority=payload.get("priority", "routine"),
                   status="requested", notes=payload.get("notes", "EXERCISE"), requested_by=ACTOR,
                   requested_at=now, updated_at=now)
    session.add(t)
    await session.commit()
    return f"{t.from_section} → {t.to_section}: {t.title}"


APPLY = {
    "message": _apply_message, "spotrep": _apply_spotrep, "system": _apply_system, "supply": _apply_supply,
    "equipment": _apply_equipment, "position": _apply_position, "posture": _apply_posture,
    "rollcall": _apply_rollcall, "tasking": _apply_tasking,
}
