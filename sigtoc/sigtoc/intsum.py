"""§5.6 INTSUM — the daily diff across every active requirement. Decision G: drafted at a fixed time, released by the
Battle Captain. It is not written from scratch: it is what the requirements, collectors, cases, and products produced
since the last INTSUM, in a fixed order a Battle Captain reads in under five minutes. Nothing to report is said as NSTR."""
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base
from shared.db_models import LedgerEventRow
from . import requirements as R
from .analysis.wall_drafter import _haversine as haversine_km
from .area import AreaAssessmentRow
from .cases import CaseRow, ReportRow

DRAFT_HOUR_UTC = int(os.environ.get("TOC_INTSUM_HOUR_UTC", "5"))  # before the Dublin day watch takes over (§3.1)
DEFAULT_PERIOD_H = 24


class IntsumRow(Base):
    __tablename__ = "s2_intsums"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    period_from: Mapped[datetime] = mapped_column(DateTime)
    period_to: Mapped[datetime] = mapped_column(DateTime)
    product_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft | released
    drafted_by: Mapped[str] = mapped_column(String, default="rule:intsum-drafter")
    drafted_at: Mapped[datetime] = mapped_column(DateTime)
    released_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


def _ev(r: LedgerEventRow) -> Dict[str, Any]:
    return {"id": r.event_id, "at": R.iso(r.timestamp), "type": r.event_type, "actor": r.actor_id, "subject": r.content_id, "summary": r.reason, "old": r.old_state, "new": r.new_state}


async def latest(session: AsyncSession) -> Optional[IntsumRow]:
    return (await session.execute(select(IntsumRow).order_by(IntsumRow.period_to.desc()).limit(1))).scalars().first()


