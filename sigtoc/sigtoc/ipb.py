"""§5.10b Phase 3 — the staff products: IPB, threat courses of action, decision points and the decision support
matrix, the intelligence estimate, and the intelligence annex to an operation.

Everything here is drafted by rule from what the wall already holds and cites the object ids it read. Nothing is
scored: a likelihood is an ICD 203 word the analyst chooses, a candidate COA is only an actor's assessed intent turned
into a sentence, and a product cannot be approved while a candidate sits unassessed. The Battle Captain releases the
annex; the analyst approves the IPB and the estimate (Decision AB)."""
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base
from . import requirements as R
from .analysis.wall_drafter import _haversine as haversine_km
from .cases import time_wheel

# ICD 203 likelihood words. No numbers: the analyst picks the word, the reader knows what it means.
LIKELIHOOD = ("unassessed", "almost no chance", "very unlikely", "unlikely", "roughly even chance", "likely", "very likely", "almost certain")
CONFIDENCE = ("low", "moderate", "high")
COA_STATUSES = ("candidate", "assessed", "rejected")
DP_STATUSES = ("open", "triggered", "passed", "cancelled")
PRODUCT_KINDS = ("ipb", "estimate", "annex")
PRODUCT_STATUSES = ("draft", "review", "approved", "released")
TERRAIN_TYPES = {"no_go", "slow_go", "obstacle", "mobility_corridor", "avenue_approach", "restricted_area"}
DEFAULT_AO_KM = 25.0


class ThreatCoaRow(Base):
    __tablename__ = "s2_threat_coas"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    subject_type: Mapped[str] = mapped_column(String)   # what the COA threatens: location | event | person | operation | place
    subject_id: Mapped[str] = mapped_column(String, index=True)
    subject_name: Mapped[str] = mapped_column(String, default="")
    actor_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    narrative: Mapped[str] = mapped_column(Text, default="")
    likelihood: Mapped[str] = mapped_column(String, default="unassessed")
    confidence: Mapped[str] = mapped_column(String, default="low")
    most_likely: Mapped[bool] = mapped_column(default=False)
    most_dangerous: Mapped[bool] = mapped_column(default=False)
    indicators_json: Mapped[str] = mapped_column(Text, default="[]")   # what we would see if this COA is the one
    nai_ids_json: Mapped[str] = mapped_column(Text, default="[]")      # where we would see it
    graphic_ids_json: Mapped[str] = mapped_column(Text, default="[]")  # the named graphic set that draws it
    status: Mapped[str] = mapped_column(String, default="candidate")
    basis: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class DecisionPointRow(Base):
    __tablename__ = "s2_decision_points"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    subject_type: Mapped[str] = mapped_column(String)
    subject_id: Mapped[str] = mapped_column(String, index=True)
    operation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    decision: Mapped[str] = mapped_column(Text, default="")      # what the commander decides
    trigger: Mapped[str] = mapped_column(Text, default="")       # what we would have to see
    pir_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    nai_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    coa_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    action: Mapped[str] = mapped_column(Text, default="")        # what happens when it triggers
    owner_section: Mapped[str] = mapped_column(String, default="S3")
    latest_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)   # no later than
    status: Mapped[str] = mapped_column(String, default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    decided_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class S2ProductRow(Base):
    __tablename__ = "s2_products"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, index=True)   # ipb | estimate | annex
    title: Mapped[str] = mapped_column(String)
    subject_type: Mapped[str] = mapped_column(String)
    subject_id: Mapped[str] = mapped_column(String, index=True)
    subject_name: Mapped[str] = mapped_column(String, default="")
    operation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    product_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String, default="draft")
    drafted_by: Mapped[str] = mapped_column(String, default="rule:ipb")
    drafted_at: Mapped[datetime] = mapped_column(DateTime)
    decided_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


def _j(s: Optional[str]) -> List[Any]:
    return json.loads(s or "[]")


