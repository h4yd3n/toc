"""§5.6 Warning — an imminent, specific threat to a subject: FLASH to the floor, and out over S6.

Collection suggests a warning by rule (a critical threat, or an elevated one an analyst confirmed, inside a subject's
radius); nothing goes out until the Battle Captain releases it. Release dispatches SMS to the people at or near the
subject and a post to the ops channel, and opens an acknowledgement row per role so the read-back is on the record."""
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base
from . import requirements as R
from .analysis.wall_drafter import _haversine as haversine_km

SEV_RANK = {"low": 0, "moderate": 1, "elevated": 2, "critical": 3}
ACTIVE_HOURS = 24  # a released warning stays on the wall this long
ROLES_TO_ACK = ["battle_captain", "ep", "security"]


class WarningRow(Base):
    __tablename__ = "s2_warnings"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text, default="")
    subject_type: Mapped[str] = mapped_column(String)  # location | person | event | ccir (§3.6, a tripped requirement)
    subject_id: Mapped[str] = mapped_column(String, index=True)
    subject_name: Mapped[str] = mapped_column(String, default="")
    threat_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    severity: Mapped[str] = mapped_column(String, default="elevated")
    status: Mapped[str] = mapped_column(String, default="suggested")  # suggested | draft | released | cancelled | expired
    suggested_by: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    released_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancelled_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    dispatch_json: Mapped[str] = mapped_column(Text, default="{}")
    recipients_json: Mapped[str] = mapped_column(Text, default="[]")  # people ids the SMS went to


