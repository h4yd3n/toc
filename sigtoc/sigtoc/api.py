"""Sigtoc's own API (Decision 3a). Mounted into the COP app under /v1/s2 and runnable standalone: `make run-s2`."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.database import async_session_factory, create_engine, init_db
from shared.ledger import AsyncDatabaseEventLedger
from coptoc import graphics as toc_graphics
from coptoc.graphics import GraphicRow
from . import requirements as R
from .requirements import CADENCES, CATALOG, INDICATORS, RequirementRow, SourceStateRow
from . import cases as C
from .cases import CaseEventRow, CaseRow, EntityRow, RelationshipRow, ReportRow
from . import picture as P
from .picture import S2ActorRow, S2SightingRow
from . import area as A
from .area import AreaAssessmentRow
from . import intsum as I
from .intsum import IntsumRow
from . import dissemination as D
from .dissemination import DistributionRow
from . import warning as W
from .warning import WarningRow

router = APIRouter(prefix="/v1/s2", tags=["sigtoc"])

_engine = None
_sessions: Optional[async_sessionmaker] = None

def sessions() -> async_sessionmaker:
    global _engine, _sessions
    if _sessions is None:
        _engine = create_engine(); _sessions = async_session_factory(_engine)
    return _sessions

async def get_session() -> AsyncSession:
    async with sessions()() as s:
        yield s

def ledger() -> AsyncDatabaseEventLedger:
    return AsyncDatabaseEventLedger(sessions())

def naive(dt: Optional[datetime]) -> Optional[datetime]:
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if (dt and dt.tzinfo) else dt

REQUIREMENT_CREATORS = {"battle_captain", "security", "analyst", "ea"}  # Decision H


class DirectedCreate(BaseModel):
    place: str
    lat: float
    lon: float
    window_from: Optional[datetime] = None
    window_to: Optional[datetime] = None
    purpose: str = "candidate venue"
    priority: int = Field(2, ge=1, le=3)
    radius_km: float = 50.0
    question: Optional[str] = None

class RequirementUpdate(BaseModel):
    status: Optional[Literal["active", "answered", "expired"]] = None
    priority: Optional[int] = Field(None, ge=1, le=3)
    indicators: Optional[List[str]] = None  # the analyst adds or drops

class SourceUpdate(BaseModel):
    enabled: Optional[bool] = None
    cadence: Optional[str] = None
    reliability: Optional[Literal["A", "B", "C", "D", "E", "F"]] = None


@router.get("/indicators")
async def indicators():
    return [{"key": k, **v, "sources": [c["id"] for c in CATALOG if k in c["indicators"]]} for k, v in INDICATORS.items()]


@router.get("/sources")
async def sources(session: AsyncSession = Depends(get_session)):
    return await R.catalog(session)


@router.patch("/sources/{source_id}")
async def update_source(source_id: str, body: SourceUpdate, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    """Decision K: cadence, enabled, and reliability are the operator's to set."""
    if source_id not in {c["id"] for c in CATALOG}:
        raise HTTPException(404, "unknown source")
    st = (await R.source_states(session))[source_id]
    changes = {}
    if body.enabled is not None: st.enabled = body.enabled; changes["enabled"] = body.enabled
    if body.cadence is not None:
        if body.cadence not in CADENCES: raise HTTPException(422, f"cadence must be one of {CADENCES}")
        st.cadence = body.cadence; changes["cadence"] = body.cadence
    if body.reliability is not None: st.reliability = body.reliability; changes["reliability"] = body.reliability
    await session.commit()
    await ledger().append_event(content_id=f"source:{source_id}", event_type="s2.source.updated", actor_type="human", actor_id=x_toc_actor or "operator",
                                reason=", ".join(f"{k}={v}" for k, v in changes.items()) or "no-op", metadata=changes)
    return next(c for c in await R.catalog(session) if c["id"] == source_id)


