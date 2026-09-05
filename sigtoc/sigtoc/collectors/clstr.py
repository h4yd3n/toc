"""CLSTR news situations — free key, 100 req/day, 7-day history on the free tier. Source reliability F until it earns a
grade (PRD §5.8); its significance score is theirs, never ours — it sets severity here only as a sort hint. Country-scoped.
Parser follows the published docs (clstr.news/developers); not exercised live here without a key."""
import os

from shared import settings
from typing import Any, Dict, List

from .common import fetch, item, parse_iso, place_country_items

API_URL = "https://api.clstr.news/v1/situations"
CATEGORY = {"health": "health", "disaster": "natural_hazard", "climate": "natural_hazard", "crime": "crime", "business": "infrastructure", "technology": "infrastructure"}


def configured() -> bool:
    return bool(settings.get("CLSTR_API_KEY"))


def parse_clstr(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for s in data.get("data", []):
        score = int(s.get("significance_score") or 0)
        sev = "elevated" if score >= 8 else "moderate" if score >= 6 else "low"
        cats = s.get("categories") or [s.get("category") or ""]
        etype = next((CATEGORY[c] for c in cats if c in CATEGORY), "civil_unrest")
        for iso in s.get("countries") or []:
            out.append(item(external_id=f"clstr:{s.get('id')}:{iso}", title=f"{s.get('title')} [{s.get('status', '')}]",
                            summary=(s.get("summary_preview") or "") + f" Latest: {s.get('latest_cluster_title') or ''}. {s.get('source_count', 0)} outlets, {s.get('cluster_count', 0)} events. CLSTR significance {score}/10 (theirs).",
                            lat=0.0, lon=0.0, radius_km=0.0 if sev == "low" else 100.0, severity=sev, event_type=etype, source="clstr",
                            observed_at=parse_iso(s.get("last_updated")), url=s.get("url"), country=iso, scope="country"))
    return out


async def collect_clstr(points, countries: Dict[str, Any], max_km: float = 0.0) -> List[Dict[str, Any]]:
    if not configured(): raise RuntimeError("CLSTR needs CLSTR_API_KEY")
    codes = ",".join(sorted(countries)[:10])
    r = await fetch(API_URL, params={"days": 7, "limit": 50, "sort": "recent", "country": codes}, headers={"Authorization": f"Bearer {settings.get('CLSTR_API_KEY')}"}, name="CLSTR")
    return place_country_items(parse_clstr(r.json()), countries)
