"""ACLED — Armed Conflict Location & Event Data. Free key + registered email. Source reliability B. Point events.
Parser follows the documented `acled/read` response; not exercised live here without a key."""
import os

from shared import settings
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Sequence, Tuple

from .common import fetch, item, near

API_URL = "https://api.acleddata.com/acled/read"
KIND = {"Protests": "civil_unrest", "Riots": "civil_unrest", "Battles": "conflict", "Explosions/Remote violence": "conflict",
        "Violence against civilians": "crime", "Strategic developments": "civil_unrest"}


def configured() -> bool:
    return bool(settings.get("ACLED_API_KEY") and settings.get("ACLED_EMAIL"))


def _sev(fatalities: int, etype: str) -> str:
    if fatalities >= 20: return "critical"
    if fatalities >= 5: return "elevated"
    if fatalities >= 1 or etype in ("Battles", "Explosions/Remote violence"): return "moderate"
    return "low"


def parse_acled(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for e in data.get("data", []):
        try:
            lat, lon = float(e["latitude"]), float(e["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        fat = int(e.get("fatalities") or 0); et = e.get("event_type") or ""
        try: observed = datetime.strptime(e.get("event_date", ""), "%Y-%m-%d")
        except ValueError: observed = datetime.now(timezone.utc).replace(tzinfo=None)
        out.append(item(external_id=f"acled:{e.get('event_id_cnty')}", title=f"{et}: {e.get('sub_event_type') or ''} — {e.get('location') or e.get('admin1') or e.get('country')}",
                        summary=(e.get("notes") or "") + f" Fatalities: {fat}. Source: {e.get('source') or 'ACLED'}.", lat=lat, lon=lon, radius_km=25.0, severity=_sev(fat, et),
                        event_type=KIND.get(et, "civil_unrest"), source="acled", observed_at=observed, url="https://acleddata.com", country=e.get("iso3") or None))
    return out


async def collect_acled(points: Sequence[Tuple[float, float]], countries: Dict[str, Any], max_km: float = 100.0, days: int = 30) -> List[Dict[str, Any]]:
    if not configured(): raise RuntimeError("ACLED needs ACLED_API_KEY and ACLED_EMAIL")
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    r = await fetch(API_URL, params={"key": settings.get("ACLED_API_KEY"), "email": settings.get("ACLED_EMAIL"), "event_date": since, "event_date_where": ">", "limit": 2000}, name="ACLED", timeout=60)
    return [it for it in parse_acled(r.json()) if near(it, points, max_km)]
