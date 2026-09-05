"""The sample force: a Combat Aviation Brigade, organized the way a heavy CAB is — HHC and five battalions
(two attack, one assault, one general-support / heavy-lift, one aviation support), each with a headquarters company
and four line companies. Numbers are approximate to a generic table of organization, not any real unit's; every
name, tail count, and quantity here is invented. Home station is a real airfield so the map has somewhere to be;
the deployed sites are an exercise area. §4 (task organization), §7 (S4), §8 (S6).

Where the people are: the aviation support battalion plus each battalion's D company (aviation unit maintenance)
are the maintainers — together well over half the brigade, which is the author's experience of where the headcount
sits in a CAB."""
import random
from datetime import timedelta

from .db_models import EventAttendeeRow, EventRow, LocationRow, PersonRow, PIRRow, AssessmentRow, TeamRow, ThreatRow, TripLegRow, TripRow
from .sections import ShipmentRow, SupplyRow, SystemRow
from .names import GRADE_RANK, split_name

# (id, name, type, lat, lon, city, country, posture, sensitivity)
LOCATIONS = [
    ("loc_bde",   "Brigade TOC — Campbell Army Airfield", "hq",       36.6706, -87.4962, "Fort Campbell", "US", "normal", "standard"),
    ("loc_caaf",  "Campbell Army Airfield",               "airfield", 36.6717, -87.4892, "Fort Campbell", "US", "normal", "standard"),
    ("loc_1atk",  "1st Attack Bn CP",                     "cp",       36.6650, -87.4900, "Fort Campbell", "US", "normal", "standard"),
    ("loc_2atk",  "2nd Attack Bn CP",                     "cp",       36.6680, -87.5010, "Fort Campbell", "US", "normal", "standard"),
    ("loc_3ahb",  "3rd Assault Bn CP",                    "cp",       36.6725, -87.4840, "Fort Campbell", "US", "normal", "standard"),
    ("loc_4gsab", "4th General Support Bn CP",            "cp",       36.6760, -87.4950, "Fort Campbell", "US", "normal", "standard"),
    ("loc_5asb",  "5th Aviation Support Bn — Motor Pool", "cp",       36.6600, -87.5060, "Fort Campbell", "US", "normal", "standard"),
    ("loc_fob",   "FOB Warrior — JRTC",                   "fob",      31.0600, -93.2000, "Fort Johnson",  "US", "guarded", "standard"),
    ("loc_farp",  "FARP Eagle",                           "farp",     31.1500, -93.3500, "Fort Johnson",  "US", "elevated", "standard"),
    ("loc_range", "Peason Ridge Range Complex",           "range",    31.4000, -93.2500, "Fort Johnson",  "US", "normal", "standard"),
]

