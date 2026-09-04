"""§5.2–5.3: requirements are first-class and the collection plan generates itself. Runs against the COP app with
Sigtoc mounted, so standing requirements come from the real wall snapshot."""
import os, tempfile
from datetime import datetime, timedelta, timezone

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_INTSUM_CLOCK"] = "off"  # the fixed-time INTSUM draft is tested directly, not on a timer
os.environ["TOC_OFFLINE"] = "1"  # no network in tests
os.environ["TOC_SOURCES_CONFIGURED"] = "gdacs,ops"  # these tests exercise the plan with GDACS as the only live feed
os.environ.pop("ANTHROPIC_API_KEY", None); os.environ.pop("CLSTR_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed")
        # seed replaces the wall; resync so standing requirements reflect it
        c.post("/v1/s2/requirements/sync", json=c.get("/v1/cop/snapshot", params={"restricted": "true"}, headers={"X-TOC-Role": "battle_captain"}).json())
        # these tests exercise the catalogue with GDACS as the only live feed; organic reporting (built, always on) is
        # switched off here so the coverage numbers stay about the external sources — see test_organic_reporting_counts
        c.patch("/v1/s2/sources/ops", json={"enabled": False})
        yield c

def iso(dt): return dt.astimezone(timezone.utc).isoformat()
NOW = datetime.now(timezone.utc)
BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "Battle Captain"}


def test_standing_requirements_write_themselves(client):
    snap = client.get("/v1/cop/snapshot", params={"restricted": "true"}, headers=BC).json()
    reqs = client.get("/v1/s2/requirements", params={"kind": "standing", "status": "active"}).json()
    ids = {r["id"] for r in reqs}
    assert {f"req_loc_{l['id']}" for l in snap["locations"]} <= ids
    assert {f"req_trip_{t['id']}" for t in snap["trips"]} <= ids
    assert {f"req_evt_{e['id']}" for e in snap["events"]} <= ids
    ceo = next(r for r in reqs if r["id"] == "req_trip_trip_001")
    assert ceo["priority"] == 1 and ceo["subject_type"] == "trip" and "Riyadh" in ceo["question"] and ceo["window_to"]
    assert ceo["indicators"] == [] and ceo["coverage"]["total"] == 8  # trip profile, not yet edited by an analyst

def test_plan_shows_coverage_and_recommends_sources_for_gaps(client):
    p = client.get("/v1/s2/requirements/req_trip_trip_001/plan").json()
    by = {r["indicator"]: r for r in p["indicators"]}
    assert by["natural_hazard"]["covered"] is True and by["natural_hazard"]["sources"][0]["id"] == "gdacs"
    assert by["civil_unrest"]["covered"] is False and {s["id"] for s in by["civil_unrest"]["recommended"]} >= {"acled", "gdelt", "clstr"}
    assert p["covered"] == 1 and p["total"] == 8 and "civil_unrest" in p["gaps"] and p["coverage_pct"] == 12
    cov = client.get("/v1/s2/coverage").json()
    assert cov["requirements"] >= 20 and cov["fully_covered"] == 0 and cov["gaps"][0]["requirements_affected"] >= 10
    assert any(s["id"] == "clstr" for g in cov["gaps"] if g["indicator"] == "civil_unrest" for s in g["recommended_sources"])

