"""§5.2–5.3 — requirements are first-class; the collection plan generates itself.

A requirement is the unit of S2 work. Standing ones are written by the wall (a trip, an event, a site); directed ones
are a four-field form (place, window, purpose, priority). Each decomposes into indicators; each indicator maps to the
sources that can observe it; coverage — and the gaps — are visible before anyone asks for an assessment."""
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


# ---------------------------------------------------------------- the indicator taxonomy
# What would answer the question, by kind of subject. Keys are stable; sources declare which keys they observe.
INDICATORS: Dict[str, Dict[str, str]] = {
    "natural_hazard":   {"label": "Hazardous weather or natural events in the window"},
    "earthquake":       {"label": "Seismic activity near the subject"},
    "advisory":         {"label": "Travel advisory level and any change"},
    "civil_unrest":     {"label": "Civil unrest or political violence near the subject"},
    "health":           {"label": "Health notices for the country"},
    "crime":            {"label": "Violent crime and kidnap-for-ransom reporting"},
    "targeted":         {"label": "Threat reporting naming the company, its people, or its sector"},
    "transit":          {"label": "Airport, transit, and route disruption"},
    "crowd":            {"label": "Planned demonstrations, large gatherings, counter-protest near the venue"},
    "baseline":         {"label": "Baseline for an unfamiliar place: holidays, climate, local norms"},
    "infrastructure":   {"label": "Power, comms, and infrastructure disruption"},
}
# Which indicators a subject kind needs. This is the decomposition rule; the analyst can add or drop per requirement.
PROFILE: Dict[str, List[str]] = {
    "location": ["natural_hazard", "earthquake", "advisory", "civil_unrest", "health", "targeted", "infrastructure"],
    "trip":     ["natural_hazard", "earthquake", "advisory", "civil_unrest", "health", "crime", "targeted", "transit"],
    "event":    ["natural_hazard", "advisory", "civil_unrest", "crowd", "targeted", "transit"],
    "person":   ["targeted", "civil_unrest", "crime"],
    "place":    ["natural_hazard", "earthquake", "advisory", "civil_unrest", "health", "crime", "crowd", "transit", "baseline"],
}

# ---------------------------------------------------------------- the source catalog (PRD §5.8)
# `configured` is computed at runtime from environment/keys; `enabled` is the operator's switch.
CATALOG: List[Dict[str, Any]] = [
    {"id": "gdacs",       "name": "GDACS",                       "indicators": ["natural_hazard"],              "access": "free, keyless", "reliability": "A", "cadence": "hourly",  "built": True},
    {"id": "usgs",        "name": "USGS earthquakes",            "indicators": ["earthquake"],                  "access": "free, keyless", "reliability": "A", "cadence": "hourly",  "built": True},
    {"id": "nws",         "name": "NWS / NOAA alerts (US)",      "indicators": ["natural_hazard"],              "access": "free, keyless", "reliability": "A", "cadence": "hourly",  "built": True},
    {"id": "reliefweb",   "name": "ReliefWeb",                   "indicators": ["natural_hazard", "civil_unrest"], "access": "free, keyless", "reliability": "B", "cadence": "daily", "built": False},
    {"id": "acled",       "name": "ACLED",                       "indicators": ["civil_unrest"],                "access": "free key",      "reliability": "B", "cadence": "daily",   "built": True},
    {"id": "gdelt",       "name": "GDELT",                       "indicators": ["civil_unrest", "crowd"],       "access": "free",          "reliability": "C", "cadence": "hourly",  "built": False},
    {"id": "clstr",       "name": "CLSTR news clusters",         "indicators": ["civil_unrest", "crowd", "targeted"], "access": "free key, 100/day", "reliability": "F", "cadence": "every few hours", "built": True},
    {"id": "who_don",     "name": "WHO Disease Outbreak News",   "indicators": ["health"],                      "access": "free RSS",      "reliability": "A", "cadence": "daily",   "built": True},
    {"id": "state_dept",  "name": "State Dept advisories (RSS)", "indicators": ["advisory"],                    "access": "free",          "reliability": "A", "cadence": "daily",   "built": True},
    {"id": "fcdo",        "name": "FCDO travel advice",          "indicators": ["advisory"],                    "access": "free",          "reliability": "A", "cadence": "daily",   "built": True},
    {"id": "wikidata",    "name": "Nager.Date · Wikidata (baseline)", "indicators": ["baseline"],           "access": "free, keyless", "reliability": "B", "cadence": "on demand", "built": True},
    {"id": "opensanctions","name": "OpenSanctions",              "indicators": ["targeted"],                    "access": "free",          "reliability": "B", "cadence": "weekly",  "built": False},
    {"id": "osac",        "name": "OSAC",                        "indicators": ["crime", "advisory", "targeted"], "access": "login",       "reliability": "A", "cadence": "daily",   "built": False},
    {"id": "commercial",  "name": "Flashpoint · Dataminr · Recorded Future", "indicators": ["targeted", "crime", "civil_unrest"], "access": "paid", "reliability": "B", "cadence": "continuous", "built": False},
    {"id": "ops",         "name": "Organic reports (our own people)", "indicators": ["crowd", "transit", "infrastructure", "targeted", "civil_unrest"], "access": "internal", "reliability": "A", "cadence": "continuous", "built": True},
]
CADENCES = ["manual", "hourly", "every few hours", "daily", "weekly", "continuous", "on demand"]  # Decision K: operator-adjustable


