"""§5.10 #1–2 and §5.11 — organic reports, cases that live for months, and the case graph with provenance.

Everything the machine extracts is `suggested` until an analyst confirms it (Decision P). Opening a case on a person
needs the Battle Captain or the S2 lead, and every read of a case goes on the ledger (Decision Q). The link chart,
timeline, and time wheel are renderings of this graph — the data for all three is served here (§5.11)."""
import json
import os

from shared import settings
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import DateTime, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None

ENTITY_TYPES = ("person", "organization", "account", "phone", "email", "vehicle", "place", "device")
RELATIONSHIP_TYPES = ("associate", "member_of", "contacted", "funded", "located_at", "owns", "targets", "same_as")
STATUSES = ("suggested", "confirmed", "rejected")


# ---------------------------------------------------------------- rows

class ReportRow(Base):
    """SPOTREP / SITREP from our own people — the most reliable source there is, graded like any other (§5.10 #1)."""
    __tablename__ = "s2_reports"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, default="spot")  # spot | sitrep | note
    reported_by: Mapped[str] = mapped_column(String)  # a person id or a name
    reporter_role: Mapped[str] = mapped_column(String, default="")
    at: Mapped[datetime] = mapped_column(DateTime)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    place: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    case_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reliability: Mapped[str] = mapped_column(String, default="A")  # our own people
    credibility: Mapped[int] = mapped_column(Integer, default=2)  # probably true until corroborated
    source: Mapped[str] = mapped_column(String, default="ops")
    status: Mapped[str] = mapped_column(String, default="filed")  # filed | corroborated | linked | promoted | dismissed
    disposition: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # corroborate | link | promote | dismiss
    disposition_target_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    disposition_target_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    disposed_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    disposed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    disposition_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    filed_at: Mapped[datetime] = mapped_column(DateTime)


class CaseRow(Base):
    __tablename__ = "s2_cases"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String, default="general")  # general | person | site | actor
    subject_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # wall entity, if any
    subject_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="open")  # open | closed
    opened_by: Mapped[str] = mapped_column(String)
    opened_at: Mapped[datetime] = mapped_column(DateTime)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    access_roles: Mapped[str] = mapped_column(String, default="battle_captain,analyst")  # who may read


class EntityRow(Base):
    __tablename__ = "s2_entities"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")
    attributes_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String, default="suggested")
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    merged_into: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decided_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class RelationshipRow(Base):
    __tablename__ = "s2_relationships"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[str] = mapped_column(String, index=True)
    from_id: Mapped[str] = mapped_column(String)
    to_id: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    first_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="suggested")
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    decided_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class CaseEventRow(Base):
    __tablename__ = "s2_case_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[str] = mapped_column(String, index=True)
    at: Mapped[datetime] = mapped_column(DateTime)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    place: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String, default="observation")
    summary: Mapped[str] = mapped_column(Text)
    participants_json: Mapped[str] = mapped_column(Text, default="[]")  # entity ids
    status: Mapped[str] = mapped_column(String, default="suggested")
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    decided_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# ---------------------------------------------------------------- evidence

def evidence_from_report(r: ReportRow, quote: str) -> Dict[str, Any]:
    return {"report_id": r.id, "quote": quote[:240], "source": r.source, "reliability": r.reliability, "credibility": r.credibility, "at": iso(r.at)}


# ---------------------------------------------------------------- extraction — suggests, never asserts

HANDLE = re.compile(r"(?<![\w@])@([A-Za-z0-9_]{3,30})")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PLATE = re.compile(r"\b(?:plate|license|licence|reg(?:istration)?)\s*[:#]?\s*([A-Z0-9]{2,4}[- ]?[A-Z0-9]{2,4})\b", re.I)
NAME = re.compile(r"\b((?:[A-Z][a-z]+|[A-Z]\.)(?:\s(?:[A-Z][a-z]+|[A-Z]\.)){1,2})\b")  # "Marcus Vane", "M. Vane", "J. R. Ortiz"
NOT_NAMES = {"North America", "South America", "United States", "New York", "San Francisco", "Battle Captain", "Security Officer",
             "Executive Protection", "Watch Floor", "Market Street", "Front Desk", "North Gate", "South Gate"}
