"""§5.6b the subject of concern: the file the desk keeps on a *person*, and the mailroom that feeds it.

The discipline under test is §5.6a's, pointed at a person instead of a place — a fixed indicator list, a rating and a
line of justification per indicator, nothing summed, a new assessment superseding the last — plus the two rules that
only matter once the object is a human being: a file names a private individual, so it sits behind a clearance; and a
message nobody can attribute stays in the inbox rather than being tidied onto a folder.
"""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app
from coptoc.subjects import indicators

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}
EP = {"X-TOC-Role": "ep", "X-TOC-Actor": "ep lead"}
AN = {"X-TOC-Role": "analyst", "X-TOC-Actor": "S2 Analyst"}
EA = {"X-TOC-Role": "ea", "X-TOC-Actor": "ea"}          # plans travel; has no business in a subject file
SEC = {"X-TOC-Role": "security", "X-TOC-Actor": "guard_07"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.put("/v1/cop/profile", json={"profile": "corporate"}, headers=BC).status_code == 200
        assert c.post("/v1/cop/seed?dataset=corporate").status_code == 200
        yield c


# ---------------------------------------------------------------- the file itself

def test_the_north_gate_pair_are_files_on_people_not_a_circle_round_a_building(client):
    """The worked example: the man two guards reported is a folder now, and his ratings say only what the reports say."""
    subjects = client.get("/v1/cop/subjects", headers=AN).json()
    vane = next(s for s in subjects if s["name"] == "Marcus Vane")
    assert vane["worst"] == "red" and vane["worst_indicator"] == "Research, planning & preparation"
    assert vane["principal_name"] == "Alex Ventura" and vane["location_id"] == "loc_sf"
    assert vane["case_id"] == "case_seed_gate"          # the evidence graph is still the case's job
    assert len(vane["assessment"]["ratings"]) == len(indicators("corporate"))
    # Nothing is summed. `worst` is the worst rated indicator and there is no score anywhere on the payload.
    assert "score" not in vane and "band" not in vane
    assert vane["counts"]["red"] == 2 and vane["counts"]["unknown"] == 4
    # What we do not know stays unknown rather than being called green, and each rating carries its line.
    threat = next(r for r in vane["assessment"]["ratings"] if r["indicator"] == "threat")
    means = next(r for r in vane["assessment"]["ratings"] if r["indicator"] == "means")
    assert threat["rating"] == "green" and "No directed or conditional threat" in threat["note"]
    assert means["rating"] == "unknown" and means["note"]
    # The second file exists because she is in both reports, and says so rather than implying anything.
    ortiz = next(s for s in subjects if s["name"] == "Dana Ortiz")
    assert ortiz["status"] == "monitoring" and ortiz["counts"]["red"] == 0
    assert next(r for r in ortiz["assessment"]["ratings"] if r["indicator"] == "pathway")["rating"] == "unknown"


def test_the_principal_and_the_site_each_carry_the_files_that_name_them(client):
    snap = client.get("/v1/cop/snapshot?restricted=true", headers=BC).json()
    ceo = next(p for p in snap["people"] if p["id"] == "p_ceo")
    assert [s["name"] for s in ceo["subjects"]] == ["Marcus Vane"]
    assert ceo["subjects"][0]["worst"] == "red" and len(ceo["subjects"][0]["strip"]) == 10
    sf = next(l for l in snap["locations"] if l["id"] == "loc_sf")
    assert sorted(s["name"] for s in sf["subjects"]) == ["Dana Ortiz", "Marcus Vane"]
    # A principal nobody is directed at carries an empty list, not a missing key.
    assert next(p for p in snap["people"] if p["id"] == "p_cto")["subjects"] == []


def test_the_tally_is_open_to_the_floor_and_the_names_are_not(client):
    """A count is not an identity. The wall says three files are open; only a cleared role gets who they are."""
    open_ = client.get("/v1/cop/snapshot").json()
    assert open_["summary"]["subjects_open"] == 2 and open_["summary"]["subjects_red"] == 1
    assert open_["summary"]["subject_inbox"] == 2
    assert open_["subjects"] == [] and open_["subject_inbox"] == []
    assert all(p["subjects"] == [] for p in open_["people"])
    assert all(l["subjects"] == [] for l in open_["locations"])
    cleared = client.get("/v1/cop/snapshot?restricted=true", headers=BC).json()
    assert len(cleared["subjects"]) == 2 and len(cleared["subject_inbox"]) == 2
    # The files carry their own clearance. The analyst who works them gets them without asking for the residences
    # layer — and asking for it changes nothing, because she is not cleared for the CEO's home address either way.
    an = client.get("/v1/cop/snapshot", headers=AN).json()
    assert len(an["subjects"]) == 2 and not any(l["sensitivity"] == "restricted" for l in an["locations"])
    assert client.get("/v1/cop/snapshot", headers=EA).json()["subjects"] == []
    # And the endpoints are gated the same way, by role alone — a section right is not a clearance.
    assert client.get("/v1/cop/subjects", headers=EA).status_code == 403
    assert client.get("/v1/cop/subjects/subj_001", headers=EA).status_code == 403
    assert client.get("/v1/cop/contacts", headers=EA).status_code == 403
    for h in (BC, EP, AN):
        assert client.get("/v1/cop/subjects", headers=h).status_code == 200


def test_an_open_file_nobody_has_assessed_is_an_exception_not_a_green_one(client):
    r = client.post("/v1/cop/subjects", headers=EP, json={
        "name": "Unknown male — Atherton verge", "summary": "Parked opposite the residence twice this week.",
        "principal_id": "p_ceo", "aliases": ["dark hatchback, partial plate 8K"]})
    assert r.status_code == 201
    s = r.json()
    assert s["unassessed"] is True and s["worst"] == "unknown" and s["assessment"] is None
    assert s["stale"] is False and s["counts"] == {"green": 0, "amber": 0, "red": 0, "unknown": 0}
    assert s["principal_name"] == "Alex Ventura"       # resolved from our own directory, not from the text
    summary = client.get("/v1/cop/snapshot").json()["summary"]
    assert summary["subjects_open"] == 3 and summary["subjects_unassessed"] == 1
    client.patch(f"/v1/cop/subjects/{s['id']}", headers=BC, json={"status": "closed", "closed_reason": "Identified as a neighbour's contractor; verified with the estate manager."})


def test_a_file_cannot_be_closed_or_referred_without_saying_why_or_to_whom(client):
    sid = client.post("/v1/cop/subjects", headers=AN, json={"name": "Caller — switchboard"}).json()["id"]
    assert client.patch(f"/v1/cop/subjects/{sid}", headers=BC, json={"status": "closed"}).status_code == 422
    assert client.patch(f"/v1/cop/subjects/{sid}", headers=BC, json={"status": "referred"}).status_code == 422
    r = client.patch(f"/v1/cop/subjects/{sid}", headers=BC, json={"status": "referred", "referred_to": "SFPD — Northern Station, report 26-114233"})
    assert r.status_code == 200 and r.json()["status"] == "referred" and r.json()["referred_at"]
    log = client.get("/v1/cop/log?limit=10").json()
    assert any(e["type"] == "cop.subject.referred" and "SFPD" in e["summary"] for e in log)


# ---------------------------------------------------------------- assessing a person

def test_assessing_supersedes_and_the_old_one_stays_as_history(client):
    before = client.get("/v1/cop/subjects/subj_001", headers=AN).json()
    assert before["history"] == []
    r = client.post("/v1/cop/subjects/subj_001/assess", headers=AN, json={
        "summary": "Means now answered by law enforcement liaison; nothing held. Everything else stands.",
        "ratings": [{"indicator": i["id"], "rating": "amber", "note": "carried forward"} for i in indicators("corporate")]
             + [{"indicator": "means", "rating": "green", "note": "SFPD liaison: no registered firearms, no history of violence."}]})
    assert r.status_code == 201
    after = client.get("/v1/cop/subjects/subj_001", headers=AN).json()
    assert after["worst"] == "amber" and after["counts"]["red"] == 0
    assert next(x for x in after["assessment"]["ratings"] if x["indicator"] == "means")["rating"] == "green"
    assert len(after["history"]) == 1 and after["history"][0]["worst"] == "red"   # the red assessment is still on the record
    assert after["assessment"]["supersedes"] == after["history"][0]["id"]
    log = client.get("/v1/cop/log?limit=10").json()
    assert any(e["type"] == "cop.subject.assessed" and "supersedes the last" in e["summary"] for e in log)


def test_only_the_hands_that_rate_a_place_may_rate_a_person(client):
    """EP may open, amend and refer a file; judging it is S2's, the same as §5.6a."""
    body = {"ratings": [{"indicator": "approach", "rating": "red", "note": "x"}]}
    assert client.post("/v1/cop/subjects/subj_002/assess", headers=EP, json=body).status_code == 403
    assert client.post("/v1/cop/subjects/subj_002/assess", headers=AN, json=body).status_code == 201
    assert client.patch("/v1/cop/subjects/subj_002", headers=EP, json={"summary": "EP holds the standing detail note."}).status_code == 200


def test_the_indicator_list_is_configuration_and_never_a_scored_instrument(client, monkeypatch):
    assert client.get("/v1/cop/subjects/indicators", headers=AN).json()["profile"] == "corporate"
    assert [i["id"] for i in indicators("military")][1] == "association"   # a different desk asks different questions
    monkeypatch.setattr("coptoc.subjects.settings.get",
                        lambda name, default=None: "grievance=Stated grievance, Approach, means=Access to weapons" if name == "TOC_SUBJECT_INDICATORS" else None)
    inds = indicators("corporate")
    assert [i["id"] for i in inds] == ["grievance", "approach", "means"]
    assert [i["label"] for i in inds] == ["Stated grievance", "Approach", "Access to weapons"]


# ---------------------------------------------------------------- the mailroom

def test_what_arrives_is_graded_when_it_lands_and_nothing_is_guessed_onto_a_folder(client):
    inbox = client.get("/v1/cop/contacts?inbox=true", headers=AN).json()
    assert len(inbox) == 2 and all(c["subject_id"] is None and c["triage"] == "new" for c in inbox)
    # The one that reads like Vane is still in the inbox, because nothing in it says it is him.
    form = next(c for c in inbox if c["channel"] == "form")
    assert "March decision" in form["text"] and form["principal_id"] is None and form["principal_name"] == ""
    # The target can be known while the sender is not: a title maps to one person in our own directory.
    dm = next(c for c in inbox if c["channel"] == "dm")
    assert dm["principal_id"] == "p_cfo" and dm["principal_name"] == "Priya Ramanathan" and dm["directness"] == "veiled"
    # Everything lands F/6 — an unknown sender cannot be judged, and one uncorroborated item says nothing.
    assert all(c["reliability"] == "F" and c["credibility"] == 6 for c in inbox)
    filed = client.get("/v1/cop/contacts?subject_id=subj_001", headers=AN).json()
    assert len(filed) == 3 and [c["directness"] for c in filed] == ["veiled", "veiled", "none"]  # newest first


def test_a_contact_filed_without_a_subject_lands_in_the_inbox(client):
    r = client.post("/v1/cop/contacts", headers=SEC, json={
        "channel": "phone", "from_label": "withheld number",
        "text": "Caller asked which entrance the executives use and rang off when asked for a name.",
        "directness": "none", "received_by": "Front desk — SF HQ"})
    assert r.status_code == 201
    c = r.json()
    assert c["subject_id"] is None and c["triage"] == "new" and c["reliability"] == "F" and c["credibility"] == 6
    assert client.get("/v1/cop/snapshot").json()["summary"]["subject_inbox"] == 3
    # Working it: the analyst attributes it, and the file picks it up.
    t = client.patch(f"/v1/cop/contacts/{c['id']}", headers=AN,
                     json={"subject_id": "subj_001", "directness": "veiled", "note": "Same question the second letter asks."})
    assert t.status_code == 200 and t.json()["subject_id"] == "subj_001" and t.json()["triage"] == "filed"
    assert t.json()["triaged_by"] == "S2 Analyst" and t.json()["triaged_at"]
    vane = client.get("/v1/cop/subjects/subj_001", headers=AN).json()
    assert vane["contact_count"] == 4 and vane["contacts"][0]["channel"] == "phone"
    assert client.get("/v1/cop/snapshot").json()["summary"]["subject_inbox"] == 2
    log = client.get("/v1/cop/log?limit=10").json()
    assert any(e["type"] == "cop.contact.triaged" and "attributed to Marcus Vane" in e["summary"] for e in log)


def test_dismissing_a_contact_needs_a_line_saying_why(client):
    cid = client.post("/v1/cop/contacts", headers=SEC, json={"channel": "email", "text": "Newsletter bounce.", "from_label": "noreply@example.invalid"}).json()["id"]
    assert client.patch(f"/v1/cop/contacts/{cid}", headers=AN, json={"triage": "dismissed"}).status_code == 422
    r = client.patch(f"/v1/cop/contacts/{cid}", headers=AN, json={"triage": "dismissed", "note": "Automated bounce; no named target."})
    assert r.status_code == 200 and r.json()["triage"] == "dismissed"
    # A guard may open the envelope; deciding what it is belongs to the desk.
    assert client.patch(f"/v1/cop/contacts/{cid}", headers=SEC, json={"triage": "assessed"}).status_code == 403
    assert client.post("/v1/cop/contacts", headers=EA, json={"channel": "email", "text": "x"}).status_code == 403


def test_a_contact_needs_the_words_it_arrived_in(client):
    assert client.post("/v1/cop/contacts", headers=AN, json={"channel": "letter", "text": "   "}).status_code == 422
    assert client.post("/v1/cop/subjects", headers=AN, json={"name": "  "}).status_code == 422
