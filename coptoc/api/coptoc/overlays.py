"""§3.4 the section overlays, derived from what the wall already holds (2026-09-05).

An overlay is a section's own situation laid over the base map, the way acetate goes on a map board. Nothing here is
drawn by hand yet: the S2 overlay is derived from the requirements (every active requirement is a named area of
interest with a window and a coverage figure), and the S3 overlay from the trips and the shipments (everything that
moves is a movement, grouped the way the profile thinks about it). The hand-drawn graphics object — routes, corridors,
phase lines, supply points — comes after this and shares the model.

The grouping rule (Decision Z). A movement is one or more travelers on a shared route in a shared window, drawn as one
line with a count. On a military desk the unit is the actor: trips group by battalion, origin, destination, and a
six-hour window into a serial named for the unit. On a corporate desk the individual is the actor: trips group only by
a shared destination event into a delegation; everyone else moves alone under their own name. A VIP never folds into a
group. A group needs at least three travelers. A shipment is a movement too — S4 keeps what is inbound to a site, S3
owns the moving — with its origin only when the wall knows where it left from."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional

GROUP_MIN = 3
SERIAL_WINDOW_H = 6


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def nais(requirements: List[Dict[str, Any]], pirs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Every active requirement as a named area of interest: where S2 is looking, why, for how long, and how well."""
    active = [r for r in requirements if r.get("status") == "active"]
    active.sort(key=lambda r: (r.get("priority", 3), r.get("kind") != "directed", r.get("created_at") or ""))
    out = []
    for n, r in enumerate(active, 1):
        cov = r.get("coverage") or {}
        linked = [p["id"] for p in pirs if p.get("subject_type") == r.get("subject_type") and p.get("subject_id") and p.get("subject_id") == r.get("subject_id")]
        out.append({"id": r["id"], "nai": n, "name": f"NAI {n}", "subject_name": r["subject_name"], "subject_type": r["subject_type"], "subject_id": r.get("subject_id"),
                    "kind": r["kind"], "lat": r["lat"], "lon": r["lon"], "radius_km": r.get("radius_km", 50.0), "priority": r.get("priority", 3),
                    "window_from": r.get("window_from"), "window_to": r.get("window_to"), "question": r.get("question", ""),
                    "coverage_pct": cov.get("pct", 0), "gaps": len(cov.get("gaps", [])), "pir_ids": linked,
                    "health": "green" if cov.get("pct", 0) >= 90 else "amber" if cov.get("pct", 0) >= 50 else "red"})
    return out


def _unit_of(team_id: str, team_by_id: Dict[str, Any]) -> Any:
    """The battalion a person belongs to, or the highest team under the root if the data has no battalion echelon."""
    t = team_by_id.get(team_id)
    seen = set()
    while t is not None and t.id not in seen:
        seen.add(t.id)
        if (t.echelon or "") == "battalion":
            return t
        parent = team_by_id.get(t.parent_id) if t.parent_id else None
        if parent is None or parent.parent_id is None:
            return t
        t = parent
    return t


