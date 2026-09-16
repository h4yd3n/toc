"""§5.10b Phase 2 — the ISR synchronization view and the pattern of life.

Both are read-only views over what the wall already knows: the NAIs (every active requirement), the sources watching
each one (the collection plan), the collection taskings S2 raised on S3, and the sightings and field reports that came
back. Nothing here is scored or invented; a cell is a count, a gap is an NAI-day nobody is watching, and a pattern is a
sentence that says how many of how many."""
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import requirements as R
from .analysis.wall_drafter import _haversine as haversine_km
from .cases import time_wheel

OPEN_TASKING = ("requested", "accepted", "scheduled")


def _day(iso: Optional[str]) -> Optional[date]:
    if not iso: return None
    return datetime.fromisoformat(iso.replace("Z", "")).date()


def _in_nai(lat: Optional[float], lon: Optional[float], n: Dict[str, Any]) -> bool:
    return lat is not None and lon is not None and haversine_km(lat, lon, n["lat"], n["lon"]) <= n["radius_km"]


def _nai_of(x: Dict[str, Any], nais: List[Dict[str, Any]]) -> Optional[str]:
    """A sighting keeps the NAI it was filed into; anything else falls to the closest NAI that contains it."""
    if x.get("nai_id"): return x["nai_id"]
    hits = [(haversine_km(x["lat"], x["lon"], n["lat"], n["lon"]), n["id"]) for n in nais if _in_nai(x.get("lat"), x.get("lon"), n)]
    return min(hits)[1] if hits else None


async def isr_sync(session: AsyncSession, snap: Dict[str, Any], now: datetime, days: int = 7, ahead: int = 3) -> Dict[str, Any]:
    """NAIs down the side, days across: who is watching, what is tasked, what came back. A gap is a day with nothing."""
    from coptoc.taskings import TaskingRow, out as tasking_out
    days, ahead = max(1, min(days, 60)), max(0, min(ahead, 30))
    first = now.date() - timedelta(days=days - 1)
    dates = [first + timedelta(days=i) for i in range(days + ahead)]
    cat = await R.catalog(session)
    reqs = {r.id: r for r in (await session.execute(select(R.RequirementRow).where(R.RequirementRow.status == "active"))).scalars()}
    taskings = [t for t in (await session.execute(select(TaskingRow).where(TaskingRow.kind == "collection"))).scalars() if t.status in OPEN_TASKING or (t.status == "complete" and t.updated_at.date() >= first)]
    nais = snap.get("nais", [])
    sightings = [s for s in snap.get("s2_sightings", [])]
    reports = [r for r in snap.get("s2_reports", []) if r.get("lat") is not None]
    out_nais, gaps = [], []
    for n in nais:
        req = reqs.get(n["id"])
        plan = R.plan_for(req, cat) if req else {"indicators": []}
        seen: Dict[str, Dict[str, Any]] = {}
        for row in plan["indicators"]:
            for s in row["sources"]: seen.setdefault(s["id"], {"id": s["id"], "name": s["name"], "cadence": s["cadence"], "indicators": []})["indicators"].append(row["indicator"])
        sources = list(seen.values())
        mine = [t for t in taskings if t.subject_type == "requirement" and t.subject_id == n["id"]]
        s_days = Counter(_day(s["at"]) for s in sightings if _nai_of(s, [n]) == n["id"])
        r_days = Counter(_day(r["at"]) for r in reports if _in_nai(r["lat"], r["lon"], n))
        cells = []
        for d in dates:
            tasked = [t.id for t in mine if (t.window_from.date() if t.window_from else d) <= d <= (t.window_to.date() if t.window_to else (t.window_from.date() if t.window_from else d))]
            future = d > now.date()
            covered = bool(sources) or bool(tasked)
            cells.append({"date": d.isoformat(), "tasked": tasked, "sightings": 0 if future else s_days.get(d, 0), "reports": 0 if future else r_days.get(d, 0), "covered": covered, "future": future})
            if not covered: gaps.append({"nai_id": n["id"], "nai": n["name"], "date": d.isoformat()})
        out_nais.append({"id": n["id"], "nai": n["nai"], "name": n["name"], "subject_name": n["subject_name"], "subject_type": n["subject_type"], "subject_id": n.get("subject_id"),
                         "priority": n["priority"], "question": n["question"], "health": n["health"], "coverage_pct": n["coverage_pct"], "pir_ids": n.get("pir_ids", []),
                         "window_from": n.get("window_from"), "window_to": n.get("window_to"),
                         "sources": sources, "taskings": [tasking_out(t, now) for t in mine], "cells": cells,
                         "sightings": sum(v for k, v in s_days.items() if k and k >= first), "reports": sum(v for k, v in r_days.items() if k and k >= first),
                         "gap_days": sum(1 for c in cells if not c["covered"])})
    return {"from": dates[0].isoformat(), "to": dates[-1].isoformat(), "today": now.date().isoformat(), "days": [d.isoformat() for d in dates],
            "nais": out_nais, "gaps": gaps, "taskings_open": sum(1 for t in taskings if t.status in OPEN_TASKING)}


