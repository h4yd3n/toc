"""§5.6 Area Assessment — the Lisbon question answered as a product.

One or more directed requirements (candidate places) laid side by side, indicator by indicator: what is known, how well
it is known, and what is missing. Three states per cell — `reported` (a term, a band, a confidence, and the evidence),
`quiet` (a tasked source is watching and has reported nothing), `gap` (nobody is watching). No numeric composite
(Decision I): ranking is the human's. A product with no qualifying evidence anywhere is a collection gap and cannot
be approved (§5.5)."""
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base
from . import requirements as R
from .analysis.wall_drafter import ICD203_TERMS, SEVERITY_TO_TERM, _haversine as haversine_km, compute_confidence, model_draft, use_model

PROXIMITY_BUFFER_KM = 5.0
LOOKBACK_DAYS = 90  # reporting this old still describes a place; older is history
SEV_RANK = {"low": 0, "moderate": 1, "elevated": 2, "critical": 3}

# A threat's event_type → the indicator it answers. Unmapped types are listed, not scored.
EVENT_TO_INDICATOR = {
    "EQ": "earthquake", "earthquake": "earthquake",
    "TC": "natural_hazard", "FL": "natural_hazard", "VO": "natural_hazard", "DR": "natural_hazard", "WF": "natural_hazard", "TS": "natural_hazard", "natural_hazard": "natural_hazard",
    "conflict": "civil_unrest", "civil_unrest": "civil_unrest", "protest": "crowd", "crowd": "crowd",
    "crime": "crime", "targeted": "targeted", "geopolitical": "advisory", "advisory": "advisory",
    "transit": "transit", "health": "health", "infrastructure": "infrastructure",
}


def indicator_for(event_type: Optional[str]) -> Optional[str]:
    """GDACS types arrive as `natural_hazard:EQ`; seed and other collectors use a bare word."""
    if not event_type: return None
    if event_type in EVENT_TO_INDICATOR: return EVENT_TO_INDICATOR[event_type]
    head, _, tail = event_type.partition(":")
    return EVENT_TO_INDICATOR.get(tail) or EVENT_TO_INDICATOR.get(head)


class AreaAssessmentRow(Base):
    __tablename__ = "s2_area_assessments"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    purpose: Mapped[str] = mapped_column(String, default="")
    requirement_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    product_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String, default="draft")  # draft | review | approved
    author: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    decided_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


def _window(req: R.RequirementRow, now: datetime):
    start = (req.window_from or now) - timedelta(days=LOOKBACK_DAYS)
    end = req.window_to or now
    return start, max(end, now)


async def _threats_near(session: AsyncSession, req: R.RequirementRow, now: datetime) -> List[Dict[str, Any]]:
    from coptoc.db_models import ThreatRow  # same DB the wall reads (see api.query)
    start, end = _window(req, now)
    out = []
    for t in (await session.execute(select(ThreatRow))).scalars():
        by_country = getattr(t, "scope", "point") == "country" and t.country and req.country and t.country == req.country
        # point events must fall in the window (with the lookback); country-scoped reporting — advisories, health notices —
        # describes the current state of the country and counts however old its last update is
        if not by_country and not (start <= t.observed_at <= end):
            continue
        if by_country and t.observed_at > end:
            continue
        d = 0.0 if by_country else haversine_km(req.lat, req.lon, t.lat, t.lon)
        if not by_country and d > req.radius_km + t.radius_km + PROXIMITY_BUFFER_KM:
            continue
        out.append({"threat_id": t.id, "title": t.title, "source": t.source, "confidence": t.confidence, "severity": t.severity,
                    "distance_km": round(d, 1), "observed_at": t.observed_at.isoformat() + "Z", "synthetic": t.synthetic, "confirmed": False,
                    "summary": t.summary, "indicator": indicator_for(t.event_type)})
    out.sort(key=lambda e: (-SEV_RANK[e["severity"]], e["distance_km"]))
    return out


