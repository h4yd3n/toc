"""Synthetic seed data. Every person, address, trip, event, and synthetic threat here is fictional."""
import json
import os
import random
from typing import Optional
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .sections import ShipmentRow, SupplyRow, SystemRow
from . import users as toc_users
from .names import split_name
from . import taskings as toc_taskings
from .taskings import TaskingRow
from . import areas as toc_areas
from .areas import AreaRatingRow
from . import graphics as toc_graphics
from .graphics import GraphicRow
from .users import UserRow
from .db_models import (TripLegRow, AccountabilityRow, AssessmentRow, EventAttendeeRow, EventRow, IncidentRow, LocationRow, PersonRow, PIRRow,
                        TeamRow, ThreatLinkRow, ThreatRow, TripRow)

def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

LOCATIONS = [
    ("loc_sf",   "San Francisco HQ",      "hq",         37.7749, -122.4194, "San Francisco", "US", "normal",   "standard"),
    ("loc_nyc",  "New York Office",       "office",     40.7128,  -74.0060, "New York",      "US", "normal",   "standard"),
    ("loc_dc",   "Washington DC Office",  "office",     38.9072,  -77.0369, "Washington",    "US", "normal",   "standard"),
    ("loc_ldn",  "London Office",         "office",     51.5074,   -0.1278, "London",        "GB", "elevated", "standard"),
    ("loc_sgp",  "Singapore Office",      "office",     1.3521,   103.8198, "Singapore",     "SG", "normal",   "standard"),
    ("loc_tyo",  "Tokyo Office",          "office",     35.6762,  139.6503, "Tokyo",         "JP", "normal",   "standard"),
    ("loc_dc1",  "DC-West (Oregon)",      "datacenter", 45.5946, -121.1787, "The Dalles",    "US", "normal",   "standard"),
    ("loc_dc2",  "DC-East (Virginia)",    "datacenter", 39.0438,  -77.4874, "Ashburn",       "US", "elevated", "standard"),
    ("loc_res1", "Residence — CEO",       "residence",  37.4613, -122.1977, "Atherton",      "US", "normal",   "restricted"),
    ("loc_res2", "Residence — CFO",       "residence",  41.0262,  -73.6282, "Greenwich",     "US", "normal",   "restricted"),
]

TEAMS = [
    ("t_exec",     "Executive Leadership",   "loc_sf",  "executive",   False, 6),
    ("t_sec_sf",   "Security — SF",          "loc_sf",  "security",    True,  8),
    ("t_eng_sf",   "Engineering — Platform", "loc_sf",  "engineering", False, 14),
    ("t_ops_sf",   "Operations",             "loc_sf",  "operations",  False, 5),
    ("t_sec_nyc",  "Security — NYC",         "loc_nyc", "security",    True,  5),
    ("t_sales_nyc","Sales — East",           "loc_nyc", "sales",       False, 9),
    ("t_pol_dc",   "Policy & Gov Affairs",   "loc_dc",  "policy",      False, 6),
    ("t_sec_dc",   "Security — DC",          "loc_dc",  "security",    True,  3),
    ("t_sec_ldn",  "Security — London",      "loc_ldn", "security",    True,  4),
    ("t_eng_ldn",  "Engineering — EMEA",     "loc_ldn", "engineering", False, 10),
    ("t_ops_sgp",  "APAC Operations",        "loc_sgp", "operations",  False, 7),
    ("t_eng_tyo",  "Engineering — Tokyo",    "loc_tyo", "engineering", False, 6),
    ("t_dc1",      "Site Reliability — West","loc_dc1", "infra",       False, 4),
    ("t_dc2",      "Site Reliability — East","loc_dc2", "infra",       False, 4),
    ("t_ep",       "Executive Protection",   "loc_sf",  "security",    True,  6),
]

FIRST = ["Avery","Jordan","Riley","Morgan","Casey","Quinn","Reese","Taylor","Dakota","Emerson",
         "Hayden","Kendall","Logan","Parker","Rowan","Sawyer","Skyler","Blake","Cameron","Drew",
         "Elliot","Finley","Harper","Jesse","Kai","Lane","Marlow","Noel","Peyton","Remy"]
LAST  = ["Okafor","Lindqvist","Nakamura","Reyes","Haddad","Whitfield","Moreau","Castellano","Ibrahim",
         "Sørensen","Vance","Achterberg","Oyelaran","Kowalski","Delgado","Brennan","Tanaka","Novak",
         "Mbeki","Fairweather","Ruiz","Halvorsen","Petrova","Oduya","Chen","Ferreira","Ashby","Nkemelu"]
