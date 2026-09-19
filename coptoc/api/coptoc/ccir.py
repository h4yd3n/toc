"""§3.6 CCIR — the commander's critical information requirements: one list of what has to wake the commander.

A TOC runs on three kinds of requirement and this is the only place they sit together:

* **PIR** — priority intelligence requirements, about the enemy or the environment. They already exist as S2 objects;
  a PIR line here points at one rather than copying it, and trips when that PIR is answered. What the commander wants
  to be told is not that a question was asked — it is that it now has an answer.
* **FFIR** — friendly force information requirements, about us. The facts were already on the wall as numbers:
  people unaccounted for, the OR rate, days of supply, a degraded PACE net, a unit nobody has heard from. What was
  missing was anyone declaring a number a *requirement* with a threshold and an owner. That declaration is this row.
* **EEFI** — essential elements of friendly information: what we must not let the other side learn. Nothing in the
  data measures our own signature, so an EEFI line never trips by itself. It is a written line the staff reads and
  checks itself against, and pretending otherwise would be an instrument with nothing behind it.

**A trip reports; it does not act.** When an FFIR crosses its threshold the board turns it red, a line goes on the
watch (so the handover brief carries it), the ledger records it, and a warning is *suggested* to the Battle Captain.
Nothing is dispatched and nobody is tasked until a human says so — the same boundary the rest of the system holds.
Recovery is recorded too: a line that comes back inside its threshold clears, with the time it spent tripped.

**Hysteresis.** State changes are what get recorded, never the evaluation itself. A line evaluated every minute for a
day writes nothing at all while it stays green, and one ledger event when it trips.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base

KINDS = ("pir", "ffir", "eefi")
STATES = ("green", "tripped", "unmeasured", "narrative")
COMPARATORS = ("lt", "lte", "gt", "gte", "eq")
SECTIONS = ("S1", "S2", "S3", "S4", "S6")
PRIORITIES = (1, 2, 3)                      # 1 is the commander's first question
SEVERITY_BY_PRIORITY = {1: "critical", 2: "elevated", 3: "moderate"}


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


# ---------------------------------------------------------------- the metrics an FFIR can watch
#
# Every one of these is already on the wall; none is computed here a second way. A metric that cannot be read from
# the snapshot returns None, and a line watching it reads "unmeasured" rather than green — the difference between
# "we checked and we are fine" and "nothing told us" is the whole point of a CCIR.

def _min_days_of_supply(snap: Dict[str, Any], scope: str) -> Optional[float]:
    days = [s["days_of_supply"] for s in snap.get("s4", {}).get("supplies", [])
            if s.get("days_of_supply") is not None and (not scope or scope.lower() in (s.get("category", "") + " " + s.get("item", "")).lower())]
    return min(days) if days else None


def _or_pct(snap: Dict[str, Any], scope: str) -> Optional[float]:
    rdy = snap.get("s4", {}).get("readiness", {})
    if not scope:
        return rdy.get("or_pct")
    for g in rdy.get("by_unit", []):       # scope names a unit, then a model — whichever matches first
        if scope.lower() in str(g.get("unit", "")).lower():
            return g.get("or_pct")
    for g in rdy.get("by_model", []):
        if scope.lower() in str(g.get("model", "")).lower():
            return g.get("or_pct")
    return None


def _pace_degraded(snap: Dict[str, Any], scope: str) -> Optional[float]:
    systems = [s for s in snap.get("s6", {}).get("systems", [])
               if not scope or scope.lower() in (s.get("location_name", "") + " " + s.get("name", "")).lower()]
    return float(sum(1 for s in systems if s.get("health") != "green")) if systems else None


def _stale_units(snap: Dict[str, Any], scope: str) -> Optional[float]:
    pos = [p for p in snap.get("unit_positions", []) if not scope or scope.lower() in (p.get("team_name", "") + " " + p.get("team_short", "")).lower()]
    return float(sum(1 for p in pos if p.get("stale"))) if pos else None


def _summary(key: str) -> Callable[[Dict[str, Any], str], Optional[float]]:
    def read(snap: Dict[str, Any], _scope: str) -> Optional[float]:
        v = snap.get("summary", {}).get(key)
        return float(v) if isinstance(v, (int, float)) else None
    return read


METRICS: Dict[str, Dict[str, Any]] = {
    "unaccounted":       {"label": "People unaccounted for in an open roll call", "section": "S1", "unit": "people", "read": _summary("unaccounted")},
    "unreachable":       {"label": "People unreachable", "section": "S1", "unit": "people", "read": _summary("unreachable")},
    "security_on_shift": {"label": "Security on shift", "section": "S1", "unit": "people", "read": _summary("security_on_shift")},
    "open_incidents":    {"label": "Open roll calls", "section": "S1", "unit": "roll calls", "read": _summary("open_incidents")},
    "stale_units":       {"label": "Units with no position report inside the staleness window", "section": "S3", "unit": "units", "read": _stale_units},
    "or_pct":            {"label": "Operational readiness rate (FMC over assigned)", "section": "S4", "unit": "%", "read": _or_pct},
    "days_of_supply":    {"label": "Lowest days of supply on any line with a use rate", "section": "S4", "unit": "days", "read": _min_days_of_supply},
    "pace_degraded":     {"label": "Comms systems not green", "section": "S6", "unit": "systems", "read": _pace_degraded},
    "defcon":            {"label": "Posture read as DEFCON", "section": "S3", "unit": "DEFCON", "read": _summary("defcon")},
    "active_threats":    {"label": "Active threats on the picture", "section": "S2", "unit": "threats", "read": _summary("active_threats")},
    "movement_risks":    {"label": "Movements crossing a threat graphic", "section": "S3", "unit": "movements", "read": _summary("movement_risks")},
    "decisions_overdue": {"label": "Decision points past their no-later-than", "section": "S3", "unit": "decisions", "read": _summary("decisions_overdue")},
    "taskings_overdue":  {"label": "Taskings past their due time", "section": "S3", "unit": "taskings", "read": _summary("taskings_overdue")},
}


def metric_catalog() -> List[Dict[str, Any]]:
    return [{"id": k, "label": v["label"], "section": v["section"], "unit": v["unit"]} for k, v in METRICS.items()]


class CcirRow(Base):
    """One line of the commander's critical information requirements."""
    __tablename__ = "cop_ccir"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, index=True)            # pir | ffir | eefi
    text: Mapped[str] = mapped_column(Text)                          # the requirement in the commander's words
    owner_section: Mapped[str] = mapped_column(String, default="S3")
    priority: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(String, default="active")    # active | inactive
    # an FFIR watches a metric; a PIR points at a PIR; an EEFI watches nothing
    metric: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    comparator: Mapped[str] = mapped_column(String, default="gte")
    threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    scope: Mapped[str] = mapped_column(String, default="")           # a unit, a site, a supply class — free text, matched by name
    pir_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # state, and the history of it
    state: Mapped[str] = mapped_column(String, default="green")
    last_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_eval_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tripped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cleared_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    trips: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    approved_by: Mapped[str] = mapped_column(String, default="")     # CCIR is the commander's list: the BC signs it


