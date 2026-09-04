"""§5.8 collectors: each parser against a saved sample of the real feed, the relevance filters, country handling, and the
registry's honesty about what is live. No network."""
import json, os
from datetime import datetime
from pathlib import Path
os.environ["TOC_OFFLINE"] = "1"
os.environ.pop("TOC_SOURCES_CONFIGURED", None)

from sigtoc.collectors import usgs, nws, who_don, state_dept, fcdo, acled, clstr
from sigtoc.collectors.common import place_country_items
from sigtoc.collectors.registry import COLLECTORS, configured
from sigtoc.countries import country_from_place, to_iso
from sigtoc.baseline import holidays_in_window

FX = Path(__file__).parent / "fixtures"
SF, LISBON = (37.7749, -122.4194), (38.7223, -9.1393)


def test_usgs_parses_and_keeps_big_or_near():
    items = usgs.parse_usgs(json.loads((FX / "usgs.json").read_text()))
    assert len(items) == 4 and all(i["source"] == "usgs" and i["event_type"] == "earthquake" for i in items)
    m5 = next(i for i in items if "South Sandwich" in i["title"])
    assert m5["severity"] == "moderate" and m5["radius_km"] == 80 and m5["external_id"].startswith("usgs:")
    far = usgs.filter_relevant(items, [SF])
    assert far == []  # nothing M6+ in the sample and nothing near SF
    texas = next(i for i in items if "Texas" in i["title"])
    assert usgs.filter_relevant(items, [(texas["lat"], texas["lon"])])[0]["title"] == texas["title"]


def test_nws_uses_polygon_centroids_and_skips_zone_only_alerts():
    items = nws.parse_nws(json.loads((FX / "nws.json").read_text()))
    assert len(items) == 2  # the zone-only Red Flag Warning has no polygon and is skipped, honestly
    a = items[0]
    assert a["country"] == "US" and a["event_type"] == "natural_hazard:NWS" and a["severity"] == "elevated" and a["radius_km"] >= 15
    assert nws.filter_relevant(items, [SF]) == [] and nws.filter_relevant(items, [(a["lat"], a["lon"])])


def test_who_state_fcdo_are_country_scoped_and_placed_at_our_site():
    who = who_don.parse_who(json.loads((FX / "who.json").read_text()))
    assert who and who[0]["scope"] == "country" and who[0]["country"] == "CD" and who[0]["event_type"] == "health" and who[0]["url"].endswith("DON616")
    st = state_dept.parse_state_dept((FX / "state.xml").read_text())
    iraq = next(i for i in st if i["country"] == "IQ")
    assert iraq["severity"] == "elevated" and "Level 4" in iraq["title"] and iraq["external_id"] == "state_dept:IQ"
    qa = next(i for i in st if i["country"] == "QA"); assert qa["severity"] == "moderate"
    fc = fcdo.parse_fcdo((FX / "fcdo.atom").read_text())
    assert {i["country"] for i in fc} == {"MX", "CO", "UG"} and all(i["event_type"] == "advisory" for i in fc)
    # placement: only countries we have a requirement in survive, at that requirement's point
    placed = place_country_items(st + fc + who, {"IQ": (33.3, 44.4), "MX": (19.4, -99.1)})
    assert {p["country"] for p in placed} == {"IQ", "MX"} and next(p for p in placed if p["country"] == "IQ")["lat"] == 33.3


def test_keyed_sources_parse_documented_shapes_and_are_not_live_without_keys(monkeypatch):
    monkeypatch.delenv("TOC_SOURCES_CONFIGURED", raising=False); monkeypatch.setenv("TOC_OFFLINE", "1")
    sample = {"data": [{"event_id_cnty": "PRT123", "event_date": "2026-09-01", "event_type": "Protests", "sub_event_type": "Peaceful protest", "country": "Portugal", "iso3": "PRT",
                        "admin1": "Lisboa", "location": "Lisbon", "latitude": "38.7223", "longitude": "-9.1393", "fatalities": "0", "notes": "Transport workers marched.", "source": "Lusa"}]}
    a = acled.parse_acled(sample)[0]
    assert a["event_type"] == "civil_unrest" and a["severity"] == "low" and a["external_id"] == "acled:PRT123"
    c = clstr.parse_clstr({"data": [{"id": "8f2b", "title": "Red Sea shipping attacks", "summary_preview": "Attacks…", "cluster_count": 34, "source_count": 212,
                                      "last_updated": "2026-08-14T11:38:00.000Z", "status": "ACTIVE", "categories": ["international", "business"], "countries": ["YE", "EG"], "significance_score": 9}]})
    assert len(c) == 2 and c[0]["country"] == "YE" and c[0]["severity"] == "elevated" and c[0]["event_type"] == "infrastructure" and "(theirs)" in c[0]["summary"]
    assert configured("acled") is False and configured("clstr") is False
    assert configured("gdacs") is False and configured("usgs") is False  # TOC_OFFLINE=1 in this test module: nothing is live
    assert set(COLLECTORS) == {"gdacs", "usgs", "nws", "who_don", "state_dept", "fcdo", "acled", "clstr"}


def test_countries_and_holiday_baseline():
    assert to_iso("Saudi Arabia") == "SA" and to_iso("UK") == "GB" and to_iso("us") == "US" and to_iso("Narnia") == "narnia"
    assert country_from_place("Lisbon, Portugal") == "PT" and country_from_place("Riyadh, Saudi Arabia") == "SA" and country_from_place("London Office") is None
    data = json.loads((FX / "nager_pt.json").read_text())
    inwin = holidays_in_window(data, datetime(2026, 4, 1), datetime(2026, 4, 30))
    assert [h["date"] for h in inwin] == ["2026-04-03", "2026-04-05", "2026-04-25"] and inwin[0]["name"] == "Good Friday"
    assert holidays_in_window(data, datetime(2026, 10, 14), datetime(2026, 10, 17)) == []
