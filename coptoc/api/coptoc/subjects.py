"""§5.6b the subject of concern (2026-09-20): the file the desk keeps on a *person* directed at us.

§5.6a rates a **place** — what the analyst judges about Lisbon, about the FARP. This is its sibling and it rates a
**person**: the individual who keeps turning up at the north gate, who writes to the CEO, who has found the
residence. A protective-intelligence desk lives on that file, and until now TOC had nowhere to put it — a threat in
`cop_threats` must carry a lat, a lon and a radius, and a person fixated on a principal does not have one. The
seeded "North gate loiterer" case shows the strain: it is `kind="person"` filed against `loc_sf`, because the only
place to put a man was a circle drawn around a building.

So the subject gets its own row rather than a nullable threat: proximity math in `service.py` runs `haversine_km`
over every threat, and a threat without coordinates would have to be special-cased everywhere it is read.

**The discipline is §5.6a's, unchanged.** A fixed indicator list, green / amber / red per indicator, each with one
line that says why, owned and dated. **Nothing is scored or summed** (Decision I): the picture is the row of ratings
and the worst of them, and the reader ranks. A new assessment supersedes the last, which stays as history.

**Where the indicators come from, and what they are not.** They are plain-language categories of concern drawn from
the open behavioral-threat-assessment literature — grievance, fixation, identification, leakage, a directly
communicated threat, research and preparation, approach, means, a change in tempo, and the stabilizers holding a
person in place. TOC does **not** implement, reproduce or score any proprietary instrument (WAVR-21, TRAP-18 and
the like): there is no item wording from one here, no total, and no band. An analyst who uses such an instrument
records its result as their own judgment in the note, the way they would any other source. The list is
configuration like §5.6a's — `TOC_SUBJECT_INDICATORS` overrides the profile's default.

**The mailroom** (`ContactRow`) is the other half: what arrives naming a principal — an email, a DM, a letter, a
call, a contact form, someone at the desk. It is graded when it lands, triaged for how the threat is expressed
(directed / conditional / veiled / none), and filed onto a subject or left in the inbox. An unattributed message
**stays unattributed**: nothing guesses a message onto a folder, the same rule §5.5 applies to everything else.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared import settings
from shared.database import Base

RATINGS = ("green", "amber", "red", "unknown")
RANK = {"unknown": 0, "green": 1, "amber": 2, "red": 3}

STATUSES = ("open", "monitoring", "referred", "closed")
CHANNELS = ("email", "dm", "letter", "phone", "form", "in_person", "other")
# How the threat is expressed, if it is expressed at all. The wording, not the analyst's view of the risk:
# a veiled message from someone at the gate outranks a directed one from another continent, and the folder says which.
DIRECTNESS = ("directed", "conditional", "veiled", "none")
TRIAGE = ("new", "assessed", "filed", "dismissed")
STALE_DAYS = 30  # same review clock as §5.6a: an open subject nobody has reassessed in a month is an exception

# The questions a desk asks of a person, by profile. Labels are the words on the wall; ids are stable keys.
INDICATORS: Dict[str, List[tuple]] = {
    "military": [
        ("grievance", "Grievance & demand"), ("association", "Association with hostile networks"),
        ("access", "Access to people, weapons or information"), ("surveillance", "Hostile reconnaissance of our sites or routes"),
        ("leakage", "Leakage to third parties"), ("threat", "Directly communicated threat or intent"),
        ("pathway", "Preparation & rehearsal"), ("approach", "Proximity to the force"),
        ("pattern", "Change in pattern of life"), ("stabilizers", "Stabilizers & constraints"),
    ],
    "corporate": [
        ("grievance", "Grievance & demand"), ("fixation", "Fixation & preoccupation"),
        ("identification", "Identification with violence"), ("leakage", "Leakage to third parties"),
        ("threat", "Directly communicated threat"), ("pathway", "Research, planning & preparation"),
        ("approach", "Approach & proximity"), ("means", "Means & capability"),
        ("escalation", "Change in tempo or intensity"), ("stabilizers", "Stabilizers & constraints"),
    ],
}


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:32] or "indicator"


def indicators(profile: str) -> List[Dict[str, str]]:
    """The indicator list this deployment rates a person on — `TOC_SUBJECT_INDICATORS` ("id=Label,Label,…") if set, else the profile's default."""
    raw = (settings.get("TOC_SUBJECT_INDICATORS") or "").strip()
    if raw:
        out_ = []
        for part in raw.split(","):
            part = part.strip()
            if not part: continue
            key, _, label = part.partition("=")
            out_.append({"id": _slug(key) if label else _slug(part), "label": (label or part).strip()})
        if out_: return out_
    return [{"id": i, "label": l} for i, l in INDICATORS.get(profile, INDICATORS["corporate"])]