LEAD_WORDS = {"Observed", "Saw", "Seen", "Noted", "Spotted", "Reported", "Both", "He", "She", "They", "The", "This", "That", "Our", "Their", "Also", "Then",
              "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "At", "On", "In"}
ASSOC = re.compile(r"\b(with|alongside|together with|accompanied by|meeting|met|talking to|speaking with)\b", re.I)
TIME_HINT = re.compile(r"\b(\d{1,2}:\d{2})\b")


def heuristic_extract(report: ReportRow, known_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Cheap, honest extraction for when there is no model: handles, phones, emails, plates, capitalized names, and an
    `associate` link between two people named in the same sentence with an association word. Every item is cited."""
    text = report.text
    ents: List[Dict[str, Any]] = []
    seen = set()
    def add(t, name, sentence):
        key = (t, name.lower())
        if key in seen: return
        seen.add(key); ents.append({"type": t, "name": name, "evidence": evidence_from_report(report, sentence)})
    sentences = re.split(r"(?<!\b[A-Z]\.)(?<=[.!?])\s+", text)  # don't split on an initial ("M. Vane")
    for s in sentences:
        for m in HANDLE.finditer(s): add("account", "@" + m.group(1), s)
        for m in EMAIL.finditer(s): add("email", m.group(0), s)
        for m in PHONE.finditer(s):
            digits = re.sub(r"\D", "", m.group(0))
            if 8 <= len(digits) <= 15 and not TIME_HINT.fullmatch(m.group(0).strip()): add("phone", m.group(0).strip(), s)
        for m in PLATE.finditer(s): add("vehicle", m.group(1).upper(), s)
        for m in NAME.finditer(s):
            words = m.group(1).split()
            while words and words[0] in LEAD_WORDS:  # "Observed Marcus Vane" → "Marcus Vane"
                words = words[1:]
            if len(words) < 2: continue
            n = " ".join(words)
            if n in NOT_NAMES: continue
            add("person", n, s)
        for kn in known_names:
            if kn.lower() in s.lower(): add("person", kn, s)
    rels: List[Dict[str, Any]] = []
    for s in sentences:
        people = [e for e in ents if e["type"] in ("person", "account") and e["name"].lower() in s.lower()]
        if len(people) >= 2 and ASSOC.search(s):
            for i in range(len(people)):
                for j in range(i + 1, len(people)):
                    rels.append({"from": people[i]["name"], "to": people[j]["name"], "type": "associate", "evidence": evidence_from_report(report, s)})
    events = [{"at": iso(report.at), "lat": report.lat, "lon": report.lon, "place": report.place, "type": report.kind,
               "summary": sentences[0][:200] if sentences else text[:200], "participants": [e["name"] for e in ents if e["type"] in ("person", "account")][:6],
               "evidence": evidence_from_report(report, sentences[0] if sentences else text)}]
    return {"entities": ents, "relationships": rels, "events": events}


SYSTEM = """You are an S2 analyst's assistant reading an operations report. Extract ONLY what the text supports.
Return a single JSON object: {"entities":[{"type":one of %s,"name":str,"quote":str}],
"relationships":[{"from":name,"to":name,"type":one of %s,"quote":str}],
"events":[{"summary":str,"participants":[names],"quote":str}]}
Every item must carry the exact quote from the report that supports it. Do not infer identities, do not merge people,
do not add anything the text does not say. Everything you return will be shown to a human as a suggestion.""" % (list(ENTITY_TYPES), list(RELATIONSHIP_TYPES))


async def model_extract(report: ReportRow) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        return None
    try:
        client = AsyncAnthropic(api_key=settings.get("ANTHROPIC_API_KEY"))
        resp = await client.messages.create(model=settings.get("TOC_MODEL") or "claude-opus-5", max_tokens=2048, system=SYSTEM,
                                            messages=[{"role": "user", "content": report.text}])
        if resp.stop_reason == "refusal":
            return None
        text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
        data = json.loads(text[text.find("{"): text.rfind("}") + 1])
        ents = [{"type": e["type"] if e.get("type") in ENTITY_TYPES else "person", "name": str(e["name"]).strip(), "evidence": evidence_from_report(report, str(e.get("quote", "")))}
                for e in data.get("entities", []) if e.get("name")]
        rels = [{"from": r["from"], "to": r["to"], "type": r["type"] if r.get("type") in RELATIONSHIP_TYPES else "associate", "evidence": evidence_from_report(report, str(r.get("quote", "")))}
                for r in data.get("relationships", []) if r.get("from") and r.get("to")]
        evs = [{"at": iso(report.at), "lat": report.lat, "lon": report.lon, "place": report.place, "type": report.kind, "summary": str(e.get("summary", ""))[:200],
                "participants": [str(p) for p in e.get("participants", [])][:6], "evidence": evidence_from_report(report, str(e.get("quote", "")))} for e in data.get("events", [])]
        return {"entities": ents, "relationships": rels, "events": evs or heuristic_extract(report, [])["events"]}
    except Exception:  # noqa: BLE001
        return None


def use_model() -> bool:
    return os.environ.get("TOC_DRAFTER", "").lower() == "ai" or bool(settings.get("ANTHROPIC_API_KEY"))


# ---------------------------------------------------------------- filing into a case

async def file_report_into_case(session: AsyncSession, report: ReportRow, case: CaseRow, known_names: List[str]) -> Dict[str, int]:
    """Extract from the report and add everything as `suggested`. Existing confirmed entities with the same name gain
    evidence instead of being duplicated — that is alias resolution's simplest form."""
    ex = (await model_extract(report)) if use_model() else None
    if ex is None:
        ex = heuristic_extract(report, known_names)
    existing = {(e.type, e.name.lower()): e for e in (await session.execute(select(EntityRow).where(EntityRow.case_id == case.id, EntityRow.merged_into.is_(None)))).scalars()}
    by_name: Dict[str, EntityRow] = {}
    created = {"entities": 0, "relationships": 0, "events": 0, "evidence_added": 0}
    for e in ex["entities"]:
        key = (e["type"], e["name"].lower())
        row = existing.get(key)
        if row:
            ev = json.loads(row.evidence_json); ev.append(e["evidence"]); row.evidence_json = json.dumps(ev); created["evidence_added"] += 1
        else:
            row = EntityRow(id=f"ent_{uuid.uuid4().hex[:8]}", case_id=case.id, type=e["type"], name=e["name"], evidence_json=json.dumps([e["evidence"]]))
            session.add(row); existing[key] = row; created["entities"] += 1
        by_name[e["name"].lower()] = row
    await session.flush()
    for r in ex["relationships"]:
        a, b = by_name.get(r["from"].lower()), by_name.get(r["to"].lower())
        if not a or not b or a.id == b.id: continue
        dup = (await session.execute(select(RelationshipRow).where(RelationshipRow.case_id == case.id, RelationshipRow.from_id == a.id, RelationshipRow.to_id == b.id, RelationshipRow.type == r["type"]))).scalar_one_or_none()
        if dup:
            ev = json.loads(dup.evidence_json); ev.append(r["evidence"]); dup.evidence_json = json.dumps(ev); dup.last_seen = report.at; created["evidence_added"] += 1
        else:
            session.add(RelationshipRow(id=f"rel_{uuid.uuid4().hex[:8]}", case_id=case.id, from_id=a.id, to_id=b.id, type=r["type"], first_seen=report.at, last_seen=report.at, evidence_json=json.dumps([r["evidence"]])))
            created["relationships"] += 1
    for ev in ex["events"]:
        parts = [by_name[p.lower()].id for p in ev.get("participants", []) if p.lower() in by_name]
        session.add(CaseEventRow(id=f"cev_{uuid.uuid4().hex[:8]}", case_id=case.id, at=datetime.fromisoformat(ev["at"].replace("Z", "")) if ev.get("at") else report.at,
                                 lat=ev.get("lat"), lon=ev.get("lon"), place=ev.get("place"), type=ev.get("type", "observation"), summary=ev["summary"],
                                 participants_json=json.dumps(parts), evidence_json=json.dumps([ev["evidence"]])))
        created["events"] += 1
    await session.commit()
    return created


# ---------------------------------------------------------------- serialization and the three views

def entity_dict(e: EntityRow) -> Dict[str, Any]:
    return {"id": e.id, "type": e.type, "name": e.name, "aliases": json.loads(e.aliases_json or "[]"), "attributes": json.loads(e.attributes_json or "{}"),
            "status": e.status, "evidence": json.loads(e.evidence_json or "[]"), "merged_into": e.merged_into, "decided_by": e.decided_by, "decided_at": iso(e.decided_at)}

def rel_dict(r: RelationshipRow) -> Dict[str, Any]:
    ev = json.loads(r.evidence_json or "[]")
    best = min((x.get("reliability", "F") for x in ev), default="F")
    return {"id": r.id, "from": r.from_id, "to": r.to_id, "type": r.type, "first_seen": iso(r.first_seen), "last_seen": iso(r.last_seen), "status": r.status,
            "evidence": ev, "grade": f"{best}{min((x.get('credibility', 6) for x in ev), default=6)}", "decided_by": r.decided_by}

def event_dict(v: CaseEventRow) -> Dict[str, Any]:
    return {"id": v.id, "at": iso(v.at), "lat": v.lat, "lon": v.lon, "place": v.place, "type": v.type, "summary": v.summary,
            "participants": json.loads(v.participants_json or "[]"), "status": v.status, "evidence": json.loads(v.evidence_json or "[]"), "decided_by": v.decided_by}

def report_dict(r: ReportRow) -> Dict[str, Any]:
    return {"id": r.id, "kind": r.kind, "reported_by": r.reported_by, "reporter_role": r.reporter_role, "at": iso(r.at), "lat": r.lat, "lon": r.lon, "place": r.place,
            "text": r.text, "case_id": r.case_id, "reliability": r.reliability, "credibility": r.credibility, "grade": f"{r.reliability}{r.credibility}", "source": r.source,
            "status": r.status, "disposition": r.disposition, "disposition_target_type": r.disposition_target_type, "disposition_target_id": r.disposition_target_id,
            "disposed_by": r.disposed_by, "disposed_at": iso(r.disposed_at), "disposition_note": r.disposition_note, "filed_at": iso(r.filed_at)}

def case_dict(c: CaseRow, counts: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    return {"id": c.id, "title": c.title, "kind": c.kind, "subject_type": c.subject_type, "subject_id": c.subject_id, "summary": c.summary, "status": c.status,
            "opened_by": c.opened_by, "opened_at": iso(c.opened_at), "closed_at": iso(c.closed_at), "access_roles": c.access_roles.split(","), **(counts or {})}


async def case_graph(session: AsyncSession, case_id: str, include: Tuple[str, ...] = ("suggested", "confirmed")) -> Dict[str, Any]:
    all_ents = (await session.execute(select(EntityRow).where(EntityRow.case_id == case_id, EntityRow.merged_into.is_(None)))).scalars().all()
    ents = [e for e in all_ents if e.status in include]
    rels = [r for r in (await session.execute(select(RelationshipRow).where(RelationshipRow.case_id == case_id))).scalars() if r.status in include]
    evs = [v for v in (await session.execute(select(CaseEventRow).where(CaseEventRow.case_id == case_id))).scalars() if v.status in include]
    # an edge is filtered on its own status; its ends only have to exist and not be rejected (a suggested link between
    # two confirmed people belongs in the queue; a confirmed link to a rejected entity does not belong anywhere)
    ids = {e.id for e in all_ents if e.status != "rejected" and (e.status in include or e.status == "confirmed")}
    return {"entities": [entity_dict(e) for e in ents], "relationships": [rel_dict(r) for r in rels if r.from_id in ids and r.to_id in ids],
            "events": sorted((event_dict(v) for v in evs), key=lambda x: x["at"] or "")}


def time_wheel(events: List[Dict[str, Any]], entity_id: Optional[str] = None) -> Dict[str, Any]:
    """Pattern of life: activity by hour-of-day × day-of-week, from confirmed-or-suggested events. 7 rows × 24 columns.
    The sentence names the hour when hours repeat, and the day too when a day×hour cell repeats."""
    grid = [[0] * 24 for _ in range(7)]
    hours = [0] * 24
    n = 0
    for v in events:
        if entity_id and entity_id not in v["participants"]: continue
        if not v["at"]: continue
        t = datetime.fromisoformat(v["at"].replace("Z", ""))
        grid[t.weekday()][t.hour] += 1; hours[t.hour] += 1; n += 1
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    cell = max(((d, h, grid[d][h]) for d in range(7) for h in range(24)), key=lambda x: x[2], default=(0, 0, 0))
    hour = max(range(24), key=lambda h: hours[h]) if n else 0
    if n and cell[2] > 1:
        pattern = f"activity clusters {days[cell[0]]} around {cell[1]:02d}:00 UTC ({cell[2]} of {n} events)"
    elif n and hours[hour] > 1:
        pattern = f"activity clusters around {hour:02d}:00 UTC ({hours[hour]} of {n} events, different days)"
    else:
        pattern = "no pattern yet — too few events"
    return {"entity_id": entity_id, "events": n, "grid": grid, "days": days, "hours": hours,
            "peak": {"day": days[cell[0]], "hour": hour, "count": hours[hour]} if n else None, "pattern": pattern}


def link_summary(graph: Dict[str, Any]) -> List[str]:
    """The judgments a link chart would show, as sentences with the edge grade — the analysis without the picture."""
    names = {e["id"]: e["name"] for e in graph["entities"]}
    deg = Counter()
    for r in graph["relationships"]:
        deg[r["from"]] += 1; deg[r["to"]] += 1
    out = []
    for eid, d in deg.most_common(3):
        out.append(f"{names.get(eid, eid)} is linked to {d} other entit{'y' if d == 1 else 'ies'} in this case")
    for r in graph["relationships"][:5]:
        out.append(f"{names.get(r['from'])} — {r['type']} — {names.get(r['to'])} [{r['grade']}, {r['status']}]")
    return out
