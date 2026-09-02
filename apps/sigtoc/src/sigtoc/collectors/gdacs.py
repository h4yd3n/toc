"""GDACS — Global Disaster Alert and Coordination System (UN OCHA / EC JRC). Free, keyless RSS.
Source reliability: A. Information credibility: 1 (the feed *is* the confirmation channel)."""
import html
import math
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Sequence, Tuple
import xml.etree.ElementTree as ET

import httpx

RSS_URL = "https://www.gdacs.org/xml/rss.xml"
NS = {"gdacs": "http://www.gdacs.org", "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#"}
ALERT_TO_SEVERITY = {"green": "low", "orange": "moderate", "red": "elevated"}
TYPE_NAME = {"EQ": "Earthquake", "TC": "Tropical cyclone", "FL": "Flood", "VO": "Volcano", "DR": "Drought", "WF": "Wildfire", "TS": "Tsunami"}
# Rough area of effect per hazard type, km. Coarse on purpose — GDACS episodes carry no polygon in the RSS.
TYPE_RADIUS_KM = {"EQ": 100, "TC": 300, "FL": 150, "VO": 50, "DR": 250, "WF": 60, "TS": 200}


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _strip_html(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).strip()


def parse_gdacs_rss(xml_text: str) -> List[Dict]:
    root = ET.fromstring(xml_text)
    out = []
    for item in root.findall(".//item"):
        etype = (item.findtext(".//gdacs:eventtype", "", NS) or "").upper()
        eid = item.findtext(".//gdacs:eventid", "", NS)
        alert = (item.findtext(".//gdacs:alertlevel", "", NS) or "green").lower()
        # GDACS nests coordinates inside <geo:Point>; search descendants, not direct children.
        lat, lon = item.findtext(".//geo:lat", "", NS), item.findtext(".//geo:long", "", NS)
        if not (etype and eid and lat and lon):
            continue
        try:
            latf, lonf = float(lat), float(lon)
        except ValueError:
            continue
        pub = item.findtext("pubDate", "")
        try:
            observed = parsedate_to_datetime(pub).astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            observed = datetime.now(timezone.utc).replace(tzinfo=None)
        title = _strip_html(item.findtext("title", ""))
        desc = _strip_html(item.findtext("description", ""))
        sev_text = item.findtext(".//gdacs:severity", "", NS)
        country = item.findtext(".//gdacs:country", "", NS)
        out.append({
            "external_id": f"gdacs:{etype}:{eid}",
            "title": f"{TYPE_NAME.get(etype, etype)} — {country or title}"[:140],
            "summary": (desc or title) + (f" Severity: {sev_text}." if sev_text else "") + f" GDACS alert level: {alert.upper()}.",
            "lat": latf, "lon": lonf,
            "radius_km": float(TYPE_RADIUS_KM.get(etype, 100)),
            "severity": ALERT_TO_SEVERITY.get(alert, "low"),
            "event_type": f"natural_hazard:{etype}",
            "source": "gdacs",
            "url": item.findtext("link", "") or None,
            "observed_at": observed,
            "_alert": alert,
        })
    return out


def filter_relevant(items: List[Dict], points: Sequence[Tuple[float, float]], max_km: float = 400.0) -> List[Dict]:
    """Keep anything Orange/Red anywhere, plus anything within max_km of a blue-force point."""
    keep = []
    for it in items:
        near = any(haversine_km(it["lat"], it["lon"], la, lo) <= max_km for la, lo in points)
        if it["_alert"] in ("orange", "red") or near:
            keep.append({k: v for k, v in it.items() if not k.startswith("_")})
    return keep


async def collect_gdacs(points: Sequence[Tuple[float, float]], max_km: float = 400.0, timeout: float = 25.0) -> List[Dict]:
    """Fetch, parse, filter. Raises RuntimeError on transport failure — a broken source must not look like a quiet one."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent": "TOC-Sigtoc/0.1"}) as client:
            r = await client.get(RSS_URL)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"GDACS unreachable: {type(e).__name__}: {e}") from e
    if r.status_code != 200:
        raise RuntimeError(f"GDACS returned HTTP {r.status_code}")
    return filter_relevant(parse_gdacs_rss(r.text), points, max_km)
