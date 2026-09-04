"""Every collector returns the same item shape (the wall's threat row, plus `country` and `scope`) and raises RuntimeError
on transport failure — a broken source must never look like a quiet one."""
import html
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import httpx

UA = "TOC-Sigtoc/0.2 (open-source COP; github.com/h4yd3n/toc)"


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def strip_html(s: Optional[str]) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).strip()


def squeeze(s: str, n: int = 400) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def parse_iso(s: Optional[str]) -> datetime:
    if not s: return datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return datetime.now(timezone.utc).replace(tzinfo=None)


def near(item: Dict[str, Any], points: Sequence[Tuple[float, float]], max_km: float) -> bool:
    return any(haversine_km(item["lat"], item["lon"], la, lo) <= max_km + item.get("radius_km", 0) for la, lo in points)


def item(*, external_id: str, title: str, summary: str, lat: float, lon: float, radius_km: float, severity: str, event_type: str, source: str,
         observed_at: datetime, url: Optional[str] = None, country: Optional[str] = None, scope: str = "point") -> Dict[str, Any]:
    return {"external_id": external_id, "title": title[:140], "summary": squeeze(summary), "lat": lat, "lon": lon, "radius_km": float(radius_km), "severity": severity,
            "event_type": event_type, "source": source, "url": url, "observed_at": observed_at, "country": country, "scope": scope}


def place_country_items(items: Iterable[Dict[str, Any]], targets: Dict[str, Tuple[float, float]]) -> List[Dict[str, Any]]:
    """Country-scoped reporting gets the position of our first requirement in that country, so the wall can draw it where
    it matters. Items for countries we have nothing in are dropped."""
    out = []
    for it in items:
        pos = targets.get(it.get("country") or "")
        if not pos: continue
        it = dict(it); it["lat"], it["lon"] = pos
        out.append(it)
    return out


async def fetch(url: str, *, timeout: float = 25.0, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None, name: str = "source") -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent": UA, **(headers or {})}) as client:
            r = await client.get(url, params=params)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"{name} unreachable: {type(e).__name__}: {e}") from e
    if r.status_code != 200:
        raise RuntimeError(f"{name} returned HTTP {r.status_code}")
    return r