# (id, name, short, echelon, parent, location, function, equipment, headcount)
TEAMS = [
    ("t_cab",   "Combat Aviation Brigade",                        "CAB",     "brigade",   None,     "loc_bde",   "hq",          "",                 0),
    ("t_cab_hhc", "HHC, Combat Aviation Brigade",                 "HHC/CAB", "company",   "t_cab",  "loc_bde",   "hq",          "Brigade staff",    120),
    ("t_1atk",  "1st Attack Reconnaissance Battalion",            "1 ATK",   "battalion", "t_cab",  "loc_1atk",  "attack",      "AH-64E ×24",       0),
    ("t_1atk_hhc", "HHC, 1st Attack",                             "HHC/1",   "company",   "t_1atk", "loc_1atk",  "hq",          "Battalion staff",  60),
    ("t_1atk_a", "A Company, 1st Attack",                         "A/1",     "company",   "t_1atk", "loc_caaf",  "attack",      "AH-64E ×8",        45),
    ("t_1atk_b", "B Company, 1st Attack",                         "B/1",     "company",   "t_1atk", "loc_caaf",  "attack",      "AH-64E ×8",        45),
    ("t_1atk_c", "C Company, 1st Attack",                         "C/1",     "company",   "t_1atk", "loc_caaf",  "attack",      "AH-64E ×8",        45),
    ("t_1atk_d", "D Company, 1st Attack (AVUM)",                  "D/1",     "company",   "t_1atk", "loc_caaf",  "maintenance", "Aviation unit maintenance", 140),
    ("t_2atk",  "2nd Attack Reconnaissance Battalion",            "2 ATK",   "battalion", "t_cab",  "loc_2atk",  "attack",      "AH-64E ×24",       0),
    ("t_2atk_hhc", "HHC, 2nd Attack",                             "HHC/2",   "company",   "t_2atk", "loc_2atk",  "hq",          "Battalion staff",  60),
    ("t_2atk_a", "A Company, 2nd Attack",                         "A/2",     "company",   "t_2atk", "loc_caaf",  "attack",      "AH-64E ×8",        45),
    ("t_2atk_b", "B Company, 2nd Attack",                         "B/2",     "company",   "t_2atk", "loc_caaf",  "attack",      "AH-64E ×8",        45),
    ("t_2atk_c", "C Company, 2nd Attack",                         "C/2",     "company",   "t_2atk", "loc_caaf",  "attack",      "AH-64E ×8",        45),
    ("t_2atk_d", "D Company, 2nd Attack (AVUM)",                  "D/2",     "company",   "t_2atk", "loc_caaf",  "maintenance", "Aviation unit maintenance", 140),
    ("t_3ahb",  "3rd Assault Helicopter Battalion",               "3 AHB",   "battalion", "t_cab",  "loc_3ahb",  "assault",     "UH-60M ×30",       0),
    ("t_3ahb_hhc", "HHC, 3rd Assault",                            "HHC/3",   "company",   "t_3ahb", "loc_3ahb",  "hq",          "Battalion staff",  60),
    ("t_3ahb_a", "A Company, 3rd Assault",                        "A/3",     "company",   "t_3ahb", "loc_caaf",  "assault",     "UH-60M ×10",       55),
    ("t_3ahb_b", "B Company, 3rd Assault",                        "B/3",     "company",   "t_3ahb", "loc_caaf",  "assault",     "UH-60M ×10",       55),
    ("t_3ahb_c", "C Company, 3rd Assault",                        "C/3",     "company",   "t_3ahb", "loc_caaf",  "assault",     "UH-60M ×10",       55),
    ("t_3ahb_d", "D Company, 3rd Assault (AVUM)",                 "D/3",     "company",   "t_3ahb", "loc_caaf",  "maintenance", "Aviation unit maintenance", 150),
    ("t_4gsab", "4th General Support Aviation Battalion",         "4 GSAB",  "battalion", "t_cab",  "loc_4gsab", "heavy_lift",  "CH-47F ×12 · UH-60M ×8 · HH-60M ×12", 0),
    ("t_4gsab_hhc", "HHC, 4th General Support",                   "HHC/4",   "company",   "t_4gsab", "loc_4gsab", "hq",         "Battalion staff",  60),
    ("t_4gsab_a", "A Company, 4th GSAB (Command Aviation)",       "A/4",     "company",   "t_4gsab", "loc_caaf", "assault",     "UH-60M ×8",        50),
    ("t_4gsab_b", "B Company, 4th GSAB (Heavy Helicopter)",       "B/4",     "company",   "t_4gsab", "loc_caaf", "heavy_lift",  "CH-47F ×12",       130),
    ("t_4gsab_c", "C Company, 4th GSAB (Air Ambulance)",          "C/4",     "company",   "t_4gsab", "loc_caaf", "medevac",     "HH-60M ×12",       60),
    ("t_4gsab_d", "D Company, 4th GSAB (AVUM)",                   "D/4",     "company",   "t_4gsab", "loc_caaf", "maintenance", "Aviation unit maintenance", 150),
    ("t_5asb",  "5th Aviation Support Battalion",                 "5 ASB",   "battalion", "t_cab",  "loc_5asb",  "support",     "Sustainment for the brigade", 0),
    ("t_5asb_hhc", "HHC, 5th Aviation Support",                   "HHC/5",   "company",   "t_5asb", "loc_5asb",  "hq",          "Battalion staff",  80),
    ("t_5asb_a", "A Company, 5th ASB (Distribution)",             "A/5",     "company",   "t_5asb", "loc_5asb",  "distribution", "Class III/V — fuel and ammunition", 150),
    ("t_5asb_b", "B Company, 5th ASB (Aviation Support)",         "B/5",     "company",   "t_5asb", "loc_caaf",  "maintenance", "AVIM — intermediate maintenance", 320),
    ("t_5asb_c", "C Company, 5th ASB (Network Support)",          "C/5",     "company",   "t_5asb", "loc_bde",   "signal",      "Brigade networks and comms", 110),
    ("t_5asb_d", "D Company, 5th ASB (Ground Maintenance)",       "D/5",     "company",   "t_5asb", "loc_5asb",  "maintenance", "Vehicles and ground equipment", 120),
]

