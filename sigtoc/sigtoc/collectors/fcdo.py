"""UK FCDO foreign travel advice — free Atom feed of recent updates. Source reliability A. Country-scoped."""
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

from ..countries import to_iso
from .common import fetch, item, parse_iso, place_country_items, strip_html

FEED_URL = "https://www.gov.uk/foreign-travel-advice.atom"
NS = {"a": "http://www.w3.org/2005/Atom"}


def _severity(summary: str) -> str:
    s = summary.lower()
    if "advise against all travel" in s or "advises against all travel" in s: return "elevated"
    if "all but essential" in s: return "moderate"
    return "low"


def parse_fcdo(xml_text: str) -> List[Dict[str, Any]]:
    root = ET.fromstring(xml_text)
    out = []
    for e in root.findall("a:entry", NS):
        country = strip_html(e.findtext("a:title", "", NS))
        summary_el = e.find("a:summary", NS)
        summary = strip_html(ET.tostring(summary_el, encoding="unicode") if summary_el is not None else "")
        link = next((l.get("href") for l in e.findall("a:link", NS) if l.get("rel") == "alternate"), None)
        iso = to_iso(country)
        sev = _severity(summary)
        out.append(item(external_id=f"fcdo:{iso}", title=f"FCDO advice updated — {country}", summary=summary or f"Travel advice for {country} updated.",
                        lat=0.0, lon=0.0, radius_km=0.0 if sev == "low" else 100.0, severity=sev, event_type="advisory", source="fcdo",
                        observed_at=parse_iso(e.findtext("a:updated", "", NS)), url=link, country=iso, scope="country"))
    return out


async def collect_fcdo(points, countries: Dict[str, Any], max_km: float = 0.0) -> List[Dict[str, Any]]:
    r = await fetch(FEED_URL, name="FCDO")
    return place_country_items(parse_fcdo(r.text), countries)
