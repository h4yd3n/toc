"""§13 connectors, honestly: the real systems (Workday, Okta, Concur, Google Calendar, badge readers, guard scheduling)
are reached through their exports. Each adapter takes what those systems produce — CSV, ICS, a JSON event stream —
and writes rows with provenance, so the wall always knows where a fact came from. OAuth connectors are the next step
and need accounts this repository does not have."""
import csv
import io
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db_models import EventAttendeeRow, EventRow, LocationRow, PersonRow, TeamRow, TripRow


def _bool(v: Optional[str]) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes", "y", "on")

def _dt(v: Optional[str]) -> Optional[datetime]:
    if not v: return None
    v = v.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d"):
        try: return datetime.strptime(v, fmt)
        except ValueError: pass
    try: return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError: return None

def rows_of(text: str) -> List[Dict[str, str]]:
    return [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(io.StringIO(text.strip()))]


async def _people_index(session: AsyncSession) -> Tuple[Dict[str, PersonRow], Dict[str, PersonRow]]:
    people = (await session.execute(select(PersonRow))).scalars().all()
    return {p.id: p for p in people}, {p.email.lower(): p for p in people if p.email}


def _find(by_id: Dict[str, PersonRow], by_email: Dict[str, PersonRow], r: Dict[str, str]) -> Optional[PersonRow]:
    return by_id.get(r.get("id") or r.get("person_id") or "") or by_email.get((r.get("email") or "").lower())


async def import_people(session: AsyncSession, text: str, source: str = "hris:csv") -> Dict[str, Any]:
    """HRIS / directory export. Columns: id?, name, role, team_id (or team_name), is_vip?, phone?, email?. Upsert by id, then email."""
    by_id, by_email = await _people_index(session)
    teams = {t.id: t for t in (await session.execute(select(TeamRow))).scalars()}
    by_team_name = {t.name.lower(): t for t in teams.values()}
    created = updated = skipped = 0; errors: List[str] = []
    for i, r in enumerate(rows_of(text), 1):
        team = teams.get(r.get("team_id") or "") or by_team_name.get((r.get("team_name") or "").lower())
        if not r.get("name") or not team:
            skipped += 1; errors.append(f"row {i}: needs name and a known team_id or team_name"); continue
        p = _find(by_id, by_email, r)
        if p:
            p.name, p.role, p.team_id = r["name"], r.get("role") or p.role, team.id
            if r.get("is_vip") != "": p.is_vip = _bool(r.get("is_vip"))
            p.phone, p.email, p.source = r.get("phone") or p.phone, r.get("email") or p.email, source
            updated += 1
        else:
            p = PersonRow(id=r.get("id") or f"p_imp_{uuid.uuid4().hex[:6]}", name=r["name"], role=r.get("role") or "", team_id=team.id, is_vip=_bool(r.get("is_vip")),
                          phone=r.get("phone") or None, email=r.get("email") or None, source=source)
            session.add(p); by_id[p.id] = p
            if p.email: by_email[p.email.lower()] = p
            created += 1
    await session.commit()
    return {"kind": "people", "source": source, "created": created, "updated": updated, "skipped": skipped, "errors": errors[:20]}


async def import_shifts(session: AsyncSession, text: str, source: str = "scheduling:csv") -> Dict[str, Any]:
    """Guard-force schedule export. Columns: id or email, on_shift, shift_role?."""
    by_id, by_email = await _people_index(session)
    updated = skipped = 0; errors: List[str] = []
    for i, r in enumerate(rows_of(text), 1):
        p = _find(by_id, by_email, r)
        if not p: skipped += 1; errors.append(f"row {i}: unknown person"); continue
        p.on_shift = _bool(r.get("on_shift")); p.shift_role = r.get("shift_role") or p.shift_role; updated += 1
    await session.commit()
    return {"kind": "shifts", "source": source, "updated": updated, "skipped": skipped, "errors": errors[:20]}