SHIFT_ROLES = ["Watch Officer", "Access Control", "Patrol", "CCTV Monitor", "Response"]

VIPS = [
    ("p_ceo", "Alex Ventura",    "Chief Executive Officer",  "t_exec"),
    ("p_cfo", "Priya Ramanathan","Chief Financial Officer",  "t_exec"),
    ("p_cto", "Daniel Osei",     "Chief Technology Officer", "t_exec"),
    ("p_coo", "Mei-Lin Zhao",    "Chief Operating Officer",  "t_exec"),
    ("p_gc",  "Samuel Achebe",   "General Counsel",          "t_exec"),
    ("p_cso", "Renata Kovač",    "Chief Security Officer",   "t_exec"),
]

def _contact(rng, name):
    first, last = name.split(" ", 1)
    return (f"+1 415 555-{rng.randint(100, 999):03d}{rng.randint(0, 9)}", f"{first.lower()}.{last.lower().replace(' ', '').replace('ø', 'o').replace('č', 'c')}@example.com")

def _people():
    rng = random.Random(1907); rows = []; used = set(); n = 0
    for pid, name, role, tid in VIPS:
        ph, em = _contact(rng, name)
        f, l, mi = split_name(name)
        rows.append(PersonRow(id=pid, name=name, first_name=f, last_name=l, middle_initial=mi, role=role, team_id=tid, is_vip=True, phone=ph, email=em, source="hris:workday"))
    for tid, tname, _loc, func, is_sec, count in TEAMS:
        if tid == "t_exec":
            continue
        for i in range(count):
            while True:
                nm = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
                if nm not in used:
                    used.add(nm); break
            n += 1
            ph, em = _contact(rng, nm)
            if is_sec:
                on = rng.random() < 0.45
                f, l, mi = split_name(nm)
                rows.append(PersonRow(id=f"p_{n:03d}", name=nm, first_name=f, last_name=l, middle_initial=mi, role=("Security Lead" if i == 0 else "Security Officer"), phone=ph, email=em, source="hris:workday",
                                      team_id=tid, on_shift=on, shift_role=(rng.choice(SHIFT_ROLES) if on else None)))
            else:
                role = {"engineering": "Engineer", "sales": "Account Executive", "policy": "Policy Analyst",
                        "operations": "Operations Manager", "infra": "SRE"}.get(func, "Staff")
                if i == 0:
                    role = f"Head of {tname.split(' — ')[0]}"
                f, l, mi = split_name(nm)
                rows.append(PersonRow(id=f"p_{n:03d}", name=nm, first_name=f, last_name=l, middle_initial=mi, role=role, team_id=tid, phone=ph, email=em, source="hris:workday"))
    return rows

