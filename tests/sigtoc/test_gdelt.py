"""GDELT DOC 2.0: press reporting, country-scoped, graded C — and honest about being articles rather than events."""
from sigtoc.collectors import gdelt

SAMPLE = {"articles": [
    {"url": "https://example.pt/noticias/manifestacao", "url_mobile": "", "title": "Protest closes Avenida da Liberdade for two hours",
     "seendate": "20260917T061500Z", "socialimage": "", "domain": "example.pt", "language": "Portuguese", "sourcecountry": "Portugal"},
    {"url": "https://example.sa/news/curfew", "title": "Curfew announced in the eastern province", "seendate": "20260917T054500Z",
     "domain": "example.sa", "language": "Arabic", "sourcecountry": "Saudi Arabia"},
    {"url": "https://example.xx/none", "title": "No country given", "seendate": "20260917T050000Z", "domain": "example.xx", "sourcecountry": ""},
    {"title": "No url either", "seendate": "20260917T050000Z", "sourcecountry": "Portugal"},
]}


def test_articles_become_country_scoped_items_and_nothing_else():
    items = gdelt.parse_gdelt(SAMPLE)
    assert [i["country"] for i in items] == ["PT", "SA"], "an article with no country or no url is dropped, not guessed"
    first = items[0]
    assert first["scope"] == "country" and first["lat"] == 0.0 and first["lon"] == 0.0, "the API gives no position; we invent none"
    assert first["source"] == "gdelt" and first["severity"] == "low" and first["event_type"] == "civil_unrest"
    assert first["observed_at"].isoformat() == "2026-09-17T06:15:00"
    assert "not an observed event" in first["summary"] and "example.pt" in first["summary"]
    assert first["external_id"] == "gdelt:https://example.pt/noticias/manifestacao"


def test_country_items_sit_on_our_own_ground_and_others_are_dropped():
    from sigtoc.collectors.common import place_country_items
    placed = place_country_items(gdelt.parse_gdelt(SAMPLE), {"PT": (38.7223, -9.1393)})
    assert len(placed) == 1 and placed[0]["country"] == "PT"
    assert (placed[0]["lat"], placed[0]["lon"]) == (38.7223, -9.1393), "placed where we have people, never where the press is"


def test_the_catalog_calls_it_built_keyless_and_grade_c():
    from sigtoc.requirements import CATALOG
    row = next(c for c in CATALOG if c["id"] == "gdelt")
    assert row["built"] is True and row["reliability"] == "C" and "keyless" in row["access"]


def test_offline_means_not_configured(monkeypatch):
    from sigtoc.collectors.registry import COLLECTORS, configured
    assert "gdelt" in COLLECTORS
    monkeypatch.delenv("TOC_SOURCES_CONFIGURED", raising=False)
    monkeypatch.setenv("TOC_OFFLINE", "1")
    assert configured("gdelt") is False
    monkeypatch.setenv("TOC_OFFLINE", "")
    assert configured("gdelt") is True   # keyless: nothing to configure but a working network
