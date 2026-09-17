"""Sigtoc plan Phase 4: the graphic INTSUM (the red picture since the last one), the area assessment's link to the
live picture, and liaison sources graded by the analyst over time (LOE 5)."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
for k in ("ANTHROPIC_API_KEY", "TWILIO_AUTH_TOKEN", "TWILIO_ACCOUNT_SID", "SLACK_WEBHOOK_URL", "TOC_DRAFTER"): os.environ.pop(k, None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc_day"}
AN = {"X-TOC-Role": "analyst", "X-TOC-Actor": "s2_lee"}
SEC = {"X-TOC-Role": "security", "X-TOC-Actor": "guard_7"}
GATE = {"lat": 37.7897, "lon": -122.3989, "place": "north gate, SF HQ"}
STATE = {}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed").status_code == 200
        import asyncio
        from sqlalchemy import delete
        from sigtoc.api import sessions
        from sigtoc.intsum import IntsumRow
        async def clear():
            async with sessions()() as s:
                await s.execute(delete(IntsumRow)); await s.commit()
        asyncio.run(clear())
        yield c


def test_liaison_report_carries_its_source_grade_and_the_analyst_grades_over_time(client):
    r = client.post("/v1/s2/reports", json={"text": "SFPD Southern Station advises a grey sedan was stopped two blocks from HQ; occupants released.", "kind": "liaison", "reported_by": "Sgt Ortiz", "liaison_source": "SFPD Southern Station", "liaison_kind": "police", **GATE}, headers=SEC)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["kind"] == "liaison" and d["grade"] == "F2" and d["source"].startswith("liaison:") and d["liaison_source"]["reliability"] == "F" and d["liaison_source"]["kind"] == "police"
    sid = d["liaison_source"]["id"]; STATE["src"] = sid; STATE["rpt"] = d["id"]
    src = client.get(f"/v1/s2/liaison-sources/{sid}").json()
    assert src["record"] == {"reports": 1, "filed": 1, "corroborated": 0, "linked": 0, "promoted": 0, "dismissed": 0, "disposed": 0, "borne_out": 0, "last_report_at": d["filed_at"]}
    # the same name again is the same source, whatever the case
    again = client.post("/v1/s2/reports", json={"text": "SFPD advises no further activity overnight.", "kind": "liaison", "reported_by": "sfpd southern station"}, headers=SEC).json()
    assert again["liaison_source"]["id"] == sid and again["grade"] == "F2"
    assert client.patch(f"/v1/s2/liaison-sources/{sid}", json={"reliability": "B"}, headers=SEC).status_code == 403
    assert client.patch(f"/v1/s2/liaison-sources/{sid}", json={"reliability": "great"}, headers=AN).status_code == 422
    client.post(f"/v1/s2/reports/{STATE['rpt']}/dispose", json={"action": "corroborate", "note": "camera confirms the stop"}, headers=AN)
    g = client.patch(f"/v1/s2/liaison-sources/{sid}", json={"reliability": "B", "note": "first report borne out by our own camera"}, headers=AN)
    assert g.status_code == 200, g.text
    assert g.json()["reliability"] == "B" and g.json()["graded_by"] == "s2_lee" and g.json()["history"][-1]["from"] == "F" and g.json()["record"]["borne_out"] == 1 and g.json()["record"]["disposed"] == 1
    # earlier reports keep the grade they were filed at; the next one carries B
    assert next(x for x in client.get(f"/v1/s2/liaison-sources/{sid}").json()["reports"] if x["id"] == STATE["rpt"])["grade"] == "F1"
    third = client.post("/v1/s2/reports", json={"text": "SFPD: sedan re-registered to a rental company.", "kind": "liaison", "reported_by": "SFPD Southern Station"}, headers=SEC).json()
    assert third["grade"] == "B2"
    assert [s["name"] for s in client.get("/v1/s2/liaison-sources").json()] == ["SFPD Southern Station"]
    assert client.post("/v1/s2/liaison-sources", json={"name": "SFPD Southern Station"}, headers=AN).status_code == 409
    venue = client.post("/v1/s2/liaison-sources", json={"name": "Moscone Center security office", "kind": "venue", "reliability": "C", "notes": "event-day desk"}, headers=AN)
    assert venue.status_code == 201 and venue.json()["reliability"] == "C" and venue.json()["history"][0]["note"] == "registered"


def test_intsum_carries_the_red_picture_with_positions_and_seed_marked(client):
    actor = client.post("/v1/s2/actors", json={"kind": "group", "name": "Grey sedan pair", "strength": "two people"}, headers=AN).json()
    rid = client.post("/v1/s2/reports", json={"text": "Sedan pair back at the loading dock.", "reported_by": "guard_7", "lat": 37.7905, "lon": -122.3975, "place": "loading dock"}, headers=SEC).json()["id"]
    client.post(f"/v1/s2/reports/{rid}/dispose", json={"action": "link", "target_type": "actor", "target_id": actor["id"], "confidence": "probable"}, headers=AN)
    i = client.post("/v1/s2/intsum/draft", headers=BC).json()
    red = i["red_picture"]
    assert i["structure"][-1] == "red_picture" and red["bounds"] and red["bounds"]["south"] <= 37.7905 <= red["bounds"]["north"]
    mine = [s for s in red["sightings"] if s["actor_id"] == actor["id"]]
    assert len(mine) == 1 and mine[0]["seed"] is False and mine[0]["lat"] == 37.7905 and mine[0]["grade"] == "A2"
    assert any(s["seed"] for s in red["sightings"])  # the seed's own sightings are shown but marked
    assert any(a["id"] == actor["id"] for a in red["new_actors"])
    mv = next(m for m in red["moves"] if m["actor_id"] == actor["id"])
    assert mv["from"] is None and mv["to"]["lat"] == 37.7905 and mv["sightings"] == 1 and mv["seed"] is False
    assert red["dispositions"]["link"] == 1 and red["dispositions"]["corroborate"] == 1 and "sighting" in red["summary"]
    assert i["nstr"] is False and red["significant"] >= 2
    STATE["intsum"] = i["id"]
    # a second sighting elsewhere becomes a move with a distance in the next INTSUM
    rid2 = client.post("/v1/s2/reports", json={"text": "Sedan pair seen at the Embarcadero garage.", "reported_by": "guard_7", "lat": 37.7955, "lon": -122.3937, "place": "Embarcadero garage"}, headers=SEC).json()["id"]
    client.post(f"/v1/s2/reports/{rid2}/dispose", json={"action": "link", "target_type": "actor", "target_id": actor["id"], "confidence": "confirmed"}, headers=AN)
    i2 = client.post("/v1/s2/intsum/draft", headers=BC).json()
    mv2 = next(m for m in i2["red_picture"]["moves"] if m["actor_id"] == actor["id"])
    assert mv2["from"]["place"] == "loading dock" and mv2["to"]["place"] == "Embarcadero garage" and 0.3 < mv2["distance_km"] < 1.5
    assert i2["period"]["from"] == i["period"]["to"] and not any(s["actor_id"] == actor["id"] and s["place"] == "loading dock" for s in i2["red_picture"]["sightings"])


def test_area_assessment_links_to_actors_and_threat_graphics_inside_the_place(client):
    req = client.post("/v1/s2/requirements", json={"place": "San Francisco, US", "lat": 37.7897, "lon": -122.3989, "purpose": "board offsite", "priority": 2, "radius_km": 5}, headers=AN)
    assert req.status_code == 201, req.text
    a = client.post("/v1/s2/area-assessments", json={"requirement_ids": [req.json()["id"]]}, headers=AN)
    assert a.status_code == 201, a.text
    c = a.json()["candidates"][0]
    assert {x["id"] for x in c["actors"]} >= {"act_sf_surveillance"} and all("sightings_lookback" in x for x in c["actors"])
    assert any(g["type"] == "surveillance_detection_point" for g in c["threat_graphics"]) and all("confidence" in g for g in c["threat_graphics"])
    assert "score" not in json_dumps(c["actors"]).lower()


def json_dumps(x):
    import json
    return json.dumps(x)
