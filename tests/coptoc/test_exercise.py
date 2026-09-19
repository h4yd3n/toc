"""§3.7 — the exercise: a MSEL driven against the wall on its own profile, on the real clock.

What is being proved here is the shape of a CPX, not a simulation: injects write what a person would have written,
the picture reacts, the ledger says EXERCISE CONTROL did it, and an inject that cannot find its target fails on the
board instead of quietly doing nothing.
"""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ["TOC_CCIR_CLOCK"] = "off"; os.environ["TOC_EXERCISE_CLOCK"] = "off"

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc_day"}
S4 = {"X-TOC-Role": "logistics", "X-TOC-Actor": "supply_sgt"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.put("/v1/cop/profile", json={"profile": "exercise"}, headers=BC).status_code == 200
        yield c


def board(client):
    return client.get("/v1/cop/exercise", headers=BC).json()


def test_the_exercise_profile_is_the_brigade_on_its_own_ground(client):
    snap = client.get("/v1/cop/snapshot", headers=BC).json()
    assert snap["profile"] == "exercise"
    assert [s["code"] for s in snap["sections"] if s["enabled"]] == ["S1", "S2", "S3", "S4", "S6"], "an exercise runs the full staff"
    assert snap["summary"]["total_people"] > 1000, "the same force as the military profile, on its own dataset"
    assert snap["exercise"]["running"] is False and snap["exercise"]["exercise"] is None
    assert {s["id"] for s in snap["exercise"]["scenarios"]} >= {"farp_eagle", "accountability_drill"}


def test_an_exercise_refuses_to_run_on_a_real_profile(client):
    """The separation is the whole guarantee: no exercise profile, no injects."""
    assert client.put("/v1/cop/profile", json={"profile": "military"}, headers=BC).status_code == 200
    r = client.post("/v1/cop/exercise", json={"scenario": "farp_eagle"}, headers=BC)
    assert r.status_code == 422 and "exercise profile" in r.text
    assert client.put("/v1/cop/profile", json={"profile": "exercise"}, headers=BC).status_code == 200


def test_setting_up_an_exercise_is_exercise_controls_alone(client):
    assert client.post("/v1/cop/exercise", json={"scenario": "farp_eagle"}, headers=S4).status_code == 403
    assert client.post("/v1/cop/exercise", json={"scenario": "no_such_scenario"}, headers=BC).status_code == 422


def test_the_msel_is_loaded_but_nothing_fires_until_startex(client):
    r = client.post("/v1/cop/exercise", json={"scenario": "farp_eagle", "speed": 60}, headers=BC)
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["exercise"]["status"] == "planned" and b["running"] is False
    assert b["exercise"]["total"] == 11 and b["exercise"]["fired"] == 0
    assert all(i["status"] == "pending" and i["due_at"] is None for i in b["injects"])
    assert [i["seq"] for i in b["injects"]] == list(range(1, 12)), "the MSEL reads in order"
    # nothing has happened to the picture
    assert client.post("/v1/cop/exercise/tick", headers=BC).json()["fired"] == []


def test_startex_fires_the_zero_offset_inject_and_the_wall_wears_the_banner(client):
    ex = board(client)["exercise"]
    r = client.post(f"/v1/cop/exercise/{ex['id']}/start", headers=BC)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["running"] is True and b["exercise"]["started_at"]
    assert [f["seq"] for f in b["fired"]] == [1], "the inject at offset zero is STARTEX itself"
    assert "EXERCISE EXERCISE EXERCISE" in b["injects"][0]["result"]
    snap = client.get("/v1/cop/snapshot", headers=BC).json()
    assert snap["exercise"]["running"] is True and snap["summary"]["exercise"] is True
    assert snap["exercise"]["exercise"]["next"]["title"], "the board names what is coming"


def test_the_schedule_compresses_and_the_clock_does_not(client):
    """At ×60 a twenty-minute MSEL runs in twenty seconds — the offsets are divided, the clock is untouched."""
    b = board(client)
    ex, injects = b["exercise"], b["injects"]
    started = ex["started_at"]
    second, last = injects[1], injects[-1]
    assert second["due_at"] > started and last["due_at"] > second["due_at"]
    # offset 1 min at ×60 is one second after STARTEX; offset 20 is twenty seconds after it
    from datetime import datetime
    t0 = datetime.fromisoformat(started.replace("Z", ""))
    assert abs((datetime.fromisoformat(second["due_at"].replace("Z", "")) - t0).total_seconds() - 1) < 0.01
    assert abs((datetime.fromisoformat(last["due_at"].replace("Z", "")) - t0).total_seconds() - 20) < 0.01


def test_every_inject_writes_what_a_person_would_have_written(client):
    """Fire the whole MSEL by hand and check the picture moved: S2 reporting, S6 comms, S4 fuel and readiness,
    S1 accountability, S3 posture and a tasking. Each one through the same rows the staff's own actions use."""
    before = client.get("/v1/cop/snapshot", headers=BC).json()
    ex = board(client)["exercise"]
    for inj in [i for i in board(client)["injects"] if i["status"] == "pending"]:
        r = client.post(f"/v1/cop/exercise/injects/{inj['id']}/fire", headers=BC)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "fired", f"{inj['title']} — {r.json().get('error')}"

    after = client.get("/v1/cop/snapshot", headers=BC).json()
    b = board(client)
    assert b["exercise"]["fired"] == 11 and b["exercise"]["failed"] == 0

    # S2: two SPOTREPs, both marked EXERCISE
    reports = [r for r in after["s2_reports"] if r["source"] == "exercise"]
    assert len(reports) == 2 and all(r["text"].startswith("EXERCISE — ") for r in reports)
    # S6: a net at the FARP is no longer green
    farp = next(l for l in after["locations"] if "FARP Eagle" in l["name"])
    assert any(s["location_id"] == farp["id"] and s["health"] != "green" for s in after["s6"]["systems"])
    # S3: the site's posture rose
    assert farp["posture"] == "high" and next(l for l in before["locations"] if l["id"] == farp["id"])["posture"] != "high"
    # S4: fuel is down to the half-day the scenario states, and two airframes are NMC
    fuel = next(s for s in after["s4"]["supplies"] if s["location_id"] == farp["id"] and "iii" in (s["category"] + s["item"]).lower())
    assert fuel["days_of_supply"] == 0.5
    assert after["s4"]["readiness"]["nmc"] >= before["s4"]["readiness"]["nmc"] + 2
    assert after["s4"]["readiness"]["or_pct"] < before["s4"]["readiness"]["or_pct"]
    # S1: a roll call is open and everyone in it starts unaccounted
    rc = next(i for i in after["incidents"] if i["status"] == "open" and "FARP Eagle" in i["title"])
    assert rc["total"] > 0 and rc["counts"]["unaccounted"] == rc["total"]
    # S3: the collection tasking S3 asked for
    assert any(t["from_section"] == "S3" and t["to_section"] == "S2" and "launch point" in t["title"] for t in after["taskings"]["items"])
    # the unit that reported in is no longer stale
    assert any(p["team_short"] == "1 ATK" and not p["stale"] for p in after["unit_positions"])


def test_exercise_control_is_the_actor_on_every_line(client):
    log = client.get("/v1/cop/activity?limit=60", headers=BC).json()
    rows = log["items"] if "items" in log else log
    injects = [r for r in rows if r["type"] == "cop.exercise.inject"]
    assert len(injects) >= 11
    assert all(r["actor"] == "EXERCISE CONTROL" and r["actor_type"] == "system" for r in injects)
    assert all("EXERCISE inject" in (r["summary"] or "") for r in injects)


def test_the_scenario_moved_the_ccir_board(client):
    """The point of the exercise: the commander's list reacts to it without anybody touching the list."""
    client.post("/v1/cop/ccir/evaluate", headers=BC)
    lines = client.get("/v1/cop/ccir", headers=BC).json()["lines"]
    tripped = {l["metric"] for l in lines if l["state"] == "tripped"}
    assert {"unaccounted", "days_of_supply"} <= tripped, "the roll call and the fuel inject are CCIR business"


def test_an_inject_that_cannot_find_its_target_fails_loudly(client):
    """A scenario written against a dataset that does not hold the thing it names must say so on the board."""
    from coptoc.exercise import SCENARIOS
    ex_id = board(client)["exercise"]["id"]
    client.post(f"/v1/cop/exercise/{ex_id}/end", json={"notes": "test"}, headers=BC)
    SCENARIOS["_broken"] = {"name": "Broken scenario", "summary": "names a site nobody has", "profile": "military",
                            "injects": [(0, "system", "A net at a place we do not hold", "S6", {"site": "Camp Nowhere", "status": "down"})]}
    try:
        b = client.post("/v1/cop/exercise", json={"scenario": "_broken"}, headers=BC).json()
        client.post(f"/v1/cop/exercise/{b['exercise']['id']}/start", headers=BC)
        inject = board(client)["injects"][0]
        assert inject["status"] == "failed"
        assert "Camp Nowhere" in inject["error"] and "does not have" in inject["error"]
        client.post(f"/v1/cop/exercise/{b['exercise']['id']}/end", json={}, headers=BC)
    finally:
        SCENARIOS.pop("_broken", None)


def test_endex_skips_what_never_came_due_and_says_so(client):
    r = client.post("/v1/cop/exercise", json={"scenario": "accountability_drill", "speed": 1}, headers=BC)
    ex_id = r.json()["exercise"]["id"]
    client.post(f"/v1/cop/exercise/{ex_id}/start", headers=BC)
    b = client.post(f"/v1/cop/exercise/{ex_id}/end", json={"notes": "cut short for the test"}, headers=BC).json()
    assert b["running"] is False and b["exercise"]["status"] == "ended" and b["exercise"]["ended_at"]
    skipped = [i for i in b["injects"] if i["status"] == "skipped"]
    assert len(skipped) == 3 and all(i["result"] == "ENDEX before this inject was due" for i in skipped)
    assert client.post("/v1/cop/exercise/tick", headers=BC).json()["fired"] == [], "an ended exercise fires nothing"
    snap = client.get("/v1/cop/snapshot", headers=BC).json()
    assert snap["exercise"]["running"] is False and snap["summary"]["exercise"] is False


def test_only_one_exercise_runs_at_a_time(client):
    a = client.post("/v1/cop/exercise", json={"scenario": "accountability_drill"}, headers=BC).json()
    client.post(f"/v1/cop/exercise/{a['exercise']['id']}/start", headers=BC)
    r = client.post("/v1/cop/exercise", json={"scenario": "farp_eagle"}, headers=BC)
    assert r.status_code == 422 and "already running" in r.text
    client.post(f"/v1/cop/exercise/{a['exercise']['id']}/end", json={}, headers=BC)


def test_leaving_the_exercise_profile_reloads_the_deployments_own_data(client):
    """The isolation, end to end: the roll call and the fuel state the exercise left do not follow you out."""
    assert client.put("/v1/cop/profile", json={"profile": "military"}, headers=BC).status_code == 200
    snap = client.get("/v1/cop/snapshot", headers=BC).json()
    assert snap["profile"] == "military"
    assert not [i for i in snap["incidents"] if "EXERCISE" in i["title"]]
    assert not [r for r in snap["s2_reports"] if r["source"] == "exercise"]
    farp = next(l for l in snap["locations"] if "FARP Eagle" in l["name"])
    assert farp["posture"] != "high", "the exercise raised this site's posture on its own ground, not here"
