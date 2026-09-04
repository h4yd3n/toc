"""COP API: S1/S2/S3 reads and writes, the three encoded decisions, and the ops ledger."""
import os, tempfile
from datetime import datetime, timedelta, timezone

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"  # the fixed-time INTSUM draft is tested directly, not on a timer
os.environ["TOC_OFFLINE"] = "1"  # collectors and the holiday lookup never touch the network in tests
os.environ.pop("ANTHROPIC_API_KEY", None)  # keep the drafter on the deterministic path in tests
os.environ.pop("TOC_DRAFTER", None)

import pytest
from fastapi.testclient import TestClient

from coptoc.app import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed")
        yield c

def iso(dt): return dt.astimezone(timezone.utc).isoformat()
NOW = datetime.now(timezone.utc)


def test_snapshot_shape_and_counts(client):
    d = client.get("/v1/cop/snapshot").json()
    assert d["summary"]["total_people"] == 97
    assert d["summary"]["traveling"] == 5 and d["summary"]["vips_traveling"] == 4
    assert {l["id"] for l in d["locations"]} >= {"loc_sf", "loc_nyc", "loc_ldn", "loc_dc2"}
    assert len(d["events"]) == 3 and len(d["pirs"]) == 4 and len(d["assessments"]) == 2
    assert all(t["synthetic"] for t in d["threats"])

def test_decision1_restricted_sites_hidden_by_default(client):
    default = client.get("/v1/cop/snapshot").json()
    cleared = client.get("/v1/cop/snapshot", params={"restricted": "true"}, headers={"X-TOC-Role": "battle_captain"}).json()
    assert not any(l["sensitivity"] == "restricted" for l in default["locations"])
    assert sum(1 for l in cleared["locations"] if l["sensitivity"] == "restricted") == 2
    assert default["restricted_included"] is False and cleared["restricted_included"] is True

def test_decision2_fresh_checkin_overrides_derived_position(client):
    d = client.get("/v1/cop/snapshot").json()
    cfo = next(p for p in d["people"] if p["id"] == "p_cfo")
    assert cfo["status"] == "traveling" and cfo["position_source"] == "checkin"
    assert abs(cfo["lat"] - 51.5145) < 1e-6 and cfo["checkin_age_h"] is not None and not cfo["checkin_stale"]
    # A stale check-in falls back to the derived position and is flagged
    r = client.post("/v1/cop/people/p_cto/checkin", json={"lat": 35.0, "lon": 139.0, "note": "old", "at": iso(NOW - timedelta(hours=30))})
    assert r.status_code == 200
    cto = next(p for p in client.get("/v1/cop/snapshot").json()["people"] if p["id"] == "p_cto")
    assert cto["position_source"] == "derived" and cto["checkin_stale"] is True and abs(cto["lat"] - 35.6762) < 1e-6
    # A fresh one takes over
    client.post("/v1/cop/people/p_cto/checkin", json={"lat": 35.70, "lon": 139.70, "note": "hotel"})
    cto = next(p for p in client.get("/v1/cop/snapshot").json()["people"] if p["id"] == "p_cto")
    assert cto["position_source"] == "checkin" and abs(cto["lat"] - 35.70) < 1e-6

