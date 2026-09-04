"""Derives the COP snapshot. Positions, presence, counts, threat suggestions, and effective posture
are computed here, never stored. Three decisions are encoded and labeled below."""
import json
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db_models import LedgerEventRow
from .watch import current_watch, estimates as section_estimates, get_config, watch_summary
from .db_models import (AccountabilityRow, AssessmentRow, DeliveryRow, EventAttendeeRow, EventRow, IncidentRow, LocationRow, PersonRow, PIRRow,
                        TeamRow, ThreatLinkRow, ThreatRow, TripRow)

SEVERITY_RANK = {"low": 0, "moderate": 1, "elevated": 2, "critical": 3}
POSTURE_RANK = {"normal": 0, "elevated": 1, "critical": 2}
POSTURES = ["normal", "elevated", "critical"]
# Decision 3: only a *confirmed* link changes posture. Severity → posture it forces.
SEVERITY_TO_POSTURE = {"low": "normal", "moderate": "elevated", "elevated": "critical", "critical": "critical"}
# Decision 2: a check-in this recent overrides the derived position.
CHECKIN_FRESH_HOURS = 12
# Decision 3: proximity *suggests*. A point is "in area" inside the threat radius plus this buffer.
PROXIMITY_BUFFER_KM = 5.0
# Decision C: only these roles may see the restricted layer (residences).
RESTRICTED_ROLES = {"battle_captain", "ep"}


def may_see_restricted(role: Optional[str]) -> bool:
    return (role or "").lower() in RESTRICTED_ROLES


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

def trip_status(t: TripRow, now: datetime) -> str:
    if t.return_at <= now:
        return "complete"
    if t.depart_at <= now:
        return "active"
    return "planned"

def event_status(e: EventRow, now: datetime) -> str:
    if e.end_at <= now:
        return "past"
    if e.start_at <= now:
        return "active"
    return "upcoming"


