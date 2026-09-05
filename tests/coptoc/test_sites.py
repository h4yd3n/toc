"""§3.1 sites: adding one, correcting one, and moving the TOC. A unit garrisoned at Fort Campbell that jumps its
TOC to a FOB has not stopped being garrisoned at Campbell — home station stays, the board follows the flag."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "CPT Ruiz"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed?dataset=cab").status_code == 200
        yield c


def test_a_site_can_be_added_and_corrected(client):
    r = client.post("/v1/cop/locations", headers=BC, json={"name": "TAA Falcon", "type": "cp", "lat": 33.4, "lon": 44.4, "city": "Baghdad", "country": "IQ"})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    r = client.patch(f"/v1/cop/locations/{sid}", headers=BC, json={"name": "TAA Falcon (fwd)", "lat": 33.45})
    assert r.status_code == 200 and set(r.json()["changed"]) == {"name", "lat"}
    site = next(l for l in client.get("/v1/cop/locations").json() if l["id"] == sid)
    assert site["name"] == "TAA Falcon (fwd)" and site["lat"] == 33.45


def test_moving_the_TOC_moves_the_board_and_leaves_home_station_alone(client):
    snap = client.get("/v1/cop/snapshot").json()
    home = next(l for l in snap["locations"] if l["type"] == "hq")
    assert (snap["view"]["center_lat"], snap["view"]["center_lon"]) == (home["lat"], home["lon"])

    fob = next(l for l in snap["locations"] if l["type"] == "fob")
    assert client.post(f"/v1/cop/locations/{fob['id']}/toc", headers=BC).status_code == 200

    snap = client.get("/v1/cop/snapshot").json()
    assert snap["view"]["center_lat"] == fob["lat"]                      # the board jumped with the TOC
    still_home = next(l for l in snap["locations"] if l["id"] == home["id"])
    assert still_home["type"] == "hq" and not still_home["is_toc"]       # home station is still home station
    assert [l["id"] for l in snap["locations"] if l["is_toc"]] == [fob["id"]]   # and only one CP carries the flag


def test_the_jump_is_on_the_record(client):
    log = client.get("/v1/cop/snapshot").json()["log"]
    assert any(e["type"] == "cop.location.toc" for e in log)


def test_a_site_needs_a_real_name_type_and_position(client):
    for bad in ({"name": "  ", "lat": 1, "lon": 1}, {"name": "X", "type": "moon base", "lat": 1, "lon": 1}, {"name": "X", "lat": 99, "lon": 1}):
        assert client.post("/v1/cop/locations", headers=BC, json=bad).status_code == 422, bad


def test_not_everyone_moves_the_TOC(client):
    fob = next(l for l in client.get("/v1/cop/locations").json() if l["type"] == "fob")
    r = client.post(f"/v1/cop/locations/{fob['id']}/toc", headers={"X-TOC-Role": "logistics", "X-TOC-Actor": "SSG Vance"})
    assert r.status_code == 403, r.text