def test_decision3_proximity_suggests_confirmation_changes_posture(client):
    d = client.get("/v1/cop/snapshot").json()
    sf = next(l for l in d["locations"] if l["id"] == "loc_sf")
    ldn = next(l for l in d["locations"] if l["id"] == "loc_ldn")
    # SF HQ is inside the Friday-protest ring: suggested, not confirmed, posture unchanged
    assert "thr_006" in sf["threat_ids_in_area"] and "thr_006" not in sf["confirmed_threat_ids"]
    assert sf["posture"] == "normal" and sf["effective_posture"] == "normal"
    # London has an analyst-confirmed low-severity link: effective posture is its own elevated setting
    assert "thr_002" in ldn["confirmed_threat_ids"] and ldn["effective_posture"] == "elevated"
    # Confirm the elevated-severity DC threat against DC-East → effective posture forced to critical
    r = client.post("/v1/cop/threats/thr_004/links", json={"target_type": "location", "target_id": "loc_dc2", "note": "corroborated"},
                    headers={"X-TOC-Actor": "S2 analyst"})
    assert r.status_code == 201
    link_id = r.json()["link_id"]
    dc2 = next(l for l in client.get("/v1/cop/snapshot").json()["locations"] if l["id"] == "loc_dc2")
    assert dc2["posture"] == "elevated" and dc2["effective_posture"] == "critical"
    assert client.get("/v1/cop/snapshot").json()["summary"]["posture"] == "critical"
    # Duplicate confirm is idempotent; unlink restores
    assert client.post("/v1/cop/threats/thr_004/links", json={"target_type": "location", "target_id": "loc_dc2"}).json()["status"] == "already_confirmed"
    assert client.delete(f"/v1/cop/threats/thr_004/links/{link_id}").status_code == 200
    dc2 = next(l for l in client.get("/v1/cop/snapshot").json()["locations"] if l["id"] == "loc_dc2")
    assert dc2["effective_posture"] == "elevated"

def test_event_generates_trips_and_moves_people(client):
    body = {"name": "Product Launch", "event_type": "conference", "venue_name": "Moscone Center", "venue_lat": 37.7842, "venue_lon": -122.4016,
            "start_at": iso(NOW + timedelta(days=10)), "end_at": iso(NOW + timedelta(days=11)),
            "attendee_ids": ["p_ceo", "p_cfo", "p_022"], "description": "Public keynote"}
    r = client.post("/v1/cop/events", json=body, headers={"X-TOC-Actor": "EA - Office of the CEO"})
    assert r.status_code == 201, r.text
    j = r.json(); eid = j["id"]
    assert j["attendees_added"] == 3 and j["trips_generated"] == 3  # venue is a raw coordinate, so everyone travels
    ev = client.get(f"/v1/cop/events/{eid}").json()
    assert ev["status"] == "upcoming" and ev["attendee_count"] == 3 and ev["vip_count"] == 2 and len(ev["trips"]) == 3
    assert all(t["event_id"] == eid and t["status"] == "planned" for t in ev["trips"])
    # Removing an attendee removes their generated trip
    assert client.delete(f"/v1/cop/events/{eid}/attendees/p_022").json()["trip_removed"] is True
    assert len(client.get(f"/v1/cop/events/{eid}").json()["trips"]) == 2
    # Attendee already based at the venue location gets no trip
    r2 = client.post("/v1/cop/events", json={"name": "SF Town Hall", "venue_location_id": "loc_sf", "start_at": iso(NOW + timedelta(days=3)),
                                             "end_at": iso(NOW + timedelta(days=3, hours=2)), "attendee_ids": ["p_ceo", "p_cfo"]})
    assert r2.json()["trips_generated"] == 0  # both are on the SF-based executive team: already at the venue
    ev2 = client.get(f"/v1/cop/events/{r2.json()['id']}").json()
    assert ev2["attendee_count"] == 2
    client.delete(f"/v1/cop/events/{eid}"); client.delete(f"/v1/cop/events/{r2.json()['id']}")

def test_trip_crud_and_validation(client):
    bad = client.post("/v1/cop/trips", json={"person_id": "p_gc", "origin_location_id": "loc_dc", "dest_location_id": "loc_sf",
                                            "depart_at": iso(NOW + timedelta(days=2)), "return_at": iso(NOW + timedelta(days=1))})
    assert bad.status_code == 422
    r = client.post("/v1/cop/trips", json={"person_id": "p_gc", "origin_location_id": "loc_dc", "dest_location_id": "loc_sf",
                                          "depart_at": iso(NOW - timedelta(hours=1)), "return_at": iso(NOW + timedelta(days=1)), "purpose": "Legal review"})
    assert r.status_code == 201
    tid = r.json()["id"]
    gc = next(p for p in client.get("/v1/cop/snapshot").json()["people"] if p["id"] == "p_gc")
    assert gc["status"] == "traveling" and gc["location_id"] == "loc_sf" and gc["trip_id"] == tid
    assert client.patch(f"/v1/cop/trips/{tid}", json={"purpose": "Legal review + board prep"}).json()["changes"]["purpose"]
    assert client.delete(f"/v1/cop/trips/{tid}").json()["status"] == "cancelled"
    gc = next(p for p in client.get("/v1/cop/snapshot").json()["people"] if p["id"] == "p_gc")
    assert gc["status"] == "at_post"