FIRST = ["Avery", "Jordan", "Riley", "Morgan", "Casey", "Quinn", "Reese", "Taylor", "Dakota", "Emerson", "Harper", "Rowan", "Sawyer", "Finley", "Blake",
         "Elliot", "Kai", "Remy", "Drew", "Lane", "Hayden", "Skyler", "Marlow", "Tatum", "Jules", "Devin", "Micah", "Noel", "Sasha", "Ari", "Wren", "Zion"]
LAST = ["Okafor", "Lindqvist", "Nakamura", "Reyes", "Haddad", "Whitfield", "Moreau", "Castellano", "Ibrahim", "Novak", "Petrova", "Ruiz", "Ferreira", "Achebe",
        "Delgado", "Oyelaran", "Vance", "Mbeki", "Okonkwo", "Sato", "Kowalski", "Brennan", "Duarte", "Yilmaz", "Hoffman", "Nilsen", "Park", "Adeyemi", "Fischer", "Quintero"]

ROLES = {
    "hq": ["Commander", "Command Sergeant Major", "Executive Officer", "S3", "S2", "S1", "S4", "S6", "Battle Captain", "Operations NCO", "Intelligence Analyst", "Signal NCO", "Supply Sergeant", "Medic"],
    "attack": ["Company Commander", "First Sergeant", "Platoon Leader", "Pilot in Command", "Pilot", "Crew Chief", "Armament Specialist", "Avionics Repairer"],
    "assault": ["Company Commander", "First Sergeant", "Platoon Leader", "Pilot in Command", "Pilot", "Crew Chief", "Door Gunner", "Flight Operations"],
    "heavy_lift": ["Company Commander", "First Sergeant", "Platoon Leader", "Pilot in Command", "Pilot", "Flight Engineer", "Crew Chief", "Loadmaster"],
    "medevac": ["Company Commander", "First Sergeant", "Pilot in Command", "Pilot", "Flight Medic", "Crew Chief"],
    "maintenance": ["Company Commander", "First Sergeant", "Maintenance Officer", "Production Control NCO", "Powertrain Repairer", "Airframe Repairer", "Avionics Repairer", "Quality Control", "Technical Inspector", "Tool Room"],
    "distribution": ["Company Commander", "First Sergeant", "Fuel Handler", "Ammunition Specialist", "Motor Transport Operator", "FARP Team Chief"],
    "signal": ["Company Commander", "First Sergeant", "Network Technician", "Satellite Systems Operator", "Radio Operator", "Information Systems Specialist"],
    "support": ["Commander"],
}


