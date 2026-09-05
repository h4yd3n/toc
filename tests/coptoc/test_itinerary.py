"""§6 itineraries: legs are optional on every trip; the traveler's pin follows the current leg; imports place or report."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app
from coptoc.imports import parse_itinerary

EA = {"X-TOC-Role": "ea", "X-TOC-Actor": "EA - Office of the CEO"}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed")
        yield c


def trip(client, tid):
    return next(t for t in client.get("/v1/cop/trips").json() if t["id"] == tid)


def test_legs_are_optional_and_ordered(client):
    trips = client.get("/v1/cop/trips").json()
    ceo = next(t for t in trips if t["id"] == "trip_001"); cfo = next(t for t in trips if t["id"] == "trip_002")
    assert [l["kind"] for l in ceo["legs"]] == ["flight", "flight", "ground", "lodging"]
    assert ceo["current_leg"]["kind"] == "lodging" and ceo["current_leg"]["label"] == "Ritz-Carlton Riyadh"
    assert [l["status"] for l in ceo["legs"]] == ["done", "done", "done", "current"]
    assert cfo["legs"] == [] and cfo["current_leg"] is None  # no itinerary supplied: blank, not invented


def test_pin_follows_the_current_leg(client):
    people = {p["id"]: p for p in client.get("/v1/cop/snapshot").json()["people"]}
    cso = people["p_cso"]  # SQ 31 still airborne: placed at the arrival airport, not the office
    assert cso["status"] == "traveling" and abs(cso["lat"] - 1.3644) < 1e-3 and abs(cso["lon"] - 103.9915) < 1e-3
    ceo = people["p_ceo"]  # at the hotel, not the city centroid
    assert abs(ceo["lat"] - 24.6905) < 1e-3
    cfo = people["p_cfo"]  # no legs: the destination, unless a fresh check-in overrides (the seed gives the CFO one)
    assert cfo["position_source"] in ("checkin", "derived")


def test_add_and_remove_a_leg(client):
    body = {"kind": "ground", "label": "Rail", "from_name": "London Paddington", "from_lat": 51.5154, "from_lon": -0.1755,
            "to_name": "Canary Wharf", "to_lat": 51.5054, "to_lon": -0.0235, "start_at": "2026-09-05T08:00:00Z", "end_at": "2026-09-05T08:40:00Z"}
    r = client.post("/v1/cop/trips/trip_002/legs", json=body, headers=EA)
    assert r.status_code == 201, r.text
    lid = r.json()["id"]
    assert [l["id"] for l in trip(client, "trip_002")["legs"]] == [lid]
    assert client.post("/v1/cop/trips/trip_002/legs", json={**body, "end_at": body["start_at"]}, headers=EA).status_code == 422
    assert client.post("/v1/cop/trips/trip_002/legs", json={**body, "from_name": None}, headers=EA).status_code == 422
    log = client.get("/v1/cop/log?limit=5").json()
    assert log[0]["type"] == "cop.trip.leg_added"
    assert client.delete(f"/v1/cop/trips/trip_002/legs/{lid}", headers=EA).status_code == 200
    assert trip(client, "trip_002")["legs"] == []


def test_parse_itinerary_places_or_reports():
    legs, errors = parse_itinerary(
        "FLIGHT UA 954 SFO-LHR 2026-09-04 18:10 - 2026-09-05 12:25 conf K7X2ZQ\n"
        "FLIGHT BA 263 LHR-RUH 2026-09-05T15:00Z → 2026-09-05T23:20Z\n"
        "HOTEL Ritz-Carlton Riyadh @24.6905,46.6250 2026-09-05 - 2026-09-08 conf 88112\n"
        "GROUND Car service RUH-@24.6905,46.6250:hotel 2026-09-05 23:40 - 2026-09-06 00:30\n"
        "FLIGHT XX 1 ZZZ-LHR 2026-09-05 - 2026-09-06\n"
        "HOTEL Somewhere 2026-09-05 - 2026-09-06\n"
        "gibberish\n")
    assert [l["kind"] for l in legs] == ["flight", "flight", "lodging", "ground"]
    assert legs[0]["label"] == "UA 954" and legs[0]["ref"] == "K7X2ZQ" and legs[0]["from_name"].endswith("SFO") and legs[0]["to_name"].endswith("LHR")
    assert legs[2]["to_lat"] == 24.6905 and legs[2]["label"] == "Ritz-Carlton Riyadh" and legs[3]["to_name"] == "hotel"
    assert len(errors) == 3 and "ZZZ" in errors[0] and "line 6" in errors[1] and "line 7" in errors[2]


def test_import_itinerary_and_legs_csv(client):
    r = client.post("/v1/cop/import/itinerary", json={"text": "TRIP trip_006\nFLIGHT UA 1010 IAD-MEX 2026-09-09 08:00 - 2026-09-09 13:30 conf Q1\nHOTEL Four Seasons Mexico City @19.4270,-99.1707 2026-09-09 15:00 - 2026-09-11 conf Q1\nFLIGHT UA 1 ZZZ-IAD 2026-09-11 - 2026-09-12\n"}, headers=EA).json()
    assert r["trip_id"] == "trip_006" and r["created"] == 2 and r["skipped"] == 1
    assert [l["label"] for l in trip(client, "trip_006")["legs"]] == ["UA 1010", "Four Seasons Mexico City"]
    bad = client.post("/v1/cop/import/itinerary", json={"text": "FLIGHT UA 1 SFO-LHR 2026-09-09 - 2026-09-10"}, headers=EA).json()
    assert bad["created"] == 0 and "line 1" in bad["errors"][0]
    csv = ("trip_id,kind,label,ref,from_name,from_lat,from_lon,to_name,to_lat,to_lon,start_at,end_at\n"
           "trip_005,flight,EK 226,Z9C1WW,San Francisco SFO,37.6213,-122.3790,Dubai DXB,25.2532,55.3657,2026-09-07T20:00:00Z,2026-09-08T12:00:00Z\n"
           "trip_005,lodging,Address Downtown Dubai,NEW1,,,,Address Downtown Dubai,25.1934,55.2774,2026-09-08T13:00:00Z,2026-09-10T08:00:00Z\n"
           "trip_nope,flight,X,,A,0,0,B,0,0,2026-09-08T13:00:00Z,2026-09-10T08:00:00Z\n")
    r = client.post("/v1/cop/import/legs", json={"text": csv}, headers=EA).json()
    assert r["updated"] == 1 and r["created"] == 1 and r["skipped"] == 1  # EK 226 upserted by ref; the hotel is a new ref
    assert client.post("/v1/cop/import/legs", json={"text": csv}, headers={"X-TOC-Role": "ep"}).status_code == 403