def _sections(now):
    """§7/§8 seed: the background boards. Mostly green, with the exceptions a Battle Captain should hear about."""
    h = lambda x: now + timedelta(hours=x)
    sup = lambda i, loc, cat, item, on, req, unit, note="": SupplyRow(id=f"sup_{i:03d}", location_id=loc, category=cat, item=item, on_hand=on, required=req, unit=unit, note=note, updated_at=h(-3), source="manual:s4")
    supplies = [
        sup(1, "loc_sf", "fuel", "Generator diesel", 1800, 1500, "L"), sup(2, "loc_sf", "water", "Bottled water", 96, 120, "cases", "Delivery Friday"),
        sup(3, "loc_sf", "medical", "Trauma kits", 12, 12, "ea"), sup(4, "loc_sf", "equipment", "Handheld radios (charged)", 18, 24, "ea", "6 on the charger, 2 U/S"),
        sup(5, "loc_dc2", "fuel", "Generator diesel", 400, 2000, "L", "Resupply inbound"), sup(6, "loc_dc2", "equipment", "Satellite phones", 2, 2, "ea"),
        sup(7, "loc_nyc", "medical", "AEDs (serviceable)", 4, 4, "ea"), sup(8, "loc_ldn", "equipment", "Body armor sets", 6, 8, "ea"),
        sup(9, None, "equipment", "Armored vehicles (mission capable)", 3, 4, "ea", "1 in maintenance, Riyadh"), sup(10, "loc_tyo", "rations", "Emergency rations (72h)", 40, 40, "person-days"),
    ]
    shp = lambda i, desc, cat, qty, frm, loc, eta, status, pri, carrier="", ref=None, note="": ShipmentRow(id=f"shp_{i:03d}", description=desc, category=cat, quantity=qty, from_name=frm, to_location_id=loc, eta=eta, status=status, priority=pri, carrier=carrier, ref=ref, note=note, updated_at=h(-1), source="manual:s4")
    shipments = [
        shp(1, "Generator diesel resupply", "fuel", "2,000 L", "Regional depot", "loc_dc2", h(6), "in_transit", "urgent", "Contract carrier", "DL-4471"),
        shp(2, "Radio batteries + chargers", "equipment", "24 ea", "Vendor", "loc_tyo", h(-3), "delayed", "priority", "Courier", "RB-0092", "Customs hold at Narita"),
        shp(3, "Bottled water", "water", "60 cases", "Local supplier", "loc_sf", h(30), "planned", "routine"),
        shp(4, "Medical resupply", "medical", "6 kits", "Vendor", "loc_ldn", h(-20), "arrived", "routine"),
    ]
    sy = lambda i, name, cat, loc, pace, status, since, note="": SystemRow(id=f"sys_{i:03d}", name=name, category=cat, location_id=loc, pace=pace, status=status, since=since, note=note, updated_at=since, source="manual:s6")
    systems = [
        sy(1, "Corporate WAN / VPN", "network", None, None, "up", h(-400)), sy(2, "Mass notification (SMS + chat)", "application", None, None, "up", h(-300)),
        sy(3, "Badge / access control", "application", "loc_dc2", None, "down", h(-2), "Controller reboot loop; vendor engaged"),
        sy(4, "Video management system", "sensor", "loc_sf", None, "degraded", h(-5), "Two cameras offline, east lobby"),
        sy(5, "Desk phones (VoIP)", "comms", "loc_sf", "primary", "up", h(-900)), sy(6, "Cellular (corporate mobiles)", "comms", "loc_sf", "alternate", "up", h(-900)),
        sy(7, "Handheld radio net", "comms", "loc_sf", "contingency", "up", h(-900)), sy(8, "Satellite phone", "comms", "loc_sf", "emergency", "up", h(-900)),
        sy(9, "Desk phones (VoIP)", "comms", "loc_dc2", "primary", "down", h(-2), "Same controller outage"), sy(10, "Cellular", "comms", "loc_dc2", "alternate", "up", h(-900)),
        sy(11, "Handheld radio net", "comms", "loc_dc2", "contingency", "up", h(-900)), sy(12, "Satellite phone", "comms", "loc_dc2", "emergency", "up", h(-900)),
        sy(13, "Site power (utility)", "power", "loc_dc2", None, "up", h(-900)), sy(14, "Backup generator", "power", "loc_dc2", None, "up", h(-900), "Fuel at 20% — see S4"),
        sy(15, "Desk phones (VoIP)", "comms", "loc_ldn", "primary", "up", h(-900)), sy(16, "Cellular", "comms", "loc_ldn", "alternate", "degraded", h(-8), "Carrier outage, central London"),
    ]
    return supplies + shipments + systems

def _trips(now):
    h = lambda x: now + timedelta(hours=x); d = lambda x: now + timedelta(days=x)
    return [
        TripRow(id="trip_001", person_id="p_ceo", origin_location_id="loc_sf", dest_location_id=None,
                dest_name="Riyadh, Saudi Arabia", dest_lat=24.7136, dest_lon=46.6753,
                depart_at=d(-1), return_at=d(2), purpose="Board meeting with energy-sector partners", source="travel_system:concur"),
        TripRow(id="trip_002", person_id="p_cfo", origin_location_id="loc_nyc", dest_location_id="loc_ldn",
                dest_name="London Office", dest_lat=51.5074, dest_lon=-0.1278,
                depart_at=d(-2), return_at=d(1), purpose="Investor roadshow — EMEA", source="travel_system:concur"),
        TripRow(id="trip_003", person_id="p_cto", origin_location_id="loc_sf", dest_location_id="loc_tyo",
                dest_name="Tokyo Office", dest_lat=35.6762, dest_lon=139.6503,
                depart_at=h(-30), return_at=d(4), purpose="Engineering leadership offsite", source="calendar:google"),
        TripRow(id="trip_004", person_id="p_cso", origin_location_id="loc_sf", dest_location_id="loc_sgp",
                dest_name="Singapore Office", dest_lat=1.3521, dest_lon=103.8198,
                depart_at=h(-8), return_at=d(3), purpose="APAC security posture review", source="calendar:google"),
        TripRow(id="trip_005", person_id="p_coo", origin_location_id="loc_sf", dest_location_id=None,
                dest_name="Dubai, UAE", dest_lat=25.2048, dest_lon=55.2708,
                depart_at=d(3), return_at=d(6), purpose="Regional partner summit", source="travel_system:concur"),
        TripRow(id="trip_006", person_id="p_gc", origin_location_id="loc_dc", dest_location_id=None,
                dest_name="Mexico City, Mexico", dest_lat=19.4326, dest_lon=-99.1332,
                depart_at=d(5), return_at=d(7), purpose="Regulatory meetings", source="calendar:google"),
        TripRow(id="trip_007", person_id="p_007", origin_location_id="loc_sf", dest_location_id="loc_dc2",
                dest_name="DC-East (Virginia)", dest_lat=39.0438, dest_lon=-77.4874,
                depart_at=h(-20), return_at=d(2), purpose="Site security audit", source="manual:ea"),
    ]

