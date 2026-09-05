"""§11.3 settings: keys entered from the wall, write-only, encrypted at rest; the environment wins; consumers see them."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"; os.environ["TOC_INTSUM_CLOCK"] = "off"; os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None); os.environ.pop("ACLED_API_KEY", None); os.environ.pop("ACLED_EMAIL", None); os.environ.pop("TOC_SECTIONS", None)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from coptoc.app import app
from shared import settings
from shared.settings import SettingRow
from sigtoc.collectors import acled

BC = {"X-TOC-Role": "battle_captain", "X-TOC-Actor": "bc"}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/v1/cop/seed")
        yield c


def test_only_the_battle_captain_reads_or_writes(client):
    assert client.get("/v1/cop/settings", headers={"X-TOC-Role": "analyst"}).status_code == 403
    assert client.put("/v1/cop/settings/ACLED_API_KEY", json={"value": "x"}, headers={"X-TOC-Role": "ea"}).status_code == 403
    assert client.put("/v1/cop/settings/NOT_A_THING", json={"value": "x"}, headers=BC).status_code == 404


def test_keys_are_write_only_and_unlock_a_source(client):
    assert acled.configured() is False  # (TOC_OFFLINE=1 in tests pins the catalog's LIVE chip off, so ask the collector)
    r = client.put("/v1/cop/settings/ACLED_API_KEY", json={"value": "abcdef123456"}, headers=BC)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["set_in"] == "stored" and d["value"] is None and d["hint"] == "…3456" and d["set_by"] == "bc"
    client.put("/v1/cop/settings/ACLED_EMAIL", json={"value": "ops@example.com"}, headers=BC)
    listing = {s["name"]: s for s in client.get("/v1/cop/settings", headers=BC).json()["settings"]}
    assert listing["ACLED_EMAIL"]["value"] == "ops@example.com" and listing["ACLED_API_KEY"]["value"] is None  # non-secrets show, secrets do not
    assert "abcdef123456" not in client.get("/v1/cop/settings", headers=BC).text
    assert acled.configured() is True  # the collector reads the store
    log = client.get("/v1/cop/log?limit=3").json()
    assert log[0]["type"] == "cop.settings.updated" and "abcdef" not in log[0]["summary"]
    assert client.delete("/v1/cop/settings/ACLED_API_KEY", headers=BC).json()["set_in"] is None
    assert acled.configured() is False


@pytest.mark.asyncio
async def test_values_are_encrypted_at_rest(client):
    client.put("/v1/cop/settings/CLSTR_API_KEY", json={"value": "plaintext-should-not-appear"}, headers=BC)
    from coptoc.routes import _sessions
    async with _sessions() as s:
        row = (await s.execute(select(SettingRow).where(SettingRow.name == "CLSTR_API_KEY"))).scalar_one()
    assert "plaintext" not in row.value_enc and row.value_enc.startswith("gAAAA")
    assert settings.get("CLSTR_API_KEY") == "plaintext-should-not-appear"
    client.delete("/v1/cop/settings/CLSTR_API_KEY", headers=BC)


def test_environment_wins_over_the_store(client, monkeypatch):
    client.put("/v1/cop/settings/TOC_MODEL", json={"value": "claude-sonnet-5"}, headers=BC)
    assert settings.get("TOC_MODEL") == "claude-sonnet-5" and settings.source_of("TOC_MODEL") == "stored"
    monkeypatch.setenv("TOC_MODEL", "claude-opus-5")
    assert settings.get("TOC_MODEL") == "claude-opus-5" and settings.source_of("TOC_MODEL") == "env"
    listing = {s["name"]: s for s in client.get("/v1/cop/settings", headers=BC).json()["settings"]}
    assert listing["TOC_MODEL"]["set_in"] == "env"
    client.delete("/v1/cop/settings/TOC_MODEL", headers=BC)


def test_sections_can_be_switched_from_the_wall(client):
    assert all(s["enabled"] for s in client.get("/v1/cop/snapshot").json()["sections"])
    client.put("/v1/cop/settings/TOC_SECTIONS", json={"value": "S1,S2,S3"}, headers=BC)
    cfg = {s["code"]: s for s in client.get("/v1/cop/snapshot").json()["sections"]}
    assert not cfg["S4"]["enabled"] and not cfg["S6"]["enabled"] and cfg["S1"]["enabled"]
    client.put("/v1/cop/settings/TOC_SECTION_TITLES", json={"value": "S4=SUPPLY"}, headers=BC)
    assert {s["code"]: s for s in client.get("/v1/cop/snapshot").json()["sections"]}["S4"]["title"] == "SUPPLY"
    client.delete("/v1/cop/settings/TOC_SECTIONS", headers=BC); client.delete("/v1/cop/settings/TOC_SECTION_TITLES", headers=BC)
    assert all(s["enabled"] for s in client.get("/v1/cop/snapshot").json()["sections"])
