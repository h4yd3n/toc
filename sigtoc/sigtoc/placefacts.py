"""Baseline facts about an unfamiliar place from Wikidata — free, keyless SPARQL. The nearest settlement with a
population inside 20 km: name, population, country, time zone. Facts, not threats; they sit on the Area Assessment's
baseline row next to the holidays."""
from typing import Any, Dict, List, Optional

from .collectors.common import fetch

ENDPOINT = "https://query.wikidata.org/sparql"
QUERY = """SELECT ?place ?placeLabel ?pop ?tzLabel ?countryLabel WHERE {
  SERVICE wikibase:around { ?place wdt:P625 ?loc . bd:serviceParam wikibase:center "Point(%f %f)"^^geo:wktLiteral ; wikibase:radius "20" . }
  ?place wdt:P1082 ?pop . ?place wdt:P31/wdt:P279* wd:Q486972 .
  OPTIONAL { ?place wdt:P421 ?tz } OPTIONAL { ?place wdt:P17 ?country }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" } } ORDER BY DESC(?pop) LIMIT 3"""


def parse_place(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rows = data.get("results", {}).get("bindings", [])
    if not rows: return None
    b = rows[0]
    val = lambda k: b.get(k, {}).get("value")
    pop = val("pop")
    return {"name": val("placeLabel"), "wikidata": (val("place") or "").rsplit("/", 1)[-1], "population": int(float(pop)) if pop else None, "country": val("countryLabel"), "timezone": val("tzLabel")}


async def place_facts(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    r = await fetch(ENDPOINT, params={"query": QUERY % (lon, lat)}, headers={"Accept": "application/sparql-results+json"}, name="Wikidata", timeout=40)
    return parse_place(r.json())