def _legs(now):
    """§6 itineraries. Present where the travel system supplied them, absent otherwise — the CFO's London trip has none."""
    h = lambda x: now + timedelta(hours=x); d = lambda x: now + timedelta(days=x)
    A = {"SFO": ("San Francisco SFO", 37.6213, -122.3790), "LHR": ("London Heathrow LHR", 51.4700, -0.4543), "RUH": ("Riyadh RUH", 24.9576, 46.6988),
         "HND": ("Tokyo Haneda HND", 35.5494, 139.7798), "SIN": ("Singapore SIN", 1.3644, 103.9915), "DXB": ("Dubai DXB", 25.2532, 55.3657), "IAD": ("Washington Dulles IAD", 38.9531, -77.4565)}
    def fl(tid, i, label, ref, a, b, s, e, src="travel_system:concur"):
        return TripLegRow(id=f"leg_{tid[-3:]}_{i}", trip_id=tid, kind="flight", label=label, ref=ref, from_name=A[a][0], from_lat=A[a][1], from_lon=A[a][2], to_name=A[b][0], to_lat=A[b][1], to_lon=A[b][2], start_at=s, end_at=e, source=src)
    def ho(tid, i, label, ref, lat, lon, s, e, src="travel_system:concur"):
        return TripLegRow(id=f"leg_{tid[-3:]}_{i}", trip_id=tid, kind="lodging", label=label, ref=ref, to_name=label, to_lat=lat, to_lon=lon, start_at=s, end_at=e, source=src)
    def gr(tid, i, label, a, lat, lon, to, s, e, src="travel_system:concur"):
        return TripLegRow(id=f"leg_{tid[-3:]}_{i}", trip_id=tid, kind="ground", label=label, from_name=A[a][0], from_lat=A[a][1], from_lon=A[a][2], to_name=to, to_lat=lat, to_lon=lon, start_at=s, end_at=e, source=src)
    return [
        # CEO → Riyadh (departed yesterday): two flights, a car, the hotel until the return
        fl("trip_001", 1, "UA 954", "K7X2ZQ", "SFO", "LHR", d(-1), h(-14)),
        fl("trip_001", 2, "BA 263", "K7X2ZQ", "LHR", "RUH", h(-12), h(-5)),
        gr("trip_001", 3, "Car service", "RUH", 24.6905, 46.6250, "Ritz-Carlton Riyadh", h(-5), h(-4)),
        ho("trip_001", 4, "Ritz-Carlton Riyadh", "88112", 24.6905, 46.6250, h(-4), d(2)),
        # CTO → Tokyo (in the air 30h ago): one flight, the hotel
        fl("trip_003", 1, "JL 1", "R4M9PP", "SFO", "HND", h(-30), h(-19)),
        ho("trip_003", 2, "Palace Hotel Tokyo", "R4M9PP", 35.6847, 139.7620, h(-18), d(4)),
        # CSO → Singapore (departed 8h ago): still airborne — the pin sits at the arrival airport
        fl("trip_004", 1, "SQ 31", "T2Q8LA", "SFO", "SIN", h(-8), h(9)),
        ho("trip_004", 2, "Fullerton Hotel Singapore", "T2Q8LA", 1.2863, 103.8531, h(10), d(3)),
        # COO → Dubai (in 3 days): planned
        fl("trip_005", 1, "EK 226", "Z9C1WW", "SFO", "DXB", d(3), d(3) + timedelta(hours=16)),
        ho("trip_005", 2, "Address Downtown Dubai", "Z9C1WW", 25.1934, 55.2774, d(3) + timedelta(hours=17), d(6)),
        # An ordinary traveler's site audit trip: the same fields, entered by an EA
        fl("trip_007", 1, "UA 2310", None, "SFO", "IAD", h(-20), h(-15), "manual:ea"),
        ho("trip_007", 2, "Hyatt Regency Reston", None, 38.9586, -77.3570, h(-14), d(2), "manual:ea"),
    ]