def _grade_for(role: str, echelon: str, func: str, rng) -> str:
    """Approximate grades by duty — a generic table, not any real unit's."""
    r = role.lower()
    if r == "commander": return "O6" if func == "hq" and echelon == "company" and rng.random() < 0 else ("O5" if "battalion" in r or True else "O5")
    if r == "command sergeant major": return "E9"
    if r in ("executive officer",): return "O4"
    if r in ("s3", "s2", "s1", "s4", "s6"): return rng.choice(["O3", "O4"])
    if r == "battle captain": return "O3"
    if r == "company commander": return "O3"
    if r == "first sergeant": return "E8"
    if r == "platoon leader": return "O2"
    if r == "pilot in command": return rng.choice(["W3", "W4"])
    if r == "pilot": return rng.choice(["W2", "O2", "O1"])
    if r in ("maintenance officer",): return rng.choice(["W3", "O3"])
    if "nco" in r or r in ("supply sergeant", "farp team chief", "quality control", "technical inspector", "production control nco"): return rng.choice(["E6", "E7"])
    if r in ("intelligence analyst", "flight medic", "flight engineer", "crew chief", "loadmaster", "network technician", "satellite systems operator"): return rng.choice(["E4", "E5", "E5"])
    if r in ("medic", "door gunner", "radio operator", "fuel handler", "ammunition specialist", "motor transport operator", "flight operations", "information systems specialist", "tool room"): return rng.choice(["E3", "E4"])
    return rng.choice(["E3", "E4", "E4", "E5"])


def _people():
    rng = random.Random(1187); rows = []; used = set(); n = 0
    def name():  # 2,400 people from two short lists: a middle initial keeps every name distinct
        while True:
            nm = f"{rng.choice(FIRST)} {rng.choice('ABCDEFGHJKLMNPRSTVW')}. {rng.choice(LAST)}"
            if nm not in used:
                used.add(nm); return nm
    for tid, tname, short, echelon, parent, loc, func, equip, count in TEAMS:
        roles = ROLES.get(func, ROLES["hq"])
        for i in range(count):
            n += 1; nm = name()
            if echelon == "company" and func == "hq" and i < 2:  # the battalion or brigade command group sits in its HHC
                role = "Commander" if i == 0 else "Command Sergeant Major"
                is_vip = True
                cmd_grade = ("O6" if parent == "t_cab" else "O5") if i == 0 else "E9"
            else:
                role = roles[min(i, len(roles) - 1)] if i < len(roles) else rng.choice(roles[3:] or roles)
                is_vip = False
            grade = cmd_grade if (echelon == "company" and func == "hq" and i < 2) else _grade_for(role, echelon, func, rng)
            first, last, mi = split_name(nm)
            phone = f"+1 270 555-{rng.randint(100, 999):03d}{rng.randint(0, 9)}"
            email = f"{nm.split()[0].lower()}.{nm.split()[-1].lower()}@example.mil"
            on = func == "hq" and rng.random() < 0.3
            rows.append(PersonRow(id=f"p_{n:04d}", name=nm, first_name=first, last_name=last, middle_initial=mi, rank=GRADE_RANK[grade], grade=grade,
                                  role=role, team_id=tid, is_vip=is_vip, phone=phone, email=email, source="hris:ipps-a",
                                  on_shift=on, shift_role=("Battle Captain" if on and i == 8 else ("Watch" if on else None))))
    return rows


def _by_team(people):
    out = {}
    for p in people:
        out.setdefault(p.team_id, []).append(p)
    return out