def to_dict(row: CcirRow, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or now_utc()
    m = METRICS.get(row.metric or "", {})
    return {
        "id": row.id, "kind": row.kind, "text": row.text, "owner_section": row.owner_section, "priority": row.priority,
        "status": row.status, "metric": row.metric, "metric_label": m.get("label", ""), "unit": m.get("unit", ""),
        "comparator": row.comparator, "threshold": row.threshold, "scope": row.scope, "pir_id": row.pir_id,
        "state": row.state, "last_value": row.last_value, "last_eval_at": iso(row.last_eval_at),
        "tripped_at": iso(row.tripped_at), "cleared_at": iso(row.cleared_at), "trips": row.trips,
        "tripped_min": round((now - row.tripped_at).total_seconds() / 60) if row.state == "tripped" and row.tripped_at else None,
        "created_by": row.created_by, "created_at": iso(row.created_at), "approved_by": row.approved_by,
        "condition": condition_text(row),
    }


def condition_text(row: CcirRow) -> str:
    """The line as a person would read it out: 'days of supply below 3 (Class III)'."""
    if row.kind == "eefi":
        return "not measured — a written line the staff checks itself against"
    if row.kind == "pir":
        return f"tripped when {row.pir_id or 'the linked PIR'} is answered"
    m = METRICS.get(row.metric or "")
    if not m or row.threshold is None:
        return "no threshold set"
    word = {"lt": "below", "lte": "at or below", "gt": "above", "gte": "at or above", "eq": "exactly"}[row.comparator]
    return f"{m['label'].lower()} {word} {row.threshold:g}{('%' if m['unit'] == '%' else '')}" + (f" ({row.scope})" if row.scope else "")


def _crossed(value: Optional[float], comparator: str, threshold: Optional[float]) -> Optional[bool]:
    if value is None or threshold is None:
        return None
    return {"lt": value < threshold, "lte": value <= threshold, "gt": value > threshold,
            "gte": value >= threshold, "eq": value == threshold}[comparator]


def evaluate(row: CcirRow, snap: Dict[str, Any]) -> Dict[str, Any]:
    """Read-only: what this line's state *should* be, given the picture. Recording the change is a separate act."""
    if row.status != "active":
        return {"state": row.state, "value": row.last_value}
    if row.kind == "eefi":
        return {"state": "narrative", "value": None}
    if row.kind == "pir":
        pir = next((p for p in snap.get("pirs", []) if p.get("id") == row.pir_id), None)
        if not pir:
            return {"state": "unmeasured", "value": None}
        return {"state": "tripped" if str(pir.get("status", "")).upper() == "ANSWERED" else "green", "value": None}
    m = METRICS.get(row.metric or "")
    if not m:
        return {"state": "unmeasured", "value": None}
    value = m["read"](snap, row.scope or "")
    crossed = _crossed(value, row.comparator, row.threshold)
    return {"state": "unmeasured" if crossed is None else "tripped" if crossed else "green", "value": value}


def board(rows: List[CcirRow], snap: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    """The board as the wall draws it: every line with its live state, and the counts the rail badge needs."""
    now = now or now_utc()
    out = []
    for r in rows:
        d = to_dict(r, now)
        ev = evaluate(r, snap)
        d["state"], d["value"] = ev["state"], ev["value"]      # live, not the last recorded state
        out.append(d)
    order = {"tripped": 0, "unmeasured": 1, "green": 2, "narrative": 3}
    out.sort(key=lambda d: (order.get(d["state"], 4), d["priority"], d["kind"]))
    return {"lines": out,
            "counts": {"tripped": sum(1 for d in out if d["state"] == "tripped"),
                       "unmeasured": sum(1 for d in out if d["state"] == "unmeasured"),
                       "active": sum(1 for d in out if d["status"] == "active"),
                       "total": len(out)},
            "by_kind": {k: sum(1 for d in out if d["kind"] == k) for k in KINDS}}


# ---------------------------------------------------------------- writes

async def create(session: AsyncSession, data: Dict[str, Any], actor: str) -> CcirRow:
    kind = (data.get("kind") or "ffir").lower()
    if kind not in KINDS:
        raise ValueError(f"kind is one of {list(KINDS)}")
    text = (data.get("text") or "").strip()
    if not text:
        raise ValueError("a CCIR line needs its text — the requirement in the commander's words")
    metric = data.get("metric") or None
    if kind == "ffir":
        if metric not in METRICS:
            raise ValueError(f"an FFIR watches one of {list(METRICS)}")
        if data.get("threshold") is None:
            raise ValueError("an FFIR needs a threshold — a requirement without one cannot trip")
    if kind == "pir" and not data.get("pir_id"):
        raise ValueError("a PIR line points at an existing PIR")
    comparator = (data.get("comparator") or "gte").lower()
    if comparator not in COMPARATORS:
        raise ValueError(f"comparator is one of {list(COMPARATORS)}")
    section = (data.get("owner_section") or METRICS.get(metric or "", {}).get("section") or "S3").upper()
    row = CcirRow(id=f"ccir_{uuid.uuid4().hex[:8]}", kind=kind, text=text, owner_section=section if section in SECTIONS else "S3",
                  priority=int(data.get("priority") or 2), metric=metric if kind == "ffir" else None, comparator=comparator,
                  threshold=float(data["threshold"]) if kind == "ffir" and data.get("threshold") is not None else None,
                  scope=(data.get("scope") or "").strip(), pir_id=data.get("pir_id") if kind == "pir" else None,
                  state="narrative" if kind == "eefi" else "green", created_by=actor, created_at=now_utc(),
                  approved_by=data.get("approved_by") or "")
    if row.priority not in PRIORITIES:
        row.priority = 2
    session.add(row)
    await session.commit()
    return row


async def update(session: AsyncSession, row: CcirRow, data: Dict[str, Any], actor: str) -> CcirRow:
    for k in ("text", "scope", "owner_section", "status", "approved_by"):
        if data.get(k) is not None:
            setattr(row, k, data[k])
    if data.get("priority") is not None and int(data["priority"]) in PRIORITIES:
        row.priority = int(data["priority"])
    if data.get("comparator") is not None and data["comparator"] in COMPARATORS:
        row.comparator = data["comparator"]
    if data.get("threshold") is not None:
        row.threshold = float(data["threshold"])
    if data.get("metric") is not None and row.kind == "ffir":
        if data["metric"] not in METRICS:
            raise ValueError(f"an FFIR watches one of {list(METRICS)}")
        row.metric = data["metric"]
    await session.commit()
    return row


async def record_changes(session: AsyncSession, snap: Dict[str, Any], ledger, *, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Evaluate every active line and record only the state *changes*: a trip, or a recovery.

    A trip writes three things and dispatches nothing: the ledger event, a line on the watch through that event (the
    handover brief buckets `cop.ccir.*`), and a *suggested* warning for the Battle Captain to release or dismiss.
    """
    from sigtoc.warning import WarningRow
    now = now or now_utc()
    rows = (await session.execute(select(CcirRow).where(CcirRow.status == "active"))).scalars().all()
    changes: List[Dict[str, Any]] = []
    for row in rows:
        ev = evaluate(row, snap)
        state, value = ev["state"], ev["value"]
        row.last_value, row.last_eval_at = value, now
        if state == row.state or state == "narrative":
            continue
        old, row.state = row.state, state
        if state == "tripped":
            row.tripped_at, row.cleared_at, row.trips = now, None, row.trips + 1
            reading = f"{value:g}" if value is not None else "no reading"
            reason = f"CCIR {row.kind.upper()} tripped — {row.text} ({condition_text(row)}; now {reading})"
            session.add(WarningRow(
                id=f"warn_{uuid.uuid4().hex[:10]}", title=f"CCIR tripped — {row.text}", text=reason,
                subject_type="ccir", subject_id=row.id, subject_name=row.owner_section,
                severity=SEVERITY_BY_PRIORITY.get(row.priority, "elevated"), status="suggested",
                suggested_by=f"ccir:{row.id}", created_at=now))
        elif old == "tripped":
            row.cleared_at = now
            held = round((now - row.tripped_at).total_seconds() / 60) if row.tripped_at else None
            reason = f"CCIR {row.kind.upper()} cleared — {row.text}" + (f" (tripped for {held} min)" if held is not None else "")
        else:
            reason = f"CCIR {row.kind.upper()} {state} — {row.text}"
        await ledger.append_event(content_id=row.id, event_type="cop.ccir.tripped" if state == "tripped" else "cop.ccir.cleared",
                                  actor_type="system", actor_id="ccir", old_state=old, new_state=state, reason=reason,
                                  metadata={"metric": row.metric, "value": value, "threshold": row.threshold, "kind": row.kind,
                                            "owner_section": row.owner_section, "priority": row.priority})
        changes.append({"id": row.id, "kind": row.kind, "text": row.text, "old": old, "new": state, "value": value})
    await session.commit()
    return changes


# ---------------------------------------------------------------- the standing board the sample force arrives with

def seed(dataset: str, now: datetime) -> List[CcirRow]:
    """A sample CCIR, so a fresh install opens on a board somebody agreed to watch rather than an empty list.

    Every threshold here is a *commander's* number, not an analytic constant: it is what the sample commander chose,
    it lives in the row, and the Battle Captain changes it on the wall. The metrics are the ones already on the wall.
    """
    def line(kind: str, text: str, section: str, priority: int, **kw: Any) -> CcirRow:
        row = CcirRow(id=f"ccir_{uuid.uuid4().hex[:8]}", kind=kind, text=text, owner_section=section, priority=priority,
                      state="narrative" if kind == "eefi" else "green", created_by="seed", created_at=now,
                      approved_by="Battle Captain", comparator=kw.pop("comparator", "gte"), **kw)
        return row

    if dataset == "cab":
        return [
            line("ffir", "Any soldier unaccounted for in an open roll call", "S1", 1, metric="unaccounted", comparator="gte", threshold=1),
            line("ffir", "A unit out of contact past the staleness window", "S3", 2, metric="stale_units", comparator="gte", threshold=1),
            line("ffir", "Aircraft readiness below the amber band the commander set", "S4", 2, metric="or_pct", comparator="lt", threshold=75),
            line("ffir", "Class III below three days of supply at any site", "S4", 1, metric="days_of_supply", comparator="lt", threshold=3, scope="III"),
            line("ffir", "A command post down to tertiary or emergency comms", "S6", 2, metric="pace_degraded", comparator="gte", threshold=1),
            line("pir", "Hostile or nuisance UAS over the airfield or FARP Eagle", "S2", 1, pir_id="pir_uas"),
            line("eefi", "Timing and route of the brigade commander's movement", "S3", 1),
            line("eefi", "The site the TOC is running from, and where it jumps next", "S6", 2),
        ]
    return [
        line("ffir", "Any person unaccounted for in an open roll call", "S1", 1, metric="unaccounted", comparator="gte", threshold=1),
        line("ffir", "Any traveler unreachable", "S1", 1, metric="unreachable", comparator="gte", threshold=1),
        line("ffir", "A movement routed across a known threat", "S3", 2, metric="movement_risks", comparator="gte", threshold=1),
        line("ffir", "A decision point past its no-later-than", "S3", 2, metric="decisions_overdue", comparator="gte", threshold=1),
        line("pir", "Credible targeting of Western business travelers during the CEO visit window", "S2", 1, pir_id="PIR-01"),
        line("eefi", "The principal's itinerary, hotel, and arrival times", "S3", 1),
    ]
