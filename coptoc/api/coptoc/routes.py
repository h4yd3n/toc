import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.ledger import AsyncDatabaseEventLedger
from shared.database import async_session_factory, create_engine, init_db
from . import db_models  # noqa: F401 — registers tables on Base.metadata
from .comms import Dispatcher, public_url
from .db_models import (AccountabilityRow, AssessmentRow, DeliveryRow, EventAttendeeRow, EventRow, IncidentRow, LocationRow, PersonRow, PIRRow,
                        TeamRow, ThreatLinkRow, ThreatRow, TripRow)
from .schemas import (AssessmentDraftRequest, AssessmentUpdate, AttendeesAdd, CheckIn, EventCreate, EventUpdate, IncidentClose, IncidentOpen,
                      PIRCreate, PIRUpdate, PostureUpdate, RosterUpdate, ShiftUpdate, ThreatLinkCreate, TripCreate, TripUpdate)
from .seed import generate_event_trips, reseed, seed_if_empty
from .service import build_snapshot, haversine_km, may_see_restricted, now_utc

router = APIRouter(prefix="/v1/cop", tags=["cop"])

_engine = None
_sessions: Optional[async_sessionmaker] = None


def sessions() -> async_sessionmaker:
    """Lazy so DATABASE_URL can be set by tests before first use."""
    global _engine, _sessions
    if _sessions is None:
        _engine = create_engine()
        _sessions = async_session_factory(_engine)
    return _sessions


async def get_session() -> AsyncSession:
    async with sessions()() as session:
        yield session


def get_ledger() -> AsyncDatabaseEventLedger:
    return AsyncDatabaseEventLedger(sessions())


async def startup() -> None:
    sessions()
    await init_db(_engine)
    async with sessions()() as session:
        await seed_if_empty(session)


def actor_from(x_toc_actor: Optional[str]) -> str:
    return x_toc_actor or "watch_floor"


ROLL_CALL_OPENERS = {"battle_captain"}  # Decision 3


def require_role(role: Optional[str], allowed: set, what: str) -> None:
    if (role or "").lower() not in allowed:
        raise HTTPException(403, f"{what} requires role {' or '.join(sorted(allowed))}; you are {role or 'unspecified'}")


def checkin_token(person_id: str, incident_id: str) -> str:
    """Per-person, per-incident link token for SMS/chat check-ins. HMAC so it can't be guessed; no DB row needed."""
    secret = os.environ.get("TOC_SECRET", "dev-only-secret-change-me").encode()
    mac = hmac.new(secret, f"{person_id}:{incident_id}".encode(), hashlib.sha256).hexdigest()[:20]
    return f"{person_id}.{incident_id}.{mac}"


def parse_checkin_token(token: str) -> tuple:
    try:
        person_id, incident_id, mac = token.split(".")
    except ValueError:
        raise HTTPException(404, "bad token")
    if not hmac.compare_digest(checkin_token(person_id, incident_id), token):
        raise HTTPException(404, "bad token")
    return person_id, incident_id


