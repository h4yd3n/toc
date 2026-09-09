"""The live S2 picture: actors and sightings.

Sigtoc owns the durable intelligence objects. Cop Talk receives the small live slice it needs for the wall: last known
actor positions, recent sightings, and report pins that still need disposition.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base

ACTOR_KINDS = ("unit", "individual", "group", "organization")
ACTOR_STATUSES = ("active", "dormant", "neutralized")
SIGHTING_CONFIDENCE = ("confirmed", "probable", "possible")


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


def _json_list(raw: str) -> List[Any]:
    try:
        data = json.loads(raw or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


class S2ActorRow(Base):
    __tablename__ = "s2_actors"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, default="group")
    name: Mapped[str] = mapped_column(String)
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")
    echelon: Mapped[str] = mapped_column(String, default="")
    strength: Mapped[str] = mapped_column(String, default="")
    equipment_json: Mapped[str] = mapped_column(Text, default="[]")
    ttps_json: Mapped[str] = mapped_column(Text, default="[]")
    assessed_intent: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="active")
    case_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    owner: Mapped[str] = mapped_column(String, default="S2")
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    place: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class S2SightingRow(Base):
    __tablename__ = "s2_sightings"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    actor_id: Mapped[str] = mapped_column(String, index=True)
    at: Mapped[datetime] = mapped_column(DateTime)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    place: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    nai_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_type: Mapped[str] = mapped_column(String, default="report")
    source_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reliability: Mapped[str] = mapped_column(String, default="A")
    credibility: Mapped[int] = mapped_column(Integer, default=2)
    what: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[str] = mapped_column(String, default="probable")
    created_by: Mapped[str] = mapped_column(String, default="S2")
    created_at: Mapped[datetime] = mapped_column(DateTime)


def actor_dict(row: S2ActorRow, sightings: Optional[Iterable[S2SightingRow]] = None) -> Dict[str, Any]:
    track = sorted(list(sightings or []), key=lambda s: s.at, reverse=True)
    return {
        "id": row.id,
        "kind": row.kind,
        "name": row.name,
        "aliases": _json_list(row.aliases_json),
        "echelon": row.echelon,
        "strength": row.strength,
        "equipment": _json_list(row.equipment_json),
        "ttps": _json_list(row.ttps_json),
        "assessed_intent": row.assessed_intent,
        "status": row.status,
        "case_id": row.case_id,
        "owner": row.owner,
        "lat": row.lat,
        "lon": row.lon,
        "place": row.place,
        "last_seen_at": iso(row.last_seen_at),
        "created_at": iso(row.created_at),
        "updated_at": iso(row.updated_at),
        "sighting_ids": [s.id for s in track],
    }


def sighting_dict(row: S2SightingRow) -> Dict[str, Any]:
    return {
        "id": row.id,
        "actor_id": row.actor_id,
        "at": iso(row.at),
        "lat": row.lat,
        "lon": row.lon,
        "place": row.place,
        "nai_id": row.nai_id,
        "source_type": row.source_type,
        "source_id": row.source_id,
        "reliability": row.reliability,
        "credibility": int(row.credibility),
        "grade": f"{row.reliability}{row.credibility}",
        "what": row.what,
        "confidence": row.confidence,
        "created_by": row.created_by,
        "created_at": iso(row.created_at),
    }


async def nai_for(session: AsyncSession, lat: float, lon: float) -> Optional[str]:
    """Return the closest active requirement that contains the point, if any."""
    from coptoc.service import haversine_km
    from sigtoc.requirements import RequirementRow

    rows = (await session.execute(select(RequirementRow).where(RequirementRow.status == "active"))).scalars().all()
    hits = [(haversine_km(lat, lon, r.lat, r.lon), r) for r in rows if haversine_km(lat, lon, r.lat, r.lon) <= r.radius_km]
    if not hits:
        return None
    return min(hits, key=lambda x: x[0])[1].id


def sighting_from_report(actor_id: str, report: Any, *, created_by: str, confidence: str = "probable", nai_id: Optional[str] = None) -> S2SightingRow:
    if report.lat is None or report.lon is None:
        raise ValueError("a linked sighting needs report lat/lon")
    now = now_utc()
    return S2SightingRow(
        id=f"sgt_{uuid.uuid4().hex[:8]}",
        actor_id=actor_id,
        at=report.at,
        lat=report.lat,
        lon=report.lon,
        place=report.place,
        nai_id=nai_id,
        source_type="report",
        source_id=report.id,
        reliability=report.reliability,
        credibility=report.credibility,
        what=report.text[:280],
        confidence=confidence,
        created_by=created_by,
        created_at=now,
    )


def touch_actor_from_sighting(actor: S2ActorRow, sighting: S2SightingRow) -> None:
    if sighting.confidence not in ("confirmed", "probable"):
        return
    if actor.last_seen_at is None or sighting.at >= actor.last_seen_at:
        actor.lat = sighting.lat
        actor.lon = sighting.lon
        actor.place = sighting.place
        actor.last_seen_at = sighting.at
        actor.updated_at = now_utc()


def seed(dataset: str, now: datetime) -> List[Any]:
    h = lambda x: now - timedelta(hours=x)
    def actor(i: str, kind: str, name: str, lat: float, lon: float, place: str, last: datetime, *, aliases=None, echelon="", strength="", equipment=None, ttps=None, intent="", case_id=None, owner="S2"):
        return S2ActorRow(
            id=i,
            kind=kind,
            name=name,
            aliases_json=json.dumps(aliases or []),
            echelon=echelon,
            strength=strength,
            equipment_json=json.dumps(equipment or []),
            ttps_json=json.dumps(ttps or []),
            assessed_intent=intent,
            status="active",
            case_id=case_id,
            owner=owner,
            lat=lat,
            lon=lon,
            place=place,
            last_seen_at=last,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(hours=2),
        )
    def sighting(i: str, act: str, at: datetime, lat: float, lon: float, place: str, what: str, *, nai=None, src="seed", rel="B", cred=3, confidence="probable"):
        return S2SightingRow(
            id=i,
            actor_id=act,
            at=at,
            lat=lat,
            lon=lon,
            place=place,
            nai_id=nai,
            source_type="seed",
            source_id=src,
            reliability=rel,
            credibility=cred,
            what=what,
            confidence=confidence,
            created_by="S2 seed",
            created_at=at + timedelta(minutes=8),
        )
    if dataset == "cab":
        return [
            actor("act_opfor_recon", "unit", "OPFOR recon element", 31.153, -93.344, "tree line west of FARP Eagle", h(2), aliases=["red team 7"], echelon="team",
                  strength="3-5 personnel", equipment=["pickup truck", "commercial UAS"], ttps=["dusk observation", "short-duration halts", "route surveillance"],
                  intent="Assessing FARP traffic and convoy timing.", owner="S2 Intelligence"),
            sighting("sgt_opfor_1", "act_opfor_recon", h(22), 31.142, -93.333, "MSR TIGER south of FARP Eagle", "Two personnel watching tanker traffic from a pull-off.", nai="req_loc_loc_farp", cred=3),
            sighting("sgt_opfor_2", "act_opfor_recon", h(14), 31.149, -93.347, "FARP Eagle west treeline", "Pickup truck halted with optics pointed at Class III/V point.", nai="req_loc_loc_farp", cred=2, confidence="confirmed"),
            sighting("sgt_opfor_3", "act_opfor_recon", h(2), 31.153, -93.344, "tree line west of FARP Eagle", "Small UAS launch reported after last light.", nai="req_loc_loc_farp", rel="A", cred=2, confidence="probable"),
            actor("act_gate_observer", "individual", "Gate route observer", 31.091, -93.239, "ACP 4 approach", h(5), aliases=["grey sedan"], strength="one person",
                  equipment=["grey sedan", "handheld radio"], ttps=["loiter near convoy choke points"], intent="Possibly coordinating demonstration-route observation.", owner="S2 Intelligence"),
            sighting("sgt_gate_1", "act_gate_observer", h(5), 31.091, -93.239, "ACP 4 approach", "Sedan loitered near the convoy turn and departed when approached.", nai="req_evt_evt_ftx", rel="A", cred=3, confidence="possible"),
        ]
    return [
        actor("act_sf_surveillance", "group", "SF loading dock surveillance pair", 37.7897, -122.3989, "north gate, SF HQ", h(18), aliases=["Vane pair"], strength="two people",
              equipment=["grey sedan", "phone cameras"], ttps=["photographs access points", "returns at same evening hour"], intent="Testing access and observing loading dock routines.",
              case_id="case_seed_gate", owner="S2 Analyst"),
        sighting("sgt_sf_1", "act_sf_surveillance", h(42), 37.7897, -122.3989, "north gate, SF HQ", "Pair observed in grey sedan near the north gate.", src="rpt_seed_1", rel="A", cred=2, confidence="confirmed"),
        sighting("sgt_sf_2", "act_sf_surveillance", h(18), 37.7897, -122.3989, "north gate, SF HQ", "Same pair photographed the loading dock and left when approached.", src="rpt_seed_2", rel="A", cred=2, confidence="confirmed"),
        actor("act_dc_threat_cluster", "organization", "DC-East posting cluster", 39.0442, -77.4870, "DC-East perimeter", h(3), aliases=["operator dox cluster"], strength="small online cluster",
              equipment=["social accounts"], ttps=["names operators", "amplifies access-control photos"], intent="Harassment and possible facilitation against DC-East operators.", owner="S2 Analyst"),
        sighting("sgt_dc_1", "act_dc_threat_cluster", h(3), 39.0442, -77.4870, "DC-East loading side", "New post named an operator and the soft-side loading dock.", nai="req_loc_loc_dc2", src="thr_004", rel="C", cred=3, confidence="probable"),
    ]
