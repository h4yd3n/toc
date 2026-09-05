"""§3.1 — the watch. Shift model, running-estimate lines, the shift change brief, handover on the ledger.

Decisions S–V: follow-the-sun by default (three 8 h watches), the brief is generated and read out, the watch does not
transfer until the incoming Battle Captain acknowledges, a 30-minute overlap whose items must be acknowledged one by
one, and NSTR is an affirmed state."""
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base
from shared.db_models import LedgerEventRow

# Default pattern: follow-the-sun, boundaries in UTC so the cycle is unambiguous; labels are the watch site.
FOLLOW_THE_SUN = [
    {"name": "Singapore", "tz": "Asia/Singapore", "start_utc": 0, "hours": 8},
    {"name": "Dublin", "tz": "Europe/Dublin", "start_utc": 8, "hours": 8},
    {"name": "San Francisco", "tz": "America/Los_Angeles", "start_utc": 16, "hours": 8},
]
DAY_NIGHT = [
    {"name": "Day", "tz": "UTC", "start_utc": 6, "hours": 12},
    {"name": "Night", "tz": "UTC", "start_utc": 18, "hours": 12},
]
PATTERNS = {"follow_the_sun": FOLLOW_THE_SUN, "day_night": DAY_NIGHT}
OVERLAP_MINUTES = 30
SECTIONS = ("S1", "S2", "S3", "S4", "S6")


class WatchConfigRow(Base):
    __tablename__ = "cop_watch_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern: Mapped[str] = mapped_column(String, default="follow_the_sun")
    watches_json: Mapped[str] = mapped_column(Text, default=json.dumps(FOLLOW_THE_SUN))
    overlap_minutes: Mapped[int] = mapped_column(Integer, default=OVERLAP_MINUTES)


class WatchRow(Base):
    """One instance of a watch slot. Created when the slot is first seen; handed over when acknowledged."""
    __tablename__ = "cop_watches"
    id: Mapped[str] = mapped_column(String, primary_key=True)  # e.g. 2026-09-02T08_Dublin
    name: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    battle_captain: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="open")  # open | pending_ack | handed_over
    brief_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # frozen at handover
    outgoing_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nstr: Mapped[int] = mapped_column(Integer, default=0)  # 1 = affirmed "nothing significant to report"
    handed_over_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class SectionEstimateRow(Base):
    """The human-owned assessment line at the top of each panel — the spine of the brief."""
    __tablename__ = "cop_section_estimates"
    section: Mapped[str] = mapped_column(String, primary_key=True)  # S1 | S2 | S3 | S6
    assessment: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


async def get_config(session: AsyncSession) -> WatchConfigRow:
    cfg = await session.get(WatchConfigRow, 1)
    if not cfg:
        cfg = WatchConfigRow(id=1)
        session.add(cfg)
        await session.commit()
    return cfg


