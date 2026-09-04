"""§13: the connectors, as export adapters — people, shifts, trips, calendar ICS, badge events — with provenance."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app
from coptoc.imports import parse_ics

EA = {"X-TOC-Role": "ea", "X-TOC-Actor": "EA - Office of the CEO"}
BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed")
        yield c


def test_people_and_shifts_from_csv_with_provenance(client):
    csv = "id,name,role,team_name,is_vip,phone,email\n,Nora Vale,Site Security Lead,Security — SF,false,+1 415 555 0177,nora.vale@example.com\np_ceo,Alex Ventura,CEO,Executive Leadership,true,,\nbad,No Team,Analyst,Nowhere,,,\n"
    r = client.post("/v1/cop/import/people", json={"text": csv}, headers=EA)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["created"] == 1 and d["updated"] == 1 and d["skipped"] == 1 and "row 3" in d["errors"][0]
    snap = client.get("/v1/cop/snapshot").json()
    nora = next(p for p in snap["people"] if p["name"] == "Nora Vale")
    assert nora["source"] == "hris:csv" and nora["phone"] == "+1 415 555 0177" and nora["team_name"] == "Security — SF"
    s = client.post("/v1/cop/import/shifts", json={"text": "email,on_shift,shift_role\nnora.vale@example.com,true,lead\nnobody@example.com,true,\n"}, headers=BC).json()
    assert s["updated"] == 1 and s["skipped"] == 1
    nora = next(p for p in client.get("/v1/cop/snapshot").json()["people"] if p["name"] == "Nora Vale")
    assert nora["on_shift"] is True and nora["availability"] == "on_shift"
    assert client.post("/v1/cop/import/people", json={"text": csv}, headers={"X-TOC-Role": "ep"}).status_code == 403


def test_trips_from_travel_export_upsert_by_booking_ref(client):
    csv = "email,origin_location_id,dest_location_id,dest_name,dest_lat,dest_lon,depart_at,return_at,purpose,booking_ref\n" \
          "nora.vale@example.com,loc_sf,,Lisbon Portugal,38.72,-9.14,2026-10-13T08:00:00Z,2026-10-18T20:00:00Z,offsite advance,BK123\n" \
          "nora.vale@example.com,loc_sf,loc_nyc,,,,2026-11-01,2026-10-30,backwards,BK124\n"
    d = client.post("/v1/cop/import/trips", json={"text": csv}, headers=EA).json()
    assert d["created"] == 1 and d["skipped"] == 1
    d2 = client.post("/v1/cop/import/trips", json={"text": csv.replace("offsite advance", "offsite advance (revised)")}, headers=EA).json()
    assert d2["updated"] == 1 and d2["created"] == 0
    t = next(t for t in client.get("/v1/cop/snapshot").json()["trips"] if t["id"] == "trip_BK123")
    assert t["source"] == "travel_system:csv" and t["purpose"].endswith("(revised)") and t["dest_name"] == "Lisbon Portugal"
    assert any(r["id"] == "req_trip_trip_BK123" for r in client.get("/v1/s2/requirements", params={"kind": "standing"}).json())  # the wall's requirements follow


ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:abc-123@example.com
SUMMARY:Investor Day
LOCATION:New York Office
DTSTART:20261105T140000Z
DTEND:20261105T200000Z
DESCRIPTION:Half-day investor briefing\\, closed session.
ATTENDEE;CN=Nora Vale:mailto:nora.vale@example.com
ATTENDEE:mailto:ghost@example.com
END:VEVENT
BEGIN:VEVENT
UID:def-456
SUMMARY:Field visit
LOCATION:Somewhere with no site
DTSTART:20261110T090000Z
END:VEVENT
BEGIN:VEVENT
UID:geo-789
SUMMARY:Vendor summit
LOCATION:Hotel Arts
GEO:41.3874;2.1966
DTSTART:20261201T090000Z
DTEND:20261202T170000Z
END:VEVENT
END:VCALENDAR
"""

def test_calendar_ics_creates_events_and_reports_what_it_cannot_place(client):
    evs = parse_ics(ICS)
    assert [e["summary"] for e in evs] == ["Investor Day", "Field visit", "Vendor summit"] and evs[0]["attendees"] == ["nora.vale@example.com", "ghost@example.com"]
    d = client.post("/v1/cop/import/ics", json={"text": ICS}, headers=EA).json()
    assert d["created"] == 2 and d["skipped"] == 1 and d["trips_generated"] >= 1
    assert any("Field visit" in e and "not a known site" in e for e in d["errors"]) and any("ghost@example.com" in e for e in d["errors"])
    snap = client.get("/v1/cop/snapshot").json()
    inv = next(e for e in snap["events"] if e["name"] == "Investor Day")
    assert inv["venue_location_id"] == "loc_nyc" and inv["source"] == "calendar:ics" and inv["attendee_count"] == 1
    art = next(e for e in snap["events"] if e["name"] == "Vendor summit")
    assert abs(art["venue_lat"] - 41.3874) < 1e-4 and art["venue_location_id"] is None
    d2 = client.post("/v1/cop/import/ics", json={"text": ICS}, headers=EA).json()
    assert d2["updated"] == 2 and d2["created"] == 0 and d2["trips_generated"] == 0  # idempotent by UID


def test_badge_in_is_a_checkin_at_the_site(client):
    r = client.post("/v1/cop/import/badge/events", json={"events": [{"email": "nora.vale@example.com", "location_id": "loc_nyc", "direction": "in"}, {"person_id": "p_nobody", "location_id": "loc_sf"}]})
    assert r.status_code == 200 and r.json()["applied"] == 1 and r.json()["skipped"] == 1
    nora = next(p for p in client.get("/v1/cop/snapshot").json()["people"] if p["name"] == "Nora Vale")
    assert nora["position_source"] == "checkin" and nora["last_checkin_note"].startswith("Badge in — New York Office")
    assert any(e["type"] == "cop.import" for e in client.get("/v1/cop/log", params={"limit": 5}).json())