class SubjectRow(Base):
    """The folder. It persists; the assessments under it version (`SubjectRatingRow`)."""
    __tablename__ = "cop_subjects"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)                                       # what we call him; may be a description before it is a name
    aliases_json: Mapped[str] = mapped_column(Text, default="[]")                   # handles, plates, phone numbers — what the reports gave us
    status: Mapped[str] = mapped_column(String, default="open")                     # open | monitoring | referred | closed
    summary: Mapped[str] = mapped_column(Text, default="")
    principal_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)   # the person he is directed at, when it is one person
    principal_name: Mapped[str] = mapped_column(String, default="")
    location_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)    # the site he keeps turning up at
    case_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)        # the S2 case that holds the evidence graph
    # Last known position, for the map. Optional on purpose: most subjects are not anywhere we know.
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_seen_place: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    opened_by: Mapped[str] = mapped_column(String)
    opened_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referred_to: Mapped[Optional[str]] = mapped_column(String, nullable=True)       # who it was handed to — law enforcement, counsel, HR
    referred_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    access_roles: Mapped[str] = mapped_column(String, default="battle_captain,analyst,security")


class SubjectRatingRow(Base):
    """One dated assessment of one subject. The current one is the assessment; the rest are how it got here."""
    __tablename__ = "cop_subject_ratings"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    subject_id: Mapped[str] = mapped_column(String, index=True)
    ratings_json: Mapped[str] = mapped_column(Text, default="[]")                   # [{indicator, label, rating, note}]
    summary: Mapped[str] = mapped_column(Text, default="")                          # the analyst's paragraph, if they wrote one
    assessed_by: Mapped[str] = mapped_column(String)
    assessed_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String, default="current")                  # current | superseded
    supersedes: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class ContactRow(Base):
    """The mailroom. Something arrived naming one of ours. Graded when it lands, filed onto a subject or left in the inbox."""
    __tablename__ = "cop_subject_contacts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    subject_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)  # null = in the inbox, unattributed
    channel: Mapped[str] = mapped_column(String, default="email")
    received_at: Mapped[datetime] = mapped_column(DateTime)
    filed_at: Mapped[datetime] = mapped_column(DateTime)
    from_label: Mapped[str] = mapped_column(String, default="")                     # the address, handle, number or return address as it arrived
    principal_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    principal_name: Mapped[str] = mapped_column(String, default="")                 # who it names
    text: Mapped[str] = mapped_column(Text)
    directness: Mapped[str] = mapped_column(String, default="none")                 # directed | conditional | veiled | none
    triage: Mapped[str] = mapped_column(String, default="new")                      # new | assessed | filed | dismissed
    reliability: Mapped[str] = mapped_column(String, default="F")                   # A–F; an unknown sender cannot be judged
    credibility: Mapped[int] = mapped_column(Integer, default=6)                    # 1–6; 6 = cannot be judged, the §5.11 default for one uncorroborated item
    received_by: Mapped[str] = mapped_column(String, default="")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)                # the analyst's line on it
    triaged_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    triaged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def normalize(ratings: List[Dict[str, Any]], inds: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """One entry per configured indicator, in the configured order; anything the analyst did not rate is `unknown`."""
    by = {r.get("indicator"): r for r in ratings}
    out_ = []
    for i in inds:
        r = by.get(i["id"], {})
        rating = r.get("rating") if r.get("rating") in RATINGS else "unknown"
        out_.append({"indicator": i["id"], "label": i["label"], "rating": rating, "note": (r.get("note") or "").strip()})
    return out_


def rating_out(row: SubjectRatingRow, now: datetime) -> Dict[str, Any]:
    ratings = json.loads(row.ratings_json or "[]")
    counts = {k: sum(1 for r in ratings if r["rating"] == k) for k in RATINGS}
    rated = [r for r in ratings if r["rating"] != "unknown"]
    worst = max(rated, key=lambda r: RANK[r["rating"]]) if rated else None
    return {"id": row.id, "subject_id": row.subject_id, "ratings": ratings, "summary": row.summary, "assessed_by": row.assessed_by,
            "assessed_at": _iso(row.assessed_at), "updated_at": _iso(row.updated_at), "status": row.status, "supersedes": row.supersedes,
            "counts": counts, "worst": worst["rating"] if worst else "unknown", "worst_indicator": worst["label"] if worst else None,
            "age_days": round((now - row.assessed_at).total_seconds() / 86400, 1), "stale": (now - row.assessed_at).days >= STALE_DAYS}


def contact_out(row: ContactRow) -> Dict[str, Any]:
    return {"id": row.id, "subject_id": row.subject_id, "channel": row.channel, "received_at": _iso(row.received_at), "filed_at": _iso(row.filed_at),
            "from_label": row.from_label, "principal_id": row.principal_id, "principal_name": row.principal_name, "text": row.text,
            "directness": row.directness, "triage": row.triage, "reliability": row.reliability, "credibility": row.credibility,
            "received_by": row.received_by, "note": row.note, "triaged_by": row.triaged_by, "triaged_at": _iso(row.triaged_at)}


def out(row: SubjectRow, rating: Optional[SubjectRatingRow], contacts: List[ContactRow], now: datetime) -> Dict[str, Any]:
    """The folder as the wall reads it: who he is, the current assessment, and what has arrived from him."""
    r = rating_out(rating, now) if rating is not None else None
    cs = sorted(contacts, key=lambda c: c.received_at, reverse=True)
    worst_directness = next((d for d in DIRECTNESS if any(c.directness == d for c in cs)), "none")
    return {"id": row.id, "name": row.name, "aliases": json.loads(row.aliases_json or "[]"), "status": row.status, "summary": row.summary,
            "principal_id": row.principal_id, "principal_name": row.principal_name, "location_id": row.location_id, "case_id": row.case_id,
            "last_seen_at": _iso(row.last_seen_at), "last_seen_place": row.last_seen_place, "lat": row.lat, "lon": row.lon,
            "opened_by": row.opened_by, "opened_at": _iso(row.opened_at), "updated_at": _iso(row.updated_at),
            "closed_at": _iso(row.closed_at), "closed_reason": row.closed_reason, "referred_to": row.referred_to, "referred_at": _iso(row.referred_at),
            "assessment": r,
            # No score anywhere. `worst` is the worst rated indicator of the current assessment, nothing more (Decision I).
            "worst": r["worst"] if r else "unknown", "worst_indicator": r["worst_indicator"] if r else None,
            "counts": r["counts"] if r else {k: 0 for k in RATINGS},
            "assessed_at": r["assessed_at"] if r else None, "age_days": r["age_days"] if r else None,
            # An open subject with no current assessment is an exception in its own right, not a green one.
            "unassessed": r is None, "stale": bool(r and r["stale"]) if row.status in ("open", "monitoring") else False,
            "contacts": [contact_out(c) for c in cs], "contact_count": len(cs),
            "new_contacts": sum(1 for c in cs if c.triage == "new"), "worst_directness": worst_directness,
            "last_contact_at": _iso(cs[0].received_at) if cs else None}


def compact(s: Dict[str, Any]) -> Dict[str, Any]:
    """What a person, a site or the posture bar carries about a subject: enough to draw the strip and say who said so."""
    return {"id": s["id"], "name": s["name"], "status": s["status"], "worst": s["worst"], "worst_indicator": s["worst_indicator"],
            "counts": s["counts"], "strip": [r["rating"] for r in (s["assessment"]["ratings"] if s["assessment"] else [])],
            "assessed_at": s["assessed_at"], "age_days": s["age_days"], "stale": s["stale"], "unassessed": s["unassessed"],
            "worst_directness": s["worst_directness"], "contact_count": s["contact_count"], "new_contacts": s["new_contacts"],
            "last_seen_place": s["last_seen_place"], "last_contact_at": s["last_contact_at"]}


def summary_counts(subjects: List[Dict[str, Any]]) -> Dict[str, int]:
    """The posture bar's line: how many files are open, how many are red, how many nobody has looked at this month."""
    live = [s for s in subjects if s["status"] in ("open", "monitoring")]
    # No "inbox" here on purpose: the inbox is what has been attributed to *nobody*, so it is not a property of the
    # files. The snapshot counts it separately (`summary.subject_inbox`).
    return {"open": len(live), "red": sum(1 for s in live if s["worst"] == "red"),
            "unassessed": sum(1 for s in live if s["unassessed"]), "stale": sum(1 for s in live if s["stale"]),
            "untriaged_on_files": sum(s["new_contacts"] for s in subjects),
            "referred": sum(1 for s in subjects if s["status"] == "referred")}


def seed(dataset: str, now: datetime, profile: str) -> tuple:
    """The worked example is the one already in the sample: the north gate pair (§5.11's seeded case).

    Marcus Vane is the man two guards reported — the second time photographing the loading dock. Until now he lived
    only as an entity inside a case graph filed against the building. Here he is a folder, rated in words that agree
    with what those two SPOTREPs say and no further: approach and reconnaissance are what we have, a directly
    communicated threat is **not**, and the things nobody has looked into stay `unknown` rather than green.

    The brigade's example is the other shape of the same file: a local national the guard force keeps seeing on the
    approach to the FARP. Every name, handle, plate and number here is invented, as everywhere else in the seed."""
    inds = indicators(profile)

    def R(sid: str, rid: str, by: str, age_h: float, summary: str, ratings: Dict[str, tuple]) -> SubjectRatingRow:
        rows = [{"indicator": k, "rating": v[0], "note": v[1]} for k, v in ratings.items()]
        return SubjectRatingRow(id=rid, subject_id=sid, ratings_json=json.dumps(normalize(rows, inds)), summary=summary,
                                assessed_by=by, assessed_at=now - timedelta(hours=age_h), updated_at=now - timedelta(hours=age_h))

    if dataset == "cab":
        s2 = "S2 Intelligence"
        subj = SubjectRow(
            id="subj_001", name="Local national — FARP Eagle approach", aliases_json=json.dumps(["white pickup, no plate"]),
            status="open", summary="Seen on three consecutive days at the turn onto the FARP access road, stopping while aircraft are on the ground.",
            location_id="loc_farp", last_seen_at=now - timedelta(hours=9), last_seen_place="FARP Eagle access road", lat=31.15, lon=-93.35,
            opened_by=s2, opened_at=now - timedelta(hours=30), updated_at=now - timedelta(hours=9))
        rating = R("subj_001", "subjr_001", s2, 9, "Pattern is consistent with observation of the FARP's air movements. No contact, no statement, nothing on association or access.", {
            "grievance": ("unknown", "No statement of grievance and no contact made"),
            "association": ("unknown", "Nothing developed; RFI to higher outstanding"),
            "access": ("green", "No access to the site; stops outside the ACP on a public road"),
            "surveillance": ("red", "Three consecutive days at the same turn, stopping while aircraft are on the ground"),
            "leakage": ("unknown", "Nothing reported"),
            "threat": ("green", "No threat expressed; no contact with the force"),
            "pathway": ("amber", "Timing tracks the air movement schedule, which suggests it is being recorded"),
            "approach": ("amber", "Stops at the turn, 400 m from the ACP; has not approached the perimeter"),
            "pattern": ("amber", "Not seen before this rotation; appeared with the FARP"),
            "stabilizers": ("unknown", "Nothing known of the man"),
        })
        contacts: List[ContactRow] = []
        return [subj], [rating], contacts

    an = "S2 Analyst"
    subj1 = SubjectRow(
        id="subj_001", name="Marcus Vane", aliases_json=json.dumps(["M. Vane", "@vane_ops", "+1 415 555 0142", "grey sedan 7ABC123"]),
        status="open", summary="Two guard sightings at the SF HQ north gate two nights running, the second photographing the loading dock; three letters to the CEO in the same fortnight.",
        principal_id="p_ceo", principal_name="Alex Ventura", location_id="loc_sf", case_id="case_seed_gate",
        last_seen_at=now - timedelta(days=1, hours=2), last_seen_place="north gate, SF HQ", lat=37.7897, lon=-122.3989,
        opened_by=an, opened_at=now - timedelta(hours=24), updated_at=now - timedelta(hours=3))
    rating1 = R("subj_001", "subjr_001", an, 3, "Approach and reconnaissance are established by two independent guard reports; the correspondence carries a grievance and a veiled line but no threat. Means, identification and stabilizers are unknown and are the collection gaps.", {
        "grievance": ("amber", "Three letters over a fortnight naming a specific decision and demanding a meeting with the CEO"),
        "fixation": ("amber", "Correspondence narrowing onto the CEO by name; frequency rising across the three"),
        "identification": ("unknown", "Nothing in what we hold speaks to a warrior or avenger self-image"),
        "leakage": ("unknown", "No third party has reported anything he said"),
        "threat": ("green", "No directed or conditional threat in any of the three; the third is veiled — 'somebody will have to answer for it in person'"),
        "pathway": ("red", "Photographed the loading dock on the second night and left when approached — reconnaissance of an access point, not a passer-by"),
        "approach": ("red", "At the north gate on two consecutive nights; the CEO's floor is in that building"),
        "means": ("unknown", "Nothing known about weapons access or capability. Open with law enforcement liaison"),
        "escalation": ("amber", "Two sightings and three letters inside a fortnight, the second sighting closer to the building than the first"),
        "stabilizers": ("unknown", "Employment, housing and support unknown; the letters do not say"),
    })
    subj2 = SubjectRow(
        id="subj_002", name="Dana Ortiz", aliases_json=json.dumps(["seen with Vane, both sightings"]),
        status="monitoring", summary="Present at both north gate sightings alongside Vane. Nothing else is known and nothing is alleged.",
        location_id="loc_sf", case_id="case_seed_gate", last_seen_at=now - timedelta(days=1, hours=2), last_seen_place="north gate, SF HQ",
        lat=37.7897, lon=-122.3989, opened_by=an, opened_at=now - timedelta(hours=22), updated_at=now - timedelta(hours=22))
    rating2 = R("subj_002", "subjr_002", an, 22, "Opened because she is in both reports, not because of anything she is reported to have done. Everything but presence is unknown, and the file says so.", {
        "grievance": ("unknown", "No correspondence, no statement"), "fixation": ("unknown", "Nothing reported"),
        "identification": ("unknown", "Nothing reported"), "leakage": ("unknown", "Nothing reported"),
        "threat": ("green", "No threat expressed by her in either report"),
        "pathway": ("unknown", "The photography in the second report is attributed to Vane, not to her"),
        "approach": ("amber", "Present at the north gate on both nights"),
        "means": ("unknown", "Nothing known"), "escalation": ("unknown", "Two sightings is not yet a tempo"),
        "stabilizers": ("unknown", "Nothing known"),
    })

    def C(i: int, sid: Optional[str], channel: str, days: float, frm: str, text: str, directness: str, triage: str,
          by: str, principal: tuple = (None, ""), note: Optional[str] = None) -> ContactRow:
        """Every one of these lands graded F/6 — an unknown sender cannot be judged, and one uncorroborated item says
        nothing about whether it is true (§5.11). The grade is the sender's, never the message's importance."""
        at = now - timedelta(days=days)
        return ContactRow(id=f"cont_{i:03d}", subject_id=sid, channel=channel, received_at=at, filed_at=at + timedelta(minutes=20),
                          from_label=frm, principal_id=principal[0], principal_name=principal[1],
                          text=text, directness=directness, triage=triage, reliability="F", credibility=6, received_by=by,
                          note=note, triaged_by=an if triage != "new" else None, triaged_at=at + timedelta(hours=2) if triage != "new" else None)

    ceo, cfo = ("p_ceo", "Alex Ventura"), ("p_cfo", "Priya Ramanathan")
    contacts = [
        C(1, "subj_001", "letter", 14, "handwritten, no return address, SF postmark",
          "Six pages about a contract decision taken in March, naming the CEO throughout and asking for a meeting to explain it face to face.",
          "none", "filed", "Mailroom — SF HQ", ceo, "Grievance is specific and checkable; no threat. Filed to the folder."),
        C(2, "subj_001", "email", 8, "vane.ops.mail@example.invalid",
          "Shorter, angrier. States that the letters are being ignored, and that he has been to the building and knows which floor the office is on.",
          "veiled", "filed", "security@ inbox", ceo, "First indication he had been to the site — it predates the first guard sighting by six days."),
        C(3, "subj_001", "email", 3, "vane.ops.mail@example.invalid",
          "One paragraph: the decision was a betrayal, silence will not make it go away, and somebody will have to answer for it in person.",
          "veiled", "filed", "security@ inbox", ceo, "Veiled, not conditional — no 'if' and no stated act. Raised the fixation and escalation ratings."),
        # In the inbox on purpose. It reads like Vane and it is not attributed to him, because nothing in it says so.
        C(4, None, "form", 1.5, "web contact form, no name given",
          "Three lines about the same March decision from an unnamed sender, in different words and with no demand.",
          "none", "new", "Website contact form", (None, "")),
        # The target is known — a title maps to exactly one person in our own directory, which is our data, not a guess.
        # The *sender* is not, so it stays in the inbox rather than being filed onto a folder to make the queue shorter.
        C(5, None, "dm", 0.4, "@anon_handle_7742",
          "A reply to the company account telling the CFO to enjoy Greenwich while it lasts.",
          "veiled", "new", "Comms — social monitoring", cfo,
          None),
    ]
    return [subj1, subj2], [rating1, rating2], contacts