class RequirementRow(Base):
    __tablename__ = "s2_requirements"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String)  # standing | directed
    subject_type: Mapped[str] = mapped_column(String)  # location | trip | event | person | place
    subject_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # wall entity id, or None for a place
    subject_name: Mapped[str] = mapped_column(String)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float, default=50.0)
    question: Mapped[str] = mapped_column(Text)
    purpose: Mapped[str] = mapped_column(String, default="")
    priority: Mapped[int] = mapped_column(Integer, default=2)
    window_from: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    window_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")  # active | answered | expired
    owner: Mapped[str] = mapped_column(String, default="S2")
    indicators_json: Mapped[str] = mapped_column(Text, default="[]")  # the analyst may add/drop
    country: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # ISO — country-scoped reporting attaches here
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class SourceStateRow(Base):
    """Operator settings per catalog source: enabled, cadence, and any reliability override (Decision K)."""
    __tablename__ = "s2_sources"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    cadence: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reliability: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


def _configured(source_id: str) -> bool:
    """Whether the source can actually be collected from right now — built, and keyed if it needs a key."""
    from .collectors.registry import configured
    return configured(source_id)


async def source_states(session: AsyncSession) -> Dict[str, SourceStateRow]:
    rows = {r.id: r for r in (await session.execute(select(SourceStateRow))).scalars()}
    for c in CATALOG:
        if c["id"] not in rows:
            r = SourceStateRow(id=c["id"], enabled=True, cadence=c["cadence"]); session.add(r); rows[c["id"]] = r
    await session.commit()
    return rows


async def catalog(session: AsyncSession) -> List[Dict[str, Any]]:
    st = await source_states(session)
    out = []
    for c in CATALOG:
        s = st[c["id"]]
        out.append({**c, "enabled": s.enabled, "cadence": s.cadence or c["cadence"], "reliability": s.reliability or c["reliability"],
                    "configured": c["built"] and _configured(c["id"]), "last_collected_at": iso(s.last_collected_at), "last_result": s.last_result,
                    "cadences": CADENCES})
    return out