async def import_trips(session: AsyncSession, text: str, actor: str, source: str = "travel_system:csv") -> Dict[str, Any]:
    """Travel system export. Columns: id or email, origin_location_id, dest_location_id | dest_name + dest_lat + dest_lon, depart_at, return_at, purpose?, booking_ref?."""
    by_id, by_email = await _people_index(session)
    locs = {l.id: l for l in (await session.execute(select(LocationRow))).scalars()}
    existing = {t.id for t in (await session.execute(select(TripRow))).scalars()}
    created = updated = skipped = 0; errors: List[str] = []
    for i, r in enumerate(rows_of(text), 1):
        p = _find(by_id, by_email, r)
        origin = locs.get(r.get("origin_location_id") or "")
        dest = locs.get(r.get("dest_location_id") or "")
        dep, ret = _dt(r.get("depart_at")), _dt(r.get("return_at"))
        if not p or not origin or not dep or not ret or ret <= dep or not (dest or (r.get("dest_name") and r.get("dest_lat") and r.get("dest_lon"))):
            skipped += 1; errors.append(f"row {i}: needs a known person, origin_location_id, a destination, and depart_at < return_at"); continue
        tid = f"trip_{r['booking_ref']}" if r.get("booking_ref") else f"trip_imp_{uuid.uuid4().hex[:6]}"
        row = await session.get(TripRow, tid) if tid in existing else None
        vals = dict(person_id=p.id, origin_location_id=origin.id, dest_location_id=dest.id if dest else None, dest_name=dest.name if dest else r["dest_name"],
                    dest_lat=dest.lat if dest else float(r["dest_lat"]), dest_lon=dest.lon if dest else float(r["dest_lon"]), depart_at=dep, return_at=ret, purpose=r.get("purpose") or "", created_by=actor, source=source)
        if row:
            for k, v in vals.items(): setattr(row, k, v)
            updated += 1
        else:
            session.add(TripRow(id=tid, **vals)); existing.add(tid); created += 1
    await session.commit()
    return {"kind": "trips", "source": source, "created": created, "updated": updated, "skipped": skipped, "errors": errors[:20]}


def parse_ics(text: str) -> List[Dict[str, Any]]:
    """Enough of RFC 5545 for a calendar export: VEVENTs with SUMMARY, LOCATION, GEO, DTSTART/DTEND, DESCRIPTION, ATTENDEE mailto."""
    text = re.sub(r"\r?\n[ \t]", "", text)  # unfold continuation lines
    out = []
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
        ev: Dict[str, Any] = {"attendees": []}
        for line in block.strip().splitlines():
            if ":" not in line: continue
            head, _, value = line.partition(":")
            name = head.split(";")[0].upper()
            if name == "SUMMARY": ev["summary"] = value.strip()
            elif name == "LOCATION": ev["location"] = value.replace("\\,", ",").strip()
            elif name == "DESCRIPTION": ev["description"] = value.replace("\\n", " ").replace("\\,", ",").strip()
            elif name == "UID": ev["uid"] = value.strip()
            elif name == "GEO":
                try: ev["lat"], ev["lon"] = (float(x) for x in value.split(";"))
                except ValueError: pass
            elif name in ("DTSTART", "DTEND"): ev[name.lower()] = _dt(value.strip())
            elif name == "ATTENDEE":
                m = re.search(r"mailto:([^\s;]+)", value, re.I)
                if m: ev["attendees"].append(m.group(1).lower())
                if "mailto:" not in value.lower() and "@" in value: ev["attendees"].append(value.strip().lower())
        if ev.get("summary") and ev.get("dtstart"): out.append(ev)
    return out