def _movements(now, people):
    """§3: who is away from home station — detachments and individual travel. A trip is a trip whether it is a TDY or a FARP team."""
    h = lambda x: now + timedelta(hours=x); d = lambda x: now + timedelta(days=x)
    bt = _by_team(people)
    trips, legs = [], []
    def trip(tid, p, origin, dest_id, dest_name, lat, lon, dep, ret, purpose, src="manual:s3"):
        trips.append(TripRow(id=tid, person_id=p.id, origin_location_id=origin, dest_location_id=dest_id, dest_name=dest_name, dest_lat=lat, dest_lon=lon, depart_at=dep, return_at=ret, purpose=purpose, source=src))
    # B/1 ATK forward at FARP Eagle with a fuel team from A/5 — the exercise advance party
    for i, p in enumerate(bt["t_1atk_b"][:6]):
        trip(f"trip_b1_{i}", p, "loc_caaf", "loc_farp", "FARP Eagle", 31.15, -93.35, d(-2), d(9), "Advance party — FARP Eagle, JRTC rotation")
    for i, p in enumerate(bt["t_5asb_a"][:8]):
        trip(f"trip_a5_{i}", p, "loc_5asb", "loc_farp", "FARP Eagle", 31.15, -93.35, d(-2), d(9), "FARP team — Class III/V at FARP Eagle")
    # MEDEVAC crew on standby at FOB Warrior; a maintenance contact team with them
    for i, p in enumerate(bt["t_4gsab_c"][:4]):
        trip(f"trip_c4_{i}", p, "loc_caaf", "loc_fob", "FOB Warrior — JRTC", 31.06, -93.20, d(-1), d(9), "MEDEVAC standby — FOB Warrior")
    for i, p in enumerate(bt["t_5asb_b"][:3]):
        trip(f"trip_b5_{i}", p, "loc_caaf", "loc_fob", "FOB Warrior — JRTC", 31.06, -93.20, d(-1), d(9), "Maintenance contact team — FOB Warrior")
    # the brigade commander at a corps planning conference, with an itinerary
    cdr = bt["t_cab_hhc"][0]
    trip("trip_cdr", cdr, "loc_bde", None, "Fort Liberty, NC", 35.1401, -79.0060, h(-30), d(2), "Corps planning conference", "travel_system:dts")
    legs += [
        TripLegRow(id="leg_cdr_1", trip_id="trip_cdr", kind="flight", label="C-12 shuttle", ref="DTS-4471", from_name="Campbell Army Airfield", from_lat=36.6717, from_lon=-87.4892, to_name="Simmons Army Airfield", to_lat=35.1318, to_lon=-78.9367, start_at=h(-30), end_at=h(-28), source="travel_system:dts"),
        TripLegRow(id="leg_cdr_2", trip_id="trip_cdr", kind="lodging", label="Airborne Inn (DVQ)", ref="DTS-4471", to_name="Airborne Inn (DVQ)", to_lat=35.1401, to_lon=-79.0060, start_at=h(-27), end_at=d(2), source="travel_system:dts"),
    ]
    # 3 AHB commander to the range for a recon, planned
    trip("trip_3cdr", bt["t_3ahb_hhc"][0], "loc_3ahb", "loc_range", "Peason Ridge Range Complex", 31.40, -93.25, d(3), d(4), "Range recon — Table VI")
    return trips, legs


EVENTS = [
    ("evt_ftx", "Brigade FTX — JRTC Rotation", "exercise", "loc_fob", "FOB Warrior — JRTC", 31.06, -93.20, 21, 10, "Brigade-level rotation. Attack and assault battalions deploy to FOB Warrior; FARP Eagle established D-3."),
    ("evt_gunnery", "Aerial Gunnery — Table VI, 2nd Attack", "training", "loc_range", "Peason Ridge Range Complex", 31.40, -93.25, 5, 3, "Crew qualification. Hellfire and 30 mm. Range hot 0600–2200."),
    ("evt_change", "Change of Command — 4th GSAB", "ceremony", "loc_caaf", "Campbell Army Airfield", 36.6717, -87.4892, 12, 1, "Division commander attending."),
]


def _events(now, people):
    bt = _by_team(people); rows = []
    for eid, name, etype, vloc, vname, vlat, vlon, start_d, dur, desc in EVENTS:
        rows.append(EventRow(id=eid, name=name, event_type=etype, venue_location_id=vloc, venue_name=vname, venue_lat=vlat, venue_lon=vlon,
                             start_at=(now + timedelta(days=start_d)).replace(hour=6, minute=0, second=0, microsecond=0),
                             end_at=(now + timedelta(days=start_d + dur)).replace(hour=22, minute=0, second=0, microsecond=0), description=desc, source="manual:s3"))
    attendees = {"evt_ftx": [p.id for p in bt["t_cab_hhc"][:12]] + [bt["t_1atk_hhc"][0].id, bt["t_2atk_hhc"][0].id, bt["t_3ahb_hhc"][0].id],
                 "evt_gunnery": [p.id for p in bt["t_2atk_a"][:8]] + [bt["t_2atk_hhc"][0].id],
                 "evt_change": [bt["t_cab_hhc"][0].id, bt["t_cab_hhc"][1].id, bt["t_4gsab_hhc"][0].id, bt["t_4gsab_hhc"][1].id]}
    return rows, attendees