def test_posture_shift_and_ledger(client):
    r = client.patch("/v1/cop/locations/loc_sgp/posture", json={"posture": "elevated", "reason": "Regional advisory"}, headers={"X-TOC-Actor": "Battle Captain"})
    assert r.json()["posture"] == "elevated"
    r = client.patch("/v1/cop/people/p_007/shift", json={"on_shift": True, "shift_role": "Watch Officer"})
    assert r.json()["shift_role"] == "Watch Officer"
    log = client.get("/v1/cop/log", params={"limit": 100}).json()
    types = [e["type"] for e in log]
    assert "cop.location.posture" in types and "cop.person.shift" in types and "cop.trip.created" in types and "cop.event.created" in types
    posture_evt = next(e for e in log if e["type"] == "cop.location.posture")
    assert posture_evt["actor"] == "Battle Captain" and posture_evt["old"] == "normal" and posture_evt["new"] == "elevated"
    # Every subject's chain verifies
    from coptoc.routes import get_ledger
    import asyncio
    assert asyncio.run(get_ledger().verify_chain_integrity("loc_sgp")) is True
    client.patch("/v1/cop/locations/loc_sgp/posture", json={"posture": "normal"})

def test_pir_and_assessment_lifecycle(client):
    r = client.post("/v1/cop/pirs", json={"question": "Is the Moscone perimeter covered by CCTV?", "priority": 1, "subject_type": "location", "subject_id": "loc_sf"})
    assert r.status_code == 201 and r.json()["id"].startswith("PIR-")
    pid = r.json()["id"]
    assert client.patch(f"/v1/cop/pirs/{pid}", json={"status": "COLLECTING"}).json()["status"] == "COLLECTING"
    # Draft an assessment for the CEO trip — heuristic path unless ANTHROPIC_API_KEY is set
    r = client.post("/v1/cop/assessments/draft", json={"subject_type": "trip", "subject_id": "trip_001"})
    assert r.status_code == 201, r.text
    d = r.json()
    from sigtoc.analysis.wall_drafter import ICD203_TERMS
    assert d["likelihood"] in ICD203_TERMS and d["band"] == ICD203_TERMS[d["likelihood"]]
    assert d["confidence"] in ("low", "moderate", "high", "insufficient") and d["evidence"]
    assert d["status"] == "draft"
    assert client.patch(f"/v1/cop/assessments/{d['id']}", json={"status": "review"}).json()["status"] == "review"
    # A subject with no threats in area must refuse — and refusal cannot be approved
    r = client.post("/v1/cop/assessments/draft", json={"subject_type": "location", "subject_id": "loc_tyo"})
    assert r.status_code == 201
    ref = r.json()
    assert ref["confidence"] == "insufficient" and ref["refused"] is True
    assert client.patch(f"/v1/cop/assessments/{ref['id']}", json={"status": "approved"}).status_code == 409


