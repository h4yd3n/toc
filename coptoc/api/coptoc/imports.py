"""§13 connectors, honestly: the real systems (Workday, Okta, Concur, Google Calendar, badge readers, guard scheduling)
are reached through their exports. Each adapter takes what those systems produce — CSV, ICS, a JSON event stream —
and writes rows with provenance, so the wall always knows where a fact came from. OAuth connectors are the next step
and need accounts this repository does not have."""
import csv
import io
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db_models import EventAttendeeRow, EventRow, LocationRow, PersonRow, TeamRow, TripLegRow, TripRow


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


# IATA codes the pasted-itinerary parser can place. Anything else is reported, never guessed (§5.5 discipline applied to S3).
AIRPORTS: Dict[str, Tuple[str, float, float]] = {
    "SFO": ("San Francisco SFO", 37.6213, -122.3790), "SJC": ("San Jose SJC", 37.3639, -121.9289), "OAK": ("Oakland OAK", 37.7126, -122.2197),
    "LAX": ("Los Angeles LAX", 33.9416, -118.4085), "SEA": ("Seattle SEA", 47.4502, -122.3088), "DEN": ("Denver DEN", 39.8561, -104.6737),
    "ORD": ("Chicago O'Hare ORD", 41.9742, -87.9073), "DFW": ("Dallas DFW", 32.8998, -97.0403), "ATL": ("Atlanta ATL", 33.6407, -84.4277),
    "JFK": ("New York JFK", 40.6413, -73.7781), "EWR": ("Newark EWR", 40.6895, -74.1745), "LGA": ("New York LaGuardia LGA", 40.7769, -73.8740),
    "BOS": ("Boston BOS", 42.3656, -71.0096), "IAD": ("Washington Dulles IAD", 38.9531, -77.4565), "DCA": ("Washington Reagan DCA", 38.8512, -77.0402),
    "MIA": ("Miami MIA", 25.7959, -80.2870), "YYZ": ("Toronto Pearson YYZ", 43.6777, -79.6248), "MEX": ("Mexico City MEX", 19.4363, -99.0721),
    "LHR": ("London Heathrow LHR", 51.4700, -0.4543), "LGW": ("London Gatwick LGW", 51.1537, -0.1821), "CDG": ("Paris CDG", 49.0097, 2.5479),
    "AMS": ("Amsterdam AMS", 52.3105, 4.7683), "FRA": ("Frankfurt FRA", 50.0379, 8.5622), "MUC": ("Munich MUC", 48.3538, 11.7861),
    "ZRH": ("Zurich ZRH", 47.4647, 8.5492), "MAD": ("Madrid MAD", 40.4983, -3.5676), "DUB": ("Dublin DUB", 53.4264, -6.2499),
    "IST": ("Istanbul IST", 41.2753, 28.7519), "DXB": ("Dubai DXB", 25.2532, 55.3657), "DOH": ("Doha DOH", 25.2731, 51.6081),
    "RUH": ("Riyadh RUH", 24.9576, 46.6988), "JED": ("Jeddah JED", 21.6796, 39.1565), "TLV": ("Tel Aviv TLV", 32.0055, 34.8854),
    "JNB": ("Johannesburg JNB", -26.1367, 28.2411), "NBO": ("Nairobi NBO", -1.3192, 36.9278), "CAI": ("Cairo CAI", 30.1219, 31.4056),
    "DEL": ("Delhi DEL", 28.5562, 77.1000), "BOM": ("Mumbai BOM", 19.0896, 72.8656), "BLR": ("Bengaluru BLR", 13.1989, 77.7068),
    "SIN": ("Singapore SIN", 1.3644, 103.9915), "KUL": ("Kuala Lumpur KUL", 2.7456, 101.7099), "BKK": ("Bangkok BKK", 13.6900, 100.7501),
    "HKG": ("Hong Kong HKG", 22.3080, 113.9185), "TPE": ("Taipei TPE", 25.0797, 121.2342), "ICN": ("Seoul Incheon ICN", 37.4602, 126.4407),
    "HND": ("Tokyo Haneda HND", 35.5494, 139.7798), "NRT": ("Tokyo Narita NRT", 35.7720, 140.3929), "PVG": ("Shanghai Pudong PVG", 31.1443, 121.8083),
    "PEK": ("Beijing PEK", 40.0799, 116.6031), "SYD": ("Sydney SYD", -33.9399, 151.1753), "MEL": ("Melbourne MEL", -37.6690, 144.8410),
    "AKL": ("Auckland AKL", -37.0082, 174.7850), "GRU": ("São Paulo GRU", -23.4356, -46.4731), "EZE": ("Buenos Aires EZE", -34.8222, -58.5358),
    "BOG": ("Bogotá BOG", 4.7016, -74.1469), "LIM": ("Lima LIM", -12.0219, -77.1143), "SCL": ("Santiago SCL", -33.3930, -70.7858),
}