def _threats(now):
    h = lambda x: now - timedelta(hours=x)
    return [
        ThreatRow(id="thr_uas", external_id=None, title="Small UAS observed over airfield perimeter", summary="Quadcopter sighted twice this week over the northeast perimeter of the airfield at dusk. Operator not located. Third sighting would meet the reporting threshold.",
                  lat=36.6760, lon=-87.4820, radius_km=3, severity="moderate", event_type="surveillance", source="synthetic", url=None, confidence="moderate", observed_at=h(14), synthetic=True),
        ThreatRow(id="thr_wx", external_id=None, title="Severe thunderstorm watch — Fort Campbell area", summary="Watch in effect through 0300Z. Gusts to 50 kt possible. Aircraft on the ramp to be moored.",
                  lat=36.67, lon=-87.49, radius_km=40, severity="low", event_type="weather", source="synthetic", url=None, confidence="high", observed_at=h(3), synthetic=True),
        ThreatRow(id="thr_acp", external_id=None, title="Suspicious vehicle at ACP 4", summary="Sedan loitered near the access control point for 20 minutes, departed when approached. Plate partial.",
                  lat=36.655, lon=-87.470, radius_km=2, severity="low", event_type="suspicious_activity", source="synthetic", url=None, confidence="low", observed_at=h(9), synthetic=True),
        ThreatRow(id="thr_demo", external_id=None, title="Demonstration planned at Fort Johnson main gate", summary="Permit filed for Saturday, 200 expected. Route passes the FARP resupply convoy's turn.",
                  lat=31.09, lon=-93.24, radius_km=5, severity="low", event_type="civil_unrest", source="synthetic", url=None, confidence="moderate", observed_at=h(20), synthetic=True),
        ThreatRow(id="thr_birds", external_id=None, title="Bird activity NOTAM — Peason Ridge", summary="Migratory activity elevated on the range approach corridor, dawn and dusk.",
                  lat=31.40, lon=-93.25, radius_km=10, severity="low", event_type="hazard", source="synthetic", url=None, confidence="high", observed_at=h(30), synthetic=True),
    ]


def _pirs(now):
    d = lambda x: now + timedelta(days=x)
    return [
        PIRRow(id="pir_uas", question="Will hostile or nuisance UAS observe or attack the airfield or FARP Eagle during the rotation window?", priority=1, status="OPEN", subject_type="location", subject_id="loc_farp", created_at=now, expires_at=d(31)),
        PIRRow(id="pir_wx", question="Will weather ground the heavy-lift company during the D-3 to D-1 movement window?", priority=2, status="OPEN", subject_type="location", subject_id="loc_fob", created_at=now, expires_at=d(21)),
    ]


def _assessments(now):
    return [AssessmentRow(id="asm_uas", title="UAS observation of Campbell Army Airfield", subject_type="location", subject_id="loc_caaf", likelihood="roughly even chance", band="even", confidence="moderate",
                          bluf="A hobbyist or nuisance operator is the most likely explanation; deliberate surveillance cannot be excluded on two sightings.",
                          key_judgments_json='[{"claim": "The sightings are the same platform and operator", "likelihood": "likely", "band": "likely", "confidence": "moderate"}]',
                          gaps_json='["No operator location", "No recovered airframe"]', author="S2", status="review", created_at=now - timedelta(hours=6))]


