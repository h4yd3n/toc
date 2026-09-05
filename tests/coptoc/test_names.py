"""§4 names and ranks: LAST, First M. · RANK on a military desk, First Last on a corporate one; grades are the constant."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None)

import io
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from coptoc.app import app
from coptoc.names import display, parse_rank, split_name

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed?dataset=cab")
        yield c


def test_rank_and_grade_parse_both_ways():
    assert parse_rank("SSG") == ("SSG", "E6") and parse_rank("E-6") == ("SSG", "E6") and parse_rank("e6") == ("SSG", "E6")
    assert parse_rank("CW3") == ("CW3", "W3") and parse_rank("O3") == ("CPT", "O3") and parse_rank("1SG") == ("1SG", "E8")
    assert parse_rank("CIV") == ("CIV", "CIV") and parse_rank("contractor") == ("CONTRACTOR", "CTR") and parse_rank("LCDR") == ("LCDR", "O4")
    assert parse_rank("Staff Sergeant") == ("STAFFSERGEANT", None) and parse_rank("") == (None, None)
    assert split_name("Avery B. Okafor") == ("Avery", "Okafor", "B") and split_name("Okafor, Avery B.") == ("Avery", "Okafor", "B") and split_name("Cher") == ("Cher", "Cher", None)
    assert display("military", "Jordan", "Reyes", "A", "SSG", "x") == "REYES, Jordan A. · SSG" and display("corporate", "Jordan", "Reyes", "A", None, "x") == "Jordan Reyes"


def test_military_display_and_sort(client):
    snap = client.get("/v1/cop/snapshot").json()
    people = snap["people"]
    cdr = next(p for p in people if p["team_id"] == "t_cab_hhc" and p["role"] == "Commander")
    assert cdr["rank"] == "COL" and cdr["grade"] == "O6" and cdr["name"].endswith("· COL") and "," in cdr["name"] and cdr["short_name"].startswith("COL ")
    bn = next(p for p in people if p["team_id"] == "t_1atk_hhc" and p["role"] == "Commander")
    assert bn["grade"] == "O5"
    pilots = [p for p in people if p["role"] == "Pilot in Command"]
    assert pilots and all(p["grade"] in ("W3", "W4") for p in pilots)
    names = [p["sort_name"] for p in people]
    assert names == sorted(names)  # the roster sorts by last name
    assert all(p["name"].split(",")[0] == p["name"].split(",")[0].upper() for p in people[:50])


def test_corporate_display_has_no_rank(client):
    client.put("/v1/cop/profile", json={"profile": "corporate"}, headers=BC)
    people = client.get("/v1/cop/snapshot").json()["people"]
    ceo = next(p for p in people if p["id"] == "p_ceo")
    assert ceo["name"] == "Alex Ventura" and ceo["rank"] is None and ceo["last_name"] == "Ventura" and ceo["short_name"] == "Alex"
    client.put("/v1/cop/profile", json={"profile": "military"}, headers=BC)


def test_upload_with_grade_only_gets_a_rank(client):
    wb = Workbook(); ws = wb.active; ws.title = "R"
    ws.append(["Last Name", "First Name", "MI", "Grade", "Unit", "Duty"]); ws.append(["Park", "Jin", "H", "E-7", "HHC/1 ATK", "Operations NCO"]); ws.append(["Doe", "Sam", "", "CTR", "HHC/CAB", "Field service rep"])
    buf = io.BytesIO(); wb.save(buf)
    pv = client.post("/v1/cop/upload/S1/preview", files={"file": ("r.xlsx", buf.getvalue())}, headers=BC).json()
    assert pv["mapping"]["Grade"] == "grade" and pv["mapping"]["MI"] == "middle_initial"
    res = client.post("/v1/cop/upload/S1/commit", json={"upload_id": pv["upload_id"], "sheet": "R", "mapping": pv["mapping"]}, headers=BC).json()
    assert res["created"] == 2, res
    people = client.get("/v1/cop/snapshot").json()["people"]
    jin = next(p for p in people if p["last_name"] == "Park" and p["first_name"] == "Jin")
    assert jin["rank"] == "SFC" and jin["grade"] == "E7" and jin["name"] == "PARK, Jin H. · SFC"
    sam = next(p for p in people if p["last_name"] == "Doe")
    assert sam["grade"] == "CTR" and sam["name"] == "DOE, Sam · CTR"