async def patterns(session: AsyncSession, snap: Dict[str, Any], now: datetime, days: int = 30) -> Dict[str, Any]:
    """Pattern of life per actor and per NAI: the 7×24 time wheel from sightings and reports, activity over 7 and
    N days, and what is new since the last INTSUM. The wheel's sentence says how many of how many; it never scores."""
    from .intsum import latest as latest_intsum
    days = max(7, min(days, 365))
    since_n = now - timedelta(days=days)
    since_7 = now - timedelta(days=7)
    nais = snap.get("nais", [])
    actors = {a["id"]: a for a in snap.get("s2_actors", [])}
    sightings = [s for s in snap.get("s2_sightings", []) if s.get("at")]
    reports = [r for r in snap.get("s2_reports", []) if r.get("at") and r.get("status") != "dismissed"]
    intsum = await latest_intsum(session)
    cut = intsum.period_to if intsum else None
    at = lambda x: datetime.fromisoformat(x["at"].replace("Z", ""))

    def ev(x: Dict[str, Any], who: List[str]) -> Dict[str, Any]:
        return {"at": x["at"], "participants": who}

    out_actors = []
    for aid, a in actors.items():
        mine = [s for s in sightings if s["actor_id"] == aid]
        n_days = [s for s in mine if at(s) >= since_n]
        wheel = time_wheel([ev(s, [aid]) for s in n_days], aid)
        in_nais = Counter(_nai_of(s, nais) for s in n_days)
        in_nais.pop(None, None)
        out_actors.append({"id": aid, "name": a["name"], "kind": a["kind"], "status": a["status"], "last_seen_at": a.get("last_seen_at"),
                           "sightings_7d": sum(1 for s in mine if at(s) >= since_7), f"sightings_{days}d": len(n_days), "sightings_total": len(mine),
                           "since_intsum": sum(1 for s in mine if cut and at(s) > cut) if cut else None,
                           "nais": [{"id": k, "name": next((n["name"] for n in nais if n["id"] == k), k), "sightings": v} for k, v in in_nais.most_common()],
                           "wheel": wheel})
    out_nais = []
    for n in nais:
        s_here = [s for s in sightings if _nai_of(s, [n]) == n["id"] and at(s) >= since_n]
        r_here = [r for r in reports if _in_nai(r.get("lat"), r.get("lon"), n) and at(r) >= since_n]
        evs = [ev(s, [s["actor_id"]]) for s in s_here] + [ev(r, []) for r in r_here]
        who = Counter(s["actor_id"] for s in s_here)
        out_nais.append({"id": n["id"], "nai": n["nai"], "name": n["name"], "subject_name": n["subject_name"], "priority": n["priority"],
                         "activity_7d": sum(1 for s in s_here if at(s) >= since_7) + sum(1 for r in r_here if at(r) >= since_7), f"activity_{days}d": len(evs),
                         "sightings": len(s_here), "reports": len(r_here),
                         "since_intsum": (sum(1 for s in s_here if at(s) > cut) + sum(1 for r in r_here if at(r) > cut)) if cut else None,
                         "actors": [{"id": k, "name": actors.get(k, {}).get("name", k), "sightings": v} for k, v in who.most_common()],
                         "wheel": time_wheel(evs)})
    out_actors.sort(key=lambda x: (-x["sightings_7d"], -x[f"sightings_{days}d"], x["name"]))
    out_nais.sort(key=lambda x: (-x["activity_7d"], -x[f"activity_{days}d"], x["nai"]))
    since = None
    if intsum:
        since = {"intsum_id": intsum.id, "period_to": R.iso(intsum.period_to), "status": intsum.status,
                 "sightings": sum(1 for s in sightings if at(s) > cut), "reports": sum(1 for r in reports if at(r) > cut),
                 "new_actors": [a["id"] for a in actors.values() if a.get("created_at") and datetime.fromisoformat(a["created_at"].replace("Z", "")) > cut]}
    return {"days": days, "generated_at": R.iso(now), "since_intsum": since, "actors": out_actors, "nais": out_nais}