def test_accountability_roll_call(client):
    # An earthquake at SF HQ: open a roll call on the site → everyone present is UNACCOUNTED
    r = client.post("/v1/cop/incidents", json={"location_id": "loc_sf", "title": "Earthquake — SF HQ", "notes": "M5.8 reported 12 km SE"}, headers={"X-TOC-Actor": "Battle Captain", "X-TOC-Role": "battle_captain"})
    assert r.status_code == 201, r.text
    inc = r.json(); iid = inc["id"]
    snap = client.get("/v1/cop/snapshot").json()
    present_sf = sum(1 for p in snap["people"] if p["location_id"] == "loc_sf")
    assigned_sf = sum(1 for p in snap["people"] if p["home_location_id"] == "loc_sf")
    # Decision A: everyone on site now + everyone assigned to the site who is elsewhere (the traveling execs)
    assert inc["roster"] == assigned_sf and inc["present"] == present_sf and inc["assigned"] == assigned_sf - present_sf
    d = client.get(f"/v1/cop/incidents/{iid}").json()
    assert d["counts"]["unaccounted"] == assigned_sf and d["pct"] == 0 and all(x["phone"] for x in d["roster"])
    assert {x["basis"] for x in d["roster"]} == {"present", "assigned"}
    assert next(x for x in d["roster"] if x["person_id"] == "p_ceo")["basis"] == "assigned"  # the CEO is in Riyadh but is on the SF roster
    assert snap["summary"]["open_incidents"] == 1 and snap["summary"]["unaccounted"] == assigned_sf
    present_sf = assigned_sf  # the rest of this test counts against the full roster
    # People in the roster carry the status on the wall
    assert next(p for p in snap["people"] if p["id"] == "p_coo")["incident_status"] == "unaccounted"
    # Work the roster: a call reaches the COO; the next one gets no answer, then a callback needs assistance
    assert client.patch(f"/v1/cop/incidents/{iid}/roster/p_coo", json={"status": "safe", "method": "call", "note": "At home, fine"}).json()["attempts"] == 1
    client.patch(f"/v1/cop/incidents/{iid}/roster/p_gc", json={"status": "unreachable", "method": "call"})
    r2 = client.patch(f"/v1/cop/incidents/{iid}/roster/p_gc", json={"status": "assist", "method": "call", "note": "Trapped in elevator, floor 4"})
    assert r2.json()["attempts"] == 2
    d = client.get(f"/v1/cop/incidents/{iid}").json()
    assert d["counts"]["safe"] == 1 and d["counts"]["assist"] == 1 and d["counts"]["unaccounted"] == present_sf - 2
    assert d["roster"][0]["status"] == "assist" and d["roster"][-1]["status"] == "safe"  # Decision M order: needs-assist and unreachable float above unaccounted; safe sinks
    assert [x["status"] for x in d["roster"]][-1] == "safe"
    # Every contact attempt is on the ledger, in order, hash-chained under the incident
    log = [e for e in client.get("/v1/cop/log", params={"limit": 200}).json() if e["subject"] == iid]
    assert [e["type"] for e in log][:4] == ["cop.incident.contact", "cop.incident.contact", "cop.incident.contact", "cop.incident.opened"]
    assert "Trapped in elevator" in log[0]["summary"]
    from coptoc.routes import get_ledger
    import asyncio
    assert asyncio.run(get_ledger().verify_chain_integrity(iid)) is True
    # Closing records how many were never reached; the incident leaves the open count
    assert client.patch(f"/v1/cop/incidents/{iid}/close", json={"notes": "All clear"}).json()["unaccounted"] == present_sf - 2
    assert client.get("/v1/cop/snapshot").json()["summary"]["open_incidents"] == 0
    assert client.patch(f"/v1/cop/incidents/{iid}/roster/p_coo", json={"status": "safe"}).status_code == 409

