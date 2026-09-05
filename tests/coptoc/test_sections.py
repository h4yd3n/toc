"""§7 S4 Logistics and §8 S6 Signal: background boards that roll up by exception; the section set is configuration."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app
from coptoc.sections import sections_config, supply_status

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}
S4 = {"X-TOC-Role": "logistics", "X-TOC-Actor": "S4 NCO"}
S6 = {"X-TOC-Role": "signal", "X-TOC-Actor": "S6 NCO"}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed")
        yield c


def test_sections_are_configuration(monkeypatch):
    assert [s["code"] for s in sections_config()] == ["S1", "S2", "S3", "S4", "S6"] and all(s["enabled"] for s in sections_config())
    monkeypatch.setenv("TOC_SECTIONS", "S1,S2,S3"); monkeypatch.setenv("TOC_SECTION_TITLES", "S4=SUPPLY")
    cfg = {s["code"]: s for s in sections_config()}
    assert not cfg["S4"]["enabled"] and not cfg["S6"]["enabled"] and cfg["S4"]["title"] == "SUPPLY" and cfg["S1"]["enabled"]
    monkeypatch.setenv("TOC_SECTIONS", "S2")  # S1–S3 cannot be switched off: the COP is built on them
    assert all(s["enabled"] for s in sections_config() if s["code"] in ("S1", "S2", "S3"))


def test_supply_status_bands():
    assert supply_status(10, 10) == "green" and supply_status(6, 10) == "amber" and supply_status(4, 10) == "red" and supply_status(0, 0) == "green"


def test_s4_rolls_up_by_exception(client):
    snap = client.get("/v1/cop/snapshot").json()
    s4 = snap["s4"]
    assert snap["summary"]["s4_status"] == "red" and s4["status"] == "red"
    diesel = next(x for x in s4["supplies"] if x["item"] == "Generator diesel" and x["location_id"] == "loc_dc2")
    assert diesel["status"] == "red" and diesel["pct"] == 20 and diesel["location_name"] == "DC-East (Virginia)"
    assert s4["supplies"][0]["status"] == "red"  # exceptions sort first
    late = next(x for x in s4["shipments"] if x["ref"] == "RB-0092")
    assert late["status"] == "delayed" and late["health"] == "amber" and late["hours_to_eta"] < 0
    urgent = next(x for x in s4["shipments"] if x["ref"] == "DL-4471")
    assert urgent["health"] == "green" and urgent["status"] == "in_transit"
    assert any("Generator diesel at DC-East" in e for e in s4["exceptions"]) and any("Radio batteries" in e for e in s4["exceptions"])
    assert s4["counts"]["late"] == 1 and s4["counts"]["red"] >= 1


def test_s6_pace_and_roll_up(client):
    s6 = client.get("/v1/cop/snapshot").json()["s6"]
    assert s6["status"] == "red"  # a primary net down at DC-East
    dc = s6["pace"]["loc_dc2"]
    assert dc["nets"]["primary"] == "down" and dc["in_use"] == "alternate"
    assert s6["pace"]["loc_sf"]["in_use"] == "primary"
    badge = next(x for x in s6["systems"] if x["name"].startswith("Badge"))
    assert badge["health"] == "amber" and badge["status"] == "down" and badge["hours"] >= 1.9  # non-primary, non-power: amber
    assert any("Desk phones (VoIP) (DC-East" in e and "DOWN" in e for e in s6["exceptions"])


def test_s4_writes_are_role_gated_and_logged(client):
    assert client.patch("/v1/cop/supply/sup_005", json={"on_hand": 2000}, headers={"X-TOC-Role": "ea"}).status_code == 403
    r = client.patch("/v1/cop/supply/sup_005", json={"on_hand": 2000, "note": "Resupply received"}, headers=S4)
    assert r.status_code == 200, r.text
    diesel = next(x for x in client.get("/v1/cop/snapshot").json()["s4"]["supplies"] if x["id"] == "sup_005")
    assert diesel["status"] == "green" and diesel["updated_by"] == "S4 NCO"
    log = client.get("/v1/cop/log?limit=3").json()
    assert log[0]["type"] == "cop.s4.supply" and "Generator diesel: 2000/2000" in log[0]["summary"]
    r = client.post("/v1/cop/shipments", json={"description": "Sandbags", "category": "other", "quantity": "500", "to_location_id": "loc_sf", "eta": "2026-09-06T12:00:00Z", "priority": "urgent", "status": "in_transit"}, headers=S4)
    assert r.status_code == 201
    sid = r.json()["id"]
    assert client.patch(f"/v1/cop/shipments/{sid}", json={"status": "delayed", "note": "Truck broke down"}, headers=S4).status_code == 200
    ship = next(x for x in client.get("/v1/cop/snapshot").json()["s4"]["shipments"] if x["id"] == sid)
    assert ship["health"] == "red" and ship["to_name"] == "San Francisco HQ"
    r = client.post("/v1/cop/supply", json={"location_id": "loc_sf", "category": "ammunition", "item": "5.56 mm", "on_hand": 4000, "required": 6000, "unit": "rds"}, headers=BC)
    assert r.status_code == 201
    assert client.delete(f"/v1/cop/supply/{r.json()['id']}", headers=S4).status_code == 200


def test_s6_status_change_restarts_the_clock(client):
    assert client.patch("/v1/cop/systems/sys_009", json={"status": "up"}, headers={"X-TOC-Role": "logistics"}).status_code == 403
    r = client.patch("/v1/cop/systems/sys_009", json={"status": "up", "note": "Controller replaced"}, headers=S6)
    assert r.status_code == 200, r.text
    s6 = client.get("/v1/cop/snapshot").json()["s6"]
    voip = next(x for x in s6["systems"] if x["id"] == "sys_009")
    assert voip["status"] == "up" and voip["hours"] < 0.1 and s6["pace"]["loc_dc2"]["in_use"] == "primary"
    assert s6["status"] == "amber"  # the badge system and two degraded nets remain
    r = client.post("/v1/cop/systems", json={"name": "Drone downlink", "category": "sensor", "location_id": "loc_sf", "status": "degraded"}, headers=S6)
    assert r.status_code == 201
    assert client.delete(f"/v1/cop/systems/{r.json()['id']}", headers=S6).status_code == 200


def test_brief_and_estimates_carry_the_background_sections(client):
    client.post("/v1/cop/watch/take", json={"battle_captain": "bc"}, headers=BC)
    client.patch("/v1/cop/supply/sup_002", json={"on_hand": 120}, headers=S4)  # on this watch
    client.patch("/v1/cop/systems/sys_016", json={"status": "up"}, headers=S6)
    brief = client.get("/v1/cop/watch/brief").json()
    assert brief["current_status"]["logistics"]["status"] in ("amber", "red") and brief["current_status"]["signal"]["exceptions"]
    assert "logistics" in brief["significant_events"] and "signal" in brief["significant_events"]
    r = client.patch("/v1/cop/watch/estimate/S4", json={"assessment": "Diesel at DC-East restored; batteries for Tokyo held at customs.", "recommendation": "Chase the customs hold."}, headers=S4)
    assert r.status_code == 200, r.text
    assert any(e["section"] == "S4" for e in client.get("/v1/cop/snapshot").json()["estimates"])
