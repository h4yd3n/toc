"""Sigtoc plan Phase 5 — the four things the plan left open at the end of §5.10b:

  * actors and their sightings as node types in the analyst's workbench (§5.11),
  * decision points on the S3 timeline (the snapshot carries what the strip draws),
  * a COA's graphic set as one named overlay (the set has to point at graphics that exist),
  * a field report filed with a kind other than SPOTREP — what the phones now offer.
"""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
for k in ("ANTHROPIC_API_KEY", "TWILIO_AUTH_TOKEN", "TWILIO_ACCOUNT_SID", "SLACK_WEBHOOK_URL", "TOC_DRAFTER"): os.environ.pop(k, None)

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc_day"}
AN = {"X-TOC-Role": "analyst", "X-TOC-Actor": "s2_lee"}
SEC = {"X-TOC-Role": "security", "X-TOC-Actor": "guard_7"}
CASE = "case_seed_gate"      # the seeded north-gate case
ACTOR = "act_sf_surveillance"  # the seeded pair, whose sightings cite that case's two reports
STATE = {}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed").status_code == 200
        yield c


def iso(dt): return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------- the workbench (§5.11)

def test_the_case_graph_carries_the_actor_its_sightings_and_a_cited_line_to_the_case_entities(client):
    d = client.get(f"/v1/s2/cases/{CASE}", headers=AN)
    assert d.status_code == 200, d.text
    g = d.json()["graph"]
    actor = next((e for e in g["entities"] if e["id"] == ACTOR), None)
    assert actor and actor["type"] == "actor" and actor["origin"] == "sigtoc"
    # an actor is Sigtoc's own object: it arrives confirmed, not as something to review
    assert actor["status"] == "confirmed"
    assert actor["attributes"]["kind"] == "group" and actor["attributes"]["actor_status"] == "active"
    assert actor["evidence"] and all(e["quote"] for e in actor["evidence"])
    # every line from the actor is derived, cited, and graded — never a plain confirmation
    lines = [r for r in g["relationships"] if r["from"] == ACTOR]
    assert lines, "the actor's sightings cite the case's reports, so it should be linked to what they produced"
    assert {r["status"] for r in lines} == {"derived"} and {r["type"] for r in lines} == {"reported_with"}
    assert all(r["grade"] and r["evidence"] for r in lines)
    names = {e["id"]: e["name"] for e in g["entities"]}
    assert "Marcus Vane" in {names[r["to"]] for r in lines}
    # the sightings are events on the case's own timeline
    sightings = [v for v in g["events"] if v["type"] == "sighting"]
    assert len(sightings) >= 2 and all(v["participants"] == [ACTOR] and v["origin"] == "sigtoc" for v in sightings)
    assert g["events"] == sorted(g["events"], key=lambda v: v["at"] or "")


def test_the_three_views_render_the_actor_and_the_wheel_counts_its_sightings(client):
    v = client.get(f"/v1/s2/cases/{CASE}/views", headers=AN).json()
    node = next(n for n in v["link_chart"]["nodes"] if n["id"] == ACTOR)
    assert node["type"] == "actor" and node["origin"] == "sigtoc" and node["label"]
    edges = [e for e in v["link_chart"]["edges"] if e["from"] == ACTOR]
    assert edges and all(e["dashed"] and e["origin"] == "sigtoc" for e in edges)  # derived is never drawn solid
    assert any(t["type"] == "sighting" for t in v["timeline"])
    only_case = client.get(f"/v1/s2/cases/{CASE}/views?confirmed_only=true", headers=AN).json()
    # confirmed-only is the analyst's picture: the actor stays, the derived arithmetic goes
    assert any(n["id"] == ACTOR for n in only_case["link_chart"]["nodes"])
    assert not [e for e in only_case["link_chart"]["edges"] if e["status"] == "derived"]
    # the time wheel and the link summary read the merged graph
    per_actor = client.get(f"/v1/s2/cases/{CASE}/views?entity_id={ACTOR}", headers=AN).json()
    assert per_actor["time_wheel"]["events"] == len([t for t in v["timeline"] if ACTOR in t["participants"]])
    assert any(ACTOR in s or "surveillance" in s for s in v["analysis"]["links"])


def test_an_actor_in_the_case_graph_is_not_something_to_confirm_or_reject(client):
    q = client.get(f"/v1/s2/cases/{CASE}/queue", headers=AN).json()
    assert not any(e["id"] == ACTOR for e in q["entities"]), "derived nodes never enter the review queue"
    r = client.post(f"/v1/s2/cases/{CASE}/decide", json={"kind": "entity", "id": ACTOR, "decision": "confirm"}, headers=AN)
    assert r.status_code == 404


def test_a_case_with_no_actor_is_unchanged(client):
    c = client.post("/v1/s2/cases", json={"title": "Empty folder", "kind": "general"}, headers=AN).json()
    g = client.get(f"/v1/s2/cases/{c['id']}", headers=AN).json()["graph"]
    assert g["entities"] == [] and g["relationships"] == [] and g["events"] == []


# ---------------------------------------------------------------- decision points on the S3 strip

