"""NWS / NOAA active alerts (US) — free, keyless GeoJSON. Source reliability A. Alerts carry a polygon or only zone
references; zone-only alerts are skipped (resolving zones is one more call per alert — [NEXT])."""
from typing import Any, Dict, List, Sequence, Tuple

from .common import fetch, haversine_km, item, near, parse_iso

FEED_URL = "https://api.weather.gov/alerts/active"
SEVERITY = {"Extreme": "critical", "Severe": "elevated", "Moderate": "moderate", "Minor": "low", "Unknown": "low"}


def _centroid_and_radius(geom: Dict[str, Any]):
    rings = geom.get("coordinates") or []
    if geom.get("type") == "MultiPolygon": rings = [r for poly in rings for r in poly[:1]]
    pts = [tuple(p) for ring in rings[:1] for p in ring] if rings else []
    if not pts: return None
    lon = sum(p[0] for p in pts) / len(pts); lat = sum(p[1] for p in pts) / len(pts)
    radius = max(haversine_km(lat, lon, p[1], p[0]) for p in pts)
    return lat, lon, max(radius, 15.0)


def parse_nws(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for f in data.get("features", []):
        p = f.get("properties", {})
        cr = _centroid_and_radius(f.get("geometry") or {}) if f.get("geometry") else None
        if not cr: continue
        lat, lon, radius = cr
        out.append(item(external_id=f"nws:{p.get('id')}", title=f"{p.get('event', 'Weather alert')} — {(p.get('areaDesc') or '')[:80]}",
                        summary=(p.get("headline") or "") + " " + (p.get("description") or "")[:300] + f" Certainty: {p.get('certainty')}. Urgency: {p.get('urgency')}. Until {p.get('ends') or p.get('expires')}.",
                        lat=lat, lon=lon, radius_km=radius, severity=SEVERITY.get(p.get("severity") or "Unknown", "low"), event_type="natural_hazard:NWS", source="nws",
                        observed_at=parse_iso(p.get("sent")), url=f.get("id"), country="US"))
    return out


def filter_relevant(items: List[Dict[str, Any]], points: Sequence[Tuple[float, float]], max_km: float = 150.0) -> List[Dict[str, Any]]:
    return [it for it in items if near(it, points, max_km)]


async def collect_nws(points: Sequence[Tuple[float, float]], countries=None, max_km: float = 150.0) -> List[Dict[str, Any]]:
    r = await fetch(FEED_URL, params={"status": "actual", "message_type": "alert", "severity": "Severe,Extreme,Moderate"}, headers={"Accept": "application/geo+json"}, name="NWS")
    return filter_relevant(parse_nws(r.json()), points, max_km)