def test_decisionB_checkin_request_and_self_clear(client):
    iid = client.post("/v1/cop/incidents", json={"location_id": "loc_nyc", "title": "Gas leak — NYC"}, headers={"X-TOC-Role": "battle_captain"}).json()["id"]
    before = client.get(f"/v1/cop/incidents/{iid}").json()
    r = client.post(f"/v1/cop/incidents/{iid}/request-checkins", headers={"X-TOC-Actor": "Battle Captain"})
    j = r.json()
    assert j["requested"] == before["total"]
    # Decision 1: both channels, every person; nothing configured in tests → SIMULATED, never "sent"
    assert j["simulated"] is True and j["deliveries"]["sms"]["simulated"] == before["total"] and j["deliveries"]["chat"]["simulated"] == before["total"]
    assert j["deliveries"]["sms"]["sent"] == 0 and j["deliveries"]["chat"]["sent"] == 0
    d = client.get(f"/v1/cop/incidents/{iid}").json()
    assert d["checkins_requested"] == d["total"] and all(x["checkin_requested_at"] for x in d["roster"])
    assert d["channels"] == ["sms", "chat"] and {x["channel"] for x in d["roster"][0]["deliveries"]} == {"sms", "chat"}
    assert all(x["status"] == "simulated" for x in d["roster"][0]["deliveries"])
    log = [e for e in client.get("/v1/cop/log", params={"limit": 50}).json() if e["subject"] == iid]
    assert "SIMULATED" in log[0]["summary"]
    # The link in the message works with no auth and no coordinates — that's the SMS reply path
    from coptoc.routes import checkin_token
    linked = d["roster"][1]["person_id"]
    r = client.post(f"/v1/cop/checkin/{checkin_token(linked, iid)}")
    assert r.status_code == 200 and r.json()["cleared_rosters"] == [iid]
    assert next(x for x in client.get(f"/v1/cop/incidents/{iid}").json()["roster"] if x["person_id"] == linked)["status"] == "safe"
    assert client.post(f"/v1/cop/checkin/{linked}.{iid}.deadbeefdeadbeefdead").status_code == 404
    # A person on the roster checks in from their phone → their row clears to SAFE via app, no call needed
    someone = d["roster"][0]["person_id"]
    r = client.post(f"/v1/cop/people/{someone}/checkin", json={"lat": 40.71, "lon": -74.0, "note": "I'm fine, outside on Broadway"})
    assert r.json()["cleared_rosters"] == [iid]
    d = client.get(f"/v1/cop/incidents/{iid}").json()
    row = next(x for x in d["roster"] if x["person_id"] == someone)
    assert row["status"] == "safe" and row["method"] == "app" and "Broadway" in row["note"] and d["counts"]["safe"] == 2  # link check-in above + this one
    log = [e for e in client.get("/v1/cop/log", params={"limit": 50}).json() if e["subject"] == iid]
    assert [e["type"] for e in log[:3]] == ["cop.incident.contact", "cop.incident.contact", "cop.incident.checkins_requested"]  # app check-in, link check-in, the request
    assert "self check-in" in log[0]["summary"]
    client.patch(f"/v1/cop/incidents/{iid}/close", json={})

def test_decision3_only_battle_captain_opens_roll_calls(client):
    for role in ("security", "ep", "analyst", None):
        h = {"X-TOC-Role": role} if role else {}
        r = client.post("/v1/cop/incidents", json={"location_id": "loc_tyo"}, headers=h)
        assert r.status_code == 403, role
    r = client.post("/v1/cop/incidents", json={"location_id": "loc_tyo"}, headers={"X-TOC-Role": "battle_captain"})
    assert r.status_code == 201
    iid = r.json()["id"]
    # Anyone on the floor may work the roster once it's open
    who = client.get(f"/v1/cop/incidents/{iid}").json()["roster"][0]["person_id"]
    assert client.patch(f"/v1/cop/incidents/{iid}/roster/{who}", json={"status": "safe"}, headers={"X-TOC-Role": "security"}).status_code == 200
    # Decision 2: may close with names still unaccounted — recorded, not blocked
    r = client.patch(f"/v1/cop/incidents/{iid}/close", json={"notes": "Drill complete"}, headers={"X-TOC-Role": "battle_captain"})
    assert r.status_code == 200 and r.json()["unaccounted"] > 0

def test_decisionC_restricted_layer_is_role_gated(client):
    for role, allowed in (("battle_captain", True), ("ep", True), ("security", False), ("analyst", False), (None, False)):
        h = {"X-TOC-Role": role} if role else {}
        d = client.get("/v1/cop/snapshot", params={"restricted": "true"}, headers=h).json()
        n = sum(1 for l in d["locations"] if l["sensitivity"] == "restricted")
        assert (n == 2) is allowed and d["restricted_included"] is allowed and d["restricted_denied"] is (not allowed), role
    # not asking for it is never a denial
    assert client.get("/v1/cop/snapshot", headers={"X-TOC-Role": "analyst"}).json()["restricted_denied"] is False

def test_provenance_is_exposed(client):
    snap = client.get("/v1/cop/snapshot").json()
    assert next(p for p in snap["people"] if p["id"] == "p_ceo")["source"] == "hris:workday"
    assert {t["source"] for t in snap["trips"]} >= {"travel_system:concur", "calendar:google", "manual:ea", "event"}
    assert all(e["source"] == "calendar:google" for e in snap["events"])