# (id, name, type, venue_location_id, venue_name, lat, lon, start_days, duration_days, description, attendees)
EVENTS = [
    ("evt_001", "Q4 Board Meeting", "board_meeting", "loc_nyc", "New York Office", 40.7128, -74.0060, 35, 2,
     "Full board session and investor dinner. Closed session day 2.",
     ["p_ceo", "p_cfo", "p_gc", "p_coo", "p_022", "p_023"]),
    ("evt_002", "Global Sales Kickoff", "conference", None, "Las Vegas Convention Center", 36.1313, -115.1512, 49, 3,
     "Company-wide sales conference, ~400 attendees, public keynote by the CEO on day 1.",
     ["p_ceo", "p_coo", "p_033", "p_034", "p_035", "p_036", "p_037", "p_022", "p_024", "p_025"]),
    ("evt_003", "EMEA Engineering Summit", "offsite", "loc_ldn", "London Office", 51.5074, -0.1278, 21, 3,
     "Engineering leadership offsite across EMEA teams.",
     ["p_cto", "p_009", "p_046", "p_047", "p_048", "p_042"]),
]

def generate_event_trips(event: EventRow, attendee_ids, people_by_id, team_loc, created_by="system") -> list:
    """S3 → S1: every attendee not already based at the venue gets a planned trip."""
    trips = []
    for pid in attendee_ids:
        p = people_by_id.get(pid)
        if not p:
            continue
        home = team_loc[p.team_id]
        if event.venue_location_id and event.venue_location_id == home:
            continue
        trips.append(TripRow(
            id=f"trip_{event.id}_{pid}", person_id=pid, origin_location_id=home,
            dest_location_id=event.venue_location_id, dest_name=event.venue_name,
            dest_lat=event.venue_lat, dest_lon=event.venue_lon,
            depart_at=event.start_at - timedelta(days=1), return_at=event.end_at + timedelta(days=1),
            purpose=f"{event.name}", event_id=event.id, created_by=created_by, source="event"))
    return trips

def _threats(now):
    h = lambda x: now - timedelta(hours=x)
    return [
        ThreatRow(id="thr_001", title="Regional drone / missile activity", lat=24.7136, lon=46.6753, radius_km=60,
                  severity="moderate", source="synthetic:osint_feed", confidence="moderate", observed_at=h(6), event_type="conflict",
                  summary="Reporting of intercepted UAS activity targeting infrastructure in the region. No indication of targeting against business travelers."),
        ThreatRow(id="thr_007", title="Transport strike called — Lisbon metro and CP rail", lat=38.7223, lon=-9.1393, radius_km=30,
                  severity="moderate", source="synthetic:news_rss", confidence="high", observed_at=h(10), event_type="transit",
                  summary="Unions announce a 48-hour stoppage across Lisbon metro and suburban rail from the 14th. Airport link affected."),
        ThreatRow(id="thr_002", title="Large demonstration planned — Westminster", lat=51.5007, lon=-0.1246, radius_km=3,
                  severity="low", source="synthetic:news_rss", confidence="high", observed_at=h(14), event_type="civil_unrest",
                  summary="Permitted march expected 20–40k attendees Saturday. Road closures around Whitehall. Historically peaceful."),
        ThreatRow(id="thr_003", title="KFR activity reported — Polanco district", lat=19.4319, lon=-99.1918, radius_km=8,
                  severity="elevated", source="synthetic:osac", confidence="moderate", observed_at=h(30), event_type="crime",
                  summary="Two express-kidnapping incidents involving foreign nationals in the past 10 days. Vetted transport recommended."),
        ThreatRow(id="thr_004", title="Online threats against data center operators", lat=39.0438, lon=-77.4874, radius_km=20,
                  severity="elevated", source="synthetic:social_monitor", confidence="low", observed_at=h(3), event_type="targeted",
                  summary="Coordinated posting naming regional facilities. Single-source; no corroboration of capability or intent."),
        ThreatRow(id="thr_005", title="Elevated regional tension", lat=25.2048, lon=55.2708, radius_km=40,
                  severity="moderate", source="synthetic:state_dept", confidence="high", observed_at=h(48), event_type="geopolitical",
                  summary="Advisory level raised. Increased security presence at hotels and transit hubs."),
        ThreatRow(id="thr_006", title="Protest planned outside HQ — Friday", lat=37.7749, lon=-122.4194, radius_km=1.5,
                  severity="low", source="synthetic:permit_feed", confidence="high", observed_at=h(20), event_type="civil_unrest",
                  summary="Permitted protest, est. 200 attendees, 1200–1500 local. Lobby access control recommended."),
    ]

