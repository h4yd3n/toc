"""Tests for tactical weather (METOC) derivation and integration into COP snapshot."""
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["TOC_OFFLINE"] = "1"
os.environ["TOC_INTSUM_CLOCK"] = "off"
os.environ["TOC_ESCALATION_CLOCK"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from coptoc.app import app
from coptoc.weather import derive_weather

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        r = c.post("/v1/cop/seed?dataset=cab")
        assert r.status_code == 200
        yield c

def test_derive_weather_unit_fort_campbell():
    # Fort Campbell coordinates ~ 36.67, -87.49
    wx = derive_weather(36.67, -87.49, radius_km=30.0, threats=[], profile="military")
    assert wx["station_id"] == "KCKV"
    assert "Clarksville" in wx["station_name"] or "Campbell" in wx["station_name"]
    assert wx["flight_category"] == "VMC"
    assert wx["temp_f"] > -40
    assert "aviationweather.gov" in wx["awc_url"]
    assert "weather.gov" in wx["external_url"]

def test_derive_weather_reacts_to_weather_threats():
    # Elevated threat -> IMC and flight restrictions
    critical_threats = [
        {
            "id": "thr_severe_storm",
            "title": "Severe Thunderstorm Warning",
            "category": "weather",
            "severity": "elevated",
            "lat": 36.65,
            "lon": -87.45,
            "summary": "T-storms with 48kt gusts and low ceilings approaching airfield",
        }
    ]
    wx_critical = derive_weather(36.67, -87.49, radius_km=30.0, threats=critical_threats, profile="military")
    assert len(wx_critical["active_advisories"]) == 1
    assert wx_critical["flight_category"] == "IMC"
    assert wx_critical["wind_gust_kt"] >= 45
    assert "HOLD / GROUNDED" in wx_critical["operational_impact"]

    # Moderate threat -> MVFR and caution
    moderate_threats = [
        {
            "id": "thr_wind_adv",
            "title": "Wind Advisory",
            "category": "weather",
            "severity": "moderate",
            "lat": 36.65,
            "lon": -87.45,
            "summary": "Sustained winds 18kt gusts 28kt",
        }
    ]
    wx_mod = derive_weather(36.67, -87.49, radius_km=30.0, threats=moderate_threats, profile="military")
    assert len(wx_mod["active_advisories"]) == 1
    assert wx_mod["flight_category"] == "MVFR"
    assert "CAUTION" in wx_mod["operational_impact"]

def test_snapshot_carries_tactical_weather(client):
    r = client.get("/v1/cop/snapshot")
    assert r.status_code == 200
    snap = r.json()
    assert "weather" in snap
    wx = snap["weather"]
    assert wx is not None
    assert wx["station_id"] == "KCKV"
    assert "flight_category" in wx
    assert "temp_f" in wx
    assert "operational_impact" in wx
    assert "awc_url" in wx and "external_url" in wx