# ---- §3.1 the watch ----
BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "Battle Captain"}

def test_watch_is_derived_and_on_the_snapshot(client):
    w = client.get("/v1/cop/watch").json()
    assert w["name"] in ("Singapore", "Dublin", "San Francisco") and w["pattern"] == "follow_the_sun" and 0 <= w["elapsed_h"] <= 8
    assert w["next_watch"] != w["name"] and w["overlap_minutes"] == 30
    snap = client.get("/v1/cop/snapshot").json()
    assert snap["watch"]["id"] == w["id"] and [e["section"] for e in snap["estimates"]] == ["S1", "S2", "S3", "S6"]

def test_estimates_are_owned_per_section(client):
    assert client.patch("/v1/cop/watch/estimate/S2", json={"assessment": "x"}, headers={"X-TOC-Role": "ea"}).status_code == 403
    r = client.patch("/v1/cop/watch/estimate/S2", json={"assessment": "Threat picture stable; DC-East single-source rhetoric only", "recommendation": "Hold DC-East at elevated"},
                     headers={"X-TOC-Role": "analyst", "X-TOC-Actor": "S2 duty analyst"})
    assert r.status_code == 200 and r.json()["updated_by"] == "S2 duty analyst"
    assert client.patch("/v1/cop/watch/estimate/S3", json={"assessment": "Two VIP moves tomorrow"}, headers={"X-TOC-Role": "ea"}).status_code == 200
    assert client.patch("/v1/cop/watch/estimate/S9", json={"assessment": "x"}, headers=BC).status_code == 404
    est = {e["section"]: e for e in client.get("/v1/cop/snapshot").json()["estimates"]}
    assert est["S2"]["assessment"].startswith("Threat picture") and est["S2"]["recommendation"].startswith("Hold")

def test_take_handover_acknowledge_transfers_the_watch(client):
    assert client.post("/v1/cop/watch/take", json={"battle_captain": "Anyone"}, headers={"X-TOC-Role": "security"}).status_code == 403
    w = client.post("/v1/cop/watch/take", json={"battle_captain": "R. Kovac"}, headers=BC).json()
    assert w["battle_captain"] == "R. Kovac" and w["status"] == "open"
    assert client.post("/v1/cop/watch/take", json={"battle_captain": "Someone Else"}, headers=BC).status_code == 409
    # The brief is generated live, in briefing order, from the wall's own data
    b = client.get("/v1/cop/watch/brief").json()
    for k in ("significant_events", "current_status", "next_shift", "handover_items", "acknowledgement"):
        assert k in b
    assert b["current_status"]["posture"] in ("normal", "elevated", "critical") and isinstance(b["current_status"]["estimates"], list)
    assert "estimates" not in b["significant_events"]  # estimate edits are context, not events to brief
    # Outgoing hands over with notes; the watch is now pending and the brief is frozen
    b2 = client.post("/v1/cop/watch/handover", json={"notes": "Watch the Vegas kickoff planning thread; EP still short two agents."}, headers=BC).json()
    assert b2["outgoing_notes"].startswith("Watch the Vegas") and b2["nstr"] is False
    assert b2["watch"]["status"] == "pending_ack" and b2["watch"]["handed_over_at"]  # the frozen brief describes a pending watch
    assert client.get("/v1/cop/watch/brief").json()["watch"]["status"] == "pending_ack"
    assert client.get("/v1/cop/watch").json()["status"] == "pending_ack"
    assert client.post("/v1/cop/watch/handover", json={}, headers=BC).status_code == 409
    # Incoming acknowledges → the watch transfers, both names on the ledger, the next slot is now held
    # If the clock happens to be inside the slot's overlap window, the seed events count as arrivals during handover
    # and must be acknowledged one by one (that rule is tested on its own below); acknowledge whatever the brief requires
    required = client.get("/v1/cop/watch/brief").json()["acknowledgement"]["required_item_ids"]
    r = client.post("/v1/cop/watch/acknowledge", json={"battle_captain": "T. Whitfield", "acknowledged_item_ids": required}, headers=BC)
    assert r.status_code == 200, r.text
    assert r.json()["now_holding"]["battle_captain"] == "T. Whitfield" and r.json()["now_holding"]["status"] == "open"
    log = client.get("/v1/cop/log", params={"limit": 20}).json()
    types = [e["type"] for e in log[:3]]
    assert types[0] == "cop.watch.taken" and types[1] == "cop.watch.acknowledged"
    assert "R. Kovac → T. Whitfield" in log[1]["summary"]
    assert client.post("/v1/cop/watch/acknowledge", json={"battle_captain": "X"}, headers=BC).status_code == 409