def _pirs(now):
    return [
        PIRRow(id="PIR-01", question="Is there credible targeting of Western business travelers in Riyadh during the CEO visit window?",
               status="OPEN", owner="S2", priority=1, subject_type="trip", subject_id="trip_001", created_at=now - timedelta(days=2), expires_at=now + timedelta(days=2)),
        PIRRow(id="PIR-02", question="Will Saturday's Westminster demonstration affect access to the London office on Monday?",
               status="OPEN", owner="S2", priority=2, subject_type="location", subject_id="loc_ldn", created_at=now - timedelta(days=1), expires_at=now + timedelta(days=4)),
        PIRRow(id="PIR-03", question="Do the online threats naming DC-East reflect capability or only rhetoric?",
               status="COLLECTING", owner="S2", priority=1, subject_type="location", subject_id="loc_dc2", created_at=now - timedelta(hours=3), expires_at=None),
        PIRRow(id="PIR-04", question="What is the crowd-management and counter-protest picture for the Las Vegas kickoff keynote?",
               status="OPEN", owner="S2", priority=2, subject_type="event", subject_id="evt_002", created_at=now - timedelta(hours=20), expires_at=now + timedelta(days=45)),
    ]

def _assessments(now):
    return [
        AssessmentRow(id="ASMT-014", title="CEO travel — Riyadh", subject_type="trip", subject_id="trip_001",
                      likelihood="unlikely", band="20–45%", confidence="moderate",
                      bluf="Direct threat to the principal is unlikely; residual risk driven by regional UAS activity. Enhanced protocols in place.",
                      key_judgments_json=json.dumps([
                          {"claim": "Direct targeting of the principal during the visit window", "likelihood": "unlikely", "band": "20–45%", "confidence": "moderate"},
                          {"claim": "Disruption to movement from regional UAS/missile activity", "likelihood": "roughly even chance", "band": "45–55%", "confidence": "moderate"}]),
                      evidence_json=json.dumps([{"threat_id": "thr_001", "title": "Regional drone / missile activity", "source": "synthetic:osint_feed", "distance_km": 0, "confidence": "moderate", "severity": "moderate", "confirmed": True, "synthetic": True}]),
                      gaps_json=json.dumps(["No reporting on hotel security-force posture", "No HUMINT from local EP vendor yet"]),
                      author="S2 duty analyst", status="approved", created_at=now - timedelta(days=1), approved_by="R. Kovač", approved_at=now - timedelta(hours=20)),
        AssessmentRow(id="ASMT-015", title="DC-East online threat", subject_type="location", subject_id="loc_dc2",
                      likelihood="very unlikely", band="05–20%", confidence="low",
                      bluf="Single-source rhetoric with no observed capability. Insufficient basis to raise site posture beyond elevated.",
                      key_judgments_json=json.dumps([{"claim": "Physical action against DC-East within 30 days", "likelihood": "very unlikely", "band": "05–20%", "confidence": "low"}]),
                      evidence_json=json.dumps([{"threat_id": "thr_004", "title": "Online threats against data center operators", "source": "synthetic:social_monitor", "distance_km": 0, "confidence": "low", "severity": "elevated", "confirmed": False, "synthetic": True}]),
                      gaps_json=json.dumps(["Single source — no corroboration", "No attribution of the posting cluster"]),
                      author="S2 duty analyst", status="review", created_at=now - timedelta(hours=2)),
    ]

async def seed_if_empty(session: AsyncSession) -> bool:
    if (await session.execute(select(LocationRow.id).limit(1))).first():
        return False
    await reseed(session)
    return True

# §5.10/5.11 demo: a site-security case with two synthetic SPOTREPs. Names, plates, handles, and numbers are invented.
CASE_REPORTS = [
    (2, "guard_07", "site security", "north gate, SF HQ",
     "Observed Marcus Vane at the north gate at 21:40 talking to Dana Ortiz. Vane was in a grey sedan, plate 7ABC123. "
     "He mentioned the account @vane_ops and gave the number +1 415 555 0142. Both left together toward Market Street."),
    (1, "guard_03", "site security", "north gate, SF HQ",
     "M. Vane seen again with Dana Ortiz at the north gate, on foot, photographing the loading dock. Left when approached."),
]


