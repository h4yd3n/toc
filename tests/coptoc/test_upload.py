"""§13 the spreadsheet upload: a messy Excel workbook → header found → mapping proposed → preview → commit; nothing lands unapproved."""
import io, os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from coptoc.app import app
from coptoc.upload import _split_unit, find_header, heuristic_mapping

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}
def U(uid): return {"X-TOC-User": uid}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed?dataset=cab")
        yield c


def xlsx(sheets):
    wb = Workbook(); wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows: ws.append(r)
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


def test_header_row_under_title_rows_and_unit_paths():
    rows = [["1st Attack Bn — Alpha Roster (FOUO)"], [], ["as of 05 SEP"], ["RANK", "LAST NAME", "FIRST NAME", "UNIT", "DUTY POSITION", "CELL"], ["SSG", "Reyes", "Jordan", "B/1-101 ARB", "Crew Chief", "270-555-0101"]]
    assert find_header(rows) == 3
    m = heuristic_mapping("S1", ["RANK", "LAST NAME", "FIRST NAME", "UNIT", "DUTY POSITION", "CELL", "EMAIL ADDR"], [{"CELL": "270-555-0101", "EMAIL ADDR": "x@example.mil"}])
    assert m == {"RANK": "rank", "LAST NAME": "last_name", "FIRST NAME": "first_name", "UNIT": "unit", "DUTY POSITION": "role", "CELL": "phone", "EMAIL ADDR": "email"}
    assert _split_unit("B/1-101 ARB") == [("battalion", "1-101 ARB"), ("company", "B")]
    assert _split_unit("HHC/CAB") == [("brigade", "CAB"), ("company", "HHC")]
    assert _split_unit("A Co, 2-17 CAV") == [("battalion", "2-17 CAV"), ("company", "A Co")]


