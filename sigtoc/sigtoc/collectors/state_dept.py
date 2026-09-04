"""US State Department travel advisories — free RSS (the JSON endpoint is dead). Source reliability A. Country-scoped."""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List

from ..countries import to_iso
from .common import item, strip_html, fetch, place_country_items

FEED_URL = "https://travel.state.gov/_res/rss/TAsTWs.xml"
LEVEL_SEVERITY = {1: "low", 2: "low", 3: "moderate", 4: "elevated"}


def parse_state_dept(xml_text: str) -> List[Dict[str, Any]]:
    root = ET.fromstring(xml_text)
    out = []
    for it in root.findall(".//item"):
        title = strip_html(it.findtext("title", ""))
        m = re.match(r"(.+?)\s*-\s*Level\s*(\d)\s*:\s*(.+)", title)
        if not m: continue
        country, level, label = m.group(1).strip(), int(m.group(2)), m.group(3).strip()
        pub = it.findtext("pubDate", "") or ""
        try:
            observed = parsedate_to_datetime(pub).astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            try: observed = datetime.strptime(pub.strip(), "%a, %d %b %Y")
            except Exception: observed = datetime.now(timezone.utc).replace(tzinfo=None)
        iso = to_iso(country)
        out.append(item(external_id=f"state_dept:{iso}", title=f"{country} — Level {level}: {label}", summary=strip_html(it.findtext("description", "")),
                        lat=0.0, lon=0.0, radius_km=0.0 if level <= 2 else 100.0, severity=LEVEL_SEVERITY.get(level, "low"), event_type="advisory", source="state_dept",
                        observed_at=observed, url=it.findtext("link", "") or None, country=iso, scope="country"))
    return out


async def collect_state_dept(points, countries: Dict[str, Any], max_km: float = 0.0) -> List[Dict[str, Any]]:
    r = await fetch(FEED_URL, name="State Dept")
    return place_country_items(parse_state_dept(r.text), countries)