async def _seed_case(session: AsyncSession, now: datetime) -> None:
    from sigtoc.cases import CaseEventRow, CaseRow, EntityRow, RelationshipRow, ReportRow, file_report_into_case
    for model in (CaseEventRow, RelationshipRow, EntityRow, ReportRow, CaseRow):
        for row in (await session.execute(select(model))).scalars():
            await session.delete(row)
    await session.flush()
    case = CaseRow(id="case_seed_gate", title="North gate loiterer", kind="person", subject_type="location", subject_id="loc_sf",
                   summary="Two sightings of the same pair at the SF HQ north gate; second time photographing the dock.", opened_by="S2 duty analyst", opened_at=now - timedelta(hours=25))
    session.add(case); await session.flush()
    for i, (days_ago, who, role, place, text) in enumerate(CASE_REPORTS):
        at = (now - timedelta(days=days_ago)).replace(hour=21, minute=40 + 10 * i, second=0, microsecond=0)  # the hour the report text names
        r = ReportRow(id=f"rpt_seed_{i + 1}", kind="spot", reported_by=who, reporter_role=role, at=at, lat=37.7897, lon=-122.3989, place=place,
                      text=text, case_id=case.id, filed_at=at + timedelta(minutes=6))
        session.add(r); await session.flush()
        known = [e.name for e in (await session.execute(select(EntityRow).where(EntityRow.case_id == case.id))).scalars()]
        await file_report_into_case(session, r, case, known)


async def _seed_directed(session: AsyncSession, now: datetime) -> None:
    """The Lisbon question (§5.1): an EA asks about two candidate offsite venues. Synthetic, like everything else here."""
    from sigtoc.area import AreaAssessmentRow
    from sigtoc.requirements import RequirementRow
    for row in (await session.execute(select(AreaAssessmentRow))).scalars():
        await session.delete(row)
    for rid, place, lat, lon in (("req_dir_seed_lisbon", "Lisbon, Portugal", 38.7223, -9.1393), ("req_dir_seed_porto", "Porto, Portugal", 41.1579, -8.6291)):
        if not await session.get(RequirementRow, rid):
            session.add(RequirementRow(id=rid, kind="directed", subject_type="place", subject_id=None, subject_name=place, lat=lat, lon=lon, radius_km=50.0, country="PT",
                                       question=f"What is the environment in {place} for the Q1 leadership offsite?", purpose="Q1 leadership offsite — candidate venue", priority=2,
                                       window_from=now + timedelta(days=40), window_to=now + timedelta(days=43), status="active", owner="EA - Office of the CEO", created_at=now, updated_at=now))
    await session.flush()


async def _seed_operation(session: AsyncSession, now: datetime) -> None:
    """§5.10 #3: the approved Riyadh assessment (ASMT-014) became an operation — the target package handed to S3."""
    from .operations import DEFAULT_TASKS, OperationRow, OpResourceRow, OpTaskRow, new_task
    for model in (OpResourceRow, OpTaskRow, OperationRow):
        for row in (await session.execute(select(model))).scalars():
            await session.delete(row)
    await session.flush()
    op = OperationRow(id="op_seed_riyadh", title="OP — CEO Riyadh visit", subject_type="trip", subject_id="trip_001", subject_name="Alex Ventura — Riyadh, Saudi Arabia",
                      from_product_type="assessment", from_product_id="ASMT-014", status="active", opened_by="Battle Captain", opened_at=now - timedelta(hours=18),
                      notes="Enhanced protocols per ASMT-014. EP detail of two; embassy RSO informed.")
    session.add(op); await session.flush()
    owners = ["EP detail lead", "S2 duty analyst", "EP detail lead", "S6 watch floor"]
    states = ["done", "done", "doing", "todo"]
    for i, t in enumerate(DEFAULT_TASKS["trip"]):
        row = new_task(op.id, t["title"], t["section"], owners[i], i); row.status = states[i]; row.updated_by = owners[i]; row.updated_at = now - timedelta(hours=12 - i)
        session.add(row)
    session.add(OpResourceRow(id="res_seed_1", operation_id=op.id, item="Armored SUV with local driver", qty=2, status="approved", note="Vendor confirmed", updated_by="S4", updated_at=now - timedelta(hours=10)))
    session.add(OpResourceRow(id="res_seed_2", operation_id=op.id, item="Satellite messenger", qty=1, status="requested", updated_by="EP detail lead", updated_at=now - timedelta(hours=3)))
    await session.flush()


DATASETS = ("cab", "corporate")