def _sections(now):
    """§7 and §8 the way a brigade S4 and S6 keep them. Classes of supply by site, aircraft readiness by battalion, comms by PACE per command post."""
    h = lambda x: now + timedelta(hours=x)
    sup = lambda i, loc, cat, item, on, req, unit, note="": SupplyRow(id=f"sup_{i:03d}", location_id=loc, category=cat, item=item, on_hand=on, required=req, unit=unit, note=note, updated_at=h(-4), source="manual:s4")
    supplies = [
        # Class III — fuel
        sup(1, "loc_5asb", "fuel", "JP-8 (Class III) — brigade stock", 180000, 200000, "gal"),
        sup(2, "loc_farp", "fuel", "JP-8 (Class III) — FARP Eagle", 8000, 20000, "gal", "Tanker convoy inbound"),
        # Class V — ammunition
        sup(3, "loc_5asb", "ammunition", "AGM-114 Hellfire", 96, 120, "ea"),
        sup(4, "loc_5asb", "ammunition", "30 mm M789 HEDP", 40000, 60000, "rds", "Draw for Table VI approved"),
        sup(5, "loc_5asb", "ammunition", "2.75 in Hydra 70", 800, 800, "ea"),
        sup(6, "loc_farp", "ammunition", "AGM-114 Hellfire — FARP Eagle", 16, 16, "ea"),
        # Class I / VIII
        sup(7, "loc_fob", "rations", "MRE (Class I)", 900, 1000, "cases"),
        sup(8, "loc_fob", "water", "Bottled water", 2400, 3000, "cases", "Second push scheduled"),
        sup(9, "loc_bde", "medical", "Class VIII — CLS bags (serviceable)", 180, 180, "ea"),
        # Class IX — repair parts
        sup(10, "loc_caaf", "parts", "T700 engines (spare)", 3, 6, "ea", "Two at depot for overhaul"),
        sup(11, "loc_caaf", "parts", "AH-64 main rotor blades", 4, 8, "ea"),
        sup(12, "loc_caaf", "parts", "APU (spare)", 5, 6, "ea"),
        # Equipment readiness — mission-capable airframes by battalion
        sup(13, "loc_1atk", "equipment", "AH-64E mission capable — 1 ATK", 19, 24, "acft", "5 NMC: 3 supply, 2 maintenance"),
        sup(14, "loc_2atk", "equipment", "AH-64E mission capable — 2 ATK", 21, 24, "acft"),
        sup(15, "loc_3ahb", "equipment", "UH-60M mission capable — 3 AHB", 24, 30, "acft", "Phase maintenance ×4"),
        sup(16, "loc_4gsab", "equipment", "CH-47F mission capable — 4 GSAB", 7, 12, "acft", "Rotor blade inspection grounding ×3"),
        sup(17, "loc_4gsab", "equipment", "HH-60M mission capable — 4 GSAB", 10, 12, "acft"),
        sup(18, "loc_5asb", "equipment", "M978 fuel tankers (FMC)", 11, 12, "ea"),
    ]
    shp = lambda i, desc, cat, qty, frm, loc, eta, status, pri, carrier="", ref=None, note="": ShipmentRow(id=f"shp_{i:03d}", description=desc, category=cat, quantity=qty, from_name=frm, to_location_id=loc, eta=eta, status=status, priority=pri, carrier=carrier, ref=ref, note=note, updated_at=h(-1), source="manual:s4")
    shipments = [
        shp(1, "JP-8 tanker convoy", "fuel", "4 × M978 (10,000 gal)", "5 ASB motor pool", "loc_farp", h(5), "in_transit", "urgent", "A/5 convoy", "CONV-0912", "Route clears the demonstration before 1400"),
        shp(2, "T700 engines from depot", "parts", "2 ea", "Corpus Christi Army Depot", "loc_caaf", h(-5), "delayed", "priority", "Line haul", "TCN-77A1", "Carrier missed pickup; rescheduled"),
        shp(3, "Hellfire resupply", "ammunition", "24 ea", "Ammunition supply point", "loc_5asb", h(48), "planned", "routine", "", "DA581-2217"),
        shp(4, "Class I push", "rations", "400 cases MRE · 600 cases water", "Fort Johnson DFAC", "loc_fob", h(-2), "in_transit", "routine", "", None, "Held at the gate for the demonstration"),
        shp(5, "Rotor blade set (CH-47)", "parts", "6 ea", "Depot", "loc_caaf", h(72), "planned", "priority", "", "TCN-77B4"),
    ]
    sy = lambda i, name, cat, loc, pace, status, since, note="": SystemRow(id=f"sys_{i:03d}", name=name, category=cat, location_id=loc, pace=pace, status=status, since=since, note=note, updated_at=since, source="manual:s6")
    systems = []
    n = 0
    for loc, tag in (("loc_bde", "Bde TOC"), ("loc_fob", "FOB Warrior"), ("loc_farp", "FARP Eagle")):
        for name, cat, pace in (("FM — SINCGARS net", "comms", "primary"), ("TACSAT", "comms", "alternate"), ("HF", "comms", "contingency"), ("JBC-P text", "comms", "emergency")):
            n += 1
            status, since, note = "up", h(-700), ""
            if loc == "loc_farp" and pace == "alternate": status, since, note = "down", h(-3), "Antenna damaged on setup; replacement with the convoy"
            if loc == "loc_bde" and pace == "contingency": status, since, note = "degraded", h(-12), "Propagation poor overnight"
            systems.append(sy(n, f"{name} — {tag}", cat, loc, pace, status, since, note))
    for name, cat, loc, status, since, note in (
        ("NIPRNET", "network", "loc_bde", "up", h(-700), ""), ("SIPRNET", "network", "loc_bde", "up", h(-700), ""),
        ("Mission command (CPOF)", "application", "loc_bde", "degraded", h(-5), "Server failover; running on one node"),
        ("JBC-P — blue force tracking", "sensor", None, "up", h(-700), ""), ("AFATDS", "application", "loc_bde", "up", h(-700), ""),
        ("Air traffic services (ATNAVICS)", "sensor", "loc_caaf", "up", h(-700), ""), ("Weather (IMETS)", "application", "loc_bde", "up", h(-700), ""),
        ("TOC generator power", "power", "loc_bde", "up", h(-700), ""), ("SIPRNET — FOB Warrior", "network", "loc_fob", "down", h(-2), "Satellite terminal re-pointing"),
        ("Generator power — FARP Eagle", "power", "loc_farp", "degraded", h(-6), "One of two generators down; fuel at 40%"),
    ):
        n += 1
        systems.append(sy(n, name, cat, loc, None, status, since, note))
    return supplies + shipments + systems