def assess_candidate(req: R.RequirementRow, plan: Dict[str, Any], threats: List[Dict[str, Any]], now: datetime, facts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """One column of the comparison. Terms come from the same fixed list as every other product; code attaches band
    and confidence; a cell with nobody watching is a gap, not a low score. The baseline row holds facts, not threats."""
    cells = []
    facts = facts or {}
    for ind in plan["indicators"]:
        ev = [e for e in threats if e["indicator"] == ind["indicator"]]
        if ind["indicator"] in facts:
            f = facts[ind["indicator"]]
            cells.append({"indicator": ind["indicator"], "label": ind["label"], "state": "facts", "likelihood": None, "band": None, "confidence": None,
                          "confidence_basis": [f["basis"]], "evidence": [], "sources": [f["source"]], "facts": f["items"], "note": f.get("note")})
        elif ev:
            worst = max(ev, key=lambda e: SEV_RANK[e["severity"]])
            term = SEVERITY_TO_TERM[worst["severity"]]
            conf, basis = compute_confidence(ev, now.replace(tzinfo=None) if now.tzinfo else now)
            cells.append({"indicator": ind["indicator"], "label": ind["label"], "state": "reported", "likelihood": term, "band": ICD203_TERMS[term],
                          "confidence": conf, "confidence_basis": basis, "worst": worst["title"], "severity": worst["severity"],
                          "evidence": [{k: v for k, v in e.items() if k not in ("summary", "indicator")} for e in ev],
                          "sources": [s["name"] for s in ind["sources"]]})
        elif ind["covered"]:
            cells.append({"indicator": ind["indicator"], "label": ind["label"], "state": "quiet", "likelihood": None, "band": None, "confidence": "low",
                          "confidence_basis": [f"{', '.join(s['name'] for s in ind['sources'])} tasked; nothing reported within {req.radius_km:.0f} km in the window"],
                          "evidence": [], "sources": [s["name"] for s in ind["sources"]]})
        else:
            cells.append({"indicator": ind["indicator"], "label": ind["label"], "state": "gap", "likelihood": None, "band": None, "confidence": None,
                          "confidence_basis": ["no source connected"], "evidence": [], "sources": [],
                          "recommended": [s["name"] for s in ind["recommended"][:3]]})
    unclassified = [e for e in threats if e["indicator"] is None]
    counts = {s: sum(1 for c in cells if c["state"] == s) for s in ("reported", "quiet", "gap", "facts")}
    worst_cell = max((c for c in cells if c["state"] == "reported"), key=lambda c: SEV_RANK[c["severity"]], default=None)
    return {"requirement_id": req.id, "place": req.subject_name, "lat": req.lat, "lon": req.lon, "radius_km": req.radius_km,
            "window_from": R.iso(req.window_from), "window_to": R.iso(req.window_to), "cells": cells, "counts": counts,
            "unclassified": [{k: v for k, v in e.items() if k not in ("summary", "indicator")} for e in unclassified],
            "worst": {"indicator": worst_cell["indicator"], "label": worst_cell["label"], "likelihood": worst_cell["likelihood"], "band": worst_cell["band"],
                      "confidence": worst_cell["confidence"], "title": worst_cell["worst"]} if worst_cell else None,
            "known": counts["reported"] + counts["quiet"] + counts["facts"] > 0}


def heuristic_bluf(c: Dict[str, Any]) -> str:
    n = len(c["cells"]); k = c["counts"]
    head = f"{c['place']}: {k['reported']} of {n} indicators reported, {k['quiet']} watched and quiet, {k['gap']} not collected" + (f", {k['facts']} baseline." if k["facts"] else ".")
    hol = next((cell for cell in c["cells"] if cell["state"] == "facts" and cell["facts"]), None)
    if hol:
        head += f" {len(hol['facts'])} public holiday(s) in the window: " + ", ".join(f"{x['name']} ({x['date']})" for x in hol["facts"][:3]) + "."
    if c["worst"]:
        w = c["worst"]
        return head + f" The most serious reporting is {w['label'].lower()}: adverse impact is {w['likelihood']} ({w['band']}), {w['confidence']} confidence, from '{w['title']}'."
    if k["reported"] == 0 and k["quiet"] > 0:
        return head + " Nothing adverse reported by the tasked sources; the gaps are where the unknowns are."
    return head + " Nothing is known: this is a collection gap, not a finding."


async def draft_bluf(c: Dict[str, Any], purpose: str) -> Dict[str, Any]:
    if use_model() and c["worst"]:
        ev = [e for cell in c["cells"] for e in cell["evidence"]]
        d = await model_draft(c["place"], f"candidate for {purpose}; window {c['window_from']} → {c['window_to']}", ev)
        if d:
            return {"bluf": d["bluf"], "author": d["author"]}
    return {"bluf": heuristic_bluf(c), "author": "rule:heuristic-drafter"}


async def _baseline_facts(req: R.RequirementRow, cat: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Holidays in the window from Nager.Date, when the source is live and the place has a country. A failed fetch is
    reported as a failure, not as 'no holidays'."""
    src = next((c for c in cat if c["id"] == "wikidata"), None)
    if not src or not (src["enabled"] and src["configured"]) or not req.country: return {}
    from .baseline import holidays
    try:
        items = await holidays(req.country, req.window_from, req.window_to)
    except RuntimeError as e:
        return {"baseline": {"source": src["name"], "items": [], "basis": f"lookup failed: {e}", "note": "failed"}}
    return {"baseline": {"source": src["name"], "items": items, "basis": f"{src['name']} for {req.country}: {len(items)} public holiday(s) in the window", "note": None}}


async def build_product(session: AsyncSession, reqs: List[R.RequirementRow], purpose: str, now: datetime) -> Dict[str, Any]:
    cat = await R.catalog(session)
    candidates = []
    for req in reqs:
        plan = R.plan_for(req, cat)
        threats = await _threats_near(session, req, now)
        c = assess_candidate(req, plan, threats, now, await _baseline_facts(req, cat))
        c.update(await draft_bluf(c, purpose))
        candidates.append(c)
    indicators = []
    for c in candidates:
        for cell in c["cells"]:
            if cell["indicator"] not in indicators: indicators.append(cell["indicator"])
    gaps = sorted({cell["label"] for c in candidates for cell in c["cells"] if cell["state"] == "gap"})
    approvable = any(c["known"] for c in candidates)
    return {"purpose": purpose, "indicators": [{"id": i, "label": R.INDICATORS[i]["label"]} for i in indicators], "candidates": candidates,
            "gaps": gaps, "approvable": approvable, "authors": sorted({c["author"] for c in candidates}),
            "refusal": None if approvable else "No qualifying evidence for any candidate: nobody is watching these places. This is a collection gap, not a finding, and it cannot be approved.",
            "note": "Candidates are compared, not scored. Ranking is the reader's (Decision I)."}


def to_dict(row: AreaAssessmentRow) -> Dict[str, Any]:
    return {"id": row.id, "title": row.title, "purpose": row.purpose, "requirement_ids": json.loads(row.requirement_ids_json), "status": row.status,
            "author": row.author, "created_at": R.iso(row.created_at), "decided_by": row.decided_by, "decided_at": R.iso(row.decided_at), **json.loads(row.product_json)}


def new_row(title: str, purpose: str, req_ids: List[str], product: Dict[str, Any], now: datetime) -> AreaAssessmentRow:
    return AreaAssessmentRow(id=f"AREA-{uuid.uuid4().hex[:6].upper()}", title=title, purpose=purpose, requirement_ids_json=json.dumps(req_ids),
                             product_json=json.dumps(product), status="draft", author=" + ".join(product["authors"]) or "rule:refuse-to-assess", created_at=now)