async def build_snapshot(session: AsyncSession, include_restricted: bool = False, log_limit: int = 40) -> Dict[str, Any]:
    now = now_utc()
    locations = (await session.execute(select(LocationRow))).scalars().all()
    teams = (await session.execute(select(TeamRow))).scalars().all()
    people = (await session.execute(select(PersonRow))).scalars().all()
    trips = (await session.execute(select(TripRow))).scalars().all()
    threats = (await session.execute(select(ThreatRow))).scalars().all()
    links = (await session.execute(select(ThreatLinkRow))).scalars().all()
    events = (await session.execute(select(EventRow))).scalars().all()
    attendees = (await session.execute(select(EventAttendeeRow))).scalars().all()
    pirs = (await session.execute(select(PIRRow))).scalars().all()
    assessments = (await session.execute(select(AssessmentRow))).scalars().all()
    incidents = (await session.execute(select(IncidentRow))).scalars().all()
    roster_rows = (await session.execute(select(AccountabilityRow))).scalars().all()
    delivery_rows = (await session.execute(select(DeliveryRow).order_by(DeliveryRow.id))).scalars().all()

    # Decision 1: restricted sites leave the payload entirely unless the caller is cleared.
    if not include_restricted:
        locations = [l for l in locations if l.sensitivity != "restricted"]
    loc_by_id = {l.id: l for l in locations}
    team_by_id = {t.id: t for t in teams}
    active_trip_by_person = {t.person_id: t for t in trips if trip_status(t, now) == "active"}
    confirmed = {}  # (target_type, target_id) -> [link]
    for lk in links:
        confirmed.setdefault((lk.target_type, lk.target_id), []).append(lk)
    threat_by_id = {t.id: t for t in threats}

    counts = {l.id: {"assigned": 0, "present": 0, "security_on_shift": 0, "vips_present": 0} for l in locations}
    people_out: List[Dict[str, Any]] = []
    for p in people:
        team = team_by_id[p.team_id]
        home = loc_by_id.get(team.location_id)
        if home is None:  # home is a restricted site the caller can't see — should not happen with seed data
            continue
        counts[home.id]["assigned"] += 1
        trip = active_trip_by_person.get(p.id)
        # Derived position first (Decision 2)
        if trip:
            lat, lon, status, loc_id = trip.dest_lat, trip.dest_lon, "traveling", trip.dest_location_id
        else:
            lat, lon, status, loc_id = home.lat, home.lon, "at_post", home.id
        position_source, checkin_age_h, checkin_stale = "derived", None, False
        if p.last_checkin_at:
            age = (now - p.last_checkin_at).total_seconds() / 3600
            checkin_age_h = round(age, 1)
            if age <= CHECKIN_FRESH_HOURS:
                lat, lon, position_source = p.last_checkin_lat, p.last_checkin_lon, "checkin"
            else:
                checkin_stale = True
        if status == "traveling":
            if loc_id and loc_id in counts:
                counts[loc_id]["present"] += 1
                if p.is_vip:
                    counts[loc_id]["vips_present"] += 1
        else:
            counts[home.id]["present"] += 1
            if p.is_vip:
                counts[home.id]["vips_present"] += 1
            if team.is_security and p.on_shift:
                counts[home.id]["security_on_shift"] += 1
        my_links = confirmed.get(("person", p.id), [])
        people_out.append({
            "id": p.id, "name": p.name, "role": p.role, "team_id": team.id, "team_name": team.name,
            "home_location_id": home.id, "location_id": loc_id, "is_vip": p.is_vip,
            "on_shift": p.on_shift, "shift_role": p.shift_role, "status": status,
            "lat": lat, "lon": lon, "trip_id": trip.id if trip else None,
            "position_source": position_source, "checkin_age_h": checkin_age_h, "checkin_stale": checkin_stale,
            "last_checkin_at": iso(p.last_checkin_at), "last_checkin_note": p.last_checkin_note,
            "phone": p.phone, "email": p.email, "source": p.source, "incident_status": None,
            "availability": ("on_shift" if p.on_shift else "off_duty") if team.is_security else "available",  # refined below: an open roll call can make anyone unreachable
            "threat_ids_in_area": [], "confirmed_threat_ids": [lk.threat_id for lk in my_links],
        })

    # Decision 3: proximity suggests. Compute "in area" for every site and every person.
    locations_out = []
    for l in locations:
        in_area = [t.id for t in threats if haversine_km(l.lat, l.lon, t.lat, t.lon) <= t.radius_km + PROXIMITY_BUFFER_KM]
        my_links = confirmed.get(("location", l.id), [])
        forced = max((POSTURE_RANK[SEVERITY_TO_POSTURE[threat_by_id[lk.threat_id].severity]] for lk in my_links if lk.threat_id in threat_by_id), default=0)
        effective = POSTURES[max(POSTURE_RANK[l.posture], forced)]
        locations_out.append({
            "id": l.id, "name": l.name, "type": l.type, "lat": l.lat, "lon": l.lon, "city": l.city,
            "country": l.country, "posture": l.posture, "effective_posture": effective, "sensitivity": l.sensitivity,
            "threat_ids_in_area": in_area, "confirmed_threat_ids": [lk.threat_id for lk in my_links],
            **counts[l.id],
        })
    for po in people_out:
        po["threat_ids_in_area"] = [t.id for t in threats if haversine_km(po["lat"], po["lon"], t.lat, t.lon) <= t.radius_km + PROXIMITY_BUFFER_KM]

    teams_out = [{"id": t.id, "name": t.name, "location_id": t.location_id, "function": t.function,
                  "is_security": t.is_security} for t in teams if t.location_id in loc_by_id]

    person_by_id = {p["id"]: p for p in people_out}
    trips_out = []
    for t in sorted(trips, key=lambda x: x.depart_at):
        st = trip_status(t, now)
        if st == "complete" or t.person_id not in person_by_id:
            continue
        o = loc_by_id.get(t.origin_location_id)
        trips_out.append({
            "id": t.id, "person_id": t.person_id, "person_name": person_by_id[t.person_id]["name"],
            "is_vip": person_by_id[t.person_id]["is_vip"],
            "origin_location_id": t.origin_location_id, "origin_name": o.name if o else "—",
            "origin_lat": o.lat if o else t.dest_lat, "origin_lon": o.lon if o else t.dest_lon,
            "dest_location_id": t.dest_location_id, "dest_name": t.dest_name, "dest_lat": t.dest_lat, "dest_lon": t.dest_lon,
            "depart_at": iso(t.depart_at), "return_at": iso(t.return_at), "purpose": t.purpose, "status": st,
            "event_id": t.event_id, "created_by": t.created_by, "source": t.source,
        })

    att_by_event: Dict[str, List[str]] = {}
    for a in attendees:
        att_by_event.setdefault(a.event_id, []).append(a.person_id)
    trips_by_event: Dict[str, int] = {}
    for t in trips:
        if t.event_id:
            trips_by_event[t.event_id] = trips_by_event.get(t.event_id, 0) + 1
    events_out = []
    for e in sorted(events, key=lambda x: x.start_at):
        st = event_status(e, now)
        if st == "past":
            continue
        ids = [i for i in att_by_event.get(e.id, []) if i in person_by_id]
        events_out.append({
            "id": e.id, "name": e.name, "event_type": e.event_type, "venue_location_id": e.venue_location_id,
            "venue_name": e.venue_name, "venue_lat": e.venue_lat, "venue_lon": e.venue_lon,
            "start_at": iso(e.start_at), "end_at": iso(e.end_at), "status": st,
            "days_until": max(0, (e.start_at - now).days), "description": e.description, "security_plan": e.security_plan,
            "attendee_ids": ids, "attendee_count": len(ids),
            "vip_count": sum(1 for i in ids if person_by_id[i]["is_vip"]),
            "security_count": sum(1 for i in ids if team_by_id[people_by_id_row(people, i).team_id].is_security),
            "trips_generated": trips_by_event.get(e.id, 0), "source": e.source,
            "threat_ids_in_area": [t.id for t in threats if haversine_km(e.venue_lat, e.venue_lon, t.lat, t.lon) <= t.radius_km + PROXIMITY_BUFFER_KM],
        })

    links_by_threat: Dict[str, List[Dict[str, Any]]] = {}
    for lk in links:
        name = (loc_by_id[lk.target_id].name if lk.target_type == "location" and lk.target_id in loc_by_id
                else person_by_id[lk.target_id]["name"] if lk.target_type == "person" and lk.target_id in person_by_id else None)
        if name is None:
            continue
        links_by_threat.setdefault(lk.threat_id, []).append({
            "link_id": lk.id, "target_type": lk.target_type, "target_id": lk.target_id, "target_name": name,
            "confirmed_by": lk.confirmed_by, "confirmed_at": iso(lk.confirmed_at), "note": lk.note})
    threats_out = []
    for th in sorted(threats, key=lambda x: (-SEVERITY_RANK[x.severity], x.observed_at), reverse=False):
        suggested = ([{"target_type": "location", "target_id": l["id"], "target_name": l["name"]} for l in locations_out if th.id in l["threat_ids_in_area"]] +
                     [{"target_type": "person", "target_id": p["id"], "target_name": p["name"]} for p in people_out if th.id in p["threat_ids_in_area"]])
        threats_out.append({
            "id": th.id, "external_id": th.external_id, "title": th.title, "summary": th.summary, "lat": th.lat, "lon": th.lon,
            "radius_km": th.radius_km, "severity": th.severity, "event_type": th.event_type, "source": th.source, "url": th.url,
            "confidence": th.confidence, "observed_at": iso(th.observed_at), "synthetic": th.synthetic,
            "suggested_targets": suggested, "confirmed_links": links_by_threat.get(th.id, []),
        })
    threats_out.sort(key=lambda t: -SEVERITY_RANK[t["severity"]])

    pirs_out = [{"id": p.id, "question": p.question, "status": p.status, "owner": p.owner, "priority": p.priority,
                 "subject_type": p.subject_type, "subject_id": p.subject_id, "created_at": iso(p.created_at), "expires_at": iso(p.expires_at)}
                for p in sorted(pirs, key=lambda x: (x.status == "ANSWERED" or x.status == "EXPIRED", x.priority, x.created_at))]
    assessments_out = [{
        "id": a.id, "title": a.title, "subject_type": a.subject_type, "subject_id": a.subject_id,
        "likelihood": a.likelihood, "band": a.band, "confidence": a.confidence, "bluf": a.bluf,
        "key_judgments": json.loads(a.key_judgments_json or "[]"), "evidence": json.loads(a.evidence_json or "[]"),
        "gaps": json.loads(a.gaps_json or "[]"), "author": a.author, "status": a.status,
        "created_at": iso(a.created_at), "approved_by": a.approved_by, "approved_at": iso(a.approved_at),
    } for a in sorted(assessments, key=lambda x: x.created_at, reverse=True) if a.status != "superseded"]

    # S6 — accountability. Open incidents (and anything closed in the last 24h) with roster progress.
    roster_by_incident: Dict[str, List[AccountabilityRow]] = {}
    for r in roster_rows:
        roster_by_incident.setdefault(r.incident_id, []).append(r)
    deliveries: Dict[tuple, List[Dict[str, Any]]] = {}
    for d in delivery_rows:
        deliveries.setdefault((d.incident_id, d.person_id), []).append({"channel": d.channel, "status": d.status, "at": iso(d.at), "error": d.error})
    from .operations import load_all as load_operations
    operations_out = [{k: o[k] for k in ("id", "title", "subject_type", "subject_id", "subject_name", "status", "tasks_total", "tasks_done", "blocked", "resources_open", "pct", "from_product_type", "from_product_id", "opened_by")}
                      for o in await load_operations(session) if o["status"] in ("planned", "active")]
    op_by_subject = {(o["subject_type"], o["subject_id"]): o for o in operations_out}
    for e in events_out: e["operation"] = op_by_subject.get(("event", e["id"]))
    for t in trips_out: t["operation"] = op_by_subject.get(("trip", t["id"]))
    from sigtoc.warning import WarningRow, to_dict as warning_dict
    warnings_out = [warning_dict(w, now) for w in (await session.execute(select(WarningRow).where(WarningRow.status.in_(("suggested", "draft", "released"))).order_by(WarningRow.created_at.desc()))).scalars()]
    incidents_out = []
    for inc in sorted(incidents, key=lambda x: x.opened_at, reverse=True):
        if inc.status == "closed" and inc.closed_at and (now - inc.closed_at).total_seconds() > 86400:
            continue
        rows = roster_by_incident.get(inc.id, [])
        rc = {k: 0 for k in ("unaccounted", "contacted", "safe", "injured", "assist", "unreachable")}
        roster = []
        for r in rows:
            rc[r.status] = rc.get(r.status, 0) + 1
            pp = person_by_id.get(r.person_id)
            if pp and inc.status == "open":
                pp["incident_status"] = r.status
            roster.append({"person_id": r.person_id, "name": pp["name"] if pp else r.person_id, "role": pp["role"] if pp else "",
                           "is_vip": pp["is_vip"] if pp else False, "phone": pp["phone"] if pp else None, "email": pp["email"] if pp else None,
                           "status": r.status, "basis": r.basis, "checkin_requested_at": iso(r.checkin_requested_at),
                           "deliveries": deliveries.get((inc.id, r.person_id), []),
                           "method": r.method, "attempts": r.attempts, "last_attempt_at": iso(r.last_attempt_at),
                           "updated_by": r.updated_by, "updated_at": iso(r.updated_at), "note": r.note})
        order = {"unreachable": 0, "assist": 1, "injured": 2, "unaccounted": 3, "contacted": 4, "safe": 5}  # Decision M: escalated names float to the top
        roster.sort(key=lambda r: (order[r["status"]], not r["is_vip"], r["name"]))
        accounted = rc["safe"] + rc["contacted"] + rc["injured"] + rc["assist"]
        requested = sum(1 for r in rows if r.checkin_requested_at)
        dsum: Dict[str, Dict[str, int]] = {"sms": {"sent": 0, "simulated": 0, "failed": 0}, "chat": {"sent": 0, "simulated": 0, "failed": 0}}
        for r in rows:
            for d in deliveries.get((inc.id, r.person_id), []):
                dsum.setdefault(d["channel"], {"sent": 0, "simulated": 0, "failed": 0})[d["status"]] += 1
        incidents_out.append({
            "id": inc.id, "title": inc.title, "kind": inc.kind, "location_id": inc.location_id, "threat_id": inc.threat_id,
            "lat": inc.lat, "lon": inc.lon, "radius_km": inc.radius_km, "status": inc.status, "opened_by": inc.opened_by,
            "opened_at": iso(inc.opened_at), "closed_at": iso(inc.closed_at), "notes": inc.notes,
            "total": len(rows), "accounted": accounted, "pct": round(100 * accounted / len(rows)) if rows else 100, "counts": rc, "checkins_requested": requested,
            "channels": ["sms", "chat"], "delivery_summary": dsum, "roster": roster,
        })

    log_rows = (await session.execute(select(LedgerEventRow).where(LedgerEventRow.event_type.like("cop.%") | LedgerEventRow.event_type.like("s2.%"))
                                      .order_by(LedgerEventRow.id.desc()).limit(log_limit))).scalars().all()
    log_out = [{"id": r.event_id, "at": iso(r.timestamp), "type": r.event_type, "actor": r.actor_id, "actor_type": r.actor_type,
                "subject": r.content_id, "old": r.old_state, "new": r.new_state, "summary": r.reason,
                "meta": json.loads(r.metadata_json or "{}")} for r in log_rows]

    worst_loc = max((POSTURE_RANK[l["effective_posture"]] for l in locations_out), default=0)
    for pp in people_out:  # §4: unreachable is a state of its own — a roll call that cannot reach you, or a stale check-in while traveling
        if pp["incident_status"] == "unreachable" or (pp["status"] == "traveling" and pp["checkin_stale"] and pp["last_checkin_at"]):
            pp["availability"] = "unreachable"
    summary = {
        "total_people": len(people_out),
        "present": sum(1 for p in people_out if p["status"] == "at_post"),
        "traveling": sum(1 for p in people_out if p["status"] == "traveling"),
        "vips_traveling": sum(1 for p in people_out if p["status"] == "traveling" and p["is_vip"]),
        "security_on_shift": sum(c["security_on_shift"] for c in counts.values()),
        "active_threats": len(threats_out),
        "real_threats": sum(1 for t in threats_out if not t["synthetic"]),
        "confirmed_links": len(links),
        "checked_in_fresh": sum(1 for p in people_out if p["position_source"] == "checkin"),
        "open_pirs": sum(1 for p in pirs_out if p["status"] in ("OPEN", "COLLECTING")),
        "off_duty": sum(1 for p in people_out if p["availability"] == "off_duty"), "unreachable": sum(1 for p in people_out if p["availability"] == "unreachable"),
        "flash": sum(1 for w in warnings_out if w["status"] == "released"), "warnings_pending": sum(1 for w in warnings_out if w["status"] in ("suggested", "draft")),
        "open_incidents": sum(1 for i in incidents_out if i["status"] == "open"),
        "unaccounted": sum(i["counts"]["unaccounted"] + i["counts"]["unreachable"] for i in incidents_out if i["status"] == "open"),
        "upcoming_events": len(events_out),
        "posture": POSTURES[worst_loc],
    }
    cfg = await get_config(session)
    wrow = await current_watch(session, now)
    return {
        "generated_at": iso(now), "restricted_included": include_restricted, "summary": summary, "warnings": warnings_out,
        "watch": watch_summary(wrow, now, cfg), "estimates": await section_estimates(session),
        "locations": locations_out, "teams": teams_out, "people": people_out, "trips": trips_out,
        "events": events_out, "threats": threats_out, "pirs": pirs_out, "assessments": assessments_out, "incidents": incidents_out, "log": log_out,
        "operations": operations_out,
    }


def people_by_id_row(people: List[PersonRow], pid: str) -> PersonRow:
    return next(p for p in people if p.id == pid)