def coa_dict(c: ThreatCoaRow, actors: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    a = (actors or {}).get(c.actor_id or "")
    return {"id": c.id, "title": c.title, "subject_type": c.subject_type, "subject_id": c.subject_id, "subject_name": c.subject_name, "actor_id": c.actor_id,
            "actor_name": a["name"] if a else None, "narrative": c.narrative, "likelihood": c.likelihood, "confidence": c.confidence, "most_likely": bool(c.most_likely),
            "most_dangerous": bool(c.most_dangerous), "indicators": _j(c.indicators_json), "nai_ids": _j(c.nai_ids_json), "graphic_ids": _j(c.graphic_ids_json),
            "status": c.status, "basis": c.basis, "created_by": c.created_by, "created_at": R.iso(c.created_at), "updated_at": R.iso(c.updated_at)}


def dp_dict(d: DecisionPointRow, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or R.now_utc()
    return {"id": d.id, "title": d.title, "subject_type": d.subject_type, "subject_id": d.subject_id, "operation_id": d.operation_id, "decision": d.decision, "trigger": d.trigger,
            "pir_id": d.pir_id, "nai_ids": _j(d.nai_ids_json), "coa_ids": _j(d.coa_ids_json), "action": d.action, "owner_section": d.owner_section,
            "latest_time": R.iso(d.latest_time), "overdue": bool(d.latest_time and d.status == "open" and d.latest_time < now), "status": d.status, "note": d.note,
            "created_by": d.created_by, "created_at": R.iso(d.created_at), "decided_by": d.decided_by, "decided_at": R.iso(d.decided_at)}


def product_dict(p: S2ProductRow, full: bool = True) -> Dict[str, Any]:
    d = {"id": p.id, "kind": p.kind, "title": p.title, "subject_type": p.subject_type, "subject_id": p.subject_id, "subject_name": p.subject_name, "operation_id": p.operation_id,
         "status": p.status, "drafted_by": p.drafted_by, "drafted_at": R.iso(p.drafted_at), "decided_by": p.decided_by, "decided_at": R.iso(p.decided_at), "notes": p.notes}
    if full: d["product"] = json.loads(p.product_json or "{}")
    return d


# ---------------------------------------------------------------- the subject and its area

async def resolve_subject(session: AsyncSession, snap: Dict[str, Any], subject_type: str, subject_id: str) -> Optional[Dict[str, Any]]:
    """Name and position for anything the wall can point at. An operation resolves to its own subject."""
    if subject_type == "operation":
        from coptoc.operations import OperationRow
        op = await session.get(OperationRow, subject_id)
        if not op: return None
        inner = await resolve_subject(session, snap, op.subject_type, op.subject_id)
        if not inner: return None
        return {**inner, "operation_id": op.id, "operation_title": op.title, "operation_status": op.status}
    if subject_type == "location":
        x = next((l for l in snap.get("locations", []) if l["id"] == subject_id), None)
        return {"subject_type": subject_type, "subject_id": subject_id, "name": x["name"], "lat": x["lat"], "lon": x["lon"], "radius_km": DEFAULT_AO_KM} if x else None
    if subject_type == "event":
        x = next((e for e in snap.get("events", []) if e["id"] == subject_id), None)
        return {"subject_type": subject_type, "subject_id": subject_id, "name": x["name"], "lat": x["venue_lat"], "lon": x["venue_lon"], "radius_km": DEFAULT_AO_KM,
                "window_from": x.get("starts_at"), "window_to": x.get("ends_at")} if x else None
    if subject_type == "person":
        x = next((p for p in snap.get("people", []) if p["id"] == subject_id), None)
        return {"subject_type": subject_type, "subject_id": subject_id, "name": x["name"], "lat": x["lat"], "lon": x["lon"], "radius_km": DEFAULT_AO_KM} if x else None
    if subject_type in ("requirement", "nai", "place"):
        req = await session.get(R.RequirementRow, subject_id)
        return {"subject_type": "place", "subject_id": subject_id, "name": req.subject_name, "lat": req.lat, "lon": req.lon, "radius_km": req.radius_km,
                "window_from": R.iso(req.window_from), "window_to": R.iso(req.window_to)} if req else None
    return None


def _within(lat: Optional[float], lon: Optional[float], s: Dict[str, Any], extra_km: float = 0.0) -> bool:
    return lat is not None and lon is not None and haversine_km(lat, lon, s["lat"], s["lon"]) <= s["radius_km"] + extra_km


def _at(x: Dict[str, Any]) -> Optional[datetime]:
    return datetime.fromisoformat(x["at"].replace("Z", "")) if x.get("at") else None


def area_of(snap: Dict[str, Any], s: Dict[str, Any]) -> Dict[str, Any]:
    nais = [n for n in snap.get("nais", []) if (n.get("subject_type") == s["subject_type"] and n.get("subject_id") == s["subject_id"]) or _within(n["lat"], n["lon"], s)]
    sites = [l for l in snap.get("locations", []) if _within(l["lat"], l["lon"], s)]
    events = [e for e in snap.get("events", []) if _within(e.get("venue_lat"), e.get("venue_lon"), s) and e.get("status") in ("active", "upcoming")]
    return {"lat": s["lat"], "lon": s["lon"], "radius_km": s["radius_km"],
            "nais": [{"id": n["id"], "name": n["name"], "subject_name": n["subject_name"], "question": n["question"], "coverage_pct": n["coverage_pct"], "health": n["health"], "pir_ids": n.get("pir_ids", [])} for n in nais],
            "sites": [{"id": l["id"], "name": l["name"], "posture": l.get("posture"), "headcount": l.get("headcount")} for l in sites],
            "events": [{"id": e["id"], "name": e["name"], "venue_name": e.get("venue_name"), "starts_at": e.get("starts_at"), "days_until": e.get("days_until")} for e in events]}


def effects_of(snap: Dict[str, Any], s: Dict[str, Any]) -> Dict[str, Any]:
    terrain = [g for g in snap.get("graphics", []) if g["type"] in TERRAIN_TYPES and g.get("status") == "active" and g.get("center") and _within(g["center"][1], g["center"][0], s)]
    w = snap.get("weather") or {}
    weather = {k: w.get(k) for k in ("station_name", "condition", "flight_category", "wind_speed_kt", "wind_gust_kt", "visibility_sm", "ceiling_ft", "summary") if k in w} if w else None
    risks = [r for r in snap.get("movement_risks", [])]
    return {"weather": weather,
            "terrain": [{"id": g["id"], "type": g["type"], "label": g["label"], "name": g["name"], "kind": g["kind"], "confidence": g["confidence"], "basis": g["basis"], "in_window": g["in_window"]} for g in terrain],
            "movement_risks": [{"id": r["id"], "movement_name": r["movement_name"], "leg_label": r["leg_label"], "graphic_name": r["graphic_name"], "severity": r["severity"], "reason": r["reason"]} for r in risks]}


def threat_of(snap: Dict[str, Any], s: Dict[str, Any], now: datetime, days: int = 30) -> Dict[str, Any]:
    since = now - timedelta(days=days)
    sightings = [x for x in snap.get("s2_sightings", []) if _at(x) and _at(x) >= since and _within(x["lat"], x["lon"], s)]
    by_actor: Dict[str, List[Dict[str, Any]]] = {}
    for x in sightings: by_actor.setdefault(x["actor_id"], []).append(x)
    actors = []
    for a in snap.get("s2_actors", []):
        mine = by_actor.get(a["id"], [])
        here_now = a.get("lat") is not None and _within(a["lat"], a["lon"], s)
        if not mine and not here_now: continue
        actors.append({"id": a["id"], "name": a["name"], "kind": a["kind"], "echelon": a.get("echelon", ""), "strength": a.get("strength", ""), "equipment": a.get("equipment", []),
                       "ttps": a.get("ttps", []), "assessed_intent": a.get("assessed_intent", ""), "status": a["status"], "last_seen_at": a.get("last_seen_at"), "place": a.get("place"),
                       "sightings": len(mine), "sightings_7d": sum(1 for x in mine if _at(x) >= now - timedelta(days=7)),
                       "nai_ids": sorted({x["nai_id"] for x in mine if x.get("nai_id")}), "pattern": time_wheel([{"at": x["at"], "participants": [a["id"]]} for x in mine])["pattern"]})
    threats = [{"id": t["id"], "title": t["title"], "severity": t["severity"], "source": t.get("source"), "synthetic": t.get("synthetic", False), "observed_at": t.get("observed_at"),
                "confirmed_links": len(t.get("confirmed_links", []))} for t in snap.get("threats", []) if _within(t.get("lat"), t.get("lon"), s, extra_km=t.get("radius_km", 0))]
    graphics = [{"id": g["id"], "type": g["type"], "label": g["label"], "name": g["name"], "kind": g["kind"], "confidence": g["confidence"], "basis": g["basis"], "in_window": g["in_window"]}
                for g in snap.get("graphics", []) if g.get("threat_graphic") and g.get("status") == "active" and g.get("center") and _within(g["center"][1], g["center"][0], s)]
    reports = [r for r in snap.get("s2_reports", []) if r.get("lat") is not None and _within(r["lat"], r["lon"], s) and _at(r) and _at(r) >= since]
    return {"days": days, "actors": actors, "threats": threats, "threat_graphics": graphics,
            "reports": {"total": len(reports), "open": sum(1 for r in reports if r["status"] == "filed"), "corroborated": sum(1 for r in reports if r["status"] == "corroborated")}}


# ---------------------------------------------------------------- courses of action and the event template

async def coas_for(session: AsyncSession, subject_type: str, subject_id: str) -> List[ThreatCoaRow]:
    return (await session.execute(select(ThreatCoaRow).where(ThreatCoaRow.subject_type == subject_type, ThreatCoaRow.subject_id == subject_id).order_by(ThreatCoaRow.created_at))).scalars().all()


async def candidate_coas(session: AsyncSession, s: Dict[str, Any], threat: Dict[str, Any], now: datetime, by: str) -> List[ThreatCoaRow]:
    """One candidate per actor with an assessed intent, if there is not one already. The sentence is the analyst's own
    intent statement turned toward the subject; the indicators are the actor's TTPs and the places it has been seen."""
    have = {c.actor_id for c in await coas_for(session, s["subject_type"], s["subject_id"]) if c.actor_id}
    new = []
    for a in threat["actors"]:
        if a["id"] in have or not (a.get("assessed_intent") or "").strip(): continue
        intent = a["assessed_intent"].strip().rstrip(".")
        indicators = list(dict.fromkeys([*a.get("ttps", []), *([f"seen again near {a['place']}"] if a.get("place") else [])]))
        c = ThreatCoaRow(id=f"COA-{uuid.uuid4().hex[:6].upper()}", title=f"{a['name']} — {intent}", subject_type=s["subject_type"], subject_id=s["subject_id"], subject_name=s["name"],
                         actor_id=a["id"], narrative=f"{a['name']} ({a['kind']}{', ' + a['strength'] if a.get('strength') else ''}) continues: {intent}, against {s['name']}. "
                                                    f"{a['sightings']} sighting{'s' if a['sightings'] != 1 else ''} in the area in {threat['days']} days; {a['pattern']}.",
                         likelihood="unassessed", confidence="low", indicators_json=json.dumps(indicators), nai_ids_json=json.dumps(a["nai_ids"]), graphic_ids_json="[]",
                         status="candidate", basis=f"actor {a['id']} assessed intent; sightings in area", created_by=by, created_at=now, updated_at=now)
        session.add(c); new.append(c)
    return new


def event_template(coas: List[Dict[str, Any]], nais: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """COA × NAI × indicators: where to look for what, to tell the COAs apart."""
    names = {n["id"]: n["name"] for n in nais}
    out = []
    for c in coas:
        if c["status"] == "rejected": continue
        for nid in c["nai_ids"] or [None]:
            out.append({"coa_id": c["id"], "coa_title": c["title"], "likelihood": c["likelihood"], "nai_id": nid, "nai_name": names.get(nid, nid) if nid else "no NAI yet", "indicators": c["indicators"]})
    return out


# ---------------------------------------------------------------- the decision support matrix

async def dsm(session: AsyncSession, snap: Dict[str, Any], now: datetime, *, subject_type: Optional[str] = None, subject_id: Optional[str] = None, operation_id: Optional[str] = None) -> Dict[str, Any]:
    q = select(DecisionPointRow).order_by(DecisionPointRow.latest_time.is_(None), DecisionPointRow.latest_time, DecisionPointRow.created_at)
    if operation_id: q = q.where(DecisionPointRow.operation_id == operation_id)
    elif subject_type and subject_id: q = q.where(DecisionPointRow.subject_type == subject_type, DecisionPointRow.subject_id == subject_id)
    dps = (await session.execute(q)).scalars().all()
    pirs = {p["id"]: p for p in snap.get("pirs", [])}
    nais = {n["id"]: n for n in snap.get("nais", [])}
    coas = {c.id: c for c in (await session.execute(select(ThreatCoaRow))).scalars()}
    rows = []
    for d in dps:
        dd = dp_dict(d, now)
        dd["pir"] = {"id": d.pir_id, "question": pirs[d.pir_id]["question"], "status": pirs[d.pir_id]["status"]} if d.pir_id in pirs else None
        dd["nais"] = [{"id": i, "name": nais[i]["name"], "coverage_pct": nais[i]["coverage_pct"], "health": nais[i]["health"]} for i in dd["nai_ids"] if i in nais]
        dd["coas"] = [{"id": i, "title": coas[i].title, "likelihood": coas[i].likelihood} for i in dd["coa_ids"] if i in coas]
        rows.append(dd)
    return {"generated_at": R.iso(now), "operation_id": operation_id, "subject_type": subject_type, "subject_id": subject_id, "rows": rows,
            "open": sum(1 for r in rows if r["status"] == "open"), "overdue": sum(1 for r in rows if r["overdue"]), "triggered": sum(1 for r in rows if r["status"] == "triggered")}


# ---------------------------------------------------------------- the products

async def draft_ipb(session: AsyncSession, snap: Dict[str, Any], s: Dict[str, Any], now: datetime, by: str) -> Tuple[S2ProductRow, List[ThreatCoaRow]]:
    threat = threat_of(snap, s, now)
    new = await candidate_coas(session, s, threat, now, by)
    await session.flush()
    actors = {a["id"]: a for a in snap.get("s2_actors", [])}
    coas = [coa_dict(c, actors) for c in await coas_for(session, s["subject_type"], s["subject_id"])]
    area = area_of(snap, s)
    matrix = await dsm(session, snap, now, subject_type=s["subject_type"], subject_id=s["subject_id"], operation_id=s.get("operation_id"))
    gaps = []
    if not area["nais"]: gaps.append("No NAI covers the area: nobody is looking, so there is nothing to watch the COAs with.")
    for n in area["nais"]:
        if n["health"] == "red": gaps.append(f"{n['name']} is red: {n['coverage_pct']}% of its indicators have a live source.")
    if not threat["actors"]: gaps.append("No actor has been sighted in the area: the threat evaluation rests on threat reports and graphics only.")
    if not coas: gaps.append("No threat course of action: no actor in the area carries an assessed intent, so nothing was drafted. The analyst writes one.")
    if any(c["status"] == "candidate" for c in coas): gaps.append("Candidate COAs await the analyst's likelihood; the product cannot be approved until they are assessed or rejected.")
    citations = sorted({*[n["id"] for n in area["nais"]], *[l["id"] for l in area["sites"]], *[a["id"] for a in threat["actors"]], *[t["id"] for t in threat["threats"]],
                        *[g["id"] for g in threat["threat_graphics"]], *[g["id"] for g in effects_of(snap, s)["terrain"]], *[c["id"] for c in coas]})
    product = {"subject": s, "step1_area": area, "step2_effects": effects_of(snap, s), "step3_threat": threat, "step4_coas": coas,
               "event_template": event_template(coas, snap.get("nais", [])), "dsm": matrix["rows"], "gaps": gaps, "citations": citations,
               "note": "Drafted by rule from the wall; every object is cited by id. Likelihoods are the analyst's words (ICD 203), never a number."}
    title = f"IPB — {s.get('operation_title') or s['name']}"
    row = S2ProductRow(id=f"IPB-{uuid.uuid4().hex[:6].upper()}", kind="ipb", title=title, subject_type=s["subject_type"], subject_id=s["subject_id"], subject_name=s["name"],
                       operation_id=s.get("operation_id"), product_json=json.dumps(product), status="draft", drafted_by="rule:ipb", drafted_at=now)
    session.add(row)
    return row, new


async def draft_estimate(session: AsyncSession, snap: Dict[str, Any], s: Dict[str, Any], now: datetime) -> S2ProductRow:
    from .isr import isr_sync
    from .intsum import latest as latest_intsum
    area = area_of(snap, s)
    threat = threat_of(snap, s, now)
    actors = {a["id"]: a for a in snap.get("s2_actors", [])}
    coas = [coa_dict(c, actors) for c in await coas_for(session, s["subject_type"], s["subject_id"]) if c.status == "assessed"]
    ml = [c for c in coas if c["most_likely"]]; md = [c for c in coas if c["most_dangerous"]]
    sync = await isr_sync(session, snap, now, days=7, ahead=3)
    nai_ids = {n["id"] for n in area["nais"]}
    gaps = [g for g in sync["gaps"] if g["nai_id"] in nai_ids]
    pirs = [p for p in snap.get("pirs", []) if any(p["id"] in n["pir_ids"] for n in area["nais"]) or (p.get("subject_type") == s["subject_type"] and p.get("subject_id") == s["subject_id"])]
    warnings = [w for w in snap.get("warnings", []) if w.get("subject_id") in {s["subject_id"], *[l["id"] for l in area["sites"]], *[e["id"] for e in area["events"]]}]
    taskings = snap.get("taskings", {}).get("items", [])
    rfis = [t for t in taskings if t.get("kind") == "rfi" and t.get("to_section") == "S2" and t.get("open")]
    intsum = await latest_intsum(session)
    since = intsum.period_to if intsum else None
    new_sightings = sum(1 for x in snap.get("s2_sightings", []) if since and _at(x) and _at(x) > since and _within(x["lat"], x["lon"], s))
    sighted_7d = [a for a in threat["actors"] if a["sightings_7d"]]
    conclusions = []
    conclusions.append(f"{len(threat['actors'])} actor{'s' if len(threat['actors']) != 1 else ''} in the area in {threat['days']} days; {len(sighted_7d)} sighted in the last 7 days"
                       + (f"; {new_sightings} sighting{'s' if new_sightings != 1 else ''} since the last INTSUM" if since else "") + ".")
    if ml: conclusions.append(f"Most likely: {ml[0]['title']} ({ml[0]['likelihood']}, {ml[0]['confidence']} confidence).")
    if md: conclusions.append(f"Most dangerous: {md[0]['title']} ({md[0]['likelihood']}, {md[0]['confidence']} confidence).")
    if not coas: conclusions.append("No assessed threat course of action yet.")
    if threat["threat_graphics"]: conclusions.append(f"{len(threat['threat_graphics'])} threat graphic{'s' if len(threat['threat_graphics']) != 1 else ''} in the area, "
                                                       f"{sum(1 for g in threat['threat_graphics'] if g['confidence'] == 'template')} of them template.")
    risks = effects_of(snap, s)["movement_risks"]
    if risks: conclusions.append(f"{len(risks)} movement leg{'s' if len(risks) != 1 else ''} cross{'es' if len(risks) == 1 else ''} a threat graphic.")
    conclusions.append(f"PIRs: {sum(1 for p in pirs if p['status'] == 'OPEN')} open, {sum(1 for p in pirs if p['status'] == 'COLLECTING')} collecting; "
                       f"{len(gaps)} NAI-day gap{'s' if len(gaps) != 1 else ''} in the sync window; "
                       f"{sum(1 for w in warnings if w['status'] == 'released')} warning{'s' if sum(1 for w in warnings if w['status'] == 'released') != 1 else ''} live, "
                       f"{sum(1 for w in warnings if w['status'] in ('suggested', 'draft'))} awaiting release.")
    product = {"subject": s, "mission": s.get("operation_title") or f"{s['name']}", "area": area, "threat_situation": {**threat, "sighted_7d": [a["id"] for a in sighted_7d], "since_intsum": new_sightings if since else None},
               "capabilities_coas": coas, "effects_on_operations": {"movement_risks": risks, "warnings": [{"id": w["id"], "title": w["title"], "status": w["status"]} for w in warnings],
                                                                    "rfis_open": [{"id": t["id"], "title": t["title"], "from_section": t["from_section"]} for t in rfis]},
               "collection": {"pirs": [{"id": p["id"], "question": p["question"], "status": p["status"]} for p in pirs], "nais": area["nais"], "gaps": gaps,
                              "avg_coverage_pct": round(sum(n["coverage_pct"] for n in area["nais"]) / len(area["nais"])) if area["nais"] else None},
               "conclusions": conclusions,
               "citations": sorted({*[a["id"] for a in threat["actors"]], *[c["id"] for c in coas], *[n["id"] for n in area["nais"]], *[p["id"] for p in pirs], *[w["id"] for w in warnings], *[r["id"] for r in risks]}),
               "note": "Sentences are counts of what the wall holds; nothing is scored."}
    row = S2ProductRow(id=f"EST-{uuid.uuid4().hex[:6].upper()}", kind="estimate", title=f"Intelligence estimate — {s.get('operation_title') or s['name']}", subject_type=s["subject_type"],
                       subject_id=s["subject_id"], subject_name=s["name"], operation_id=s.get("operation_id"), product_json=json.dumps(product), status="draft", drafted_by="rule:estimate", drafted_at=now)
    session.add(row)
    return row


async def latest_product(session: AsyncSession, kind: str, subject_type: str, subject_id: str, approved_only: bool = False) -> Optional[S2ProductRow]:
    q = select(S2ProductRow).where(S2ProductRow.kind == kind, S2ProductRow.subject_type == subject_type, S2ProductRow.subject_id == subject_id).order_by(S2ProductRow.drafted_at.desc())
    rows = (await session.execute(q)).scalars().all()
    if approved_only: rows = [r for r in rows if r.status in ("approved", "released")]
    return rows[0] if rows else None


async def draft_annex(session: AsyncSession, snap: Dict[str, Any], s: Dict[str, Any], now: datetime) -> S2ProductRow:
    """Annex B (Intelligence) to an operation: the approved IPB and estimate if there are any, else the latest drafts,
    the COAs, the DSM, the collection plan and the warnings on the subject. Release needs both products approved."""
    ipb = await latest_product(session, "ipb", s["subject_type"], s["subject_id"], approved_only=True) or await latest_product(session, "ipb", s["subject_type"], s["subject_id"])
    est = await latest_product(session, "estimate", s["subject_type"], s["subject_id"], approved_only=True) or await latest_product(session, "estimate", s["subject_type"], s["subject_id"])
    actors = {a["id"]: a for a in snap.get("s2_actors", [])}
    coas = [coa_dict(c, actors) for c in await coas_for(session, s["subject_type"], s["subject_id"]) if c.status != "rejected"]
    matrix = await dsm(session, snap, now, operation_id=s["operation_id"])
    area = area_of(snap, s)
    pirs = [p for p in snap.get("pirs", []) if any(p["id"] in n["pir_ids"] for n in area["nais"]) or (p.get("subject_type") == s["subject_type"] and p.get("subject_id") == s["subject_id"])]
    warnings = [w for w in snap.get("warnings", []) if w.get("subject_id") in {s["subject_id"], *[l["id"] for l in area["sites"]], *[e["id"] for e in area["events"]]}]
    missing = []
    if not ipb or ipb.status not in ("approved", "released"): missing.append("an approved IPB")
    if not est or est.status not in ("approved", "released"): missing.append("an approved intelligence estimate")
    product = {"operation": {"id": s["operation_id"], "title": s["operation_title"], "status": s["operation_status"], "subject": s},
               "ipb": product_dict(ipb, full=False) if ipb else None, "estimate": product_dict(est, full=False) if est else None,
               "situation": json.loads(est.product_json)["conclusions"] if est else [], "coas": coas, "dsm": matrix["rows"],
               "collection": {"nais": area["nais"], "pirs": [{"id": p["id"], "question": p["question"], "status": p["status"]} for p in pirs]},
               "warnings": [{"id": w["id"], "title": w["title"], "status": w["status"]} for w in warnings],
               "releasable": not missing, "missing": missing,
               "citations": sorted({*([ipb.id] if ipb else []), *([est.id] if est else []), *[c["id"] for c in coas], *[r["id"] for r in matrix["rows"]], *[n["id"] for n in area["nais"]]})}
    row = S2ProductRow(id=f"ANNEX-{uuid.uuid4().hex[:6].upper()}", kind="annex", title=f"Annex B (Intelligence) — {s['operation_title']}", subject_type=s["subject_type"], subject_id=s["subject_id"],
                       subject_name=s["name"], operation_id=s["operation_id"], product_json=json.dumps(product), status="draft", drafted_by="rule:annex", drafted_at=now)
    session.add(row)
    return row


async def approval_blockers(session: AsyncSession, p: S2ProductRow) -> List[str]:
    """What stops a product being approved or released. The IPB waits on its candidates; the annex on its parts."""
    out = []
    if p.kind == "ipb":
        coas = await coas_for(session, p.subject_type, p.subject_id)
        if any(c.status == "candidate" for c in coas): out.append("candidate COAs are unassessed")
        if sum(1 for c in coas if c.most_likely and c.status == "assessed") > 1: out.append("more than one most-likely COA")
        if sum(1 for c in coas if c.most_dangerous and c.status == "assessed") > 1: out.append("more than one most-dangerous COA")
    if p.kind == "annex":
        ipb = await latest_product(session, "ipb", p.subject_type, p.subject_id, approved_only=True)
        est = await latest_product(session, "estimate", p.subject_type, p.subject_id, approved_only=True)
        if not ipb: out.append("no approved IPB for the subject")
        if not est: out.append("no approved intelligence estimate for the subject")
    return out
