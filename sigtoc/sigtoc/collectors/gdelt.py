"""GDELT DOC 2.0 — worldwide news monitoring, free and keyless. Source reliability C. Country-scoped.

What this source is and is not, plainly. GDELT's GEO 2.0 API, which returned coordinates, is gone; the DOC 2.0 API
returns *articles* — a headline, a domain, a language, a publication time and the country the article's source is
registered in. So an item from here is **not an observed event**. It is press reporting, placed at our own ground in
that country the way every other country-scoped source is (§5.3), graded C, and never given a position it does not
have. Two articles about the same protest are two articles, and the analyst is the one who decides whether either
describes something real — which is exactly what reliability C means.

The API is rate-limited and unannounced; a failure raises like any other collector, because a broken source must never
look like a quiet one.
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from ..countries import to_iso
from .common import fetch, item, parse_iso, squeeze

FEED_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
# The query GDELT is asked. Unrest and crowds are what this source is in the catalog for (§5.8); anything else here
# would be a claim about coverage the source does not support.
QUERY = '(protest OR demonstration OR riot OR unrest OR strike OR curfew OR "state of emergency")'
MAX_RECORDS = 50


def _country_of(article: Dict[str, Any]) -> Optional[str]:
    """GDELT names the source country of the outlet, not of the event. It is the only place claim the API makes, and
    we carry it as exactly that."""
    for key in ("sourcecountry", "sourceCountry"):
        if article.get(key):
            return to_iso(str(article[key]))
    return None


def parse_gdelt(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for a in data.get("articles", []) or []:
        url = a.get("url") or ""
        country = _country_of(a)
        if not country or not url:
            continue
        domain = a.get("domain") or urlparse(url).netloc
        title = squeeze(a.get("title") or domain, 140)
        out.append(item(external_id=f"gdelt:{url}", title=title,
                        summary=f"Press reporting via {domain}"
                                + (f" in {a.get('language')}" if a.get("language") else "")
                                + ". GDELT returns the article, not an observed event: unverified, position is our own ground in this country.",
                        lat=0.0, lon=0.0, radius_km=0.0, severity="low", event_type="civil_unrest", source="gdelt",
                        observed_at=parse_iso(_seen(a)), url=url, country=country, scope="country"))
    return out


def _seen(a: Dict[str, Any]) -> Optional[str]:
    """GDELT stamps `seendate` as 20260917T061500Z; anything else it sends is passed through to the ISO parser."""
    raw = a.get("seendate") or a.get("seenDate") or ""
    if len(raw) == 16 and raw[8] == "T":
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}T{raw[9:11]}:{raw[11:13]}:{raw[13:15]}Z"
    return raw or None


async def collect_gdelt(points: Sequence[Tuple[float, float]], countries: Dict[str, Tuple[float, float]], max_km: float = 0.0) -> List[Dict[str, Any]]:
    from .common import place_country_items
    if not countries:
        return []
    r = await fetch(FEED_URL, params={"query": QUERY, "mode": "ArtList", "format": "json", "maxrecords": MAX_RECORDS, "sort": "datedesc"}, name="GDELT")
    return place_country_items(parse_gdelt(r.json()), countries)