async def populate(session, now) -> None:
    session.add_all([LocationRow(id=i, name=n, type=t, lat=la, lon=lo, city=c, country=co, posture=p, sensitivity=s) for i, n, t, la, lo, c, co, p, s in LOCATIONS])
    session.add_all([TeamRow(id=i, name=n, location_id=loc, function=f, is_security=(f == "hq"), parent_id=parent, echelon=ech, short=short, equipment=equip)
                     for i, n, short, ech, parent, loc, f, equip, _ in TEAMS])
    await session.flush()
    people = _people()
    session.add_all(people)
    await session.flush()
    trips, legs = _movements(now, people)
    session.add_all(trips); session.add_all(legs)
    events, attendees = _events(now, people)
    session.add_all(events)
    await session.flush()
    for eid, ids in attendees.items():
        session.add_all([EventAttendeeRow(event_id=eid, person_id=pid) for pid in ids])
    session.add_all(_threats(now)); session.add_all(_pirs(now)); session.add_all(_assessments(now)); session.add_all(_sections(now))
    # a brigade TOC stands a day and a night watch, not a follow-the-sun desk (§3.1)
    import json
    from sqlalchemy import select
    from .watch import DAY_NIGHT, WatchRow, get_config
    cfg = await get_config(session)
    cfg.pattern, cfg.watches_json = "day_night", json.dumps(DAY_NIGHT)
    for w in (await session.execute(select(WatchRow))).scalars():  # watches stood under the old pattern
        await session.delete(w)
    await session.commit()
