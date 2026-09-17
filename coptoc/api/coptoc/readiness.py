"""§4 and §7 — the pieces a military or police deployment adds first: where the units are, what the equipment can do,
and how long the fuel lasts.

Three things, and each one only says what its data supports:

* **Unit positions.** A tracker report — JBC-P, a vehicle tracker, or a radio call written down — puts a team on the
  map the way a traveller's check-in puts a person there. Nothing is inferred: a team with no report has no position,
  and a report that has aged past the staleness setting says so rather than pretending to be current.
* **Equipment readiness by bumper number.** One row per airframe, vehicle or generator, in FMC / PMC / NMC with the
  fault and the clock since it went down. The OR rate is the definition — fully mission capable over assigned — and
  nothing else; there is no weighting, no score, and no rate at all for a unit that has no equipment recorded.
* **Days of supply.** On hand divided by the daily use rate S4 *entered*. A line with no rate shows no days: the
  honest answer to "how long will the fuel last" without a consumption figure is that we do not know.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared import settings
from shared.database import Base

STATUSES = ("fmc", "pmc", "nmc")          # fully / partially / not mission capable
CATEGORIES = ("airframe", "vehicle", "generator", "radio", "weapon", "other")
POSITION_SOURCES = ("jbc-p", "tracker", "radio", "manual")
DEFAULT_STALE_MINUTES = 30                 # a setting, not a judgment: TOC_UNIT_STALE_MIN
DEFAULT_OR_GREEN, DEFAULT_OR_AMBER = 90, 75   # where an OR rate stops being green and stops being amber — settings too


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


def _setting(name: str, default: int) -> int:
    try:
        return max(1, int(settings.get(name, os.environ.get(name, default)) or default))
    except (TypeError, ValueError):
        return default


def stale_minutes() -> int:
    return _setting("TOC_UNIT_STALE_MIN", DEFAULT_STALE_MINUTES)


def or_bands() -> tuple:
    """What counts as a green or an amber OR rate. The rate itself is a definition; where the line sits is a command
    decision, so it is a setting — TOC_OR_GREEN / TOC_OR_AMBER — and never a number this code decided."""
    return _setting("TOC_OR_GREEN", DEFAULT_OR_GREEN), _setting("TOC_OR_AMBER", DEFAULT_OR_AMBER)


class UnitPositionRow(Base):
    """One position report for a team. The chain is the track; the latest one is where the unit is."""
    __tablename__ = "cop_unit_positions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    team_id: Mapped[str] = mapped_column(String, index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    at: Mapped[datetime] = mapped_column(DateTime, index=True)
    source: Mapped[str] = mapped_column(String, default="tracker")   # jbc-p | tracker | radio | manual
    speed_kph: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    heading: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    reported_by: Mapped[str] = mapped_column(String, default="")


class EquipmentRow(Base):
    """One piece of equipment, by bumper number. §7's [LATER], built."""
    __tablename__ = "cop_equipment"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    bumper_number: Mapped[str] = mapped_column(String, index=True)
    model: Mapped[str] = mapped_column(String, default="")
    category: Mapped[str] = mapped_column(String, default="vehicle")
    team_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    location_id: Mapped[Optional[str]] = mapped_column(ForeignKey("cop_locations.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String, default="fmc")
    fault: Mapped[str] = mapped_column(Text, default="")
    since: Mapped[datetime] = mapped_column(DateTime)
    updated_by: Mapped[str] = mapped_column(String, default="seed")
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(String, default="manual")


# ---------------------------------------------------------------- the board

def position_out(row: UnitPositionRow, team_name: str, now: datetime, team_short: str = "") -> Dict[str, Any]:
    age = round((now - row.at).total_seconds() / 60)
    return {"team_id": row.team_id, "team_name": team_name, "team_short": team_short or team_name, "lat": row.lat, "lon": row.lon, "at": iso(row.at), "age_min": age,
            "stale": age > stale_minutes(), "stale_after_min": stale_minutes(), "source": row.source,
            "speed_kph": row.speed_kph, "heading": row.heading, "note": row.note, "reported_by": row.reported_by}


async def latest_positions(session: AsyncSession, team_name: Dict[str, str], now: datetime, team_short: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """The last report per team. A team nobody has reported is simply absent — the map shows what is known."""
    rows = (await session.execute(select(UnitPositionRow).order_by(UnitPositionRow.at.desc()).limit(2000))).scalars().all()
    latest: Dict[str, UnitPositionRow] = {}
    for r in rows:
        if r.team_id not in latest:
            latest[r.team_id] = r
    return [position_out(r, team_name.get(r.team_id, r.team_id), now, (team_short or {}).get(r.team_id, "")) for r in sorted(latest.values(), key=lambda x: team_name.get(x.team_id, x.team_id))]


def equipment_out(row: EquipmentRow, team_name: Dict[str, str], loc_name: Dict[str, str], now: datetime) -> Dict[str, Any]:
    return {"id": row.id, "bumper_number": row.bumper_number, "model": row.model, "category": row.category,
            "team_id": row.team_id, "team_name": team_name.get(row.team_id or "", ""), "location_id": row.location_id,
            "location_name": loc_name.get(row.location_id or "", ""), "status": row.status, "fault": row.fault,
            "since": iso(row.since), "hours_down": round((now - row.since).total_seconds() / 3600, 1) if row.status != "fmc" else 0.0,
            "updated_by": row.updated_by, "updated_at": iso(row.updated_at), "source": row.source}


def readiness(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Readiness by model and by unit. The OR rate is its definition — FMC over assigned — and nothing else: no
    weighting, no score, and no rate at all where nothing is recorded."""
    green_at, amber_at = or_bands()
    def group(key: str, label: str) -> List[Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            k = r[key] or "unassigned"
            g = out.setdefault(k, {label: k, "assigned": 0, "fmc": 0, "pmc": 0, "nmc": 0})
            g["assigned"] += 1
            g[r["status"]] = g.get(r["status"], 0) + 1
        for g in out.values():
            g["or_pct"] = round(100 * g["fmc"] / g["assigned"]) if g["assigned"] else None
            g["status"] = "green" if g["or_pct"] is not None and g["or_pct"] >= green_at else "amber" if g["or_pct"] is not None and g["or_pct"] >= amber_at else "red"
        return sorted(out.values(), key=lambda g: (g["or_pct"] if g["or_pct"] is not None else 101, g[label]))
    down = [r for r in rows if r["status"] != "fmc"]
    total = len(rows)
    fmc = sum(1 for r in rows if r["status"] == "fmc")
    return {"bands": {"green_at": green_at, "amber_at": amber_at}, "assigned": total, "fmc": fmc, "pmc": sum(1 for r in rows if r["status"] == "pmc"), "nmc": sum(1 for r in rows if r["status"] == "nmc"),
            "or_pct": round(100 * fmc / total) if total else None, "by_model": group("model", "model"), "by_unit": group("team_name", "unit"),
            "down": sorted(down, key=lambda r: -r["hours_down"]),
            "exceptions": [f"{r['bumper_number']} ({r['model'] or r['category']}): {r['status'].upper()} {r['hours_down']:g}h"
                           + (f" — {r['fault']}" if r["fault"] else "") for r in sorted(down, key=lambda r: -r["hours_down"])[:8]]}


def days_of_supply(on_hand: float, daily_use: Optional[float]) -> Optional[float]:
    """On hand over the daily use rate S4 entered. No rate, no number — 'how long will the fuel last' has no honest
    answer without a consumption figure, and a made-up one is worse than a blank."""
    if not daily_use or daily_use <= 0:
        return None
    return round(on_hand / daily_use, 1)


# ---------------------------------------------------------------- writes

async def report_position(session: AsyncSession, team_id: str, *, lat: float, lon: float, at: Optional[datetime], source: str,
                          speed_kph: Optional[float], heading: Optional[float], note: str, reported_by: str) -> UnitPositionRow:
    row = UnitPositionRow(id=f"pos_{uuid.uuid4().hex[:10]}", team_id=team_id, lat=lat, lon=lon, at=at or now_utc(),
                          source=source if source in POSITION_SOURCES else "tracker", speed_kph=speed_kph, heading=heading,
                          note=note or "", reported_by=reported_by or "")
    session.add(row)
    await session.commit()
    return row


async def upsert_equipment(session: AsyncSession, data: Dict[str, Any], actor: str) -> EquipmentRow:
    """By bumper number: the same airframe reported twice is the same row. A status that changes starts its own clock."""
    bumper = (data.get("bumper_number") or "").strip()
    if not bumper:
        raise ValueError("equipment needs a bumper number")
    status = (data.get("status") or "fmc").lower()
    if status not in STATUSES:
        raise ValueError(f"status is one of {list(STATUSES)}")
    row = (await session.execute(select(EquipmentRow).where(EquipmentRow.bumper_number == bumper))).scalars().first()
    now = now_utc()
    if not row:
        row = EquipmentRow(id=f"eq_{uuid.uuid4().hex[:8]}", bumper_number=bumper, since=now, updated_at=now)
        session.add(row)
    for k in ("model", "category", "team_id", "location_id", "fault", "source"):
        if data.get(k) is not None:
            setattr(row, k, data[k])
    if row.category not in CATEGORIES:
        row.category = "other"
    if status != row.status:
        row.since = now
    row.status, row.updated_by, row.updated_at = status, actor, now
    await session.commit()
    return row