def movements(trips: List[Dict[str, Any]], person_by_id: Dict[str, Dict[str, Any]], team_by_id: Dict[str, Any], events_by_id: Dict[str, Dict[str, Any]],
              shipments: List[Dict[str, Any]], loc_by_id: Dict[str, Any], profile: str, now: datetime) -> List[Dict[str, Any]]:
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for t in trips:
        p = person_by_id.get(t["person_id"])
        if not p:
            continue
        if p["is_vip"]:
            key: tuple = ("vip", t["id"])
        elif profile == "military":
            unit = _unit_of(p["team_id"], team_by_id)
            slot = int(datetime.fromisoformat(t["depart_at"].replace("Z", "")).timestamp() // (SERIAL_WINDOW_H * 3600))
            key = ("unit", unit.id if unit else p["team_id"], t["origin_location_id"], t["dest_name"], slot)
        else:
            key = ("event", t["event_id"], t["dest_name"]) if t.get("event_id") else ("solo", t["id"])
        groups.setdefault(key, []).append(t)
    out: List[Dict[str, Any]] = []
    def emit(kind: str, ts: List[Dict[str, Any]], name: str, unit: Optional[str] = None) -> None:
        ts = sorted(ts, key=lambda x: x["depart_at"])
        first = ts[0]
        with_legs = next((x for x in ts if x.get("legs")), None)
        legs = [{"kind": lg["kind"], "label": lg.get("label") or lg["to_name"], "from_lat": lg["from_lat"], "from_lon": lg["from_lon"], "to_lat": lg["to_lat"], "to_lon": lg["to_lon"], "start_at": lg["start_at"], "end_at": lg["end_at"], "status": lg["status"]}
                for lg in (with_legs["legs"] if with_legs else [])]
        if not legs:
            legs = [{"kind": "route", "label": f"{first['origin_name']} → {first['dest_name']}", "from_lat": first["origin_lat"], "from_lon": first["origin_lon"], "to_lat": first["dest_lat"], "to_lon": first["dest_lon"],
                     "start_at": first["depart_at"], "end_at": max(x["return_at"] for x in ts), "status": "current" if first["status"] == "active" else "planned"}]
        head = person_by_id[first["person_id"]]
        status = "active" if any(x["status"] == "active" for x in ts) else "planned"
        out.append({"id": f"mv_{first['id']}", "kind": kind, "owner": "S3", "name": name, "unit": unit, "pax": len(ts), "person_ids": [x["person_id"] for x in ts], "trip_ids": [x["id"] for x in ts],
                    "is_vip": any(person_by_id[x["person_id"]]["is_vip"] for x in ts), "event_id": first.get("event_id"), "purpose": first["purpose"],
                    "origin_name": first["origin_name"], "origin_lat": first["origin_lat"], "origin_lon": first["origin_lon"], "dest_name": first["dest_name"], "dest_lat": first["dest_lat"], "dest_lon": first["dest_lon"],
                    "depart_at": first["depart_at"], "return_at": max(x["return_at"] for x in ts), "status": status, "mode": "air" if any(lg["kind"] == "flight" for lg in legs) else "ground" if any(lg["kind"] == "ground" for lg in legs) else "unknown",
                    "head_lat": head["lat"], "head_lon": head["lon"], "current_leg": next((lg["label"] for lg in legs if lg["status"] == "current"), None), "legs": legs, "health": "green"})
    for key, ts in groups.items():
        if key[0] in ("unit", "event") and len(ts) >= GROUP_MIN:
            if key[0] == "unit":
                unit = _unit_of(person_by_id[ts[0]["person_id"]]["team_id"], team_by_id)
                short = (unit.short or unit.name) if unit else person_by_id[ts[0]["person_id"]]["team_name"]
                emit("serial", ts, f"{short} · {len(ts)} pax · {ts[0]['origin_name'].split(' — ')[0]} → {ts[0]['dest_name'].split(',')[0]}", short)
            else:
                ev = events_by_id.get(key[1]) or {}
                emit("delegation", ts, f"{ev.get('name', 'Delegation')} · {len(ts)} travelers → {ts[0]['dest_name'].split(',')[0]}")
        else:
            for t in ts:
                p = person_by_id[t["person_id"]]
                emit("individual", [t], f"{'★ ' if p['is_vip'] else ''}{p.get('short_name') or p['name']} → {t['dest_name'].split(',')[0]}")
    # what is inbound: a shipment moves too, on the S3 overlay as a movement and on S4 as what the site is waiting for
    import re
    toks = lambda text: {w for w in re.split(r"[^a-z0-9]+", text.lower()) if len(w) > 2 and w not in ("the", "and", "army")}
    site_tokens = [(l, toks(l.name)) for l in loc_by_id.values()]
    def origin_site(from_name: str):
        """A shipment's origin is free text; it is a site when the words say so — two shared words, or one name inside the other."""
        if not from_name: return None
        f = from_name.lower(); ft = toks(from_name)
        exact = next((l for l, _ in site_tokens if l.name.lower() in f or f in l.name.lower()), None)
        if exact: return exact
        best = max(site_tokens, key=lambda x: len(x[1] & ft), default=None)
        return best[0] if best and len(best[1] & ft) >= 2 else None
    for s in shipments:
        if s["status"] in ("arrived", "cancelled"):
            continue
        origin = origin_site(s["from_name"])
        dest = loc_by_id.get(s["to_location_id"]) if s.get("to_location_id") else None
        if dest is None:
            continue
        out.append({"id": f"mv_{s['id']}", "kind": "shipment", "owner": "S4", "name": f"{s['description']} → {dest.name.split(' — ')[0]}", "unit": None, "pax": 0, "person_ids": [], "trip_ids": [], "shipment_id": s["id"],
                    "is_vip": False, "event_id": None, "purpose": s["quantity"], "origin_name": s["from_name"] or "unknown", "origin_lat": origin.lat if origin else None, "origin_lon": origin.lon if origin else None,
                    "dest_name": dest.name, "dest_lat": dest.lat, "dest_lon": dest.lon, "depart_at": None, "return_at": s["eta"], "eta": s["eta"], "hours_to_eta": s["hours_to_eta"],
                    "status": "active" if s["status"] in ("in_transit", "delayed") else "planned", "mode": "ground", "head_lat": None, "head_lon": None, "current_leg": s["status"].replace("_", " "),
                    "legs": ([{"kind": "ground", "label": f"{s['from_name']} → {dest.name}", "from_lat": origin.lat, "from_lon": origin.lon, "to_lat": dest.lat, "to_lon": dest.lon, "start_at": None, "end_at": s["eta"], "status": "current" if s["status"] in ("in_transit", "delayed") else "planned"}] if origin else []),
                    "health": s["health"], "priority": s["priority"]})
    rank = {"active": 0, "planned": 1}
    out.sort(key=lambda m: (rank.get(m["status"], 2), not m["is_vip"], m["return_at"] or ""))
    return out


THREAT_SEVERITY = {
    "kill_zone": "critical",
    "ambush_site": "critical",
    "danger_area": "elevated",
    "attack_hotspot": "elevated",
    "hostile_checkpoint": "elevated",
    "hostile_op": "elevated",
    "no_go": "elevated",
}


def _xy(lon: float, lat: float, origin_lat: float) -> tuple[float, float]:
    return (lon * 111.32 * math.cos(math.radians(origin_lat)), lat * 110.57)


def _dist_point_segment_km(p: List[float], a: List[float], b: List[float]) -> float:
    origin = p[1]
    px, py = _xy(p[0], p[1], origin)
    ax, ay = _xy(a[0], a[1], origin)
    bx, by = _xy(b[0], b[1], origin)
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _ccw(a: List[float], b: List[float], c: List[float]) -> bool:
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(a: List[float], b: List[float], c: List[float], d: List[float]) -> bool:
    return _ccw(a, c, d) != _ccw(b, c, d) and _ccw(a, b, c) != _ccw(a, b, d)


def _point_in_poly(p: List[float], poly: List[List[float]]) -> bool:
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        pi, pj = poly[i], poly[j]
        if ((pi[1] > p[1]) != (pj[1] > p[1])) and p[0] < (pj[0] - pi[0]) * (p[1] - pi[1]) / ((pj[1] - pi[1]) or 1e-9) + pi[0]:
            inside = not inside
        j = i
    return inside


def _segment_hits_graphic(a: List[float], b: List[float], graphic: Dict[str, Any]) -> bool:
    kind, geom = graphic["kind"], graphic["geometry"]
    if kind == "point":
        return _dist_point_segment_km(geom, a, b) <= 1.0
    pts = geom
    if kind == "line":
        return any(_segments_intersect(a, b, pts[i], pts[i + 1]) or _dist_point_segment_km(pts[i], a, b) <= 0.5 for i in range(len(pts) - 1))
    if kind == "polygon":
        poly = pts
        edges = list(zip(poly, poly[1:] + [poly[0]]))
        return _point_in_poly(a, poly) or _point_in_poly(b, poly) or any(_segments_intersect(a, b, x, y) for x, y in edges)
    return False


def movement_risks(movements: List[Dict[str, Any]], graphics: List[Dict[str, Any]], now: datetime) -> List[Dict[str, Any]]:
    """Flag movement legs that cross live S2 threat graphics. The flags are derived snapshot data, never stored."""
    threats = [g for g in graphics if g.get("threat_graphic") and g.get("status") == "active" and g.get("in_window", True)]
    flags: List[Dict[str, Any]] = []
    for mv in movements:
        mv_flags = []
        for leg in mv.get("legs", []):
            if leg.get("kind") == "lodging" or leg.get("from_lat") is None or leg.get("from_lon") is None:
                continue
            a = [leg["from_lon"], leg["from_lat"]]
            b = [leg["to_lon"], leg["to_lat"]]
            for g in threats:
                if not _segment_hits_graphic(a, b, g):
                    continue
                severity = THREAT_SEVERITY.get(g["type"], "moderate")
                flag = {
                    "id": f"risk_{mv['id']}_{g['id']}_{len(flags) + 1}",
                    "movement_id": mv["id"],
                    "movement_name": mv["name"],
                    "leg_label": leg["label"],
                    "graphic_id": g["id"],
                    "graphic_name": g["name"],
                    "graphic_type": g["type"],
                    "confidence": g.get("confidence", "confirmed"),
                    "basis": g.get("basis", ""),
                    "severity": severity,
                    "reason": f"{leg['label']} crosses {g['name']} ({g.get('confidence', 'confirmed')})",
                }
                flags.append(flag)
                mv_flags.append(flag)
        mv["risk_flags"] = sorted(mv_flags, key=lambda f: {"critical": 0, "elevated": 1, "moderate": 2}.get(f["severity"], 3))
    return sorted(flags, key=lambda f: ({"critical": 0, "elevated": 1, "moderate": 2}.get(f["severity"], 3), f["movement_name"]))
