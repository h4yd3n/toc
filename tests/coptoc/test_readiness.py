"""§4 and §7 — the pieces a military deployment adds first: unit positions from a tracker, equipment readiness by
bumper number, and days of supply from the rate S4 entered. Nothing here invents a number."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc_day"}
S4 = {"X-TOC-Role": "logistics", "X-TOC-Actor": "supply_sgt"}
S1 = {"X-TOC-Role": "security", "X-TOC-Actor": "s1_duty"}
AN = {"X-TOC-Role": "analyst", "X-TOC-Actor": "s2_lee"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed?dataset=cab").status_code == 200
        yield c


def test_a_tracker_report_puts_a_unit_on_the_map_and_an_old_one_says_so(client):
    snap = client.get("/v1/cop/snapshot", headers=BC).json()
    positions = {p["team_id"]: p for p in snap["unit_positions"]}
    assert positions, "the brigade sample reports three units"
    fresh = positions["t_5asb"]
    assert fresh["source"] == "jbc-p" and fresh["stale"] is False and fresh["age_min"] <= fresh["stale_after_min"]
    assert fresh["team_name"] and fresh["lat"] and fresh["lon"]
    stale = positions["t_1atk"]
    assert stale["stale"] is True and stale["age_min"] > stale["stale_after_min"], "an aged report is marked, not hidden and not refreshed"
    # a unit nobody has reported has no position at all — the map shows what is known
    assert "t_2atk" not in positions
    # filing one moves the unit; the newest report wins
    r = client.post("/v1/cop/units/t_2atk/position", json={"lat": 36.6721, "lon": -87.4919, "source": "jbc-p", "note": "arrived Campbell"}, headers=S1)
    assert r.status_code == 201, r.text
    again = {p["team_id"]: p for p in client.get("/v1/cop/snapshot", headers=BC).json()["unit_positions"]}
    assert again["t_2atk"]["lat"] == 36.6721 and again["t_2atk"]["stale"] is False
    client.post("/v1/cop/units/t_2atk/position", json={"lat": 36.7, "lon": -87.5, "source": "radio"}, headers=S1)
    latest = {p["team_id"]: p for p in client.get("/v1/cop/snapshot", headers=BC).json()["unit_positions"]}["t_2atk"]
    assert latest["lat"] == 36.7 and latest["source"] == "radio"
    # the analyst does not move the force, and a unit that does not exist cannot be reported
    assert client.post("/v1/cop/units/t_2atk/position", json={"lat": 1, "lon": 1}, headers=AN).status_code == 403
    assert client.post("/v1/cop/units/t_nope/position", json={"lat": 1, "lon": 1}, headers=S1).status_code == 404
    assert client.post("/v1/cop/units/t_2atk/position", json={"lat": 999, "lon": 1}, headers=S1).status_code == 422


def test_readiness_is_fmc_over_assigned_and_nothing_else(client):
    board = client.get("/v1/cop/equipment", headers=BC).json()
    r = board["readiness"]
    assert r["assigned"] == len(board["equipment"]) == 102
    assert r["or_pct"] == round(100 * r["fmc"] / r["assigned"])
    assert r["fmc"] + r["pmc"] + r["nmc"] == r["assigned"]
    ch47 = next(g for g in r["by_model"] if g["model"] == "CH-47F")
    assert ch47["assigned"] == 12 and ch47["or_pct"] == round(100 * ch47["fmc"] / 12)
    assert r["by_model"][0]["or_pct"] <= r["by_model"][-1]["or_pct"], "worst first: the board leads with what is broken"
    # every down airframe carries its fault and how long it has been down
    assert all(x["fault"] and x["hours_down"] > 0 for x in r["down"])
    assert any("CH-47F" in e or "NMC" in e for e in r["exceptions"])
    # and the same numbers reach the wall's S4 board
    s4 = client.get("/v1/cop/snapshot", headers=BC).json()["s4"]
    assert s4["readiness"]["or_pct"] == r["or_pct"] and s4["readiness"]["exceptions"]


def test_equipment_is_kept_by_bumper_number_and_a_status_change_starts_its_clock(client):
    first = client.post("/v1/cop/equipment", json={"bumper_number": "Z99", "model": "AH-64E", "category": "airframe", "team_id": "t_1atk", "status": "fmc"}, headers=S4)
    assert first.status_code == 201, first.text
    eid = first.json()["id"]
    again = client.post("/v1/cop/equipment", json={"bumper_number": "Z99", "model": "AH-64E", "status": "fmc"}, headers=S4)
    assert again.json()["id"] == eid, "the same bumper number is the same airframe, not a second one"
    down = client.patch(f"/v1/cop/equipment/{eid}", json={"status": "nmc", "fault": "Engine chip light"}, headers=S4)
    assert down.status_code == 200 and down.json()["status"] == "nmc"
    row = next(x for x in client.get("/v1/cop/equipment", headers=BC).json()["equipment"] if x["id"] == eid)
    assert row["fault"] == "Engine chip light" and row["hours_down"] >= 0 and row["status"] == "nmc"
    assert client.patch(f"/v1/cop/equipment/{eid}", json={"status": "flying"}, headers=S4).status_code == 422
    assert client.post("/v1/cop/equipment", json={"bumper_number": "  ", "status": "fmc"}, headers=S4).status_code == 422
    assert client.post("/v1/cop/equipment", json={"bumper_number": "Y01", "status": "fmc"}, headers=AN).status_code == 403


def test_days_of_supply_needs_a_rate_and_says_nothing_without_one(client):
    from coptoc.readiness import days_of_supply
    assert days_of_supply(8000, 6400) == 1.2
    assert days_of_supply(8000, None) is None and days_of_supply(8000, 0) is None
    supplies = client.get("/v1/cop/snapshot", headers=BC).json()["s4"]["supplies"]
    fuel = [x for x in supplies if x["category"] == "fuel"]
    assert fuel and all(x["days_of_supply"] == round(x["on_hand"] / x["daily_use"], 1) for x in fuel)
    rationless = [x for x in supplies if not x["daily_use"]]
    assert rationless and all(x["days_of_supply"] is None for x in rationless), "no rate, no number"