def test_overlap_items_must_be_acknowledged_individually_and_nstr_is_affirmed(client):
    import asyncio
    from datetime import datetime, timedelta, timezone
    from coptoc.routes import sessions
    from coptoc.watch import WatchRow
    from sqlalchemy import select
    # Pull the current watch's end to 10 minutes from now so the overlap window is live
    async def shorten():
        async with sessions()() as s:
            row = (await s.execute(select(WatchRow).where(WatchRow.status == "open").order_by(WatchRow.started_at.desc()))).scalars().first()
            row.ends_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10); await s.commit(); return row.id
    wid = asyncio.run(shorten())
    # Something happens inside the overlap
    client.patch("/v1/cop/locations/loc_sgp/posture", json={"posture": "elevated", "reason": "Regional advisory during handover"}, headers=BC)
    b = client.post("/v1/cop/watch/handover", json={"nstr": True}, headers=BC).json()
    assert b["nstr"] is True and b["watch"]["in_overlap"] is True
    required = b["acknowledgement"]["required_item_ids"]
    assert len(required) >= 1 and all(e["during_handover"] for e in b["significant_events"]["posture"])
    # Acknowledging without the overlap items is refused; with them, the watch transfers
    assert client.post("/v1/cop/watch/acknowledge", json={"battle_captain": "N. Haddad"}, headers=BC).status_code == 409
    r = client.post("/v1/cop/watch/acknowledge", json={"battle_captain": "N. Haddad", "acknowledged_item_ids": required}, headers=BC)
    assert r.status_code == 200
    log = client.get("/v1/cop/log", params={"limit": 10}).json()
    ho = next(e for e in log if e["type"] == "cop.watch.handover" and e["subject"] == wid)
    assert "NSTR" in ho["summary"] and "affirmed" in ho["summary"]
    client.patch("/v1/cop/locations/loc_sgp/posture", json={"posture": "normal"}, headers=BC)

def test_shift_pattern_is_configurable(client):
    assert client.patch("/v1/cop/watch/config", json={"pattern": "day_night"}, headers={"X-TOC-Role": "security"}).status_code == 403
    r = client.patch("/v1/cop/watch/config", json={"pattern": "day_night", "overlap_minutes": 45}, headers=BC)
    assert r.json() == {"pattern": "day_night", "overlap_minutes": 45}
    w = client.get("/v1/cop/watch").json()
    assert w["overlap_minutes"] == 45
    client.patch("/v1/cop/watch/config", json={"pattern": "follow_the_sun", "overlap_minutes": 30}, headers=BC)


# ---------------------------------------------------------------- S6 decisions L–N