def plan_for(req: RequirementRow, cat: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The synchronization matrix for one requirement: indicator → sources that observe it → covered or gap."""
    keys = json.loads(req.indicators_json or "[]") or PROFILE.get(req.subject_type, PROFILE["place"])
    rows, covered = [], 0
    for k in keys:
        srcs = [c for c in cat if k in c["indicators"]]
        live = [c for c in srcs if c["enabled"] and c["configured"]]
        rec = [c for c in srcs if not (c["enabled"] and c["configured"])]
        ok = bool(live)
        covered += ok
        rows.append({"indicator": k, "label": INDICATORS[k]["label"], "covered": ok,
                     "sources": [{"id": c["id"], "name": c["name"], "reliability": c["reliability"], "cadence": c["cadence"]} for c in live],
                     "recommended": [{"id": c["id"], "name": c["name"], "access": c["access"], "reliability": c["reliability"], "built": c["built"]} for c in rec]})
    return {"requirement_id": req.id, "indicators": rows, "covered": covered, "total": len(rows),
            "gaps": [r["indicator"] for r in rows if not r["covered"]], "coverage_pct": round(100 * covered / len(rows)) if rows else 100}


def to_dict(req: RequirementRow, plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    d = {"id": req.id, "kind": req.kind, "subject_type": req.subject_type, "subject_id": req.subject_id, "subject_name": req.subject_name,
         "lat": req.lat, "lon": req.lon, "radius_km": req.radius_km, "question": req.question, "purpose": req.purpose, "priority": req.priority,
         "window_from": iso(req.window_from), "window_to": iso(req.window_to), "status": req.status, "owner": req.owner, "country": req.country,
         "indicators": json.loads(req.indicators_json or "[]"), "created_at": iso(req.created_at), "updated_at": iso(req.updated_at)}
    if plan:
        d["coverage"] = {"covered": plan["covered"], "total": plan["total"], "pct": plan["coverage_pct"], "gaps": plan["gaps"]}
    return d


# ---------------------------------------------------------------- standing requirements write themselves (§5.2)

def _standing_from_snapshot(snap: Dict[str, Any]) -> List[Dict[str, Any]]:
    """What the wall implies. Called by Coptoc whenever S1/S3 changes."""
    from .countries import country_from_place, to_iso
    out = []
    loc_country = {l["id"]: to_iso(l.get("country")) for l in snap.get("locations", [])}
    for l in snap.get("locations", []):
        out.append({"id": f"req_loc_{l['id']}", "subject_type": "location", "subject_id": l["id"], "subject_name": l["name"], "lat": l["lat"], "lon": l["lon"], "country": loc_country[l["id"]],
                    "radius_km": 50.0, "question": f"What threatens {l['name']} and the people assigned there?", "purpose": f"{l['type']} — standing force protection",
                    "priority": 2 if l["type"] in ("hq", "datacenter") else 3, "window_from": None, "window_to": None})
    for t in snap.get("trips", []):
        out.append({"id": f"req_trip_{t['id']}", "subject_type": "trip", "subject_id": t["id"], "subject_name": f"{t['person_name']} — {t['dest_name']}",
                    "lat": t["dest_lat"], "lon": t["dest_lon"], "radius_km": 50.0, "country": loc_country.get(t.get("dest_location_id") or "") or country_from_place(t["dest_name"]),
                    "question": f"What threatens {t['person_name']} in {t['dest_name']} between {t['depart_at'][:10]} and {t['return_at'][:10]}?",
                    "purpose": t["purpose"], "priority": 1 if t["is_vip"] else 2,
                    "window_from": datetime.fromisoformat(t["depart_at"].replace("Z", "")), "window_to": datetime.fromisoformat(t["return_at"].replace("Z", ""))})
    for e in snap.get("events", []):
        out.append({"id": f"req_evt_{e['id']}", "subject_type": "event", "subject_id": e["id"], "subject_name": f"{e['name']} — {e['venue_name']}",
                    "lat": e["venue_lat"], "lon": e["venue_lon"], "radius_km": 30.0, "country": loc_country.get(e.get("venue_location_id") or "") or country_from_place(e["venue_name"]),
                    "question": f"What threatens {e['name']} at {e['venue_name']} ({e['attendee_count']} attending, {e['vip_count']} VIP)?",
                    "purpose": e["event_type"], "priority": 1 if e["vip_count"] else 2,
                    "window_from": datetime.fromisoformat(e["start_at"].replace("Z", "")), "window_to": datetime.fromisoformat(e["end_at"].replace("Z", ""))})
    return out


async def sync_standing(session: AsyncSession, snap: Dict[str, Any]) -> Dict[str, int]:
    """Upsert standing requirements from the wall; expire those whose subject or window is gone."""
    now = now_utc()
    wanted = {r["id"]: r for r in _standing_from_snapshot(snap)}
    existing = {r.id: r for r in (await session.execute(select(RequirementRow).where(RequirementRow.kind == "standing"))).scalars()}
    created = updated = expired = 0
    for rid, w in wanted.items():
        row = existing.get(rid)
        if row is None:
            fields = {k: v for k, v in w.items() if k != "id"}
            session.add(RequirementRow(id=rid, kind="standing", owner="S1/S3", status="active", created_at=now, updated_at=now, **fields)); created += 1
        else:
            changed = any(getattr(row, k) != v for k, v in w.items() if k != "id")
            if changed or row.status == "expired":
                for k, v in w.items():
                    if k != "id": setattr(row, k, v)
                row.status, row.updated_at = "active", now; updated += 1
    for rid, row in existing.items():
        if rid not in wanted and row.status != "expired":
            row.status, row.updated_at = "expired", now; expired += 1
    await session.commit()
    return {"created": created, "updated": updated, "expired": expired}


async def create_directed(session: AsyncSession, *, place: str, lat: float, lon: float, window_from: Optional[datetime], window_to: Optional[datetime],
                          purpose: str, priority: int, owner: str, radius_km: float = 50.0, question: Optional[str] = None) -> RequirementRow:
    now = now_utc()
    from .countries import country_from_place
    row = RequirementRow(id=f"req_dir_{uuid.uuid4().hex[:8]}", kind="directed", subject_type="place", subject_id=None, subject_name=place, lat=lat, lon=lon, country=country_from_place(place),
                         radius_km=radius_km, question=question or f"What is the environment in {place} for {purpose}?", purpose=purpose, priority=priority,
                         window_from=window_from, window_to=window_to, status="active", owner=owner, created_at=now, updated_at=now)
    session.add(row)
    await session.commit()
    return row


async def expire_due(session: AsyncSession) -> int:
    now = now_utc()
    n = 0
    for r in (await session.execute(select(RequirementRow).where(RequirementRow.status == "active", RequirementRow.window_to.isnot(None)))).scalars():
        if r.window_to and r.window_to < now - timedelta(hours=12):
            r.status, r.updated_at = "expired", now; n += 1
    await session.commit()
    return n