@router.get("/requirements")
async def list_requirements(status: Optional[str] = None, kind: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    await R.expire_due(session)
    cat = await R.catalog(session)
    rows = (await session.execute(select(RequirementRow).order_by(RequirementRow.priority, RequirementRow.created_at.desc()))).scalars().all()
    out = [R.to_dict(r, R.plan_for(r, cat)) for r in rows if (status is None or r.status == status) and (kind is None or r.kind == kind)]
    return out


@router.get("/requirements/{req_id}")
async def get_requirement(req_id: str, session: AsyncSession = Depends(get_session)):
    row = await session.get(RequirementRow, req_id)
    if not row: raise HTTPException(404, "requirement not found")
    return R.to_dict(row, R.plan_for(row, await R.catalog(session)))


@router.get("/requirements/{req_id}/plan")
async def plan(req_id: str, session: AsyncSession = Depends(get_session)):
    """The synchronization matrix: indicator → live sources → covered or gap, with recommended sources for the gaps."""
    row = await session.get(RequirementRow, req_id)
    if not row: raise HTTPException(404, "requirement not found")
    return R.plan_for(row, await R.catalog(session))


@router.post("/requirements", status_code=201)
async def create_requirement(body: DirectedCreate, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    """A directed requirement — the Lisbon question. Four fields."""
    if (x_toc_role or "").lower() not in REQUIREMENT_CREATORS:
        raise HTTPException(403, f"Creating a requirement needs one of {sorted(REQUIREMENT_CREATORS)}; you are {x_toc_role or 'unspecified'}")
    if body.window_from and body.window_to and naive(body.window_to) <= naive(body.window_from):
        raise HTTPException(422, "window_to must be after window_from")
    row = await R.create_directed(session, place=body.place, lat=body.lat, lon=body.lon, window_from=naive(body.window_from), window_to=naive(body.window_to),
                                  purpose=body.purpose, priority=body.priority, owner=x_toc_actor or "unspecified", radius_km=body.radius_km, question=body.question)
    p = R.plan_for(row, await R.catalog(session))
    await ledger().append_event(content_id=row.id, event_type="s2.requirement.created", actor_type="human", actor_id=x_toc_actor or "unspecified", new_state="active",
                                reason=f"{row.question} — coverage {p['covered']}/{p['total']}", metadata={"kind": "directed", "gaps": p["gaps"]})
    return R.to_dict(row, p)


@router.patch("/requirements/{req_id}")
async def update_requirement(req_id: str, body: RequirementUpdate, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    row = await session.get(RequirementRow, req_id)
    if not row: raise HTTPException(404, "requirement not found")
    old = row.status; changes = {}
    if body.status: row.status = body.status; changes["status"] = body.status
    if body.priority is not None: row.priority = body.priority; changes["priority"] = body.priority
    if body.indicators is not None:
        bad = [k for k in body.indicators if k not in INDICATORS]
        if bad: raise HTTPException(422, f"unknown indicators: {bad}")
        row.indicators_json = json.dumps(body.indicators); changes["indicators"] = body.indicators
    row.updated_at = R.now_utc()
    await session.commit()
    await ledger().append_event(content_id=row.id, event_type="s2.requirement.updated", actor_type="human", actor_id=x_toc_actor or "unspecified",
                                old_state=old, new_state=row.status, reason=", ".join(f"{k}={v}" for k, v in changes.items()) or "no-op", metadata=changes)
    return R.to_dict(row, R.plan_for(row, await R.catalog(session)))


@router.post("/requirements/sync")
async def sync(snapshot: Dict[str, Any], session: AsyncSession = Depends(get_session)):
    """Standing requirements from the wall. The COP calls this (as a library) whenever S1/S3 changes; exposed here for standalone use."""
    result = await R.sync_standing(session, snapshot)
    if any(result.values()):
        await ledger().append_event(content_id="s2", event_type="s2.requirements.synced", actor_type="system", actor_id="wall",
                                    reason=f"standing requirements: +{result['created']} ~{result['updated']} −{result['expired']}", metadata=result)
    return result


@router.get("/coverage")
async def coverage(session: AsyncSession = Depends(get_session)):
    """The whole plan at a glance: every active requirement's coverage, and the indicators that are gaps everywhere."""
    cat = await R.catalog(session)
    rows = (await session.execute(select(RequirementRow).where(RequirementRow.status == "active"))).scalars().all()
    plans = [R.plan_for(r, cat) for r in rows]
    gap_counts: Dict[str, int] = {}
    for p in plans:
        for g in p["gaps"]: gap_counts[g] = gap_counts.get(g, 0) + 1
    rec = {}
    for k in gap_counts:
        rec[k] = [{"id": c["id"], "name": c["name"], "access": c["access"], "built": c["built"]} for c in cat if k in c["indicators"]]
    return {"requirements": len(rows), "fully_covered": sum(1 for p in plans if not p["gaps"]),
            "avg_coverage_pct": round(sum(p["coverage_pct"] for p in plans) / len(plans)) if plans else 100,
            "gaps": [{"indicator": k, "label": INDICATORS[k]["label"], "requirements_affected": n, "recommended_sources": rec[k]} for k, n in sorted(gap_counts.items(), key=lambda x: -x[1])]}


@router.get("/query")
async def query(lat: float = Query(...), lon: float = Query(...), radius_km: float = 100.0, session: AsyncSession = Depends(get_session)):
    """The standalone use: what do we hold near a point? Threats from the shared table plus requirements whose subject is nearby."""
    from coptoc.db_models import ThreatRow  # shared DB; sigtoc reads the same threat table the wall does
    from .collectors.gdacs import haversine_km
    threats = [t for t in (await session.execute(select(ThreatRow))).scalars() if haversine_km(lat, lon, t.lat, t.lon) <= radius_km + t.radius_km]
    reqs = [r for r in (await session.execute(select(RequirementRow).where(RequirementRow.status == "active"))).scalars() if haversine_km(lat, lon, r.lat, r.lon) <= radius_km]
    cat = await R.catalog(session)
    return {"center": {"lat": lat, "lon": lon}, "radius_km": radius_km,
            "threats": [{"id": t.id, "title": t.title, "severity": t.severity, "source": t.source, "confidence": t.confidence, "synthetic": t.synthetic,
                         "observed_at": t.observed_at.isoformat() + "Z", "distance_km": round(haversine_km(lat, lon, t.lat, t.lon), 1)} for t in threats],
            "requirements": [R.to_dict(r, R.plan_for(r, cat)) for r in reqs]}


# ---------------------------------------------------------------- §5.10 reports, §5.11 cases

CASE_OPENERS = {"battle_captain", "analyst"}  # Decision Q: "Battle Captain or S2 lead"
REPORT_FILERS = {"battle_captain", "security", "analyst", "ea", "ep"}


class ReportCreate(BaseModel):
    text: str
    kind: Literal["spot", "sitrep", "note"] = "spot"
    reported_by: str
    reporter_role: str = ""
    at: Optional[datetime] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    place: Optional[str] = None
    case_id: Optional[str] = None
    credibility: int = Field(2, ge=1, le=6)

class ActorCreate(BaseModel):
    kind: Literal["unit", "individual", "group", "organization"] = "group"
    name: str
    aliases: List[str] = []
    echelon: str = ""
    strength: str = ""
    equipment: List[str] = []
    ttps: List[str] = []
    assessed_intent: str = ""
    status: Literal["active", "dormant", "neutralized"] = "active"
    case_id: Optional[str] = None
    owner: str = "S2"
    lat: Optional[float] = None
    lon: Optional[float] = None
    place: Optional[str] = None
    last_seen_at: Optional[datetime] = None

class ActorUpdate(BaseModel):
    kind: Optional[Literal["unit", "individual", "group", "organization"]] = None
    name: Optional[str] = None
    aliases: Optional[List[str]] = None
    echelon: Optional[str] = None
    strength: Optional[str] = None
    equipment: Optional[List[str]] = None
    ttps: Optional[List[str]] = None
    assessed_intent: Optional[str] = None
    status: Optional[Literal["active", "dormant", "neutralized"]] = None
    case_id: Optional[str] = None
    owner: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    place: Optional[str] = None
    last_seen_at: Optional[datetime] = None

class SightingCreate(BaseModel):
    at: Optional[datetime] = None
    lat: float
    lon: float
    place: Optional[str] = None
    nai_id: Optional[str] = None
    source_type: Literal["report", "threat", "feed", "liaison", "analyst", "seed"] = "analyst"
    source_id: Optional[str] = None
    reliability: Literal["A", "B", "C", "D", "E", "F"] = "B"
    credibility: int = Field(3, ge=1, le=6)
    what: str
    confidence: Literal["confirmed", "probable", "possible"] = "probable"

class ReportDisposition(BaseModel):
    action: Literal["corroborate", "link", "promote", "dismiss"]
    target_type: Optional[Literal["actor", "threat", "case", "nai", "graphic"]] = None
    target_id: Optional[str] = None
    confidence: Literal["confirmed", "probable", "possible", "template"] = "probable"
    graphic_type: Optional[str] = None
    kind: Optional[Literal["point", "line", "polygon"]] = None
    name: Optional[str] = None
    geometry: Optional[Any] = None
    note: str = ""
    basis: str = ""

class CaseCreate(BaseModel):
    title: str
    kind: Literal["general", "person", "site", "actor"] = "general"
    subject_type: Optional[str] = None
    subject_id: Optional[str] = None
    summary: str = ""

class Decision(BaseModel):
    kind: Literal["entity", "relationship", "event"]
    id: str
    decision: Literal["confirm", "reject"]
    note: Optional[str] = None

class Merge(BaseModel):
    into: str


PICTURE_EDITORS = {"battle_captain", "analyst"}


def _picture_role(role: Optional[str], what: str) -> None:
    if (role or "").lower() not in PICTURE_EDITORS:
        raise HTTPException(403, f"{what} needs the analyst's or the Battle Captain's role")


async def _read_logged(case: CaseRow, role: Optional[str], actor: Optional[str]) -> None:
    allowed = set(case.access_roles.split(","))
    if (role or "").lower() not in allowed:
        raise HTTPException(403, f"Case {case.id} is readable by {sorted(allowed)}; you are {role or 'unspecified'}")
    await ledger().append_event(content_id=case.id, event_type="s2.case.read", actor_type="human", actor_id=actor or "unspecified", reason=f"{case.title} read")


@router.post("/reports", status_code=201)
async def file_report(body: ReportCreate, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    """An organic report — our own people saying what they see. Filed into a case if one is named; extraction runs and
    everything it finds is suggested to the analyst."""
    if (x_toc_role or "").lower() not in REPORT_FILERS:
        raise HTTPException(403, "Filing a report needs a security, EP, analyst, EA, or Battle Captain role")
    now = R.now_utc()
    r = ReportRow(id=f"rpt_{uuid.uuid4().hex[:8]}", kind=body.kind, reported_by=body.reported_by, reporter_role=body.reporter_role, at=naive(body.at) or now,
                  lat=body.lat, lon=body.lon, place=body.place, text=body.text.strip(), case_id=body.case_id, credibility=body.credibility, filed_at=now)
    session.add(r); await session.commit()
    extracted = None
    if body.case_id:
        case = await session.get(CaseRow, body.case_id)
        if not case: raise HTTPException(404, "case not found")
        known = [e.name for e in (await session.execute(select(EntityRow).where(EntityRow.case_id == case.id, EntityRow.status == "confirmed"))).scalars()]
        extracted = await C.file_report_into_case(session, r, case, known)
    await ledger().append_event(content_id=body.case_id or r.id, event_type="s2.report.filed", actor_type="human", actor_id=x_toc_actor or body.reported_by,
                                reason=f"{body.kind.upper()} from {body.reported_by}: {r.text[:100]}" + (f" — suggested {extracted['entities']} entities, {extracted['relationships']} links, {extracted['events']} events" if extracted else ""),
                                metadata={"report_id": r.id, "grade": f"{r.reliability}{r.credibility}", **(extracted or {})})
    return {**C.report_dict(r), "extracted": extracted}


@router.get("/reports")
async def list_reports(case_id: Optional[str] = None, limit: int = 50, session: AsyncSession = Depends(get_session)):
    q = select(ReportRow).order_by(ReportRow.at.desc()).limit(limit)
    if case_id: q = q.where(ReportRow.case_id == case_id)
    return [C.report_dict(r) for r in (await session.execute(q)).scalars()]


@router.get("/actors")
async def list_actors(status: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(S2ActorRow).order_by(S2ActorRow.updated_at.desc()))).scalars().all()
    sightings = (await session.execute(select(S2SightingRow).order_by(S2SightingRow.at.desc()))).scalars().all()
    by_actor: Dict[str, List[S2SightingRow]] = {}
    for s in sightings:
        by_actor.setdefault(s.actor_id, []).append(s)
    return [P.actor_dict(a, by_actor.get(a.id, [])) for a in rows if status is None or a.status == status]


@router.post("/actors", status_code=201)
async def create_actor(body: ActorCreate, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    _picture_role(x_toc_role, "Creating an S2 actor")
    if not body.name.strip():
        raise HTTPException(422, "an actor needs a name")
    if (body.lat is None) != (body.lon is None):
        raise HTTPException(422, "actor position needs both lat and lon")
    now = R.now_utc()
    row = S2ActorRow(id=f"act_{uuid.uuid4().hex[:8]}", kind=body.kind, name=body.name.strip(), aliases_json=json.dumps(body.aliases),
                     echelon=body.echelon, strength=body.strength, equipment_json=json.dumps(body.equipment), ttps_json=json.dumps(body.ttps),
                     assessed_intent=body.assessed_intent, status=body.status, case_id=body.case_id, owner=body.owner, lat=body.lat, lon=body.lon,
                     place=body.place, last_seen_at=naive(body.last_seen_at), created_at=now, updated_at=now)
    session.add(row); await session.commit()
    await ledger().append_event(content_id=row.id, event_type="s2.actor.created", actor_type="human", actor_id=x_toc_actor or x_toc_role or "analyst",
                                new_state=row.status, reason=f"{row.kind} actor: {row.name}", metadata={"kind": row.kind, "case_id": row.case_id})
    return P.actor_dict(row)


@router.get("/actors/{actor_id}")
async def get_actor(actor_id: str, session: AsyncSession = Depends(get_session)):
    row = await session.get(S2ActorRow, actor_id)
    if not row: raise HTTPException(404, "actor not found")
    sightings = (await session.execute(select(S2SightingRow).where(S2SightingRow.actor_id == actor_id).order_by(S2SightingRow.at.desc()))).scalars().all()
    return {**P.actor_dict(row, sightings), "sightings": [P.sighting_dict(s) for s in sightings]}


@router.patch("/actors/{actor_id}")
async def update_actor(actor_id: str, body: ActorUpdate, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    _picture_role(x_toc_role, "Changing an S2 actor")
    row = await session.get(S2ActorRow, actor_id)
    if not row: raise HTTPException(404, "actor not found")
    changes = body.model_dump(exclude_unset=True)
    if ("lat" in changes) != ("lon" in changes) and (changes.get("lat", row.lat) is None or changes.get("lon", row.lon) is None):
        raise HTTPException(422, "actor position needs both lat and lon")
    for k, v in changes.items():
        if k == "aliases":
            row.aliases_json = json.dumps(v)
        elif k == "equipment":
            row.equipment_json = json.dumps(v)
        elif k == "ttps":
            row.ttps_json = json.dumps(v)
        elif k == "last_seen_at":
            row.last_seen_at = naive(v)
        elif k == "name":
            row.name = v.strip()
        else:
            setattr(row, k, v)
    row.updated_at = R.now_utc()
    await session.commit()
    await ledger().append_event(content_id=row.id, event_type="s2.actor.updated", actor_type="human", actor_id=x_toc_actor or x_toc_role or "analyst",
                                new_state=row.status, reason=f"{row.name}: actor updated", metadata={"changed": sorted(changes)})
    return P.actor_dict(row)


@router.get("/sightings")
async def list_sightings(actor_id: Optional[str] = None, limit: int = 100, session: AsyncSession = Depends(get_session)):
    q = select(S2SightingRow).order_by(S2SightingRow.at.desc()).limit(limit)
    if actor_id:
        q = q.where(S2SightingRow.actor_id == actor_id)
    return [P.sighting_dict(s) for s in (await session.execute(q)).scalars()]


@router.post("/actors/{actor_id}/sightings", status_code=201)
async def create_sighting(actor_id: str, body: SightingCreate, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    _picture_role(x_toc_role, "Creating an S2 sighting")
    actor = await session.get(S2ActorRow, actor_id)
    if not actor: raise HTTPException(404, "actor not found")
    at = naive(body.at) or R.now_utc()
    nai_id = body.nai_id or await P.nai_for(session, body.lat, body.lon)
    row = S2SightingRow(id=f"sgt_{uuid.uuid4().hex[:8]}", actor_id=actor_id, at=at, lat=body.lat, lon=body.lon, place=body.place, nai_id=nai_id,
                        source_type=body.source_type, source_id=body.source_id, reliability=body.reliability, credibility=body.credibility,
                        what=body.what.strip(), confidence=body.confidence, created_by=x_toc_actor or x_toc_role or "analyst", created_at=R.now_utc())
    session.add(row)
    P.touch_actor_from_sighting(actor, row)
    await session.commit()
    await ledger().append_event(content_id=row.id, event_type="s2.sighting.created", actor_type="human", actor_id=x_toc_actor or x_toc_role or "analyst",
                                new_state=row.confidence, reason=f"{actor.name}: {row.what[:120]}", metadata={"actor_id": actor_id, "grade": f"{row.reliability}{row.credibility}", "nai_id": nai_id})
    return P.sighting_dict(row)


@router.post("/reports/{report_id}/dispose")
async def dispose_report(report_id: str, body: ReportDisposition, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    _picture_role(x_toc_role, "Disposing an S2 report")
    report = await session.get(ReportRow, report_id)
    if not report: raise HTTPException(404, "report not found")
    now = R.now_utc()
    old = report.status
    actor_id = x_toc_actor or x_toc_role or "analyst"
    created: Optional[Dict[str, Any]] = None

    if body.action == "corroborate":
        report.credibility = max(1, report.credibility - 1)
        report.status = "corroborated"
        report.disposition = "corroborate"
    elif body.action == "dismiss":
        if not body.note.strip():
            raise HTTPException(422, "dismissal needs a reason")
        report.status = "dismissed"
        report.disposition = "dismiss"
    elif body.action == "link":
        if not body.target_type or not body.target_id:
            raise HTTPException(422, "link needs target_type and target_id")
        if body.target_type == "actor":
            actor = await session.get(S2ActorRow, body.target_id)
            if not actor: raise HTTPException(404, "actor not found")
            if body.confidence == "template":
                raise HTTPException(422, "a sighting cannot have template confidence")
            try:
                nai_id = await P.nai_for(session, report.lat, report.lon) if report.lat is not None and report.lon is not None else None
                sighting = P.sighting_from_report(body.target_id, report, created_by=actor_id, confidence=body.confidence, nai_id=nai_id)
            except ValueError as e:
                raise HTTPException(422, str(e))
            session.add(sighting)
            P.touch_actor_from_sighting(actor, sighting)
            report.status = "linked"
            report.disposition = "link"
            report.disposition_target_type = "sighting"
            report.disposition_target_id = sighting.id
            created = {"object_type": "sighting", **P.sighting_dict(sighting)}
            await ledger().append_event(content_id=sighting.id, event_type="s2.sighting.created", actor_type="human", actor_id=actor_id,
                                        new_state=sighting.confidence, reason=f"{actor.name}: sighting from report {report.id}", metadata={"actor_id": actor.id, "report_id": report.id})
        elif body.target_type == "case":
            case = await session.get(CaseRow, body.target_id)
            if not case: raise HTTPException(404, "case not found")
            report.case_id = case.id
            known = [e.name for e in (await session.execute(select(EntityRow).where(EntityRow.case_id == case.id, EntityRow.status == "confirmed"))).scalars()]
            extracted = await C.file_report_into_case(session, report, case, known)
            report.status = "linked"
            report.disposition = "link"
            report.disposition_target_type = "case"
            report.disposition_target_id = case.id
            created = {"object_type": "case_extraction", **extracted}
        elif body.target_type in ("threat", "nai", "graphic"):
            report.status = "linked"
            report.disposition = "link"
            report.disposition_target_type = body.target_type
            report.disposition_target_id = body.target_id
        else:
            raise HTTPException(422, "unknown link target")
    elif body.action == "promote":
        if not body.graphic_type or not body.name:
            raise HTTPException(422, "promote needs graphic_type and name")
        c = toc_graphics.CATALOG.get(body.graphic_type)
        if not c or body.graphic_type not in toc_graphics.THREAT_GRAPHIC_TYPES:
            raise HTTPException(422, "promote creates an S2 threat graphic type")
        kind = body.kind or ("point" if report.lat is not None and report.lon is not None else None)
        geometry = body.geometry
        if geometry is None and kind == "point" and report.lat is not None and report.lon is not None:
            geometry = [report.lon, report.lat]
        if not kind or geometry is None:
            raise HTTPException(422, "promote needs geometry, or a report point")
        why = toc_graphics.validate(body.graphic_type, kind, geometry)
        if why: raise HTTPException(422, why)
        graphic = GraphicRow(id=f"gfx_{uuid.uuid4().hex[:8]}", type=body.graphic_type, kind=kind, section=c["section"], name=body.name.strip(), geometry_json=json.dumps(geometry),
                             window_from=None, window_to=None, status="active", note=body.note or report.text[:180], confidence=body.confidence, basis=body.basis or f"report {report.id}",
                             subject_type="report", subject_id=report.id, created_by=actor_id, created_at=now, updated_at=now)
        session.add(graphic)
        report.status = "promoted"
        report.disposition = "promote"
        report.disposition_target_type = "graphic"
        report.disposition_target_id = graphic.id
        from coptoc.sections import profile as toc_profile
        created = {"object_type": "graphic", **toc_graphics.out(graphic, now, toc_profile())}
        await ledger().append_event(content_id=graphic.id, event_type="s2.graphic.promoted", actor_type="human", actor_id=actor_id,
                                    new_state=graphic.confidence, reason=f"{graphic.name} from report {report.id}", metadata={"type": graphic.type, "report_id": report.id})

    report.disposed_by = actor_id
    report.disposed_at = now
    report.disposition_note = body.note or report.disposition_note
    if body.action != "link" or body.target_type != "actor":
        if body.action != "promote":
            report.disposition_target_type = report.disposition_target_type or body.target_type
            report.disposition_target_id = report.disposition_target_id or body.target_id
    await session.commit()
    await ledger().append_event(content_id=report.id, event_type="s2.report.disposed", actor_type="human", actor_id=actor_id,
                                old_state=old, new_state=report.status, reason=f"{report.kind.upper()} {report.id}: {body.action}" + (f" - {body.note}" if body.note else ""),
                                metadata={"action": body.action, "target_type": report.disposition_target_type, "target_id": report.disposition_target_id, **({"created": created} if created else {})})
    return {**C.report_dict(report), **({"created": created} if created else {})}


@router.get("/cases")
async def list_cases(status: Optional[str] = None, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None)):
    rows = (await session.execute(select(CaseRow).order_by(CaseRow.opened_at.desc()))).scalars().all()
    out = []
    for c in rows:
        if status and c.status != status: continue
        if (x_toc_role or "").lower() not in set(c.access_roles.split(",")): continue  # you don't see cases you can't read
        ents = (await session.execute(select(EntityRow).where(EntityRow.case_id == c.id, EntityRow.merged_into.is_(None)))).scalars().all()
        rels = (await session.execute(select(RelationshipRow).where(RelationshipRow.case_id == c.id))).scalars().all()
        evs = (await session.execute(select(CaseEventRow).where(CaseEventRow.case_id == c.id))).scalars().all()
        pending = sum(1 for x in list(ents) + list(rels) + list(evs) if x.status == "suggested")
        out.append(C.case_dict(c, {"entities": len(ents), "relationships": len(rels), "events": len(evs), "pending_review": pending}))
    return out


@router.post("/cases", status_code=201)
async def open_case(body: CaseCreate, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    role = (x_toc_role or "").lower()
    if role not in CASE_OPENERS:
        raise HTTPException(403, f"Opening a case needs {sorted(CASE_OPENERS)}; you are {role or 'unspecified'}")
    now = R.now_utc()
    c = CaseRow(id=f"case_{uuid.uuid4().hex[:8]}", title=body.title, kind=body.kind, subject_type=body.subject_type, subject_id=body.subject_id, summary=body.summary,
                opened_by=x_toc_actor or role, opened_at=now)
    session.add(c); await session.commit()
    await ledger().append_event(content_id=c.id, event_type="s2.case.opened", actor_type="human", actor_id=x_toc_actor or role, new_state="open",
                                reason=f"{body.kind} case: {body.title}" + (f" on {body.subject_type} {body.subject_id}" if body.subject_id else ""),
                                metadata={"kind": body.kind, "on_person": body.kind == "person" or body.subject_type == "person"})
    return C.case_dict(c)


@router.get("/cases/{case_id}")
async def get_case(case_id: str, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    """Every read is on the ledger (Decision Q)."""
    c = await session.get(CaseRow, case_id)
    if not c: raise HTTPException(404, "case not found")
    await _read_logged(c, x_toc_role, x_toc_actor)
    g = await C.case_graph(session, case_id)
    reports = [C.report_dict(r) for r in (await session.execute(select(ReportRow).where(ReportRow.case_id == case_id).order_by(ReportRow.at))).scalars()]
    pending = [x for x in g["entities"] + g["relationships"] + g["events"] if x["status"] == "suggested"]
    return {**C.case_dict(c, {"pending_review": len(pending)}), "graph": g, "reports": reports,
            "analysis": {"links": C.link_summary(g), "pattern": C.time_wheel(g["events"])["pattern"]}}


@router.get("/cases/{case_id}/queue")
async def review_queue(case_id: str, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    """The officer's v1 workbench: every suggested fact with its citation — confirm, reject, or merge."""
    c = await session.get(CaseRow, case_id)
    if not c: raise HTTPException(404, "case not found")
    await _read_logged(c, x_toc_role, x_toc_actor)
    g = await C.case_graph(session, case_id, include=("suggested",))
    names = {e["id"]: e["name"] for e in (await C.case_graph(session, case_id))["entities"]}
    return {"case_id": case_id,
            "entities": g["entities"],
            "relationships": [{**r, "from_name": names.get(r["from"]), "to_name": names.get(r["to"])} for r in g["relationships"]],
            "events": g["events"], "total": len(g["entities"]) + len(g["relationships"]) + len(g["events"])}


@router.post("/cases/{case_id}/decide")
async def decide(case_id: str, body: Decision, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    c = await session.get(CaseRow, case_id)
    if not c: raise HTTPException(404, "case not found")
    if (x_toc_role or "").lower() not in CASE_OPENERS:
        raise HTTPException(403, "Confirming or rejecting evidence is the analyst's or the Battle Captain's")
    model = {"entity": EntityRow, "relationship": RelationshipRow, "event": CaseEventRow}[body.kind]
    row = await session.get(model, body.id)
    if not row or row.case_id != case_id: raise HTTPException(404, f"{body.kind} not found in this case")
    old = row.status
    row.status = "confirmed" if body.decision == "confirm" else "rejected"
    row.decided_by, row.decided_at = x_toc_actor or x_toc_role, R.now_utc()
    await session.commit()
    label = getattr(row, "name", None) or getattr(row, "summary", None) or f"{row.from_id}→{row.to_id}"
    await ledger().append_event(content_id=case_id, event_type=f"s2.case.{body.decision}ed", actor_type="human", actor_id=x_toc_actor or x_toc_role, old_state=old, new_state=row.status,
                                reason=f"{body.kind} {body.decision}ed: {str(label)[:100]}" + (f" — {body.note}" if body.note else ""), metadata={"kind": body.kind, "id": body.id})
    return {"kind": body.kind, "id": body.id, "status": row.status}


@router.post("/cases/{case_id}/entities/{entity_id}/merge")
async def merge_entity(case_id: str, entity_id: str, body: Merge, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    """Alias resolution, decided by a human: this entity is the same as that one. Evidence and edges move; the alias is kept."""
    if (x_toc_role or "").lower() not in CASE_OPENERS: raise HTTPException(403, "Merging is the analyst's call")
    a, b = await session.get(EntityRow, entity_id), await session.get(EntityRow, body.into)
    if not a or not b or a.case_id != case_id or b.case_id != case_id or a.id == b.id: raise HTTPException(404, "entities not found in this case")
    aliases = set(json.loads(b.aliases_json or "[]")) | {a.name} | set(json.loads(a.aliases_json or "[]"))
    b.aliases_json = json.dumps(sorted(aliases))
    b.evidence_json = json.dumps(json.loads(b.evidence_json or "[]") + json.loads(a.evidence_json or "[]"))
    for r in (await session.execute(select(RelationshipRow).where(RelationshipRow.case_id == case_id))).scalars():
        if r.from_id == a.id: r.from_id = b.id
        if r.to_id == a.id: r.to_id = b.id
    for v in (await session.execute(select(CaseEventRow).where(CaseEventRow.case_id == case_id))).scalars():
        parts = json.loads(v.participants_json or "[]")
        if a.id in parts: v.participants_json = json.dumps([b.id if p == a.id else p for p in parts])
    a.merged_into, a.status = b.id, "rejected"
    await session.commit()
    await ledger().append_event(content_id=case_id, event_type="s2.case.merged", actor_type="human", actor_id=x_toc_actor or x_toc_role,
                                reason=f"'{a.name}' merged into '{b.name}' (alias)", metadata={"from": a.id, "into": b.id})
    return C.entity_dict(b)


@router.get("/cases/{case_id}/views")
async def case_views(case_id: str, entity_id: Optional[str] = None, confirmed_only: bool = False, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    """The data behind the three views (§5.11): link chart (nodes/edges with grade and status), timeline, time wheel."""
    c = await session.get(CaseRow, case_id)
    if not c: raise HTTPException(404, "case not found")
    await _read_logged(c, x_toc_role, x_toc_actor)
    g = await C.case_graph(session, case_id, include=("confirmed",) if confirmed_only else ("suggested", "confirmed"))
    return {"case_id": case_id,
            "link_chart": {"nodes": [{"id": e["id"], "label": e["name"], "type": e["type"], "status": e["status"]} for e in g["entities"]],
                           "edges": [{"id": r["id"], "from": r["from"], "to": r["to"], "type": r["type"], "status": r["status"], "grade": r["grade"], "dashed": r["status"] != "confirmed"} for r in g["relationships"]]},
            "timeline": [{"id": v["id"], "at": v["at"], "summary": v["summary"], "participants": v["participants"], "status": v["status"], "place": v["place"]} for v in g["events"]],
            "time_wheel": C.time_wheel(g["events"], entity_id),
            "analysis": {"links": C.link_summary(g), "pattern": C.time_wheel(g["events"], entity_id)["pattern"]}}


@router.patch("/cases/{case_id}/close")
async def close_case(case_id: str, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    if (x_toc_role or "").lower() not in CASE_OPENERS: raise HTTPException(403, "Closing a case is the analyst's or the Battle Captain's")
    c = await session.get(CaseRow, case_id)
    if not c: raise HTTPException(404, "case not found")
    c.status, c.closed_at = "closed", R.now_utc(); await session.commit()
    await ledger().append_event(content_id=case_id, event_type="s2.case.closed", actor_type="human", actor_id=x_toc_actor or x_toc_role, old_state="open", new_state="closed", reason=f"{c.title} closed")
    return C.case_dict(c)


# ---------------------------------------------------------------- §5.6 Area Assessment

AREA_DRAFTERS = {"battle_captain", "analyst"}
AREA_APPROVERS = {"battle_captain", "analyst"}


class AreaCreate(BaseModel):
    requirement_ids: List[str] = Field(..., min_length=1, max_length=6)
    title: Optional[str] = None
    purpose: Optional[str] = None

class AreaUpdate(BaseModel):
    status: Literal["draft", "review", "approved"]


@router.post("/area-assessments", status_code=201)
async def draft_area(body: AreaCreate, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    """Candidates side by side. Directed requirements only — the wall's own subjects get the per-subject Assessment."""
    if (x_toc_role or "").lower() not in AREA_DRAFTERS:
        raise HTTPException(403, f"Drafting an Area Assessment needs {sorted(AREA_DRAFTERS)}")
    reqs = []
    for rid in body.requirement_ids:
        r = await session.get(RequirementRow, rid)
        if not r: raise HTTPException(404, f"requirement {rid} not found")
        if r.kind != "directed": raise HTTPException(422, f"{rid} is a standing requirement; an Area Assessment compares directed candidates")
        reqs.append(r)
    now = R.now_utc()
    purpose = body.purpose or reqs[0].purpose
    product = await A.build_product(session, reqs, purpose, now)
    title = body.title or (f"Area Assessment — {' vs '.join(r.subject_name for r in reqs)}" if len(reqs) > 1 else f"Area Assessment — {reqs[0].subject_name}")
    row = A.new_row(title, purpose, body.requirement_ids, product, now)
    session.add(row); await session.commit()
    await ledger().append_event(content_id=row.id, event_type="s2.area.drafted", actor_type="ai_model" if "heuristic" in row.author or "claude" in row.author else "system", actor_id=row.author, new_state="draft",
                                reason=f"{title}: " + "; ".join(f"{c['place']} {c['counts']['reported']}/{c['counts']['quiet']}/{c['counts']['gap']}" for c in product["candidates"]) + (" — REFUSED" if not product["approvable"] else ""),
                                metadata={"requirement_ids": body.requirement_ids, "approvable": product["approvable"], "requested_by": x_toc_actor or x_toc_role})
    return A.to_dict(row)


@router.get("/area-assessments")
async def list_areas(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(AreaAssessmentRow).order_by(AreaAssessmentRow.created_at.desc()))).scalars().all()
    return [{k: v for k, v in A.to_dict(r).items() if k != "candidates"} | {"places": [c["place"] for c in json.loads(r.product_json).get("candidates", [])]} for r in rows]


@router.get("/area-assessments/{area_id}")
async def get_area(area_id: str, session: AsyncSession = Depends(get_session)):
    row = await session.get(AreaAssessmentRow, area_id)
    if not row: raise HTTPException(404, "area assessment not found")
    return A.to_dict(row)


@router.patch("/area-assessments/{area_id}")
async def update_area(area_id: str, body: AreaUpdate, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    row = await session.get(AreaAssessmentRow, area_id)
    if not row: raise HTTPException(404, "area assessment not found")
    if (x_toc_role or "").lower() not in AREA_APPROVERS:
        raise HTTPException(403, "Reviewing or approving is the analyst's or the Battle Captain's")
    product = json.loads(row.product_json)
    if body.status == "approved" and not product.get("approvable"):
        raise HTTPException(409, "No qualifying evidence: a collection gap cannot be approved (§5.5)")
    old = row.status
    row.status, row.decided_by, row.decided_at = body.status, x_toc_actor or x_toc_role, R.now_utc()
    await session.commit()
    await ledger().append_event(content_id=row.id, event_type="s2.area.status", actor_type="human", actor_id=x_toc_actor or x_toc_role, old_state=old, new_state=body.status, reason=f"{row.title} → {body.status}")
    return A.to_dict(row)


# ---------------------------------------------------------------- §5.6 INTSUM (Decision G)

INTSUM_RELEASERS = {"battle_captain"}
INTSUM_DRAFTERS = {"battle_captain", "analyst"}


class IntsumRelease(BaseModel):
    notes: Optional[str] = None


@router.post("/intsum/draft", status_code=201)
async def draft_intsum(session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    """Manual draft (the fixed-time draft calls the same code). Covers everything since the last INTSUM."""
    if (x_toc_role or "").lower() not in INTSUM_DRAFTERS:
        raise HTTPException(403, "Drafting the INTSUM is the analyst's or the Battle Captain's; it also drafts itself at the fixed hour")
    row = await I.draft(session, R.now_utc())
    d = I.to_dict(row)
    await ledger().append_event(content_id=row.id, event_type="s2.intsum.drafted", actor_type="ai_model", actor_id=row.drafted_by, new_state="draft",
                                reason=f"INTSUM {d['period']['from'][:16]}Z → {d['period']['to'][:16]}Z: {d['headline']}", metadata={"requested_by": x_toc_actor or x_toc_role, "nstr": d["nstr"]})
    return d


async def draft_if_due(session: AsyncSession, now: Optional[datetime] = None) -> Optional[IntsumRow]:
    """Called by the COP on a timer: Decision G's fixed-time draft. Idempotent per day."""
    now = now or R.now_utc()
    if not await I.due(session, now): return None
    row = await I.draft(session, now)
    d = I.to_dict(row)
    await ledger().append_event(content_id=row.id, event_type="s2.intsum.drafted", actor_type="system", actor_id="scheduler", new_state="draft",
                                reason=f"INTSUM (fixed-time {I.DRAFT_HOUR_UTC:02d}00Z) {d['period']['from'][:16]}Z → {d['period']['to'][:16]}Z: {d['headline']}", metadata={"nstr": d["nstr"]})
    return row


@router.get("/intsum")
async def list_intsums(limit: int = 14, session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(IntsumRow).order_by(IntsumRow.period_to.desc()).limit(limit))).scalars().all()
    return [{"id": r.id, "status": r.status, "period": json.loads(r.product_json)["period"], "headline": json.loads(r.product_json)["headline"], "nstr": json.loads(r.product_json)["nstr"],
             "released_by": r.released_by, "released_at": R.iso(r.released_at)} for r in rows]


@router.get("/intsum/latest")
async def latest_intsum(session: AsyncSession = Depends(get_session)):
    row = await I.latest(session)
    if not row: raise HTTPException(404, "no INTSUM yet — one drafts itself at %02d00Z, or POST /intsum/draft" % I.DRAFT_HOUR_UTC)
    return I.to_dict(row)


@router.get("/intsum/{intsum_id}")
async def get_intsum(intsum_id: str, session: AsyncSession = Depends(get_session)):
    row = await session.get(IntsumRow, intsum_id)
    if not row: raise HTTPException(404, "INTSUM not found")
    return I.to_dict(row)


@router.post("/intsum/{intsum_id}/release")
async def release_intsum(intsum_id: str, body: IntsumRelease, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    """Decision G: the Battle Captain releases. One human gate on the product the whole floor reads."""
    if (x_toc_role or "").lower() not in INTSUM_RELEASERS:
        raise HTTPException(403, "Only the Battle Captain releases the INTSUM (Decision G)")
    row = await session.get(IntsumRow, intsum_id)
    if not row: raise HTTPException(404, "INTSUM not found")
    if row.status == "released": raise HTTPException(409, "already released")
    row.status, row.released_by, row.released_at, row.notes = "released", x_toc_actor or "battle_captain", R.now_utc(), body.notes or ""
    await session.commit()
    await ledger().append_event(content_id=row.id, event_type="s2.intsum.released", actor_type="human", actor_id=row.released_by, old_state="draft", new_state="released",
                                reason=f"INTSUM released" + (f" — {body.notes}" if body.notes else ""))
    return I.to_dict(row)


# ---------------------------------------------------------------- §5.10 #4 dissemination

DISSEMINATORS = {"battle_captain", "analyst"}


class Disseminate(BaseModel):
    recipients: List[str] = Field(..., min_length=1, max_length=50)  # roles, person ids, or names
    channel: Literal["wall", "chat"] = "wall"
    note: str = ""


async def _product(session: AsyncSession, ptype: str, pid: str):
    """(title, status, created_at, releasable) for any product type. Only approved / released products go out."""
    if ptype == "assessment":
        from coptoc.db_models import AssessmentRow
        a = await session.get(AssessmentRow, pid)
        if not a: raise HTTPException(404, "assessment not found")
        return a.title, a.status, a.created_at, a.status == "approved"
    if ptype == "area":
        a = await session.get(AreaAssessmentRow, pid)
        if not a: raise HTTPException(404, "area assessment not found")
        return a.title, a.status, a.created_at, a.status == "approved"
    if ptype == "intsum":
        a = await session.get(IntsumRow, pid)
        if not a: raise HTTPException(404, "INTSUM not found")
        return f"INTSUM {a.id}", a.status, a.drafted_at, a.status == "released"
    if ptype == "warning":
        a = await session.get(WarningRow, pid)
        if not a: raise HTTPException(404, "warning not found")
        return a.title, a.status, a.created_at, a.status == "released"
    raise HTTPException(404, f"unknown product type {ptype}")


@router.post("/products/{ptype}/{pid}/disseminate", status_code=201)
async def disseminate(ptype: str, pid: str, body: Disseminate, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    """Send a released product to named recipients (roles, people) and start the clock on their acknowledgement.
    `chat` posts one line to the ops channel when Slack is configured and records `simulated` otherwise."""
    if (x_toc_role or "").lower() not in DISSEMINATORS:
        raise HTTPException(403, "Disseminating is the analyst's or the Battle Captain's")
    title, status, created_at, ok = await _product(session, ptype, pid)
    if not ok:
        raise HTTPException(409, f"{title} is {status}: only approved or released products are disseminated")
    now = R.now_utc()
    delivery = "recorded"
    if body.channel == "chat":
        from coptoc.comms import ChatChannel
        d = await ChatChannel().post(f":clipboard: *TOC {ptype.upper()} released — {title}* → {', '.join(body.recipients)}. Acknowledge on the wall.")
        delivery = d.status
    rows = [D.new_row(ptype, pid, title, rcpt.strip(), body.channel, delivery, x_toc_actor or x_toc_role, now, created_at) for rcpt in body.recipients if rcpt.strip()]
    for r in rows: r.note = body.note
    session.add_all(rows); await session.commit()
    lat = D._mins(created_at, now)
    await ledger().append_event(content_id=pid, event_type="s2.product.disseminated", actor_type="human", actor_id=x_toc_actor or x_toc_role,
                                reason=f"{title} → {len(rows)} recipient(s) via {body.channel}" + (f" ({delivery})" if delivery != "recorded" else "") + (f"; {lat} min after creation" if lat is not None else ""),
                                metadata={"product_type": ptype, "recipients": [r.recipient for r in rows], "channel": body.channel, "delivery": delivery, "created_to_sent_min": lat})
    return await D.for_product(session, ptype, pid, now)


@router.post("/products/{ptype}/{pid}/ack")
async def acknowledge_product(ptype: str, pid: str, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    """The read-back. Matches the caller to a recipient row by actor or role; an unlisted reader is recorded as an
    unsolicited read so the record still shows who saw it."""
    title, status, created_at, _ = await _product(session, ptype, pid)
    now = R.now_utc()
    actor, role = (x_toc_actor or "").strip(), (x_toc_role or "").lower().strip()
    rows = (await session.execute(select(DistributionRow).where(DistributionRow.product_type == ptype, DistributionRow.product_id == pid, DistributionRow.acknowledged_at.is_(None)))).scalars().all()
    hit = next((r for r in rows if actor and r.recipient.lower() == actor.lower()), None) or next((r for r in rows if role and r.recipient == role), None)
    if hit is None:
        hit = D.new_row(ptype, pid, title, actor or role or "unknown", "wall", "recorded", "self", now, created_at); hit.note = "unsolicited read"
        session.add(hit)
    hit.acknowledged_at, hit.acknowledged_by = now, actor or role or "unknown"
    await session.commit()
    await ledger().append_event(content_id=pid, event_type="s2.product.acknowledged", actor_type="human", actor_id=hit.acknowledged_by,
                                reason=f"{title} acknowledged by {hit.acknowledged_by}" + (f" ({D._mins(hit.sent_at, now)} min after send)" if hit.note != "unsolicited read" else " (not on the distribution)"),
                                metadata={"product_type": ptype, "recipient": hit.recipient, "sent_to_ack_min": D._mins(hit.sent_at, now)})
    return await D.for_product(session, ptype, pid, now)


@router.get("/products/{ptype}/{pid}/distribution")
async def distribution(ptype: str, pid: str, session: AsyncSession = Depends(get_session)):
    await _product(session, ptype, pid)
    return await D.for_product(session, ptype, pid, R.now_utc())


@router.get("/products/unacknowledged")
async def products_unacknowledged(session: AsyncSession = Depends(get_session)):
    return await D.unacknowledged(session, R.now_utc())


# ---------------------------------------------------------------- §5.6 Warning — FLASH to the floor

WARNING_DRAFTERS = {"battle_captain", "analyst"}
WARNING_RELEASERS = {"battle_captain"}


class WarningCreate(BaseModel):
    subject_type: Literal["location", "person", "event"]
    subject_id: str
    title: str
    text: str = ""
    severity: Literal["elevated", "critical"] = "elevated"
    threat_id: Optional[str] = None


@router.get("/warnings")
async def list_warnings(status: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    now = R.now_utc()
    await W.expire(session, now)
    rows = (await session.execute(select(WarningRow).order_by(WarningRow.created_at.desc()))).scalars().all()
    return [W.to_dict(w, now) for w in rows if not status or w.status == status]


@router.post("/warnings", status_code=201)
async def draft_warning(body: WarningCreate, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    """A human-drafted warning (the rule suggests the rest). Still needs the Battle Captain's release."""
    if (x_toc_role or "").lower() not in WARNING_DRAFTERS:
        raise HTTPException(403, "Drafting a warning is the analyst's or the Battle Captain's")
    from coptoc.service import build_snapshot
    snap = await build_snapshot(session, include_restricted=True, log_limit=1)
    name = next((x["name"] for k in ("locations", "people", "events") for x in snap.get(k, []) if x["id"] == body.subject_id), None)
    if name is None: raise HTTPException(404, f"{body.subject_type} {body.subject_id} not on the wall")
    now = R.now_utc()
    w = WarningRow(id=f"WARN-{uuid.uuid4().hex[:6].upper()}", title=body.title if body.title.startswith("FLASH") else f"FLASH — {body.title}", text=body.text, subject_type=body.subject_type,
                   subject_id=body.subject_id, subject_name=name, threat_id=body.threat_id, severity=body.severity, status="draft", suggested_by=x_toc_actor or x_toc_role, created_at=now)
    session.add(w); await session.commit()
    await ledger().append_event(content_id=w.id, event_type="s2.warning.drafted", actor_type="human", actor_id=x_toc_actor or x_toc_role, new_state="draft", reason=f"{w.title} ({w.severity})")
    return W.to_dict(w, now)


@router.post("/warnings/suggest")
async def suggest_warnings(session: AsyncSession = Depends(get_session)):
    """Run the rule now (collection runs it after every refresh)."""
    from coptoc.service import build_snapshot
    now = R.now_utc()
    snap = await build_snapshot(session, include_restricted=True, log_limit=1)
    new = await W.suggest(session, snap, now)
    for w in new:
        await ledger().append_event(content_id=w.id, event_type="s2.warning.suggested", actor_type="system", actor_id=w.suggested_by, new_state="suggested", reason=f"{w.title} — awaiting the Battle Captain")
    return {"suggested": [W.to_dict(w, now) for w in new]}


@router.post("/warnings/{wid}/release")
async def release_warning(wid: str, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    """The Battle Captain releases: FLASH on the wall, SMS to the people at the subject, a post to the ops channel,
    and an acknowledgement row per role. Nothing leaves the building before this."""
    if (x_toc_role or "").lower() not in WARNING_RELEASERS:
        raise HTTPException(403, "Only the Battle Captain releases a warning")
    w = await session.get(WarningRow, wid)
    if not w: raise HTTPException(404, "warning not found")
    if w.status not in ("suggested", "draft"): raise HTTPException(409, f"warning is {w.status}")
    from coptoc.comms import ChatChannel, SMSChannel
    from coptoc.service import build_snapshot
    now = R.now_utc()
    snap = await build_snapshot(session, include_restricted=True, log_limit=1)
    people = W.people_for_subject(snap, w)
    sms = SMSChannel()
    text = W.flash_text(w)
    deliveries = {"sent": 0, "simulated": 0, "failed": 0}
    for p in people:
        d = await sms.send(p.get("phone"), text)
        deliveries[d.status] = deliveries.get(d.status, 0) + 1
    chat = await ChatChannel().post(f":rotating_light: *{w.title}*\n{w.text}\nAcknowledge on the wall.")
    w.status, w.released_by, w.released_at = "released", x_toc_actor or "battle_captain", now
    w.dispatch_json = json.dumps({"sms": deliveries, "chat": chat.status, "people": len(people), "simulated": not sms.configured and not ChatChannel().configured})
    w.recipients_json = json.dumps([p["id"] for p in people])
    session.add_all([D.new_row("warning", w.id, w.title, role, "wall", "recorded", w.released_by, now, w.created_at) for role in W.ROLES_TO_ACK])
    await session.commit()
    await ledger().append_event(content_id=w.id, event_type="s2.warning.released", actor_type="human", actor_id=w.released_by, old_state="draft", new_state="released",
                                reason=f"{w.title}: SMS to {len(people)} ({deliveries}), chat {chat.status}" + (" — SIMULATED, no Twilio/Slack" if not sms.configured and not ChatChannel().configured else ""),
                                metadata={"people": len(people), "deliveries": deliveries, "chat": chat.status})
    return W.to_dict(w, now)


@router.post("/warnings/{wid}/cancel")
async def cancel_warning(wid: str, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None), x_toc_actor: Optional[str] = Header(None)):
    if (x_toc_role or "").lower() not in WARNING_DRAFTERS:
        raise HTTPException(403, "Cancelling is the analyst's or the Battle Captain's")
    w = await session.get(WarningRow, wid)
    if not w: raise HTTPException(404, "warning not found")
    old = w.status
    w.status, w.cancelled_by = "cancelled", x_toc_actor or x_toc_role
    await session.commit()
    await ledger().append_event(content_id=w.id, event_type="s2.warning.cancelled", actor_type="human", actor_id=w.cancelled_by, old_state=old, new_state="cancelled", reason=f"{w.title} cancelled")
    return W.to_dict(w)


def standalone_app() -> FastAPI:
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def lifespan(_app):
        sessions(); await init_db(_engine); yield
    app = FastAPI(title="Sigtoc — S2 API", version="0.1.0", description="Requirements, the collection plan, sources, query. PRD §5.", lifespan=lifespan)
    app.include_router(router)
    @app.get("/v1/health")
    def health(): return {"status": "ok", "service": "sigtoc"}
    return app

app = standalone_app()
