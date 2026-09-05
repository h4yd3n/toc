"""§3.4 the derived overlays: every active requirement is an NAI; everything that moves is a movement, grouped by the profile's rule (Decision Z)."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed?dataset=cab").status_code == 200
        yield c


def test_every_active_requirement_is_an_nai_with_its_coverage(client):
    snap = client.get("/v1/cop/snapshot").json()
    nais = snap["nais"]
    reqs = client.get("/v1/s2/requirements?status=active").json()
    assert len(nais) == len(reqs) and [n["nai"] for n in nais] == list(range(1, len(nais) + 1))
    farp = next(n for n in nais if n["subject_id"] == "loc_farp")
    assert farp["radius_km"] == 50.0 and 0 <= farp["coverage_pct"] <= 100 and farp["health"] in ("green", "amber", "red")
    assert "pir_uas" in farp["pir_ids"]   # the PIR on the FARP rides on its NAI
    assert nais[0]["priority"] <= nais[-1]["priority"]   # numbered by priority


def test_the_brigade_moves_as_serials_and_the_vip_moves_alone(client):
    mv = client.get("/v1/cop/snapshot").json()["movements"]
    serials = [m for m in mv if m["kind"] == "serial"]
    assert {(m["unit"], m["pax"], m["dest_name"]) for m in serials} == {("1 ATK", 6, "FARP Eagle"), ("5 ASB", 8, "FARP Eagle"), ("4 GSAB", 4, "FOB Warrior — JRTC"), ("5 ASB", 3, "FOB Warrior — JRTC")}
    assert all(m["owner"] == "S3" and m["status"] == "active" and len(m["legs"]) == 1 and m["legs"][0]["kind"] == "route" for m in serials)
    cdr = next(m for m in mv if m["is_vip"] and "Adeyemi" in m["name"])
    assert cdr["kind"] == "individual" and cdr["pax"] == 1 and cdr["mode"] == "air" and len(cdr["legs"]) == 2 and cdr["current_leg"] == "Airborne Inn (DVQ)"
    assert mv[0]["status"] == "active" and mv[0]["is_vip"]   # active first, the VIP first among them


def test_shipments_are_movements_with_an_origin_when_the_wall_knows_it(client):
    mv = client.get("/v1/cop/snapshot").json()["movements"]
    tanker = next(m for m in mv if m["kind"] == "shipment" and "tanker" in m["name"])
    assert tanker["owner"] == "S4" and tanker["dest_name"] == "FARP Eagle" and tanker["status"] == "active" and tanker["health"] == "green"
    assert tanker["origin_name"] == "5 ASB motor pool" and tanker["origin_lat"] is not None and len(tanker["legs"]) == 1   # matched to the motor pool by its words
    depot = next(m for m in mv if m["kind"] == "shipment" and "T700" in m["name"])
    assert depot["origin_lat"] is None and depot["legs"] == [] and depot["health"] in ("amber", "red")   # a depot off the wall has no line, only an ETA at the site
    assert not any(m["kind"] == "shipment" and "Hellfire" in m["name"] and m["status"] == "active" for m in mv)


def test_the_corporate_desk_moves_as_individuals_and_delegations(client):
    assert client.put("/v1/cop/profile", json={"profile": "corporate"}, headers=BC).status_code == 200
    mv = client.get("/v1/cop/snapshot").json()["movements"]
    kinds = {m["kind"] for m in mv}
    assert "serial" not in kinds and "delegation" in kinds and "individual" in kinds
    dl = [m for m in mv if m["kind"] == "delegation"]
    assert all(m["pax"] >= 3 and m["event_id"] for m in dl) and any("Sales Kickoff" in m["name"] for m in dl)
    vips = [m for m in mv if m["is_vip"]]
    assert vips and all(m["kind"] == "individual" and m["pax"] == 1 for m in vips)   # a principal never folds into a group
    client.put("/v1/cop/profile", json={"profile": "military"}, headers=BC)