def test_the_snapshot_carries_the_decision_points_the_strip_draws(client):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    site = client.get("/v1/cop/snapshot").json()["locations"][0]["id"]
    soon = client.post("/v1/s2/decision-points", json={
        "title": "DP 1 — close the north gate", "subject_type": "location", "subject_id": site,
        "decision": "Close the north gate to visitors", "trigger": "The pair is seen a third time inside the NAI",
        "action": "Gate closed, EP briefed", "owner_section": "S3", "latest_time": iso(now + timedelta(hours=30))}, headers=AN)
    assert soon.status_code == 201, soon.text
    late = client.post("/v1/s2/decision-points", json={
        "title": "DP 2 — move the loading dock", "subject_type": "location", "subject_id": site,
        "decision": "Move deliveries to the south dock", "owner_section": "S4", "latest_time": iso(now - timedelta(hours=2))}, headers=AN).json()
    undated = client.post("/v1/s2/decision-points", json={
        "title": "DP 3 — no clock", "subject_type": "location", "subject_id": site, "decision": "Stand up a second guard"}, headers=AN).json()
    STATE["soon"], STATE["late"], STATE["undated"] = soon.json()["id"], late["id"], undated["id"]

    snap = client.get("/v1/cop/snapshot").json()
    dps = {d["id"]: d for d in snap["decision_points"]}
    assert STATE["soon"] in dps and STATE["late"] in dps and STATE["undated"] in dps
    assert dps[STATE["soon"]]["latest_time"] and dps[STATE["soon"]]["overdue"] is False
    assert dps[STATE["late"]]["overdue"] is True, "a no-later-than that has passed reads red on the strip"
    assert dps[STATE["undated"]]["latest_time"] is None, "a decision with no clock has no place in time; the matrix keeps it"
    assert dps[STATE["soon"]]["decision"] and dps[STATE["soon"]]["trigger"] and dps[STATE["soon"]]["action"] and dps[STATE["soon"]]["owner_section"] == "S3"
    assert snap["summary"]["decisions_open"] == 3 and snap["summary"]["decisions_overdue"] == 1
    # ordered by the clock, the undated ones last, the way the matrix orders them
    ordered = [d["id"] for d in snap["decision_points"]]
    assert ordered.index(STATE["late"]) < ordered.index(STATE["soon"]) < ordered.index(STATE["undated"])


def test_a_decided_decision_point_leaves_the_strip_and_a_triggered_one_stays(client):
    client.patch(f"/v1/s2/decision-points/{STATE['undated']}", json={"status": "passed"}, headers=BC)
    client.patch(f"/v1/s2/decision-points/{STATE['soon']}", json={"status": "triggered", "note": "third sighting inside the NAI"}, headers=AN)
    snap = client.get("/v1/cop/snapshot").json()
    dps = {d["id"]: d for d in snap["decision_points"]}
    assert STATE["undated"] not in dps, "passed is decided: it comes off the strip"
    assert dps[STATE["soon"]]["status"] == "triggered" and dps[STATE["soon"]]["note"]
    assert snap["summary"]["decisions_open"] == 1 and snap["summary"]["decisions_overdue"] == 1
    # the matrix under the S2 panel still holds all of them
    assert {r["id"] for r in client.get("/v1/s2/dsm").json()["rows"]} >= {STATE["soon"], STATE["late"], STATE["undated"]}


# ---------------------------------------------------------------- a COA's graphic set as one overlay

def test_a_coa_graphic_set_names_graphics_the_wall_can_actually_draw(client):
    snap = client.get("/v1/cop/snapshot").json()
    site = snap["locations"][0]["id"]
    gfx = [g["id"] for g in snap["graphics"] if g["section"] == "S2"][:2]
    assert gfx, "the seed draws S2 threat graphics"
    c = client.post("/v1/s2/coas", json={"title": "COA 1 — approach from the loading side", "subject_type": "location", "subject_id": site,
                                         "likelihood": "likely", "confidence": "moderate", "narrative": "Observation from the dock side, then entry with a delivery.",
                                         "indicators": ["a vehicle held at the dock"], "graphic_ids": gfx}, headers=AN)
    assert c.status_code == 201, c.text
    coa = c.json()
    assert coa["graphic_ids"] == gfx and coa["status"] == "assessed"
    STATE["coa"] = coa["id"]
    # the overlay draws the set, so the set cannot name a graphic nobody drew
    bad = client.post("/v1/s2/coas", json={"title": "COA 2", "subject_type": "location", "subject_id": site, "graphic_ids": ["gfx_nope"]}, headers=AN)
    assert bad.status_code == 404 and "graphic" in bad.json()["detail"]
    assert client.patch(f"/v1/s2/coas/{STATE['coa']}", json={"graphic_ids": ["gfx_nope"]}, headers=AN).status_code == 404
    # every id in the set resolves on the wall, which is what the overlay needs to bring them forward together
    ids = {g["id"] for g in client.get("/v1/cop/snapshot").json()["graphics"]}
    assert set(client.get(f"/v1/s2/coas?subject_type=location&subject_id={site}").json()[0]["graphic_ids"]) <= ids


# ---------------------------------------------------------------- the phones file more than a SPOTREP

@pytest.mark.parametrize("kind", ["spot", "sitrep", "note", "liaison"])
def test_the_field_can_file_every_report_kind_the_phones_now_offer(client, kind):
    body = {"text": f"{kind.upper()} from the gate: quiet since last light.", "kind": kind, "reported_by": "Sgt Ortiz",
            "lat": 37.7897, "lon": -122.3989, "place": "north gate, SF HQ"}
    if kind == "liaison":
        body["liaison_source"] = "SFPD Southern Station"
    r = client.post("/v1/s2/reports", json=body, headers=SEC)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["kind"] == kind
    if kind == "liaison":
        # the source is the liaison desk, graded F until the analyst judges it — not the person who relayed it
        assert d["source"].startswith("liaison:") and d["grade"] == "F2" and d["liaison_source"]["name"] == "SFPD Southern Station"
    else:
        assert d["grade"] == "A2" and d["source"] == "ops"