def test_directed_requirement_is_a_four_field_form_and_role_gated(client):
    body = {"place": "Lisbon, Portugal", "lat": 38.7223, "lon": -9.1393, "window_from": iso(NOW + timedelta(days=60)), "window_to": iso(NOW + timedelta(days=63)),
            "purpose": "candidate Q1 offsite venue", "priority": 2}
    assert client.post("/v1/s2/requirements", json=body).status_code == 403
    r = client.post("/v1/s2/requirements", json=body, headers={"X-TOC-Role": "ea", "X-TOC-Actor": "EA - Office of the CEO"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["kind"] == "directed" and d["subject_type"] == "place" and d["owner"].startswith("EA") and "Lisbon" in d["question"]
    assert d["coverage"]["total"] == 9 and "baseline" in d["coverage"]["gaps"]  # the place profile asks for a baseline nobody collects yet
    bad = dict(body, window_to=body["window_from"])
    assert client.post("/v1/s2/requirements", json=bad, headers={"X-TOC-Role": "ea"}).status_code == 422
    # The analyst trims the indicator set; coverage recomputes
    r2 = client.patch(f"/v1/s2/requirements/{d['id']}", json={"indicators": ["natural_hazard", "civil_unrest"]}, headers={"X-TOC-Actor": "S2 analyst"})
    assert r2.json()["coverage"] == {"covered": 1, "total": 2, "pct": 50, "gaps": ["civil_unrest"]}
    assert client.patch(f"/v1/s2/requirements/{d['id']}", json={"indicators": ["nope"]}).status_code == 422
    # Directed places count as blue-force points for collection relevance
    from coptoc.routes import build_snapshot  # noqa
    log = [e for e in client.get("/v1/cop/log", params={"limit": 50}).json() if e["subject"] == d["id"]]
    assert log[0]["type"] == "s2.requirement.updated" and log[1]["type"] == "s2.requirement.created" and "coverage 1/9" in log[1]["summary"]

def test_sources_are_operator_adjustable(client):
    cat = {c["id"]: c for c in client.get("/v1/s2/sources").json()}
    assert cat["gdacs"]["configured"] is True and cat["clstr"]["configured"] is False and cat["clstr"]["reliability"] == "F"
    r = client.patch("/v1/s2/sources/gdacs", json={"cadence": "every few hours", "reliability": "A"}, headers={"X-TOC-Actor": "collection manager"})
    assert r.json()["cadence"] == "every few hours"
    assert client.patch("/v1/s2/sources/gdacs", json={"cadence": "whenever"}).status_code == 422
    # Disabling the only live source for an indicator opens a gap on every plan that needs it
    client.patch("/v1/s2/sources/gdacs", json={"enabled": False})
    assert client.get("/v1/s2/requirements/req_loc_loc_sf/plan").json()["covered"] == 0
    client.patch("/v1/s2/sources/gdacs", json={"enabled": True})
    assert client.get("/v1/s2/requirements/req_loc_loc_sf/plan").json()["covered"] == 1

def test_wall_writes_create_and_expire_standing_requirements(client):
    r = client.post("/v1/cop/trips", json={"person_id": "p_gc", "origin_location_id": "loc_dc", "dest_name": "Lisbon", "dest_lat": 38.72, "dest_lon": -9.14,
                                          "depart_at": iso(NOW + timedelta(days=1)), "return_at": iso(NOW + timedelta(days=3)), "purpose": "Regulator visit"}, headers=BC)
    tid = r.json()["id"]
    req = client.get(f"/v1/s2/requirements/req_trip_{tid}").json()
    assert req["status"] == "active" and req["kind"] == "standing" and "Lisbon" in req["question"]
    client.delete(f"/v1/cop/trips/{tid}", headers=BC)
    assert client.get(f"/v1/s2/requirements/req_trip_{tid}").json()["status"] == "expired"

def test_query_is_the_standalone_use(client):
    client.post("/v1/cop/intel/refresh", headers=BC)  # may be 502 offline; the query must still work on what we hold
    q = client.get("/v1/s2/query", params={"lat": 24.7136, "lon": 46.6753, "radius_km": 100}).json()
    assert any(t["title"].startswith("Regional drone") for t in q["threats"])
    assert any(r["id"] == "req_trip_trip_001" for r in q["requirements"])

def test_sigtoc_runs_standalone(client):
    from sigtoc.api import app as s2app
    with TestClient(s2app) as s2:
        assert s2.get("/v1/health").json()["service"] == "sigtoc"
        assert len(s2.get("/v1/s2/requirements").json()) >= 20


def test_organic_reporting_counts_as_a_source(client):
    """Our own people are a tasked source (the guards are told what to look for), reliability A, and cover the human indicators."""
    client.patch("/v1/s2/sources/ops", json={"enabled": True})
    try:
        p = client.get("/v1/s2/requirements/req_loc_loc_sf/plan").json()
        by = {i["indicator"]: i for i in p["indicators"]}
        assert by["targeted"]["covered"] is True and by["targeted"]["sources"][0]["id"] == "ops" and by["targeted"]["sources"][0]["reliability"] == "A"
        assert by["natural_hazard"]["sources"][0]["id"] == "gdacs"  # ops doesn't pretend to watch earthquakes
        assert p["covered"] > 1
    finally:
        client.patch("/v1/s2/sources/ops", json={"enabled": False})