async def reseed(session: AsyncSession, dataset: Optional[str] = None) -> None:
    """`cab` (default): the Combat Aviation Brigade — the force this TOC is organized around (§4, §7, §8).
    `corporate`: the original executive-protection sample, kept for the test suite and as a second shape of the same model."""
    if not dataset:
        from .sections import dataset_for, profile
        dataset = os.environ.get("TOC_SEED") or dataset_for(profile())
    dataset = dataset.lower()
    if dataset not in DATASETS:
        raise ValueError(f"dataset must be one of {DATASETS}")
    if dataset == "corporate":
        await _seed_case(session, now_utc())
        await _seed_directed(session, now_utc())
        await _seed_operation(session, now_utc())
    for model in (GraphicRow, AreaRatingRow, TaskingRow, SupplyRow, ShipmentRow, SystemRow, AccountabilityRow, IncidentRow, ThreatLinkRow, AssessmentRow, PIRRow, TripLegRow, TripRow, EventAttendeeRow, EventRow, ThreatRow, PersonRow, TeamRow, LocationRow):
        for row in (await session.execute(select(model))).scalars():
            await session.delete(row)
    await session.flush()
    now = now_utc()
    # §9 the directory follows the dataset
    for u in (await session.execute(select(UserRow))).scalars():
        await session.delete(u)
    await session.flush()
    toc_users._cache.clear()
    for spec in toc_users.seed_users(dataset):
        await toc_users.upsert(session, spec, "seed")
    session.add_all(toc_taskings.seed(dataset, now))  # §5.10 the work moving between sections
    from .sections import profile as _profile
    session.add_all(toc_areas.seed(dataset, now, _profile()))  # §5.6a what the analyst judges about each place
    session.add_all(toc_graphics.seed(dataset, now))  # §3.4 the control measures on the board
    if dataset == "cab":
        from . import seed_cab
        await seed_cab.populate(session, now)
        return
    # the corporate desk follows the sun (§3.1); undo a brigade's day/night watch if that is what was loaded before
    import json as _json
    from .watch import FOLLOW_THE_SUN, WatchRow, get_config
    cfg = await get_config(session)
    if cfg.pattern != "follow_the_sun":
        cfg.pattern, cfg.watches_json = "follow_the_sun", _json.dumps(FOLLOW_THE_SUN)
        for w in (await session.execute(select(WatchRow))).scalars():
            await session.delete(w)
        await session.flush()
    session.add_all([LocationRow(id=i, name=n, type=t, lat=la, lon=lo, city=c, country=co, posture=p, sensitivity=s)
                     for i, n, t, la, lo, c, co, p, s in LOCATIONS])
    session.add_all([TeamRow(id=i, name=n, location_id=l, function=f, is_security=s) for i, n, l, f, s, _ in TEAMS])
    await session.flush()
    people = _people()
    # Hybrid presence demo: the CFO checked in from a hotel near the London office two hours ago.
    cfo = next(p for p in people if p.id == "p_cfo")
    cfo.last_checkin_lat, cfo.last_checkin_lon = 51.5145, -0.1420
    cfo.last_checkin_at, cfo.last_checkin_note = now - timedelta(hours=2), "Hotel, Mayfair — all normal"
    session.add_all(people)
    await session.flush()
    session.add_all(_trips(now))
    session.add_all(_legs(now))
    session.add_all(_sections(now))
    people_by_id = {p.id: p for p in people}
    team_loc = {t[0]: t[2] for t in TEAMS}
    for eid, name, etype, vloc, vname, vlat, vlon, start_d, dur, desc, attendees in EVENTS:
        ev = EventRow(id=eid, name=name, event_type=etype, venue_location_id=vloc, venue_name=vname, venue_lat=vlat, venue_lon=vlon,
                      start_at=(now + timedelta(days=start_d)).replace(hour=9, minute=0, second=0, microsecond=0),
                      end_at=(now + timedelta(days=start_d + dur)).replace(hour=17, minute=0, second=0, microsecond=0),
                      description=desc, source="calendar:google")
        session.add(ev)
        session.add_all([EventAttendeeRow(event_id=eid, person_id=pid) for pid in attendees if pid in people_by_id])
        session.add_all(generate_event_trips(ev, attendees, people_by_id, team_loc, created_by="seed"))
    session.add_all(_threats(now))
    session.add_all(_pirs(now))
    session.add_all(_assessments(now))
    await session.flush()
    # Analyst-confirmed links: proximity suggested these, a human confirmed them.
    session.add_all([
        ThreatLinkRow(threat_id="thr_001", target_type="person", target_id="p_ceo", confirmed_by="S2 duty analyst",
                      confirmed_at=now - timedelta(hours=5), note="Principal inside the reported UAS activity radius for the full visit."),
        ThreatLinkRow(threat_id="thr_002", target_type="location", target_id="loc_ldn", confirmed_by="Battle Captain",
                      confirmed_at=now - timedelta(hours=12), note="March route passes within 400 m of the office. Posture elevated for Saturday."),
    ])
    await session.commit()