async def build(session: AsyncSession, period_from: datetime, period_to: datetime) -> Dict[str, Any]:
    from coptoc.db_models import ThreatRow  # the wall's threat table, same DB
    reqs = (await session.execute(select(R.RequirementRow))).scalars().all()
    active = [r for r in reqs if r.status == "active"]
    cat = await R.catalog(session)
    ev = (await session.execute(select(LedgerEventRow).where((LedgerEventRow.event_type.like("cop.%") | LedgerEventRow.event_type.like("s2.%")),
                                                           LedgerEventRow.timestamp > period_from, LedgerEventRow.timestamp <= period_to).order_by(LedgerEventRow.id))).scalars().all()
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for r in ev: by_type.setdefault(r.event_type, []).append(_ev(r))
    T = lambda *types: [e for t in types for e in by_type.get(t, [])]

    # 1. Requirements — what the wall asked for
    req_changes = {"created": [e for e in T("s2.requirement.created")], "updated": T("s2.requirement.updated"),
                   "expired": [{"id": r.id, "subject": r.subject_name} for r in reqs if r.status == "expired" and r.updated_at and period_from < r.updated_at <= period_to],
                   "answered": [{"id": r.id, "subject": r.subject_name} for r in reqs if r.status == "answered" and r.updated_at and period_from < r.updated_at <= period_to],
                   "synced": T("s2.requirements.synced")}
    # 2. New threats in the period, attributed to the requirements they fall inside
    threats = [t for t in (await session.execute(select(ThreatRow).where(ThreatRow.observed_at > period_from, ThreatRow.observed_at <= period_to))).scalars()]
    new_threats = []
    for t in sorted(threats, key=lambda t: ({"low": 0, "moderate": 1, "elevated": 2, "critical": 3}[t.severity]), reverse=True):
        hits = [r for r in active if (getattr(t, "scope", "point") == "country" and t.country and r.country == t.country) or haversine_km(r.lat, r.lon, t.lat, t.lon) <= r.radius_km + t.radius_km]
        new_threats.append({"id": t.id, "title": t.title, "severity": t.severity, "source": t.source, "confidence": t.confidence, "observed_at": R.iso(t.observed_at), "country": t.country, "scope": getattr(t, "scope", "point"),
                            "synthetic": t.synthetic, "requirements": [{"id": r.id, "subject": r.subject_name, "priority": r.priority} for r in sorted(hits, key=lambda r: r.priority)][:6]})
    # 3. What changed on the wall because of intel: confirmed links, posture, roll calls
    wall = {"links": T("cop.threat.link_confirmed", "cop.threat.link_removed"), "posture": T("cop.location.posture"),
            "roll_calls": T("cop.incident.opened", "cop.incident.closed")}
    # 4. Organic reporting and cases
    reports = [{"id": r.id, "kind": r.kind, "by": r.reported_by, "place": r.place, "grade": f"{r.reliability}{r.credibility}", "text": r.text[:160], "case_id": r.case_id}
               for r in (await session.execute(select(ReportRow).where(ReportRow.filed_at > period_from, ReportRow.filed_at <= period_to).order_by(ReportRow.at))).scalars()]
    cases = {"opened": T("s2.case.opened"), "closed": T("s2.case.closed"), "decisions": len(T("s2.case.confirmed", "s2.case.rejected", "s2.case.merged"))}
    open_cases = (await session.execute(select(CaseRow).where(CaseRow.status == "open"))).scalars().all()
    # 5. Products
    products = {"assessments": T("cop.assessment.drafted", "cop.assessment.status"), "area_assessments": T("s2.area.drafted", "s2.area.status")}
    pending_area = [{"id": a.id, "title": a.title, "status": a.status} for a in (await session.execute(select(AreaAssessmentRow).where(AreaAssessmentRow.status != "approved"))).scalars()]
    # 6. Collection — who reported, who is broken, where the gaps are
    collection = {"runs": T("cop.intel.refresh", "cop.intel.refresh_failed"), "source_changes": T("s2.source.updated"),
                  "sources": [{"id": c["id"], "name": c["name"], "last_collected_at": c.get("last_collected_at"), "last_result": c.get("last_result")} for c in cat if c["enabled"] and c["configured"]]}
    cov = R.coverage_summary(active, cat) if hasattr(R, "coverage_summary") else None
    gaps: Dict[str, int] = {}
    for r in active:
        for g in R.plan_for(r, cat)["gaps"]: gaps[g] = gaps.get(g, 0) + 1
    gaps_ranked = [{"indicator": k, "label": R.INDICATORS[k]["label"], "requirements_affected": n} for k, n in sorted(gaps.items(), key=lambda kv: -kv[1])]

    significant = len(new_threats) + len(wall["links"]) + len(wall["posture"]) + len(wall["roll_calls"]) + len(reports) + len(cases["opened"]) + len(products["assessments"]) + len(products["area_assessments"])
    nstr = significant == 0
    headline = ("NSTR — nothing significant to report across %d active requirements." % len(active)) if nstr else \
        (f"{len(new_threats)} new threat(s)" + (f", worst {new_threats[0]['severity']}" if new_threats else "") + f"; {len(wall['links'])} link change(s); {len(wall['posture'])} posture change(s); "
         f"{len(reports)} organic report(s); {len(products['assessments']) + len(products['area_assessments'])} product event(s); {len(gaps_ranked)} open collection gap(s).")
    return {"period": {"from": R.iso(period_from), "to": R.iso(period_to), "hours": round((period_to - period_from).total_seconds() / 3600, 1)},
            "headline": headline, "nstr": nstr, "requirements": {"active": len(active), "standing": sum(1 for r in active if r.kind == "standing"), "directed": sum(1 for r in active if r.kind == "directed"), **req_changes},
            "new_threats": new_threats, "wall": wall, "reports": reports, "cases": {**cases, "open": len(open_cases)},
            "products": {**products, "pending_area_assessments": pending_area}, "collection": {**collection, "gaps": gaps_ranked, "coverage": cov},
            "event_count": len(ev), "structure": ["headline", "requirements", "new_threats", "wall", "reports_and_cases", "products", "collection"]}


async def draft(session: AsyncSession, now: datetime, period_from: Optional[datetime] = None) -> IntsumRow:
    prev = await latest(session)
    start = period_from or (prev.period_to if prev else now - timedelta(hours=DEFAULT_PERIOD_H))
    product = await build(session, start, now)
    row = IntsumRow(id=f"INTSUM-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}", period_from=start, period_to=now, product_json=json.dumps(product), drafted_at=now)
    session.add(row); await session.commit()
    return row


async def due(session: AsyncSession, now: datetime) -> bool:
    """Decision G: one draft a day at the fixed hour. True when today's has not been drafted yet and the hour has passed."""
    if now.hour < DRAFT_HOUR_UTC: return False
    prev = await latest(session)
    return not prev or prev.period_to.date() < now.date()


def to_dict(row: IntsumRow) -> Dict[str, Any]:
    return {"id": row.id, "status": row.status, "drafted_by": row.drafted_by, "drafted_at": R.iso(row.drafted_at), "released_by": row.released_by, "released_at": R.iso(row.released_at),
            "notes": row.notes, **json.loads(row.product_json)}