async def import_ics(session: AsyncSession, text: str, actor: str, source: str = "calendar:ics") -> Dict[str, Any]:
    """Calendar export → events with attendees (matched by email) and generated trips. A venue is a known site by name,
    or a GEO property, or 'lat,lon' in LOCATION; anything else is reported, not guessed."""
    from .seed import generate_event_trips
    by_id, by_email = await _people_index(session)
    locs = (await session.execute(select(LocationRow))).scalars().all()
    teams = {t.id: t for t in (await session.execute(select(TeamRow))).scalars()}
    team_loc = {t.id: t.location_id for t in teams.values()}
    created = updated = skipped = 0; errors: List[str] = []; trips = 0
    for ev in parse_ics(text):
        loc = next((l for l in locs if ev.get("location") and (l.name.lower() in ev["location"].lower() or ev["location"].lower() in l.name.lower())), None)
        lat, lon = ev.get("lat"), ev.get("lon")
        if not loc and lat is None:
            m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", ev.get("location") or "")
            if m: lat, lon = float(m.group(1)), float(m.group(2))
        if not loc and lat is None:
            skipped += 1; errors.append(f"{ev['summary']}: venue '{ev.get('location') or ''}' is not a known site and carries no coordinates"); continue
        eid = f"evt_{re.sub(r'[^A-Za-z0-9]', '', ev.get('uid') or ev['summary'])[:16].lower()}"
        end = ev.get("dtend") or ev["dtstart"]
        row = await session.get(EventRow, eid)
        vals = dict(name=ev["summary"], event_type="calendar", venue_location_id=loc.id if loc else None, venue_name=loc.name if loc else (ev.get("location") or "venue"),
                    venue_lat=loc.lat if loc else lat, venue_lon=loc.lon if loc else lon, start_at=ev["dtstart"], end_at=end, description=ev.get("description") or "", created_by=actor, source=source)
        if row:
            for k, v in vals.items(): setattr(row, k, v)
            updated += 1
        else:
            row = EventRow(id=eid, **vals); session.add(row); created += 1
        await session.flush()
        attendees = [by_email[e].id for e in ev["attendees"] if e in by_email]
        have = {a.person_id for a in (await session.execute(select(EventAttendeeRow).where(EventAttendeeRow.event_id == eid))).scalars()}
        new_att = [a for a in attendees if a not in have]
        session.add_all([EventAttendeeRow(event_id=eid, person_id=a) for a in new_att])
        gen = generate_event_trips(row, new_att, by_id, team_loc, created_by=actor)
        session.add_all(gen); trips += len(gen)
        unknown = [e for e in ev["attendees"] if e not in by_email]
        if unknown: errors.append(f"{ev['summary']}: {len(unknown)} attendee(s) not in the directory: {', '.join(unknown[:3])}")
    await session.commit()
    return {"kind": "events", "source": source, "created": created, "updated": updated, "skipped": skipped, "trips_generated": trips, "errors": errors[:20]}


async def import_badge(session: AsyncSession, events: List[Dict[str, Any]], source: str = "badge") -> Dict[str, Any]:
    """Badge reader stream: [{person_id | email, location_id, at, direction: in|out}]. A badge-in is a check-in at the
    site (Decision 2: it overrides the derived position for 12 h); a badge-out records the note only."""
    by_id, by_email = await _people_index(session)
    locs = {l.id: l for l in (await session.execute(select(LocationRow))).scalars()}
    applied = skipped = 0; errors: List[str] = []
    for i, e in enumerate(events, 1):
        p = _find(by_id, by_email, {k: str(v) for k, v in e.items() if v is not None})
        loc = locs.get(e.get("location_id") or "")
        at = _dt(e.get("at")) or datetime.now(timezone.utc).replace(tzinfo=None)
        if not p or not loc: skipped += 1; errors.append(f"event {i}: unknown person or site"); continue
        if (e.get("direction") or "in").lower() == "in":
            p.last_checkin_lat, p.last_checkin_lon, p.last_checkin_at, p.last_checkin_note = loc.lat, loc.lon, at, f"Badge in — {loc.name} ({source})"
        else:
            p.last_checkin_note = f"Badge out — {loc.name} ({source})"; p.last_checkin_at = at
        applied += 1
    await session.commit()
    return {"kind": "badge", "source": source, "applied": applied, "skipped": skipped, "errors": errors[:20]}
