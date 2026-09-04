"""Baseline for an unfamiliar place (§5.8): public holidays in the window from Nager.Date — free, keyless. Facts, not
threats: a holiday in the window changes what a venue, its transit, and its security posture look like."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from .collectors.common import fetch

API = "https://date.nager.at/api/v3/PublicHolidays/{year}/{iso}"


def holidays_in_window(data: List[Dict[str, Any]], window_from: Optional[datetime], window_to: Optional[datetime]) -> List[Dict[str, Any]]:
    out = []
    for h in data:
        try: d = datetime.strptime(h["date"], "%Y-%m-%d")
        except (KeyError, ValueError): continue
        if window_from and d.date() < window_from.date(): continue
        if window_to and d.date() > window_to.date(): continue
        out.append({"date": h["date"], "name": h.get("name"), "local_name": h.get("localName"), "national": bool(h.get("global", True)), "types": h.get("types") or []})
    return out


async def holidays(iso: str, window_from: Optional[datetime], window_to: Optional[datetime]) -> List[Dict[str, Any]]:
    years = sorted({(window_from or datetime.utcnow()).year, (window_to or window_from or datetime.utcnow()).year})
    data: List[Dict[str, Any]] = []
    for y in years:
        r = await fetch(API.format(year=y, iso=iso), name="Nager.Date")
        data += r.json()
    return holidays_in_window(data, window_from, window_to)