def slot_for(now: datetime, watches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Which watch owns `now`, with its absolute window. Watches are defined by UTC start hour and length."""
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    candidates = []
    for w in watches:
        for d in (-1, 0):
            start = day + timedelta(days=d, hours=w["start_utc"])
            candidates.append((start, start + timedelta(hours=w["hours"]), w))
    for start, end, w in candidates:
        if start <= now < end:
            nxt = next_slot(end, watches)
            return {"name": w["name"], "tz": w["tz"], "started_at": start, "ends_at": end, "next": nxt["name"]}
    raise RuntimeError("no watch covers now — pattern does not span 24h")


def next_slot(at: datetime, watches: List[Dict[str, Any]]) -> Dict[str, Any]:
    day = at.replace(hour=0, minute=0, second=0, microsecond=0)
    starts = sorted((day + timedelta(days=d, hours=w["start_utc"]), w) for w in watches for d in (0, 1))
    for start, w in starts:
        if start >= at:
            return {"name": w["name"], "started_at": start, "ends_at": start + timedelta(hours=w["hours"])}
    return {"name": watches[0]["name"], "started_at": at, "ends_at": at}


async def current_watch(session: AsyncSession, now: datetime) -> WatchRow:
    """The WatchRow for the slot that owns `now`, created on first sight. A watch stays 'open' or 'pending_ack'
    past its end until the incoming Battle Captain acknowledges (Decision T)."""
    cfg = await get_config(session)
    watches = json.loads(cfg.watches_json)
    # An unacknowledged watch keeps the floor even past its slot end.
    pending = (await session.execute(select(WatchRow).where(WatchRow.status.in_(("open", "pending_ack"))).order_by(WatchRow.started_at.desc()))).scalars().first()
    slot = slot_for(now, watches)
    wid = f"{slot['started_at'].strftime('%Y-%m-%dT%H')}_{slot['name'].replace(' ', '')}"
    if pending and pending.id != wid:
        return pending
    row = await session.get(WatchRow, wid)
    if not row:
        prev_bc = pending.battle_captain if pending else None
        row = WatchRow(id=wid, name=slot["name"], started_at=slot["started_at"], ends_at=slot["ends_at"], battle_captain=None)
        session.add(row)
        await session.commit()
    return row


def watch_summary(row: WatchRow, now: datetime, cfg: WatchConfigRow) -> Dict[str, Any]:
    watches = json.loads(cfg.watches_json)
    nxt = next_slot(row.ends_at, watches)
    elapsed = (now - row.started_at).total_seconds() / 3600
    remaining = (row.ends_at - now).total_seconds() / 3600
    in_overlap = remaining * 60 <= cfg.overlap_minutes
    return {
        "id": row.id, "name": row.name, "battle_captain": row.battle_captain, "status": row.status,
        "started_at": iso(row.started_at), "ends_at": iso(row.ends_at), "elapsed_h": round(elapsed, 2), "remaining_h": round(remaining, 2),
        "overdue": remaining < 0, "in_overlap": in_overlap, "overlap_minutes": cfg.overlap_minutes,
        "next_watch": nxt["name"], "next_starts_at": iso(nxt["started_at"]), "pattern": cfg.pattern,
        "nstr": bool(row.nstr), "outgoing_notes": row.outgoing_notes, "handed_over_at": iso(row.handed_over_at),
        "acknowledged_by": row.acknowledged_by, "acknowledged_at": iso(row.acknowledged_at),
    }


async def estimates(session: AsyncSession) -> List[Dict[str, Any]]:
    rows = {r.section: r for r in (await session.execute(select(SectionEstimateRow))).scalars()}
    return [{"section": s, "assessment": rows[s].assessment if s in rows else "", "recommendation": rows[s].recommendation if s in rows else "",
             "updated_by": rows[s].updated_by if s in rows else None, "updated_at": iso(rows[s].updated_at) if s in rows else None} for s in SECTIONS]


LOG_BUCKETS = {
    "cop.location.posture": "posture", "cop.threat.link_confirmed": "threats", "cop.threat.link_removed": "threats",
    "cop.intel.refresh": "collection", "cop.intel.refresh_failed": "collection",
    "cop.incident.opened": "roll_calls", "cop.incident.closed": "roll_calls", "cop.incident.checkins_requested": "roll_calls", "cop.incident.contact": "roll_calls",
    "cop.trip.created": "movement", "cop.trip.updated": "movement", "cop.trip.cancelled": "movement", "cop.person.checkin": "movement",
    "cop.event.created": "operations", "cop.event.updated": "operations", "cop.event.cancelled": "operations", "cop.event.attendees_added": "operations",
    "cop.assessment.drafted": "intel", "cop.assessment.status": "intel", "cop.pir.created": "intel", "cop.pir.updated": "intel",
    "cop.person.shift": "personnel", "cop.watch.estimate": "estimates", "cop.area.assessed": "intel", "cop.area.updated": "intel", "cop.graphic.drawn": "operations", "cop.graphic.updated": "operations", "cop.graphic.retired": "operations",
    "cop.s4.supply": "logistics", "cop.s4.shipment": "logistics", "cop.s6.system": "signal",
    "cop.tasking.raised": "operations", "cop.tasking.accepted": "operations", "cop.tasking.scheduled": "operations", "cop.tasking.complete": "operations", "cop.tasking.declined": "operations", "cop.tasking.amended": "operations",
    "s2.requirement.created": "intel", "s2.requirement.updated": "intel", "s2.source.updated": "collection", "s2.requirements.synced": "estimates",
}


async def build_brief(session: AsyncSession, snap: Dict[str, Any], row: WatchRow, cfg: WatchConfigRow, now: datetime) -> Dict[str, Any]:
    """The running estimates read out at handover, in briefing order (§3.1)."""
    start, end = row.started_at, max(row.ends_at, now)
    overlap_from = row.ends_at - timedelta(minutes=cfg.overlap_minutes)
    rows = (await session.execute(select(LedgerEventRow).where((LedgerEventRow.event_type.like("cop.%") | LedgerEventRow.event_type.like("s2.%")), LedgerEventRow.timestamp >= start,
                                                                LedgerEventRow.timestamp <= end).order_by(LedgerEventRow.id))).scalars().all()
    events, buckets = [], {}
    for r in rows:
        e = {"id": r.event_id, "at": iso(r.timestamp), "type": r.event_type, "actor": r.actor_id, "subject": r.content_id, "summary": r.reason,
             "old": r.old_state, "new": r.new_state, "during_handover": r.timestamp >= overlap_from}
        events.append(e)
        b = LOG_BUCKETS.get(r.event_type, "other")
        if b not in ("estimates",):
            buckets.setdefault(b, []).append(e)
    significant = {k: v for k, v in buckets.items() if k in ("posture", "threats", "roll_calls", "movement", "operations", "intel", "personnel", "collection", "logistics", "signal")}
    s = snap["summary"]
    nxt = next_slot(row.ends_at, json.loads(cfg.watches_json))
    def within(iso_s: Optional[str], a: datetime, b: datetime) -> bool:
        if not iso_s: return False
        t = datetime.fromisoformat(iso_s.replace("Z", ""))
        return a <= t <= b
    n0, n1 = nxt["started_at"], nxt["ends_at"]
    upcoming = {
        "events_starting": [{"id": e["id"], "name": e["name"], "venue": e["venue_name"], "start_at": e["start_at"]} for e in snap["events"] if within(e["start_at"], n0, n1)],
        "trips_departing": [{"id": t["id"], "who": t["person_name"], "to": t["dest_name"], "at": t["depart_at"]} for t in snap["trips"] if within(t["depart_at"], n0, n1)],
        "trips_returning": [{"id": t["id"], "who": t["person_name"], "from": t["dest_name"], "at": t["return_at"]} for t in snap["trips"] if within(t["return_at"], n0, n1)],
        "pirs_expiring": [{"id": p["id"], "question": p["question"], "expires_at": p["expires_at"]} for p in snap["pirs"] if within(p["expires_at"], n0, n1)],
    }
    status = {
        "estimates": snap.get("estimates", []),
        "posture": s["posture"],
        "open_incidents": [{"id": i["id"], "title": i["title"], "accounted": i["accounted"], "total": i["total"]} for i in snap["incidents"] if i["status"] == "open"],
        "unaccounted": s["unaccounted"],
        "travelers": [{"id": p["id"], "name": p["name"], "where": p["location_id"] or "en route / raw position", "checkin": p["position_source"] == "checkin"} for p in snap["people"] if p["status"] == "traveling"],
        "assessments_in_review": [{"id": a["id"], "title": a["title"]} for a in snap["assessments"] if a["status"] == "review"],
        "open_pirs": [{"id": p["id"], "question": p["question"]} for p in snap["pirs"] if p["status"] in ("OPEN", "COLLECTING")],
        "stale_checkins": [{"id": p["id"], "name": p["name"]} for p in snap["people"] if p["checkin_stale"]],
        "logistics": {"status": snap.get("s4", {}).get("status", "green"), "exceptions": snap.get("s4", {}).get("exceptions", [])},  # §7: by exception
        "signal": {"status": snap.get("s6", {}).get("status", "green"), "exceptions": snap.get("s6", {}).get("exceptions", [])},    # §8: by exception
        "taskings": [{"id": x["id"], "title": x["title"], "from": x["from_section"], "to": x["to_section"], "status": x["status"], "priority": x["priority"], "overdue": x["overdue"]} for x in snap.get("taskings", {}).get("items", []) if x["open"]],  # §5.10
    }
    handover_items = [{"kind": "open_incident", **i} for i in status["open_incidents"]] + \
                     [{"kind": "during_handover", "id": e["id"], "summary": e["summary"], "at": e["at"]} for e in events if e["during_handover"]]
    return {
        "watch": watch_summary(row, now, cfg), "window": {"from": iso(start), "to": iso(end), "overlap_from": iso(overlap_from)},
        "significant_events": significant, "event_count": len(events),
        "current_status": status, "next_shift": {"watch": nxt["name"], "from": iso(n0), "to": iso(n1), **upcoming},
        "handover_items": handover_items, "outgoing_notes": row.outgoing_notes, "nstr": bool(row.nstr),
        "acknowledgement": {"required_item_ids": [h["id"] for h in handover_items if h["kind"] == "during_handover"],
                            "by": row.acknowledged_by, "at": iso(row.acknowledged_at)},
        "generated_at": iso(now),
    }
