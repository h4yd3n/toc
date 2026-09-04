"""Sigtoc's own API (Decision 3a). Mounted into the COP app under /v1/s2 and runnable standalone: `make run-s2`."""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.database import async_session_factory, create_engine, init_db
from shared.ledger import AsyncDatabaseEventLedger
from . import requirements as R
from .requirements import CADENCES, CATALOG, INDICATORS, RequirementRow, SourceStateRow

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
