"""USGS earthquakes — free, keyless GeoJSON. Source reliability A."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Tuple

from .common import fetch, item, near

FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"


def _sev(mag: float) -> str:
    return "low" if mag < 4.5 else "moderate" if mag < 5.5 else "elevated" if mag < 6.5 else "critical"

def _radius(mag: float) -> float:
    return 30 if mag < 4.5 else 80 if mag < 5.5 else 150 if mag < 6.5 else 300


def parse_usgs(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for f in data.get("features", []):
        p, g = f.get("properties", {}), f.get("geometry") or {}
        coords = g.get("coordinates") or []
        if len(coords) < 2 or p.get("mag") is None: continue
        mag = float(p["mag"])
        observed = datetime.fromtimestamp(p["time"] / 1000, tz=timezone.utc).replace(tzinfo=None) if p.get("time") else datetime.now(timezone.utc).replace(tzinfo=None)
        out.append({**item(external_id=f"usgs:{f.get('id')}", title=f"M{mag:.1f} earthquake — {p.get('place') or 'unknown location'}",
                          summary=f"Magnitude {mag:.1f}, depth {coords[2]:.0f} km. {p.get('place') or ''}. Tsunami flag: {p.get('tsunami', 0)}. Felt reports: {p.get('felt') or 0}.",
                          lat=float(coords[1]), lon=float(coords[0]), radius_km=_radius(mag), severity=_sev(mag), event_type="earthquake", source="usgs",
                          observed_at=observed, url=p.get("url")), "_mag": mag})
    return out


def filter_relevant(items: List[Dict[str, Any]], points: Sequence[Tuple[float, float]], max_km: float = 400.0) -> List[Dict[str, Any]]:
    """Keep M6+ anywhere, plus anything within max_km (+ its radius) of a blue-force point."""
    return [{k: v for k, v in it.items() if not k.startswith("_")} for it in items if it["_mag"] >= 6.0 or near(it, points, max_km)]


async def collect_usgs(points: Sequence[Tuple[float, float]], countries=None, max_km: float = 400.0) -> List[Dict[str, Any]]:
    r = await fetch(FEED_URL, name="USGS")
    return filter_relevant(parse_usgs(r.json()), points, max_km)
