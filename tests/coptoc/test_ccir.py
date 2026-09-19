"""§3.6 — CCIR: one list of what has to wake the commander, and the discipline that a trip reports rather than acts.

The three kinds behave differently on purpose: an FFIR watches a number that is already on the wall, a PIR points at
an S2 requirement, and an EEFI never trips because nothing in the data measures our own signature.
"""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"; os.environ["TOC_CCIR_CLOCK"] = "off"

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc_day"}
S4 = {"X-TOC-Role": "logistics", "X-TOC-Actor": "supply_sgt"}
AN = {"X-TOC-Role": "analyst", "X-TOC-Actor": "s2_lee"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.post("/v1/cop/seed?dataset=cab").status_code == 200
        yield c


def lines(client):
    return {l["text"]: l for l in client.get("/v1/cop/ccir", headers=BC).json()["lines"]}


def test_the_sample_force_arrives_with_a_board_of_all_three_kinds(client):
    board = client.get("/v1/cop/ccir", headers=BC).json()
    kinds = board["by_kind"]
    assert kinds["ffir"] >= 4 and kinds["pir"] >= 1 and kinds["eefi"] >= 1, "a CCIR is PIR, FFIR and EEFI together"
    assert board["counts"]["total"] == len(board["lines"])
    # every FFIR reads as a sentence, with the threshold in it — the Battle Captain has to be able to read it out
    ffir = next(l for l in board["lines"] if l["kind"] == "ffir")
    assert ffir["condition"] and str(ffir["threshold"]).replace(".0", "") in ffir["condition"]
    assert ffir["owner_section"] in ("S1", "S2", "S3", "S4", "S6")


def test_an_eefi_never_trips_because_nothing_measures_our_own_signature(client):
    eefi = [l for l in client.get("/v1/cop/ccir", headers=BC).json()["lines"] if l["kind"] == "eefi"]
    assert eefi, "the sample includes EEFI"
    assert all(l["state"] == "narrative" and l["metric"] is None for l in eefi)
    assert all("not measured" in l["condition"] for l in eefi)


def test_an_ffir_reads_the_number_already_on_the_wall(client):
    snap = client.get("/v1/cop/snapshot", headers=BC).json()
    board = snap["ccir"]
    or_line = next(l for l in board["lines"] if l["metric"] == "or_pct")
    assert or_line["value"] == snap["s4"]["readiness"]["or_pct"], "the board never computes a number a second way"
    supply = next(l for l in board["lines"] if l["metric"] == "days_of_supply")
    on_the_wall = [s["days_of_supply"] for s in snap["s4"]["supplies"] if s["days_of_supply"] is not None and "iii" in (s["category"] + s["item"]).lower()]
    assert supply["value"] == (min(on_the_wall) if on_the_wall else None)


def test_a_metric_with_no_reading_says_so_rather_than_green(client):
    r = client.post("/v1/cop/ccir", json={"kind": "ffir", "text": "Fuel at a site that does not exist", "metric": "days_of_supply",
                                          "comparator": "lt", "threshold": 3, "scope": "no-such-supply-class"}, headers=BC)
    assert r.status_code == 201, r.text
    line = lines(client)["Fuel at a site that does not exist"]
    assert line["state"] == "unmeasured", "nothing told us is not the same as we checked and we are fine"
    client.patch(f"/v1/cop/ccir/{line['id']}", json={"status": "inactive"}, headers=BC)


def test_writing_a_line_is_the_battle_captains_alone(client):
    r = client.post("/v1/cop/ccir", json={"kind": "ffir", "text": "Anything", "metric": "unaccounted", "comparator": "gte", "threshold": 1}, headers=S4)
    assert r.status_code == 403
    assert client.patch("/v1/cop/ccir/ccir_nope", json={"status": "inactive"}, headers=AN).status_code == 403


def test_an_ffir_needs_a_threshold_and_a_metric_that_exists(client):
    assert client.post("/v1/cop/ccir", json={"kind": "ffir", "text": "No threshold", "metric": "unaccounted"}, headers=BC).status_code == 422
    assert client.post("/v1/cop/ccir", json={"kind": "ffir", "text": "No such metric", "metric": "vibes", "threshold": 1}, headers=BC).status_code == 422
    assert client.post("/v1/cop/ccir", json={"kind": "pir", "text": "Points nowhere"}, headers=BC).status_code == 422


def test_a_trip_reports_and_does_not_act(client):
    """Crossing the threshold turns the line red, suggests a warning, and writes the ledger. Nothing is dispatched."""
    # the threshold is set one above what the board reads now, so the line starts green and only this test's
    # outage can trip it — the sample force already runs with some comms degraded
    systems = client.get("/v1/cop/snapshot", headers=BC).json()["s6"]["systems"]
    degraded_now = sum(1 for s in systems if s["health"] != "green")
    r = client.post("/v1/cop/ccir", json={"kind": "ffir", "text": "One more comms system than we already carry",
                                          "metric": "pace_degraded", "comparator": "gte", "threshold": degraded_now + 1, "priority": 1}, headers=BC)
    line_id = r.json()["id"]
    assert client.post("/v1/cop/ccir/evaluate", headers=BC).json() is not None
    assert next(l for l in client.get("/v1/cop/ccir", headers=BC).json()["lines"] if l["id"] == line_id)["state"] == "green"
    # take a system down: the number on the S6 board moves, so the requirement watching it must move with it
    victim = next(s for s in systems if s["health"] == "green")
    assert client.patch(f"/v1/cop/systems/{victim['id']}", json={"status": "down", "note": "generator failure"}, headers=BC).status_code == 200

    changes = client.post("/v1/cop/ccir/evaluate", headers=BC).json()["changes"]
    assert any(c["id"] == line_id and c["new"] == "tripped" for c in changes)

    snap = client.get("/v1/cop/snapshot", headers=BC).json()
    tripped = next(l for l in snap["ccir"]["lines"] if l["id"] == line_id)
    assert tripped["state"] == "tripped" and tripped["trips"] == 1 and tripped["tripped_at"]
    assert snap["summary"]["ccir_tripped"] >= 1

    warnings = [w for w in snap["warnings"] if w["subject_type"] == "ccir" and w["subject_id"] == line_id]
    assert len(warnings) == 1, "a trip suggests exactly one warning"
    assert warnings[0]["status"] == "suggested", "suggested, not released: the machine reports and the human decides"
    assert warnings[0]["severity"] == "critical", "a priority-1 line is a critical suggestion"

    # the watch carries it, so the handover brief does
    assert any(e["type"] == "cop.ccir.tripped" and e["subject"] == line_id for e in snap["watch_log"])

    # evaluating again while nothing has changed records nothing for this line: the change is the event, not the evaluation
    assert [c for c in client.post("/v1/cop/ccir/evaluate", headers=BC).json()["changes"] if c["id"] == line_id] == []
    assert len([w for w in client.get("/v1/cop/snapshot", headers=BC).json()["warnings"] if w["subject_id"] == line_id]) == 1

    # fix it and the line clears, with the time it spent tripped on the record
    assert client.patch(f"/v1/cop/systems/{victim['id']}", json={"status": "up", "note": "generator replaced"}, headers=BC).status_code == 200
    cleared = client.post("/v1/cop/ccir/evaluate", headers=BC).json()["changes"]
    assert any(c["id"] == line_id and c["new"] == "green" for c in cleared)
    line = next(l for l in client.get("/v1/cop/ccir", headers=BC).json()["lines"] if l["id"] == line_id)
    assert line["state"] == "green" and line["cleared_at"] and line["trips"] == 1
    client.patch(f"/v1/cop/ccir/{line_id}", json={"status": "inactive"}, headers=BC)


def test_a_pir_line_trips_when_its_pir_is_answered(client):
    board = client.get("/v1/cop/ccir", headers=BC).json()
    pir_line = next(l for l in board["lines"] if l["kind"] == "pir")
    assert pir_line["state"] == "green" and pir_line["pir_id"]
    assert client.patch(f"/v1/cop/pirs/{pir_line['pir_id']}", json={"status": "ANSWERED"}, headers=AN).status_code == 200
    after = next(l for l in client.get("/v1/cop/ccir", headers=BC).json()["lines"] if l["id"] == pir_line["id"])
    assert after["state"] == "tripped", "what the commander wants told is that the question now has an answer"


def test_the_metric_catalog_only_offers_numbers_the_wall_already_carries(client):
    cat = client.get("/v1/cop/ccir/metrics", headers=BC).json()
    snap = client.get("/v1/cop/snapshot", headers=BC).json()
    assert cat["kinds"] == ["pir", "ffir", "eefi"]
    for m in cat["metrics"]:
        assert m["label"] and m["section"] and m["unit"]
        if m["id"] in snap["summary"]:
            assert isinstance(snap["summary"][m["id"]], (int, float))


def test_a_retired_line_stops_being_watched(client):
    r = client.post("/v1/cop/ccir", json={"kind": "ffir", "text": "Retire me", "metric": "open_incidents", "comparator": "gte", "threshold": 0}, headers=BC)
    line_id = r.json()["id"]
    assert next(l for l in client.get("/v1/cop/ccir", headers=BC).json()["lines"] if l["id"] == line_id)["state"] == "tripped"
    assert client.patch(f"/v1/cop/ccir/{line_id}", json={"status": "inactive"}, headers=BC).status_code == 200
    assert [c for c in client.post("/v1/cop/ccir/evaluate", headers=BC).json()["changes"] if c["id"] == line_id] == []
