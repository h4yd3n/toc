"""GDACS parser and relevance filter, offline."""
from sigtoc.collectors.gdacs import filter_relevant, parse_gdacs_rss

RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:gdacs="http://www.gdacs.org" xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">
<channel><title>GDACS</title>
<item><title>Green earthquake alert (Magnitude 5.1M) in Japan</title><link>https://www.gdacs.org/report.aspx?eventid=1</link>
<description>&lt;p&gt;Depth 10km&lt;/p&gt;</description><pubDate>Tue, 02 Sep 2026 01:00:00 GMT</pubDate>
<gdacs:eventtype>EQ</gdacs:eventtype><gdacs:eventid>1</gdacs:eventid><gdacs:alertlevel>Green</gdacs:alertlevel>
<gdacs:severity>Magnitude 5.1M</gdacs:severity><gdacs:country>Japan</gdacs:country>
<geo:Point><geo:lat>35.9</geo:lat><geo:long>139.9</geo:long></geo:Point></item>
<item><title>Red tropical cyclone alert</title><link>https://www.gdacs.org/report.aspx?eventid=2</link>
<description>Cat 4</description><pubDate>Tue, 02 Sep 2026 00:00:00 GMT</pubDate>
<gdacs:eventtype>TC</gdacs:eventtype><gdacs:eventid>2</gdacs:eventid><gdacs:alertlevel>Red</gdacs:alertlevel>
<gdacs:country>Philippines</gdacs:country>
<geo:Point><geo:lat>14.6</geo:lat><geo:long>121.0</geo:long></geo:Point></item>
<item><title>Green flood far away</title><link>x</link><pubDate>Tue, 02 Sep 2026 00:00:00 GMT</pubDate>
<gdacs:eventtype>FL</gdacs:eventtype><gdacs:eventid>3</gdacs:eventid><gdacs:alertlevel>Green</gdacs:alertlevel>
<geo:Point><geo:lat>-33.9</geo:lat><geo:long>18.4</geo:long></geo:Point></item>
</channel></rss>"""

def test_parse_reads_nested_geo_and_maps_fields():
    items = parse_gdacs_rss(RSS)
    assert len(items) == 3
    eq = next(i for i in items if i["external_id"] == "gdacs:EQ:1")
    assert eq["lat"] == 35.9 and eq["lon"] == 139.9 and eq["severity"] == "low" and eq["radius_km"] == 100
    assert eq["title"].startswith("Earthquake — Japan") and "Magnitude 5.1M" in eq["summary"] and "Depth 10km" in eq["summary"]
    assert eq["event_type"] == "natural_hazard:EQ" and eq["source"] == "gdacs" and eq["observed_at"].year == 2026
    tc = next(i for i in items if i["external_id"] == "gdacs:TC:2")
    assert tc["severity"] == "elevated" and tc["radius_km"] == 300

def test_filter_keeps_red_anywhere_and_green_only_near_blue_force():
    items = parse_gdacs_rss(RSS)
    tokyo = [(35.6762, 139.6503)]
    kept = filter_relevant(items, tokyo, max_km=400)
    ids = {k["external_id"] for k in kept}
    assert ids == {"gdacs:EQ:1", "gdacs:TC:2"}  # Japan quake is near Tokyo; Red cyclone kept regardless; Cape Town flood dropped
    assert all(not k.startswith("_") for it in kept for k in it)
