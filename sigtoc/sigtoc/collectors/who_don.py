"""WHO Disease Outbreak News — free JSON (the old RSS is gone). Source reliability A. Country-scoped."""
import re
from typing import Any, Dict, List

from ..countries import to_iso
from .common import fetch, item, parse_iso, strip_html

FEED_URL = "https://www.who.int/api/news/diseaseoutbreaknews"
ITEM_URL = "https://www.who.int/emergencies/disease-outbreak-news/item/"


def parse_who(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for v in data.get("value", []):
        title = v.get("Title") or ""
        m = re.split(r"\s[–-]\s", title)
        country = to_iso(m[-1]) if len(m) > 1 else None
        out.append(item(external_id=f"who_don:{v.get('DonId') or v.get('Id')}", title=title, summary=strip_html(v.get("Summary") or v.get("Overview") or title),
                        lat=0.0, lon=0.0, radius_km=0.0, severity="moderate", event_type="health", source="who_don", observed_at=parse_iso(v.get("PublicationDateAndTime")),
                        url=ITEM_URL + (v.get("UrlName") or ""), country=country, scope="country"))
    return out


async def collect_who(points, countries: Dict[str, Any], max_km: float = 0.0) -> List[Dict[str, Any]]:
    from .common import place_country_items
    r = await fetch(FEED_URL, params={"$top": 40, "$orderby": "PublicationDateAndTime desc"}, name="WHO DON")
    return place_country_items(parse_who(r.json()), countries)