def naive(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


async def one_or_404(session: AsyncSession, model, id_: str, what: str):
    row = await session.get(model, id_)
    if not row:
        raise HTTPException(404, f"{what} not found")
    return row


# ---------------------------------------------------------------- read

@router.get("/snapshot")
async def snapshot(restricted: bool = Query(False, description="Include restricted-tier sites (residences). Decision 1: off by default."),
                   session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Everything the wall needs, in one call. Decision C: `restricted=true` is honored only for X-TOC-Role
    battle_captain or ep; anyone else gets the standard picture with `restricted_denied: true`."""
    allowed = restricted and may_see_restricted(x_toc_role)
    snap = await build_snapshot(session, include_restricted=allowed)
    snap["restricted_denied"] = bool(restricted and not allowed)
    snap["role"] = (x_toc_role or "unspecified").lower()
    return snap


@router.get("/locations")
async def locations(restricted: bool = False, session: AsyncSession = Depends(get_session), x_toc_role: Optional[str] = Header(None)):
    return (await build_snapshot(session, include_restricted=restricted and may_see_restricted(x_toc_role)))["locations"]


@router.get("/locations/{location_id}")
async def location_detail(location_id: str, restricted: bool = True, session: AsyncSession = Depends(get_session)):
    snap = await build_snapshot(session, include_restricted=restricted)
    loc = next((l for l in snap["locations"] if l["id"] == location_id), None)
    if not loc:
        raise HTTPException(404, "location not found")
    teams = [t for t in snap["teams"] if t["location_id"] == location_id]
    for t in teams:
        t["people"] = [p for p in snap["people"] if p["team_id"] == t["id"]]
    present = [p for p in snap["people"] if p["location_id"] == location_id]
    return {**loc, "teams": teams, "present_people": present}


@router.get("/people")
async def people(status: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    ps = (await build_snapshot(session, include_restricted=True))["people"]
    return [p for p in ps if status is None or p["status"] == status]


@router.get("/people/{person_id}")
async def person_detail(person_id: str, session: AsyncSession = Depends(get_session)):
    snap = await build_snapshot(session, include_restricted=True)
    p = next((p for p in snap["people"] if p["id"] == person_id), None)
    if not p:
        raise HTTPException(404, "person not found")
    trip = next((t for t in snap["trips"] if t["id"] == p["trip_id"]), None) if p["trip_id"] else None
    return {**p, "trip": trip}


@router.get("/trips")
async def trips(session: AsyncSession = Depends(get_session)):
    return (await build_snapshot(session))["trips"]


@router.get("/events")
async def events(session: AsyncSession = Depends(get_session)):
    return (await build_snapshot(session))["events"]


@router.get("/events/{event_id}")
async def event_detail(event_id: str, session: AsyncSession = Depends(get_session)):
    snap = await build_snapshot(session, include_restricted=True)
    e = next((e for e in snap["events"] if e["id"] == event_id), None)
    if not e:
        raise HTTPException(404, "event not found")
    people_by_id = {p["id"]: p for p in snap["people"]}
    return {**e, "attendees": [people_by_id[i] for i in e["attendee_ids"] if i in people_by_id],
            "trips": [t for t in snap["trips"] if t["event_id"] == event_id]}


@router.get("/threats")
async def threats(session: AsyncSession = Depends(get_session)):
    return (await build_snapshot(session))["threats"]


@router.get("/pirs")
async def pirs(session: AsyncSession = Depends(get_session)):
    return (await build_snapshot(session))["pirs"]


@router.get("/assessments")
async def assessments(session: AsyncSession = Depends(get_session)):
    return (await build_snapshot(session))["assessments"]


@router.get("/log")
async def ops_log(limit: int = 50, session: AsyncSession = Depends(get_session)):
    """The battle log — every write to the COP, hash-chained per subject."""
    return (await build_snapshot(session, log_limit=limit))["log"]


# ---------------------------------------------------------------- S3 writes: trips

@router.post("/trips", status_code=201)
async def create_trip(body: TripCreate, session: AsyncSession = Depends(get_session),
                      x_toc_actor: Optional[str] = Header(None)):
    person = await one_or_404(session, PersonRow, body.person_id, "person")
    await one_or_404(session, LocationRow, body.origin_location_id, "origin location")
    if body.dest_location_id:
        dest = await one_or_404(session, LocationRow, body.dest_location_id, "destination location")
        name, lat, lon = dest.name, dest.lat, dest.lon
    else:
        if body.dest_lat is None or body.dest_lon is None or not body.dest_name:
            raise HTTPException(422, "dest_location_id or dest_name+dest_lat+dest_lon required")
        name, lat, lon = body.dest_name, body.dest_lat, body.dest_lon
    if naive(body.return_at) <= naive(body.depart_at):
        raise HTTPException(422, "return_at must be after depart_at")
    trip = TripRow(id=f"trip_{uuid.uuid4().hex[:8]}", person_id=person.id, origin_location_id=body.origin_location_id,
                   dest_location_id=body.dest_location_id, dest_name=name, dest_lat=lat, dest_lon=lon,
                   depart_at=naive(body.depart_at), return_at=naive(body.return_at), purpose=body.purpose,
                   created_by=actor_from(x_toc_actor))
    session.add(trip)
    await session.commit()
    await get_ledger().append_event(content_id=trip.id, event_type="cop.trip.created", actor_type="human",
                                    actor_id=actor_from(x_toc_actor), new_state="planned",
                                    reason=f"{person.name} → {name}", metadata={"person_id": person.id, "dest": name})
    return {"id": trip.id, "status": "created"}


@router.patch("/trips/{trip_id}")
async def update_trip(trip_id: str, body: TripUpdate, session: AsyncSession = Depends(get_session),
                      x_toc_actor: Optional[str] = Header(None)):
    trip = await one_or_404(session, TripRow, trip_id, "trip")
    changes = {}
    if body.dest_location_id:
        dest = await one_or_404(session, LocationRow, body.dest_location_id, "destination location")
        trip.dest_location_id, trip.dest_name, trip.dest_lat, trip.dest_lon = dest.id, dest.name, dest.lat, dest.lon
        changes["dest"] = dest.name
    elif body.dest_name and body.dest_lat is not None and body.dest_lon is not None:
        trip.dest_location_id, trip.dest_name, trip.dest_lat, trip.dest_lon = None, body.dest_name, body.dest_lat, body.dest_lon
        changes["dest"] = body.dest_name
    for f in ("depart_at", "return_at"):
        v = getattr(body, f)
        if v is not None:
            setattr(trip, f, naive(v)); changes[f] = v.isoformat()
    if body.purpose is not None:
        trip.purpose = body.purpose; changes["purpose"] = body.purpose
    if trip.return_at <= trip.depart_at:
        raise HTTPException(422, "return_at must be after depart_at")
    await session.commit()
    await get_ledger().append_event(content_id=trip.id, event_type="cop.trip.updated", actor_type="human",
                                    actor_id=actor_from(x_toc_actor), reason=", ".join(f"{k}={v}" for k, v in changes.items()) or "no-op",
                                    metadata=changes)
    return {"id": trip.id, "status": "updated", "changes": changes}


@router.delete("/trips/{trip_id}")
async def delete_trip(trip_id: str, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    trip = await one_or_404(session, TripRow, trip_id, "trip")
    await session.delete(trip)
    await session.commit()
    await get_ledger().append_event(content_id=trip_id, event_type="cop.trip.cancelled", actor_type="human",
                                    actor_id=actor_from(x_toc_actor), old_state="planned", new_state="cancelled", reason="Trip cancelled")
    return {"id": trip_id, "status": "cancelled"}


# ---------------------------------------------------------------- S3 writes: events

async def _apply_attendees(session, event: EventRow, person_ids, generate: bool, actor: str) -> Dict[str, int]:
    existing = {a.person_id for a in (await session.execute(select(EventAttendeeRow).where(EventAttendeeRow.event_id == event.id))).scalars()}
    people = {p.id: p for p in (await session.execute(select(PersonRow))).scalars()}
    team_loc = {t.id: t.location_id for t in (await session.execute(select(TeamRow))).scalars()}
    added = [pid for pid in person_ids if pid in people and pid not in existing]
    session.add_all([EventAttendeeRow(event_id=event.id, person_id=pid) for pid in added])
    trips = generate_event_trips(event, added, people, team_loc, created_by=actor) if generate else []
    existing_trip_ids = set((await session.execute(select(TripRow.id))).scalars().all()) if trips else set()
    trips = [t for t in trips if t.id not in existing_trip_ids]
    session.add_all(trips)
    return {"attendees_added": len(added), "trips_generated": len(trips)}


@router.post("/events", status_code=201)
async def create_event(body: EventCreate, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    if body.venue_location_id:
        v = await one_or_404(session, LocationRow, body.venue_location_id, "venue location")
        vname, vlat, vlon = v.name, v.lat, v.lon
    else:
        if body.venue_lat is None or body.venue_lon is None or not body.venue_name:
            raise HTTPException(422, "venue_location_id or venue_name+venue_lat+venue_lon required")
        vname, vlat, vlon = body.venue_name, body.venue_lat, body.venue_lon
    if naive(body.end_at) <= naive(body.start_at):
        raise HTTPException(422, "end_at must be after start_at")
    actor = actor_from(x_toc_actor)
    ev = EventRow(id=f"evt_{uuid.uuid4().hex[:8]}", name=body.name, event_type=body.event_type,
                  venue_location_id=body.venue_location_id, venue_name=vname, venue_lat=vlat, venue_lon=vlon,
                  start_at=naive(body.start_at), end_at=naive(body.end_at), description=body.description,
                  security_plan=body.security_plan, created_by=actor)
    session.add(ev)
    await session.flush()
    result = await _apply_attendees(session, ev, body.attendee_ids, body.generate_trips, actor)
    await session.commit()
    await get_ledger().append_event(content_id=ev.id, event_type="cop.event.created", actor_type="human", actor_id=actor,
                                    new_state="upcoming", reason=f"{ev.name} @ {vname}", metadata={"venue": vname, **result})
    return {"id": ev.id, "status": "created", **result}


@router.patch("/events/{event_id}")
async def update_event(event_id: str, body: EventUpdate, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    ev = await one_or_404(session, EventRow, event_id, "event")
    changes = {}
    for f in ("name", "description", "security_plan"):
        v = getattr(body, f)
        if v is not None:
            setattr(ev, f, v); changes[f] = v if f != "security_plan" else "(updated)"
    for f in ("start_at", "end_at"):
        v = getattr(body, f)
        if v is not None:
            setattr(ev, f, naive(v)); changes[f] = v.isoformat()
    if ev.end_at <= ev.start_at:
        raise HTTPException(422, "end_at must be after start_at")
    await session.commit()
    await get_ledger().append_event(content_id=ev.id, event_type="cop.event.updated", actor_type="human",
                                    actor_id=actor_from(x_toc_actor), reason=", ".join(f"{k}={v}" for k, v in changes.items()) or "no-op", metadata=changes)
    return {"id": ev.id, "status": "updated", "changes": changes}


@router.post("/events/{event_id}/attendees")
async def add_attendees(event_id: str, body: AttendeesAdd, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    ev = await one_or_404(session, EventRow, event_id, "event")
    actor = actor_from(x_toc_actor)
    result = await _apply_attendees(session, ev, body.person_ids, body.generate_trips, actor)
    await session.commit()
    await get_ledger().append_event(content_id=ev.id, event_type="cop.event.attendees_added", actor_type="human", actor_id=actor,
                                    reason=f"+{result['attendees_added']} attendees, {result['trips_generated']} trips", metadata=result)
    return {"id": ev.id, **result}


@router.delete("/events/{event_id}/attendees/{person_id}")
async def remove_attendee(event_id: str, person_id: str, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    ev = await one_or_404(session, EventRow, event_id, "event")
    row = await session.get(EventAttendeeRow, {"event_id": event_id, "person_id": person_id})
    if not row:
        raise HTTPException(404, "attendee not found")
    await session.delete(row)
    trip = await session.get(TripRow, f"trip_{event_id}_{person_id}")
    if trip:
        await session.delete(trip)
    await session.commit()
    await get_ledger().append_event(content_id=ev.id, event_type="cop.event.attendee_removed", actor_type="human",
                                    actor_id=actor_from(x_toc_actor), reason=f"-{person_id}", metadata={"person_id": person_id, "trip_removed": bool(trip)})
    return {"id": ev.id, "removed": person_id, "trip_removed": bool(trip)}


@router.delete("/events/{event_id}")
async def delete_event(event_id: str, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    ev = await one_or_404(session, EventRow, event_id, "event")
    for t in (await session.execute(select(TripRow).where(TripRow.event_id == event_id))).scalars():
        await session.delete(t)
    for a in (await session.execute(select(EventAttendeeRow).where(EventAttendeeRow.event_id == event_id))).scalars():
        await session.delete(a)
    await session.delete(ev)
    await session.commit()
    await get_ledger().append_event(content_id=event_id, event_type="cop.event.cancelled", actor_type="human",
                                    actor_id=actor_from(x_toc_actor), old_state="upcoming", new_state="cancelled", reason=f"{ev.name} cancelled")
    return {"id": event_id, "status": "cancelled"}


# ---------------------------------------------------------------- S1 writes

@router.post("/people/{person_id}/checkin")
async def checkin(person_id: str, body: CheckIn, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    """Decision 2: a fresh check-in overrides the derived position for 12 hours."""
    p = await one_or_404(session, PersonRow, person_id, "person")
    if body.lat is None or body.lon is None:
        raise HTTPException(422, "lat and lon required")
    p.last_checkin_lat, p.last_checkin_lon = body.lat, body.lon
    p.last_checkin_at = naive(body.at) or now_utc()
    p.last_checkin_note = body.note
    # Decision B: a check-in while on an open roster is an answer — clear the row as SAFE via app, no phone call needed.
    cleared = []
    open_rows = (await session.execute(
        select(AccountabilityRow).join(IncidentRow, IncidentRow.id == AccountabilityRow.incident_id)
        .where(AccountabilityRow.person_id == person_id, IncidentRow.status == "open",
               AccountabilityRow.status.in_(("unaccounted", "unreachable"))))).scalars().all()
    for r in open_rows:
        r.status, r.method, r.attempts = "safe", "app", r.attempts + 1
        r.last_attempt_at = r.updated_at = p.last_checkin_at
        r.updated_by, r.note = p.name, (body.note or "Self check-in")
        cleared.append(r.incident_id)
    await session.commit()
    await get_ledger().append_event(content_id=p.id, event_type="cop.person.checkin", actor_type="human", actor_id=x_toc_actor or p.id,
                                    reason=body.note or "Checked in", metadata={"lat": body.lat, "lon": body.lon, "cleared_rosters": cleared})
    for iid in cleared:
        await get_ledger().append_event(content_id=iid, event_type="cop.incident.contact", actor_type="human", actor_id=p.name,
                                        old_state="unaccounted", new_state="safe", reason=f"{p.name}: SAFE via app (self check-in)", metadata={"person_id": p.id, "method": "app"})
    return {"id": p.id, "status": "checked_in", "at": p.last_checkin_at.isoformat() + "Z", "cleared_rosters": cleared}


@router.patch("/people/{person_id}/shift")
async def set_shift(person_id: str, body: ShiftUpdate, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    p = await one_or_404(session, PersonRow, person_id, "person")
    old = "on" if p.on_shift else "off"
    p.on_shift, p.shift_role = body.on_shift, (body.shift_role if body.on_shift else None)
    await session.commit()
    await get_ledger().append_event(content_id=p.id, event_type="cop.person.shift", actor_type="human", actor_id=actor_from(x_toc_actor),
                                    old_state=old, new_state="on" if body.on_shift else "off",
                                    reason=f"{p.name} {'on shift as ' + (body.shift_role or 'unassigned') if body.on_shift else 'off shift'}")
    return {"id": p.id, "on_shift": p.on_shift, "shift_role": p.shift_role}


@router.patch("/locations/{location_id}/posture")
async def set_posture(location_id: str, body: PostureUpdate, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    """The Battle Captain sets posture. Confirmed threat links can raise the *effective* posture above this, never lower it."""
    loc = await one_or_404(session, LocationRow, location_id, "location")
    old = loc.posture
    loc.posture = body.posture
    await session.commit()
    await get_ledger().append_event(content_id=loc.id, event_type="cop.location.posture", actor_type="human", actor_id=actor_from(x_toc_actor),
                                    old_state=old, new_state=body.posture, reason=body.reason or f"{loc.name} posture {old} → {body.posture}")
    return {"id": loc.id, "posture": loc.posture}


# ---------------------------------------------------------------- S2 writes

@router.post("/threats/{threat_id}/links", status_code=201)
async def confirm_link(threat_id: str, body: ThreatLinkCreate, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    """Decision 3: an analyst confirms that a threat applies to a site or person. This is what changes posture."""
    th = await one_or_404(session, ThreatRow, threat_id, "threat")
    target = await one_or_404(session, LocationRow if body.target_type == "location" else PersonRow, body.target_id, body.target_type)
    dup = (await session.execute(select(ThreatLinkRow).where(ThreatLinkRow.threat_id == threat_id, ThreatLinkRow.target_type == body.target_type,
                                                              ThreatLinkRow.target_id == body.target_id))).scalar_one_or_none()
    if dup:
        return {"link_id": dup.id, "status": "already_confirmed"}
    actor = actor_from(x_toc_actor)
    link = ThreatLinkRow(threat_id=threat_id, target_type=body.target_type, target_id=body.target_id, confirmed_by=actor, confirmed_at=now_utc(), note=body.note)
    session.add(link)
    await session.commit()
    await get_ledger().append_event(content_id=body.target_id, event_type="cop.threat.link_confirmed", actor_type="human", actor_id=actor,
                                    new_state=th.severity, reason=f"Confirmed: {th.title} → {target.name}", metadata={"threat_id": threat_id, "link_id": link.id})
    return {"link_id": link.id, "status": "confirmed"}


@router.delete("/threats/{threat_id}/links/{link_id}")
async def unlink(threat_id: str, link_id: int, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    link = await session.get(ThreatLinkRow, link_id)
    if not link or link.threat_id != threat_id:
        raise HTTPException(404, "link not found")
    await session.delete(link)
    await session.commit()
    await get_ledger().append_event(content_id=link.target_id, event_type="cop.threat.link_removed", actor_type="human",
                                    actor_id=actor_from(x_toc_actor), reason=f"Unlinked threat {threat_id}", metadata={"threat_id": threat_id, "link_id": link_id})
    return {"link_id": link_id, "status": "removed"}


@router.post("/pirs", status_code=201)
async def create_pir(body: PIRCreate, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    n = len((await session.execute(select(PIRRow.id))).scalars().all()) + 1
    pir = PIRRow(id=f"PIR-{n:02d}", question=body.question, status="OPEN", owner=body.owner, priority=body.priority,
                 subject_type=body.subject_type, subject_id=body.subject_id, created_at=now_utc(), expires_at=naive(body.expires_at))
    session.add(pir)
    await session.commit()
    await get_ledger().append_event(content_id=pir.id, event_type="cop.pir.created", actor_type="human", actor_id=actor_from(x_toc_actor),
                                    new_state="OPEN", reason=body.question[:120])
    return {"id": pir.id, "status": "OPEN"}


@router.patch("/pirs/{pir_id}")
async def update_pir(pir_id: str, body: PIRUpdate, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    pir = await one_or_404(session, PIRRow, pir_id, "PIR")
    old = pir.status
    if body.status: pir.status = body.status
    if body.priority is not None: pir.priority = body.priority
    if body.question: pir.question = body.question
    await session.commit()
    await get_ledger().append_event(content_id=pir.id, event_type="cop.pir.updated", actor_type="human", actor_id=actor_from(x_toc_actor),
                                    old_state=old, new_state=pir.status, reason=f"{pir.id} {old} → {pir.status}")
    return {"id": pir.id, "status": pir.status}


@router.post("/assessments/draft", status_code=201)
async def draft_assessment(body: AssessmentDraftRequest, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    """S2, CLUE-style: the model drafts, code computes confidence, a human approves. See sigtoc.analysis.wall_drafter."""
    from sigtoc.analysis.wall_drafter import draft_for_subject  # lazy: keeps the API importable without sigtoc extras
    snap = await build_snapshot(session, include_restricted=True)
    try:
        draft = await draft_for_subject(snap, body.subject_type, body.subject_id)
    except KeyError:
        raise HTTPException(404, f"{body.subject_type} {body.subject_id} not found")
    n = len((await session.execute(select(AssessmentRow.id))).scalars().all()) + 14
    row = AssessmentRow(id=f"ASMT-{n:03d}", title=draft["title"], subject_type=body.subject_type, subject_id=body.subject_id,
                        likelihood=draft["likelihood"], band=draft["band"], confidence=draft["confidence"], bluf=draft["bluf"],
                        key_judgments_json=json.dumps(draft["key_judgments"]), evidence_json=json.dumps(draft["evidence"]),
                        gaps_json=json.dumps(draft["gaps"]), author=draft["author"], status="draft", created_at=now_utc())
    session.add(row)
    await session.commit()
    await get_ledger().append_event(content_id=row.id, event_type="cop.assessment.drafted", actor_type="ai_model", actor_id=draft["author"],
                                    new_state="draft", reason=f"{row.title}: {row.likelihood} ({row.band}), {row.confidence} confidence",
                                    metadata={"subject_type": body.subject_type, "subject_id": body.subject_id, "refused": draft.get("refused", False)})
    return {"id": row.id, "status": "draft", **draft}


@router.patch("/assessments/{assessment_id}")
async def update_assessment(assessment_id: str, body: AssessmentUpdate, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    a = await one_or_404(session, AssessmentRow, assessment_id, "assessment")
    old = a.status
    actor = actor_from(x_toc_actor)
    if body.bluf is not None:
        a.bluf = body.bluf
    if body.status:
        if body.status == "approved" and a.confidence == "insufficient":
            raise HTTPException(409, "Cannot approve an assessment with insufficient evidence — it is a collection gap, not a finding")
        a.status = body.status
        if body.status == "approved":
            a.approved_by, a.approved_at = actor, now_utc()
    await session.commit()
    await get_ledger().append_event(content_id=a.id, event_type="cop.assessment.status", actor_type="human", actor_id=actor,
                                    old_state=old, new_state=a.status, reason=f"{a.id} {old} → {a.status}")
    return {"id": a.id, "status": a.status, "approved_by": a.approved_by}


# ---------------------------------------------------------------- S6 accountability

@router.get("/incidents")
async def incidents(session: AsyncSession = Depends(get_session)):
    return (await build_snapshot(session, include_restricted=True))["incidents"]


@router.get("/incidents/{incident_id}")
async def incident_detail(incident_id: str, session: AsyncSession = Depends(get_session)):
    inc = next((i for i in (await build_snapshot(session, include_restricted=True))["incidents"] if i["id"] == incident_id), None)
    if not inc:
        raise HTTPException(404, "incident not found")
    return inc


@router.post("/incidents", status_code=201)
async def open_incident(body: IncidentOpen, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None),
                        x_toc_role: Optional[str] = Header(None)):
    """Open a roll call — Battle Captain only (Decision 3). The roster is everyone in the area now plus everyone
    assigned to the site (Decision A). Every one of them starts UNACCOUNTED."""
    require_role(x_toc_role, ROLL_CALL_OPENERS, "Opening a roll call")
    actor = actor_from(x_toc_actor)
    snap = await build_snapshot(session, include_restricted=True)
    if body.location_id:
        loc = await one_or_404(session, LocationRow, body.location_id, "location")
        kind, lat, lon, radius, title = "site", loc.lat, loc.lon, body.radius_km, body.title or f"Roll call — {loc.name}"
        # Decision A: everyone in the area now, plus everyone assigned to the site wherever they are.
        members = []
        for p in snap["people"]:
            if p["location_id"] == loc.id:
                members.append((p, "present"))
            elif haversine_km(p["lat"], p["lon"], lat, lon) <= radius:
                members.append((p, "in_area"))
            elif p["home_location_id"] == loc.id:
                members.append((p, "assigned"))
    elif body.threat_id:
        th = await one_or_404(session, ThreatRow, body.threat_id, "threat")
        kind, lat, lon, radius, title = "threat", th.lat, th.lon, th.radius_km + 5.0, body.title or f"Roll call — {th.title}"
        members = [(p, "in_area") for p in snap["people"] if haversine_km(p["lat"], p["lon"], lat, lon) <= radius]
    elif body.lat is not None and body.lon is not None:
        kind, lat, lon, radius, title = "manual", body.lat, body.lon, body.radius_km, body.title or "Roll call"
        members = [(p, "in_area") for p in snap["people"] if haversine_km(p["lat"], p["lon"], lat, lon) <= radius]
    else:
        raise HTTPException(422, "location_id, threat_id, or lat+lon required")
    inc = IncidentRow(id=f"inc_{uuid.uuid4().hex[:8]}", title=title, kind=kind, location_id=body.location_id, threat_id=body.threat_id,
                      lat=lat, lon=lon, radius_km=radius, status="open", opened_by=actor, opened_at=now_utc(), notes=body.notes)
    session.add(inc)
    await session.flush()
    session.add_all([AccountabilityRow(incident_id=inc.id, person_id=p["id"], status="unaccounted", basis=basis) for p, basis in members])
    await session.commit()
    by_basis = {b: sum(1 for _, x in members if x == b) for b in ("present", "in_area", "assigned")}
    await get_ledger().append_event(content_id=inc.id, event_type="cop.incident.opened", actor_type="human", actor_id=actor, new_state="open",
                                    reason=f"{title}: {len(members)} to account for ({by_basis['present']} on site, {by_basis['in_area']} nearby, {by_basis['assigned']} assigned elsewhere)",
                                    metadata={"kind": kind, "roster": len(members), "radius_km": radius, **by_basis})
    return {"id": inc.id, "title": title, "roster": len(members), "status": "open", **by_basis}


@router.patch("/incidents/{incident_id}/roster/{person_id}")
async def update_roster(incident_id: str, person_id: str, body: RosterUpdate, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    """One contact attempt. Every call is a ledger entry — this *is* the comms log."""
    inc = await one_or_404(session, IncidentRow, incident_id, "incident")
    if inc.status != "open":
        raise HTTPException(409, "incident is closed")
    row = (await session.execute(select(AccountabilityRow).where(AccountabilityRow.incident_id == incident_id, AccountabilityRow.person_id == person_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "person not on this roster")
    person = await one_or_404(session, PersonRow, person_id, "person")
    actor = actor_from(x_toc_actor)
    old = row.status
    row.status, row.method, row.note = body.status, body.method, body.note
    row.attempts += 1
    row.last_attempt_at = row.updated_at = now_utc()
    row.updated_by = actor
    await session.commit()
    await get_ledger().append_event(content_id=inc.id, event_type="cop.incident.contact", actor_type="human", actor_id=actor, old_state=old, new_state=body.status,
                                    reason=f"{person.name}: {body.status.upper()} via {body.method}" + (f" — {body.note}" if body.note else ""),
                                    metadata={"person_id": person_id, "attempt": row.attempts, "method": body.method})
    return {"incident_id": incident_id, "person_id": person_id, "status": row.status, "attempts": row.attempts}


@router.post("/incidents/{incident_id}/request-checkins")
async def request_checkins(incident_id: str, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    """Decision B: push a check-in request to everyone still unaccounted, at once. Work by exception afterwards.
    (Outbound delivery — SMS/app push — is the S6 LATER item; this records the request and arms the auto-clear.)"""
    inc = await one_or_404(session, IncidentRow, incident_id, "incident")
    if inc.status != "open":
        raise HTTPException(409, "incident is closed")
    rows = (await session.execute(select(AccountabilityRow).where(AccountabilityRow.incident_id == incident_id,
                                                                   AccountabilityRow.status.in_(("unaccounted", "unreachable"))))).scalars().all()
    now = now_utc()
    people = {p.id: p for p in (await session.execute(select(PersonRow).where(PersonRow.id.in_([r.person_id for r in rows])))).scalars()} if rows else {}
    dispatcher = Dispatcher()
    targets = [{"id": r.person_id, "name": people[r.person_id].name, "phone": people[r.person_id].phone} for r in rows if r.person_id in people]
    results = await dispatcher.request_checkins(inc.title, targets, lambda pid: f"{public_url()}/checkin/{checkin_token(pid, inc.id)}")
    summary = {"sms": {"sent": 0, "simulated": 0, "failed": 0}, "chat": {"sent": 0, "simulated": 0, "failed": 0}}
    for r in rows:
        r.checkin_requested_at = now
        for d in results.get(r.person_id, []):
            session.add(DeliveryRow(incident_id=inc.id, person_id=r.person_id, channel=d.channel, status=d.status, provider_id=d.provider_id, error=d.error, at=now))
            summary[d.channel][d.status] += 1
    await session.commit()
    actor = actor_from(x_toc_actor)
    sim = " (SIMULATED — no Twilio/Slack configured)" if dispatcher.simulated else ""
    await get_ledger().append_event(content_id=inc.id, event_type="cop.incident.checkins_requested", actor_type="human", actor_id=actor,
                                    reason=f"Check-in requested from {len(rows)} unaccounted via SMS + chat{sim}",
                                    metadata={"requested": len(rows), "deliveries": summary, "simulated": dispatcher.simulated})
    return {"incident_id": incident_id, "requested": len(rows), "deliveries": summary, "simulated": dispatcher.simulated}


@router.post("/checkin/{token}")
async def checkin_by_token(token: str, body: Optional[CheckIn] = None, session: AsyncSession = Depends(get_session)):
    """The link in the SMS / chat message. No auth — the token is the credential. Clears the person's roster
    row (Decision B). Position defaults to where the wall already has them if the reply carries no coordinates."""
    person_id, incident_id = parse_checkin_token(token)
    inc = await one_or_404(session, IncidentRow, incident_id, "incident")
    if inc.status != "open":
        raise HTTPException(409, "this roll call is closed")
    p = await one_or_404(session, PersonRow, person_id, "person")
    if body is None or body.lat is None:
        snap = await build_snapshot(session, include_restricted=True)
        me = next((x for x in snap["people"] if x["id"] == person_id), None)
        lat, lon = (me["lat"], me["lon"]) if me else (inc.lat, inc.lon)
        note = (body.note if body else None) or "Confirmed safe via check-in link"
    else:
        lat, lon, note = body.lat, body.lon, body.note or "Confirmed safe via check-in link"
    return await checkin(person_id, CheckIn(lat=lat, lon=lon, note=note), session, x_toc_actor=p.name)


@router.patch("/incidents/{incident_id}/close")
async def close_incident(incident_id: str, body: IncidentClose, session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    inc = await one_or_404(session, IncidentRow, incident_id, "incident")
    rows = (await session.execute(select(AccountabilityRow).where(AccountabilityRow.incident_id == incident_id))).scalars().all()
    open_count = sum(1 for r in rows if r.status in ("unaccounted", "unreachable"))
    inc.status, inc.closed_at = "closed", now_utc()
    if body.notes:
        inc.notes = body.notes
    await session.commit()
    await get_ledger().append_event(content_id=inc.id, event_type="cop.incident.closed", actor_type="human", actor_id=actor_from(x_toc_actor), old_state="open", new_state="closed",
                                    reason=f"Closed with {len(rows) - open_count}/{len(rows)} accounted" + (f"; {open_count} still unaccounted" if open_count else ""), metadata={"unaccounted": open_count})
    return {"id": inc.id, "status": "closed", "unaccounted": open_count}


# ---------------------------------------------------------------- S2 collection

@router.post("/intel/refresh")
async def intel_refresh(session: AsyncSession = Depends(get_session), x_toc_actor: Optional[str] = Header(None)):
    """Run the real Sigtoc collectors and upsert what they find. GDACS today."""
    from sigtoc.collectors.gdacs import collect_gdacs
    snap = await build_snapshot(session, include_restricted=True)
    points = [(l["lat"], l["lon"]) for l in snap["locations"]] + [(p["lat"], p["lon"]) for p in snap["people"] if p["status"] == "traveling"] \
             + [(e["venue_lat"], e["venue_lon"]) for e in snap["events"]]
    try:
        found = await collect_gdacs(points)
    except RuntimeError as e:
        await get_ledger().append_event(content_id="sigtoc", event_type="cop.intel.refresh_failed", actor_type="collector", actor_id="gdacs", reason=str(e))
        raise HTTPException(502, str(e))
    created = updated = 0
    for f in found:
        row = (await session.execute(select(ThreatRow).where(ThreatRow.external_id == f["external_id"]))).scalar_one_or_none()
        if row:
            for k in ("title", "summary", "lat", "lon", "radius_km", "severity", "observed_at", "url"):
                setattr(row, k, f[k])
            updated += 1
        else:
            session.add(ThreatRow(id=f"thr_{uuid.uuid4().hex[:8]}", synthetic=False, confidence="high", **f))
            created += 1
    await session.commit()
    await get_ledger().append_event(content_id="sigtoc", event_type="cop.intel.refresh", actor_type="collector", actor_id="gdacs",
                                    reason=f"GDACS: {created} new, {updated} updated", metadata={"created": created, "updated": updated, "collected": len(found)})
    return {"source": "gdacs", "collected": len(found), "created": created, "updated": updated}


@router.post("/seed")
async def seed(session: AsyncSession = Depends(get_session)):
    """Dev only: wipe and reload synthetic data."""
    await reseed(session)
    return {"status": "reseeded"}
