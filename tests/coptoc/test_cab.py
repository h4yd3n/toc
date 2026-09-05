"""§4 the sample force: a Combat Aviation Brigade as a task organization; §7/§8 the way a brigade S4 and S6 keep their boards."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        r = c.post("/v1/cop/seed?dataset=cab")
        assert r.status_code == 200 and r.json()["dataset"] == "cab", r.text
        yield c


def test_task_organization(client):
    snap = client.get("/v1/cop/snapshot").json()
    teams = {t["id"]: t for t in snap["teams"]}
    bde = teams["t_cab"]
    assert bde["echelon"] == "brigade" and bde["parent_id"] is None
    bns = [t for t in snap["teams"] if t["echelon"] == "battalion"]
    assert len(bns) == 5 and all(t["parent_id"] == "t_cab" for t in bns)
    for bn in bns:
        cos = [t for t in snap["teams"] if t["parent_id"] == bn["id"]]
        assert len(cos) == 5 and sum(1 for c in cos if c["function"] == "hq") == 1  # HHC + four companies
    assert teams["t_1atk_a"]["short"] == "A/1" and teams["t_1atk_a"]["equipment"] == "AH-64E ×8"
    people = snap["people"]
    assert 2300 <= len(people) <= 2500
    by_team = {}
    for p in people: by_team.setdefault(p["team_id"], []).append(p)
    assert len(by_team["t_5asb_b"]) == 320 and len(by_team["t_1atk_a"]) == 45
    # maintainers — the ASB plus every battalion's D company — are more than half the brigade
    maint = sum(len(v) for k, v in by_team.items() if k.startswith("t_5asb") or k.endswith("_d"))
    assert maint / len(people) > 0.5
    # the command groups are the VIPs: one commander and one CSM per HHC
    vips = [p for p in people if p["is_vip"]]
    assert len(vips) == 12 and all(p["role"] in ("Commander", "Command Sergeant Major") for p in vips)
    assert client.post("/v1/cop/seed?dataset=nope").status_code == 422


def test_movements_and_positions(client):
    snap = client.get("/v1/cop/snapshot").json()
    away = [p for p in snap["people"] if p["status"] == "traveling"]
    assert 20 <= len(away) <= 25
    farp = {l["id"]: l for l in snap["locations"]}["loc_farp"]
    assert farp["type"] == "farp" and farp["present"] == 14 and farp["effective_posture"] == "elevated"
    cdr = next(p for p in snap["people"] if p["team_id"] == "t_cab_hhc" and p["role"] == "Commander")
    assert cdr["status"] == "traveling" and abs(cdr["lat"] - 35.1401) < 1e-3  # at the DVQ per the itinerary
    trip = next(t for t in snap["trips"] if t["id"] == "trip_cdr")
    assert trip["current_leg"]["kind"] == "lodging"


def test_s4_and_s6_the_brigade_way(client):
    snap = client.get("/v1/cop/snapshot").json()
    s4, s6 = snap["s4"], snap["s6"]
    assert s4["status"] == "red"  # FARP fuel and spare engines
    farp_fuel = next(x for x in s4["supplies"] if x["item"].startswith("JP-8") and x["location_id"] == "loc_farp")
    assert farp_fuel["status"] == "red" and farp_fuel["unit"] == "gal"
    readiness = [x for x in s4["supplies"] if x["category"] == "equipment" and x["unit"] == "acft"]
    assert len(readiness) == 5 and next(x for x in readiness if "CH-47F" in x["item"])["status"] == "amber"
    convoy = next(x for x in s4["shipments"] if x["ref"] == "CONV-0912")
    assert convoy["to_name"] == "FARP Eagle" and convoy["priority"] == "urgent" and convoy["health"] == "green"
    assert s6["status"] == "amber"  # an alternate net down, a network down, a generator degraded: nothing primary or power is out, so AMBER not RED
    assert s6["pace"]["loc_farp"]["nets"]["alternate"] == "down" and s6["pace"]["loc_farp"]["in_use"] == "primary"
    assert s6["pace"]["loc_bde"]["nets"]["contingency"] == "degraded"
    assert any("SIPRNET — FOB Warrior" in e for e in s6["exceptions"])