def test_s1_roster_builds_the_task_organization(client):
    data = xlsx({"Roster": [["Alpha Company Roster"], [], ["Rank", "Last Name", "First Name", "Unit", "Duty Position", "Cell", "Email"],
                            ["SSG", "Nguyen", "Alex", "A/1 ATK", "Crew Chief", "270-555-0100", "alex.nguyen@example.mil"],
                            ["CPT", "Brooks", "Riley", "F/1 ATK", "Company Commander", "", ""],           # a company that does not exist yet
                            ["SGT", "Kim", "Dana", "B/2-17 CAV", "Scout", "", ""],                        # a battalion that does not exist yet
                            ["", "", "", "", "", "", ""], ["PV2", "Smith", "Lee", "", "", "", ""]]})     # no unit: reported, not guessed
    r = client.post("/v1/cop/upload/S1/preview", files={"file": ("roster.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, headers=BC)
    assert r.status_code == 200, r.text
    pv = r.json()
    assert pv["sheet"] == "Roster" and pv["header_row"] == 1 and pv["rows"] == 4  # blank rows are dropped before the header is found and pv["proposed_by"] == "headers" and pv["issues"] == []
    assert pv["mapping"]["Unit"] == "unit" and pv["mapping"]["Last Name"] == "last_name"
    assert client.get("/v1/cop/snapshot").json()["summary"]["total_people"] == 2395  # preview landed nothing
    r = client.post("/v1/cop/upload/S1/commit", json={"upload_id": pv["upload_id"], "sheet": pv["sheet"], "mapping": pv["mapping"]}, headers=BC)
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["created"] == 3 and res["skipped"] == 1 and "row 4" in res["errors"][0]
    snap = client.get("/v1/cop/snapshot").json()
    teams = {t["id"]: t for t in snap["teams"]}
    alex = next(p for p in snap["people"] if p["name"] == "SSG Alex Nguyen")
    assert teams[alex["team_id"]]["short"] == "A/1" and alex["phone"] == "270-555-0100" and alex["source"] == "upload:roster.xlsx"
    riley = next(p for p in snap["people"] if p["name"].endswith("Riley Brooks"))
    f_co = teams[riley["team_id"]]
    assert f_co["short"] == "F/1 ATK" and teams[f_co["parent_id"]]["short"] == "1 ATK"  # new company under the existing battalion
    dana = next(p for p in snap["people"] if p["name"].endswith("Dana Kim"))
    b_co = teams[dana["team_id"]]; cav = teams[b_co["parent_id"]]
    assert cav["echelon"] == "battalion" and cav["parent_id"] == "t_cab" and b_co["echelon"] == "company"  # new battalion under the brigade
    assert snap["log"][0]["type"] == "cop.import" and "S1 upload" in snap["log"][0]["summary"]


def test_s4_supply_sheet_with_classes_of_supply(client):
    data = xlsx({"Class III-V": [["BRIGADE LOGSTAT 05 SEP"], ["Site", "Class", "Nomenclature", "O/H", "Auth", "UOM", "Remarks"],
                                 ["FARP Eagle", "III", "JP-8", "12000", "20000", "gal", "convoy inbound"],
                                 ["FOB Warrior", "V", "7.62 mm linked", "18000", "24000", "rds", ""],
                                 ["Nowhere Base", "I", "MRE", "100", "200", "cases", ""],
                                 ["1 ATK", "IX", "T700 engine", "1", "2", "ea", "at the unit's site"]]})
    pv = client.post("/v1/cop/upload/S4/preview", files={"file": ("logstat.xlsx", data, "application/octet-stream")}, headers=U("u_supply")).json()
    assert pv["kind"] == "supply" and pv["mapping"]["O/H"] == "on_hand" and pv["mapping"]["Auth"] == "required" and pv["mapping"]["Nomenclature"] == "item" and pv["mapping"]["Class"] == "category"
    res = client.post("/v1/cop/upload/S4/commit", json={"upload_id": pv["upload_id"], "sheet": pv["sheet"], "mapping": pv["mapping"], "kind": "supply"}, headers=U("u_supply")).json()
    assert res["created"] == 4 and res["updated"] == 0 and res["skipped"] == 0  # "JP-8" is not the seed's "JP-8 (Class III) — FARP Eagle": a new line, matched only on the exact item
    s4 = client.get("/v1/cop/snapshot").json()["s4"]
    jp8 = next(x for x in s4["supplies"] if x["location_id"] == "loc_farp" and x["item"] == "JP-8")
    assert jp8["on_hand"] == 12000 and jp8["status"] == "amber" and jp8["category"] == "fuel"
    linked = next(x for x in s4["supplies"] if x["item"] == "7.62 mm linked")
    assert linked["category"] == "ammunition" and linked["location_name"].startswith("FOB Warrior")
    engine = next(x for x in s4["supplies"] if x["item"] == "T700 engine")
    assert engine["category"] == "parts" and engine["location_id"] == "loc_1atk"  # a unit name placed it at the unit's site
    mre = next(x for x in s4["supplies"] if x["item"] == "MRE" and x["on_hand"] == 100)
    assert mre["location_id"] is None  # unknown site: force-wide, not guessed
    assert client.post("/v1/cop/upload/S4/preview", files={"file": ("x.xlsx", data)}, headers=U("u_s6")).status_code == 403


def test_s6_and_s3_sheets_and_csv(client):
    data = xlsx({"Comms": [["CP", "System", "PACE", "OPSTAT", "Remarks"], ["FARP Eagle", "TACSAT — FARP Eagle", "Alternate", "UP", "antenna replaced"], ["Brigade TOC", "SIPRNET", "", "NMC", "switch failed"], ["Peason Ridge", "Range FM", "Primary", "Green", ""]]})
    pv = client.post("/v1/cop/upload/S6/preview", files={"file": ("comms.xlsx", data)}, headers=U("u_s6")).json()
    assert pv["mapping"]["OPSTAT"] == "status" and pv["mapping"]["PACE"] == "pace" and pv["mapping"]["CP"] == "site"
    res = client.post("/v1/cop/upload/S6/commit", json={"upload_id": pv["upload_id"], "sheet": "Comms", "mapping": pv["mapping"]}, headers=U("u_s6")).json()
    assert res["updated"] == 2 and res["created"] == 1
    s6 = client.get("/v1/cop/snapshot").json()["s6"]
    assert s6["pace"]["loc_farp"]["nets"]["alternate"] == "up"
    sipr = next(x for x in s6["systems"] if x["name"] == "SIPRNET" and x["location_id"] == "loc_bde")
    assert sipr["status"] == "down" and sipr["note"] == "switch failed"
    csv_text = "Activity,Type,Start,End,Location,Who,Notes\nTable VII Gunnery,event,2026-10-02 06:00,2026-10-04 22:00,Peason Ridge Range Complex,,crews A/1\nCorps conference,trip,2026-10-06,2026-10-08,Fort Liberty NC,MAJ Casey Whitfield,planning\nMystery event,event,2026-10-10,,Somewhere unknown,,\n"
    pv = client.post("/v1/cop/upload/S3/preview", files={"file": ("plan.csv", csv_text.encode())}, headers=U("u_s3")).json()
    assert pv["mapping"]["Activity"] == "name" and pv["mapping"]["Start"] == "start" and pv["mapping"]["Location"] == "place" and pv["mapping"]["Who"] == "who"
    res = client.post("/v1/cop/upload/S3/commit", json={"upload_id": pv["upload_id"], "sheet": pv["sheet"], "mapping": pv["mapping"]}, headers=U("u_s3")).json()
    assert res["created"] == 1 and res["skipped"] == 2, res  # the gunnery lands; the trip needs a directory name, the mystery place has no coordinates
    assert any(e["name"] == "Table VII Gunnery" for e in client.get("/v1/cop/snapshot").json()["events"])
    assert client.post("/v1/cop/upload/S3/commit", json={"upload_id": "up_nope", "sheet": "x", "mapping": {}}, headers=BC).status_code == 410