def to_dict(w: WarningRow, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or R.now_utc()
    return {"id": w.id, "title": w.title, "text": w.text, "subject_type": w.subject_type, "subject_id": w.subject_id, "subject_name": w.subject_name, "threat_id": w.threat_id,
            "severity": w.severity, "status": w.status, "suggested_by": w.suggested_by, "created_at": R.iso(w.created_at), "released_by": w.released_by, "released_at": R.iso(w.released_at),
            "cancelled_by": w.cancelled_by, "dispatch": json.loads(w.dispatch_json or "{}"), "recipients": json.loads(w.recipients_json or "[]"),
            "age_min": round((now - w.released_at).total_seconds() / 60) if w.released_at else None}


def _in_radius(lat: float, lon: float, t: Dict[str, Any], buffer_km: float = 5.0) -> bool:
    return haversine_km(lat, lon, t["lat"], t["lon"]) <= t["radius_km"] + buffer_km


def rule_suggestions(snap: Dict[str, Any]) -> List[Dict[str, Any]]:
    """What collection says deserves a FLASH: critical severity inside a subject's radius, or elevated with an
    analyst-confirmed link to that subject. Synthetic seed threats count only when confirmed (they are exercises)."""
    out = []
    for t in snap.get("threats", []):
        confirmed = {(l["target_type"], l["target_id"]) for l in t.get("confirmed_links", [])}
        strong = t["severity"] == "critical" and not t.get("synthetic")
        for l in snap.get("locations", []):
            hit = ("location", l["id"]) in confirmed
            if (strong and _in_radius(l["lat"], l["lon"], t)) or (hit and SEV_RANK[t["severity"]] >= 2):
                out.append({"subject_type": "location", "subject_id": l["id"], "subject_name": l["name"], "threat_id": t["id"], "severity": t["severity"],
                            "title": f"FLASH — {t['title']} — {l['name']}", "text": f"{t['title']} ({t['severity']}, {t['source']}) affects {l['name']}. " + (t.get("summary") or "")[:240],
                            "basis": "confirmed link" if hit else "critical inside radius"})
        for p in snap.get("people", []):
            if p.get("status") != "traveling": continue
            hit = ("person", p["id"]) in confirmed
            if (strong and _in_radius(p["lat"], p["lon"], t)) or (hit and SEV_RANK[t["severity"]] >= 2):
                out.append({"subject_type": "person", "subject_id": p["id"], "subject_name": p["name"], "threat_id": t["id"], "severity": t["severity"],
                            "title": f"FLASH — {t['title']} — {p['name']}", "text": f"{t['title']} ({t['severity']}, {t['source']}) affects {p['name']}, traveling. " + (t.get("summary") or "")[:240],
                            "basis": "confirmed link" if hit else "critical inside radius"})
        for e in snap.get("events", []):
            if strong and _in_radius(e["venue_lat"], e["venue_lon"], t) and e.get("status") in ("active", "upcoming") and e.get("days_until", 99) <= 3:
                out.append({"subject_type": "event", "subject_id": e["id"], "subject_name": e["name"], "threat_id": t["id"], "severity": t["severity"],
                            "title": f"FLASH — {t['title']} — {e['name']}", "text": f"{t['title']} ({t['severity']}) at or near {e['venue_name']} within the event window. " + (t.get("summary") or "")[:240],
                            "basis": "critical inside radius, event within 3 days"})
    out.extend(threshold_suggestions(snap))
    return out


# ---------------------------------------------------------------- Phase 2: what the picture itself says (§5.10b)
# Thresholds are settings, not judgments: the rule counts, the analyst decides. Seed sightings are exercises and never count.

def thresholds() -> Dict[str, Any]:
    import os
    return {"sightings": int(os.environ.get("TOC_S2_SIGHTING_THRESHOLD", "3")), "days": int(os.environ.get("TOC_S2_SIGHTING_DAYS", "7")),
            "site_km": float(os.environ.get("TOC_S2_SITE_BUFFER_KM", "5"))}


def _at(x: Dict[str, Any]) -> Optional[datetime]:
    return datetime.fromisoformat(x["at"].replace("Z", "")) if x.get("at") else None


def _subject_for_nai(n: Dict[str, Any], snap: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The wall subject a warning about this NAI goes to: the NAI's own subject, or the site inside it."""
    if n.get("subject_type") in ("location", "person", "event") and n.get("subject_id"):
        key = {"location": "locations", "person": "people", "event": "events"}[n["subject_type"]]
        x = next((x for x in snap.get(key, []) if x["id"] == n["subject_id"]), None)
        if x: return {"subject_type": n["subject_type"], "subject_id": x["id"], "subject_name": x["name"]}
    inside = [(haversine_km(l["lat"], l["lon"], n["lat"], n["lon"]), l) for l in snap.get("locations", []) if haversine_km(l["lat"], l["lon"], n["lat"], n["lon"]) <= n["radius_km"]]
    if inside:
        l = min(inside, key=lambda x: x[0])[1]
        return {"subject_type": "location", "subject_id": l["id"], "subject_name": l["name"]}
    return None


def _inside_graphic(lat: float, lon: float, g: Dict[str, Any]) -> bool:
    from coptoc.overlays import _point_in_poly
    geom = g.get("geometry") or []
    if g.get("kind") == "point" and len(geom) == 2:
        return haversine_km(lat, lon, geom[1], geom[0]) <= 1.0
    if g.get("kind") == "polygon" and len(geom) >= 3:
        return _point_in_poly([lon, lat], geom)
    return False


def threshold_suggestions(snap: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Three rules over the live picture, none of them a judgment:
    1. one actor sighted N or more times in one NAI within D days;
    2. a corroborated field report inside a threat graphic (danger area, ambush site, surveillance point ...);
    3. an actor's latest real sighting within the site buffer of one of our sites."""
    th = thresholds()
    now = R.now_utc()
    out: List[Dict[str, Any]] = []
    actors = {a["id"]: a for a in snap.get("s2_actors", []) if a.get("status") == "active"}
    nais = {n["id"]: n for n in snap.get("nais", [])}
    live = [s for s in snap.get("s2_sightings", []) if s.get("source_type") != "seed" and s["actor_id"] in actors and _at(s)]
    # 1 — repeat sightings in an NAI
    recent = [s for s in live if now - _at(s) <= timedelta(days=th["days"])]
    counts: Dict[tuple, int] = {}
    for s in recent:
        nid = s.get("nai_id") or next((n["id"] for n in nais.values() if haversine_km(s["lat"], s["lon"], n["lat"], n["lon"]) <= n["radius_km"]), None)
        if nid: counts[(s["actor_id"], nid)] = counts.get((s["actor_id"], nid), 0) + 1
    for (aid, nid), k in counts.items():
        if k < th["sightings"]: continue
        subj = _subject_for_nai(nais[nid], snap)
        if not subj: continue
        a = actors[aid]
        out.append({**subj, "threat_id": f"actor-repeat:{aid}", "severity": "elevated",
                    "title": f"FLASH — {a['name']} seen {k}× in {nais[nid]['name']} — {subj['subject_name']}",
                    "text": f"{a['name']} ({a.get('kind', 'actor')}{', ' + a['strength'] if a.get('strength') else ''}) sighted {k} times in {nais[nid]['name']} within {th['days']} days. " + (a.get("assessed_intent") or "")[:200],
                    "basis": f"{k} sightings in {th['days']} days"})
    # 2 — corroborated report inside a threat graphic
    graphics = [g for g in snap.get("graphics", []) if g.get("threat_graphic") and g.get("status", "active") == "active" and g.get("in_window", True)]
    for r in snap.get("s2_reports", []):
        if r.get("status") != "corroborated" or r.get("lat") is None or r.get("lon") is None: continue
        for g in graphics:
            if not _inside_graphic(r["lat"], r["lon"], g): continue
            near = [(haversine_km(l["lat"], l["lon"], r["lat"], r["lon"]), l) for l in snap.get("locations", [])]
            near = [x for x in near if x[0] <= max(th["site_km"], 25.0)]
            if not near: continue
            l = min(near, key=lambda x: x[0])[1]
            out.append({"subject_type": "location", "subject_id": l["id"], "subject_name": l["name"], "threat_id": f"graphic:{g['id']}", "severity": "elevated",
                        "title": f"FLASH — {r['kind'].upper()} inside {g['name']} — {l['name']}",
                        "text": f"Corroborated {r['kind'].upper()} {r.get('grade', '')} from {r.get('reported_by', '')} falls inside {g.get('label') or g['type']} '{g['name']}'. {r.get('text', '')[:200]}",
                        "basis": "corroborated report inside threat graphic"})
    # 3 — an actor's latest real sighting at one of our sites
    latest: Dict[str, Dict[str, Any]] = {}
    for s in live:
        if s["actor_id"] not in latest or _at(s) > _at(latest[s["actor_id"]]): latest[s["actor_id"]] = s
    for aid, s in latest.items():
        for l in snap.get("locations", []):
            if haversine_km(s["lat"], s["lon"], l["lat"], l["lon"]) <= th["site_km"]:
                a = actors[aid]
                out.append({"subject_type": "location", "subject_id": l["id"], "subject_name": l["name"], "threat_id": f"actor-near:{aid}", "severity": "elevated",
                            "title": f"FLASH — {a['name']} at {l['name']}",
                            "text": f"{a['name']} last sighted {s.get('place') or 'nearby'} within {th['site_km']:g} km of {l['name']} ({s.get('grade', '')}, {s.get('confidence', '')}). {s.get('what', '')[:200]}",
                            "basis": f"actor within {th['site_km']:g} km of site"})
    return out


async def suggest(session: AsyncSession, snap: Dict[str, Any], now: datetime) -> List[WarningRow]:
    """Idempotent per (threat, subject): a suggestion already on the books is not repeated; a cancelled one is not revived."""
    existing = {(w.threat_id, w.subject_type, w.subject_id) for w in (await session.execute(select(WarningRow))).scalars()}
    new = []
    for s in rule_suggestions(snap):
        key = (s["threat_id"], s["subject_type"], s["subject_id"])
        if key in existing: continue
        w = WarningRow(id=f"WARN-{uuid.uuid4().hex[:6].upper()}", title=s["title"], text=s["text"], subject_type=s["subject_type"], subject_id=s["subject_id"], subject_name=s["subject_name"],
                       threat_id=s["threat_id"], severity=s["severity"], status="suggested", suggested_by=f"rule:{s['basis']}", created_at=now)
        session.add(w); new.append(w); existing.add(key)
    if new: await session.commit()
    return new


async def expire(session: AsyncSession, now: datetime) -> int:
    n = 0
    for w in (await session.execute(select(WarningRow).where(WarningRow.status == "released"))).scalars():
        if w.released_at and now - w.released_at > timedelta(hours=ACTIVE_HOURS):
            w.status = "expired"; n += 1
    if n: await session.commit()
    return n


def people_for_subject(snap: Dict[str, Any], w: WarningRow) -> List[Dict[str, Any]]:
    """Who the SMS goes to: everyone at or assigned to the site, the traveler, or the event's attendees."""
    people = snap.get("people", [])
    if w.subject_type == "location":
        loc = next((l for l in snap.get("locations", []) if l["id"] == w.subject_id), None)
        if not loc: return []
        return [p for p in people if p.get("location_id") == w.subject_id or p.get("home_location_id") == w.subject_id or haversine_km(p["lat"], p["lon"], loc["lat"], loc["lon"]) <= 5]
    if w.subject_type == "person":
        return [p for p in people if p["id"] == w.subject_id]
    if w.subject_type == "ccir":
        return []  # §3.6 — a tripped requirement is a message to the floor, not an SMS to a site; releasing it posts to the ops channel
    ev = next((e for e in snap.get("events", []) if e["id"] == w.subject_id), None)
    ids = set(ev.get("attendee_ids", [])) if ev else set()
    return [p for p in people if p["id"] in ids]


def flash_text(w: WarningRow) -> str:
    return f"TOC FLASH — {w.subject_name}: {w.title.replace('FLASH — ', '')}. {w.text[:200]} Reply SAFE, HELP, or INJURED, or call the watch floor."