def test_decision_n_anyone_adds_a_missed_name(client):
    inc = client.post("/v1/cop/incidents", json={"location_id": "loc_sf"}, headers={"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}).json()
    r = client.post(f"/v1/cop/incidents/{inc['id']}/roster", json={"name": "Jordan Blake", "phone": "+1 415 555 0199", "role": "Contractor — HVAC", "note": "seen on floor 3"},
                    headers={"X-TOC-Role": "security", "X-TOC-Actor": "guard_07"})
    assert r.status_code == 201, r.text
    pid = r.json()["person_id"]
    assert r.json()["basis"] == "manual" and pid.startswith("p_man_")
    assert client.post(f"/v1/cop/incidents/{inc['id']}/roster", json={"person_id": pid}).status_code == 409  # already on it
    i = next(x for x in client.get("/v1/cop/snapshot").json()["incidents"] if x["id"] == inc["id"])
    row = next(x for x in i["roster"] if x["person_id"] == pid)
    assert row["basis"] == "manual" and row["status"] == "unaccounted" and row["phone"] == "+1 415 555 0199"
    assert any(e["type"] == "cop.incident.roster_added" for e in client.get("/v1/cop/log", params={"limit": 5}).json())
    client.patch(f"/v1/cop/incidents/{inc['id']}/close", json={})


def test_decision_m_fifteen_minutes_without_response_escalates_and_floats(client):
    import asyncio
    from coptoc.routes import escalate_due, sessions
    inc = client.post("/v1/cop/incidents", json={"location_id": "loc_nyc"}, headers={"X-TOC-Role": "battle_captain"}).json()
    client.post(f"/v1/cop/incidents/{inc['id']}/request-checkins")
    async def run(minutes):
        async with sessions()() as s:
            return await escalate_due(s, datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=minutes))
    assert asyncio.run(run(10)) == []  # too early
    done = asyncio.run(run(16))
    assert len(done) == inc["roster"] and all(d["incident_id"] == inc["id"] for d in done)
    assert asyncio.run(run(17)) == []  # idempotent
    i = next(x for x in client.get("/v1/cop/snapshot").json()["incidents"] if x["id"] == inc["id"])
    assert i["counts"]["unreachable"] == inc["roster"] and i["roster"][0]["status"] == "unreachable" and i["roster"][0]["updated_by"] == "rule:escalation-15m"
    # a name marked SAFE sorts below the escalated ones
    client.patch(f"/v1/cop/incidents/{inc['id']}/roster/{i['roster'][-1]['person_id']}", json={"status": "safe"})
    i = next(x for x in client.get("/v1/cop/snapshot").json()["incidents"] if x["id"] == inc["id"])
    assert i["roster"][0]["status"] == "unreachable" and i["roster"][-1]["status"] == "safe"
    assert any(e["type"] == "cop.incident.escalated" for e in client.get("/v1/cop/log", params={"limit": 10}).json())
    client.patch(f"/v1/cop/incidents/{inc['id']}/close", json={})


def test_decision_l_inbound_sms_clears_or_flags_by_phone(client):
    os.environ.pop("TWILIO_AUTH_TOKEN", None)  # simulator mode: no signature required
    inc = client.post("/v1/cop/incidents", json={"location_id": "loc_ldn"}, headers={"X-TOC-Role": "battle_captain"}).json()
    i = next(x for x in client.get("/v1/cop/snapshot").json()["incidents"] if x["id"] == inc["id"])
    with_phone = [r for r in i["roster"] if r["phone"]]
    assert with_phone, "seed people need phones for this test"
    a, b = with_phone[0], with_phone[1]
    r = client.post("/v1/cop/comms/sms/inbound", data={"From": a["phone"], "Body": "SAFE, at the hotel"})
    assert r.status_code == 200 and "marked SAFE" in r.text and r.headers["content-type"].startswith("application/xml")
    r2 = client.post("/v1/cop/comms/sms/inbound", data={"From": b["phone"], "Body": "help — stuck in the lift"})
    assert "calling you now" in r2.text
    unknown = client.post("/v1/cop/comms/sms/inbound", data={"From": "+1 999 000 0000", "Body": "SAFE"})
    assert "not on file" in unknown.text
    i = next(x for x in client.get("/v1/cop/snapshot").json()["incidents"] if x["id"] == inc["id"])
    st = {r["person_id"]: r for r in i["roster"]}
    assert st[a["person_id"]]["status"] == "safe" and st[a["person_id"]]["method"] == "sms"
    assert st[b["person_id"]]["status"] == "assist" and i["roster"][0]["status"] == "assist"  # needs-assist floats above unaccounted
    # with Twilio configured, an unsigned request is refused
    os.environ["TWILIO_AUTH_TOKEN"] = "test-token"
    try:
        assert client.post("/v1/cop/comms/sms/inbound", data={"From": a["phone"], "Body": "SAFE"}).status_code == 403
    finally:
        os.environ.pop("TWILIO_AUTH_TOKEN", None)
    client.patch(f"/v1/cop/incidents/{inc['id']}/close", json={})