LEG_KINDS = {"flight": "flight", "fly": "flight", "air": "flight", "hotel": "lodging", "lodging": "lodging", "stay": "lodging",
             "ground": "ground", "car": "ground", "train": "ground", "rail": "ground", "transfer": "ground"}


def _place(token: str) -> Optional[Tuple[str, float, float]]:
    """An IATA code or an explicit @lat,lon[:name]. None for anything else — unknown places are reported, not guessed."""
    t = token.strip()
    if t.upper() in AIRPORTS: return AIRPORTS[t.upper()]
    m = re.fullmatch(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)(?::(.+))?", t)
    if m: return (m.group(3) or f"{m.group(1)},{m.group(2)}", float(m.group(1)), float(m.group(2)))
    return None


_ITIN = re.compile(r"^(?P<kind>[A-Za-z]+)\s+(?P<body>.+?)\s+(?P<start>\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?Z?)?)\s*(?:-|–|→|to)\s*(?P<end>\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?Z?)?)(?:\s+conf\s+(?P<ref>\S+))?\s*$", re.I)


def parse_itinerary(text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """One leg per line, the way a confirmation reads when pasted:
        FLIGHT UA 954 SFO-LHR 2026-09-04 18:10 - 2026-09-05 12:25 conf K7X2ZQ
        FLIGHT BA 263 LHR-RUH 2026-09-05T15:00Z → 2026-09-05T23:20Z
        HOTEL Ritz-Carlton Riyadh @24.6905,46.6250 2026-09-05 - 2026-09-08 conf 88112
        GROUND Car service RUH-@24.6905,46.6250:hotel 2026-09-05 23:40 - 2026-09-06 00:30
    Places are IATA codes from the table above or @lat,lon[:name]. Everything else is reported, never guessed."""
    legs, errors = [], []
    for n, raw in enumerate((l for l in text.splitlines() if l.strip()), 1):
        m = _ITIN.match(raw.strip())
        kind = LEG_KINDS.get(m.group("kind").lower()) if m else None
        start, end = (_dt(m.group("start")), _dt(m.group("end"))) if m else (None, None)
        if not m or not kind or not start or not end or end <= start:
            errors.append(f"line {n}: expected '<FLIGHT|HOTEL|GROUND> <label> <FROM-TO | @lat,lon> <start> - <end> [conf REF]'"); continue
        body = m.group("body").split()
        if kind == "lodging":
            place = _place(body[-1]) if body else None
            if not place: errors.append(f"line {n}: a hotel needs @lat,lon at the end"); continue
            legs.append({"kind": kind, "label": " ".join(body[:-1]) or place[0], "ref": m.group("ref"), "from_name": None, "from_lat": None, "from_lon": None,
                         "to_name": place[0], "to_lat": place[1], "to_lon": place[2], "start_at": start, "end_at": end, "line": n})
            continue
        route = body[-1] if body else ""
        parts = re.split(r"(?<=[A-Za-z0-9])-(?=[A-Za-z@])", route, maxsplit=1)
        a, b = (_place(parts[0]), _place(parts[1])) if len(parts) == 2 else (None, None)
        if not a or not b:
            errors.append(f"line {n}: route '{route}' — use IATA codes from the known list or @lat,lon"); continue
        legs.append({"kind": kind, "label": " ".join(body[:-1]), "ref": m.group("ref"), "from_name": a[0], "from_lat": a[1], "from_lon": a[2],
                     "to_name": b[0], "to_lat": b[1], "to_lon": b[2], "start_at": start, "end_at": end, "line": n})
    return legs, errors


async def _trip_for(session: AsyncSession, r: Dict[str, str], by_id: Dict[str, PersonRow], by_email: Dict[str, PersonRow], at: Optional[datetime]) -> Optional[TripRow]:
    """The trip a leg belongs to: by trip_id or booking_ref, else the traveler's trip that spans the leg's start."""
    tid = r.get("trip_id") or (f"trip_{r['booking_ref']}" if r.get("booking_ref") else None)
    if tid:
        return await session.get(TripRow, tid)
    p = _find(by_id, by_email, r)
    if not p or not at: return None
    trips = (await session.execute(select(TripRow).where(TripRow.person_id == p.id))).scalars().all()
    return next((t for t in sorted(trips, key=lambda t: t.depart_at) if t.depart_at - timedelta(hours=12) <= at <= t.return_at + timedelta(hours=12)), None)


async def import_legs(session: AsyncSession, text: str, actor: str, source: str = "travel_system:csv") -> Dict[str, Any]:
    """Itinerary export. Columns: trip_id | booking_ref | email, kind (flight|ground|lodging), label, ref?, from_name?, from_lat?, from_lon?,
    to_name, to_lat, to_lon, start_at, end_at, note?. Upsert by ref within a trip."""
    by_id, by_email = await _people_index(session)
    created = updated = skipped = 0; errors: List[str] = []
    for i, r in enumerate(rows_of(text), 1):
        kind = LEG_KINDS.get((r.get("kind") or "").lower()); st, en = _dt(r.get("start_at")), _dt(r.get("end_at"))
        trip = await _trip_for(session, r, by_id, by_email, st)
        try: to = (r["to_name"], float(r["to_lat"]), float(r["to_lon"]))
        except (KeyError, ValueError): to = None
        if not trip or not kind or not st or not en or en <= st or not to or (kind != "lodging" and not r.get("from_name")):
            skipped += 1; errors.append(f"row {i}: needs a known trip (trip_id, booking_ref, or the traveler's email), a kind, to_name/to_lat/to_lon, start_at < end_at" + ("" if kind == "lodging" else ", and from_name for a flight or ground leg")); continue
        existing = next((l for l in (await session.execute(select(TripLegRow).where(TripLegRow.trip_id == trip.id))).scalars() if r.get("ref") and l.ref == r["ref"]), None)
        vals = dict(trip_id=trip.id, kind=kind, label=r.get("label") or "", ref=r.get("ref") or None, from_name=r.get("from_name") or None,
                    from_lat=float(r["from_lat"]) if r.get("from_lat") else None, from_lon=float(r["from_lon"]) if r.get("from_lon") else None,
                    to_name=to[0], to_lat=to[1], to_lon=to[2], start_at=st, end_at=en, note=r.get("note") or "", source=source, created_by=actor)
        if existing:
            for k, v in vals.items(): setattr(existing, k, v)
            updated += 1
        else:
            session.add(TripLegRow(id=f"leg_imp_{uuid.uuid4().hex[:6]}", **vals)); created += 1
    await session.commit()
    return {"kind": "legs", "source": source, "created": created, "updated": updated, "skipped": skipped, "errors": errors[:20]}


async def import_itinerary(session: AsyncSession, text: str, actor: str, source: str = "itinerary:paste") -> Dict[str, Any]:
    """A pasted confirmation. The first line names the trip: 'TRIP <trip_id>' or 'TRAVELER <email>'; the rest are legs (see parse_itinerary)."""
    lines = [l for l in text.splitlines() if l.strip()]
    head = lines[0].split(maxsplit=1) if lines else []
    by_id, by_email = await _people_index(session)
    legs, errors = parse_itinerary("\n".join(lines[1:])) if len(head) == 2 and head[0].upper() in ("TRIP", "TRAVELER") else ([], ["line 1: start with 'TRIP <trip_id>' or 'TRAVELER <email>'"])
    trip = None
    if head and head[0].upper() == "TRIP": trip = await session.get(TripRow, head[1].strip())
    elif head and head[0].upper() == "TRAVELER" and legs: trip = await _trip_for(session, {"email": head[1].strip()}, by_id, by_email, legs[0]["start_at"])
    if not trip and len(head) == 2:
        errors.insert(0, f"line 1: no trip found for {head[1].strip()}")
    created = 0
    if trip:
        for lg in legs:
            session.add(TripLegRow(id=f"leg_imp_{uuid.uuid4().hex[:6]}", trip_id=trip.id, kind=lg["kind"], label=lg["label"], ref=lg["ref"], from_name=lg["from_name"], from_lat=lg["from_lat"], from_lon=lg["from_lon"],
                                   to_name=lg["to_name"], to_lat=lg["to_lat"], to_lon=lg["to_lon"], start_at=lg["start_at"], end_at=lg["end_at"], source=source, created_by=actor)); created += 1
        await session.commit()
    return {"kind": "itinerary", "source": source, "trip_id": trip.id if trip else None, "created": created, "updated": 0, "skipped": len(errors), "errors": errors[:20]}


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
