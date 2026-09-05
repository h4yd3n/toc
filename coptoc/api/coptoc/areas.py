"""§5.6a the rated area assessment (2026-09-05): what the analyst judges about a place, indicator by indicator.

Collection tells the wall what has been *reported* about a place (§5.6, the evidence matrix). This is the other half:
the analyst's own judgment of the place against a fixed list of indicators — green, amber, or red, each with one line
that says why — owned, dated, and attached to the site it describes and to every trip and event going there. Nothing is
scored or summed (Decision I): the picture is the row of ratings and the worst of them, and the reader ranks.

The indicator list is configuration, like the section titles: a brigade and a corporate desk ask different questions
of a place. `TOC_AREA_INDICATORS` overrides the profile's default. A new assessment of a place supersedes the last one;
the old one stays on the ledger and in the table, marked superseded."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared import settings
from shared.database import Base

RATINGS = ("green", "amber", "red", "unknown")
RANK = {"unknown": 0, "green": 1, "amber": 2, "red": 3}

# The questions a staff asks of a place, by profile. Labels are the words on the wall; ids are stable keys.
INDICATORS: Dict[str, List[tuple]] = {
    "military": [
        ("perimeter", "Physical security & perimeter"), ("unrest", "Civil unrest & demonstrations"), ("routes", "Routes, corridors & evacuation"),
        ("medical", "Medical & MEDEVAC reach"), ("comms", "Communications redundancy (PACE)"), ("host_nation", "Host-nation & local law enforcement"),
        ("sustainment", "Sustainment & resupply"), ("isr", "ISR & sensor coverage"), ("infrastructure", "Power, water & infrastructure"),
        ("weather", "Weather & terrain effects on operations"),
    ],
    "corporate": [
        ("perimeter", "Physical security & perimeter"), ("unrest", "Civil unrest & demonstrations"), ("transit", "VIP transit & evacuation corridors"),
        ("medical", "Healthcare & trauma proximity"), ("cyber", "Cyber & telecom redundancy"), ("law", "Local law enforcement liaison"),
        ("logistics", "Supply chain & logistics"), ("surveillance", "Surveillance & sensor density"), ("infrastructure", "Infrastructure resiliency"),
    ],
}


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:32] or "indicator"


def indicators(profile: str) -> List[Dict[str, str]]:
    """The indicator list for this deployment: `TOC_AREA_INDICATORS` ("id=Label,Label,…") if set, else the profile's default."""
    raw = (settings.get("TOC_AREA_INDICATORS") or "").strip()
    if raw:
        out = []
        for part in raw.split(","):
            part = part.strip()
            if not part: continue
            key, _, label = part.partition("=")
            out.append({"id": _slug(key) if label else _slug(part), "label": (label or part).strip()})
        if out: return out
    return [{"id": i, "label": l} for i, l in INDICATORS.get(profile, INDICATORS["corporate"])]


class AreaRatingRow(Base):
    __tablename__ = "cop_area_ratings"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    place: Mapped[str] = mapped_column(String)                                     # what the analyst calls it — a site's name, or "Lisbon, Portugal"
    location_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)  # the site on the wall, when it is one
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ratings_json: Mapped[str] = mapped_column(Text, default="[]")                  # [{indicator, label, rating, note}]
    summary: Mapped[str] = mapped_column(Text, default="")                         # the analyst's one paragraph, if they wrote one
    assessed_by: Mapped[str] = mapped_column(String)
    assessed_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String, default="current")                 # current | superseded
    supersedes: Mapped[Optional[str]] = mapped_column(String, nullable=True)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def normalize(ratings: List[Dict[str, Any]], inds: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """One entry per configured indicator, in the configured order; anything the analyst did not rate is `unknown`."""
    by = {r.get("indicator"): r for r in ratings}
    out = []
    for i in inds:
        r = by.get(i["id"], {})
        rating = r.get("rating") if r.get("rating") in RATINGS else "unknown"
        out.append({"indicator": i["id"], "label": i["label"], "rating": rating, "note": (r.get("note") or "").strip()})
    return out


def out(row: AreaRatingRow, now: datetime) -> Dict[str, Any]:
    ratings = json.loads(row.ratings_json or "[]")
    counts = {k: sum(1 for r in ratings if r["rating"] == k) for k in RATINGS}
    rated = [r for r in ratings if r["rating"] != "unknown"]
    worst = max(rated, key=lambda r: RANK[r["rating"]]) if rated else None
    return {"id": row.id, "place": row.place, "location_id": row.location_id, "lat": row.lat, "lon": row.lon, "ratings": ratings, "summary": row.summary,
            "assessed_by": row.assessed_by, "assessed_at": _iso(row.assessed_at), "updated_at": _iso(row.updated_at), "status": row.status, "supersedes": row.supersedes,
            "counts": counts, "worst": worst["rating"] if worst else "unknown", "worst_indicator": worst["label"] if worst else None,
            "age_days": round((now - row.assessed_at).total_seconds() / 86400, 1), "stale": (now - row.assessed_at).days >= 30}


def compact(a: Dict[str, Any]) -> Dict[str, Any]:
    """What a site, a trip, or an event carries about its place: enough to draw the strip and say who said so."""
    return {"id": a["id"], "place": a["place"], "worst": a["worst"], "worst_indicator": a["worst_indicator"], "counts": a["counts"],
            "strip": [r["rating"] for r in a["ratings"]], "assessed_by": a["assessed_by"], "assessed_at": a["assessed_at"], "age_days": a["age_days"], "stale": a["stale"]}


def same_place(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


def seed(dataset: str, now: datetime, profile: str) -> List[AreaRatingRow]:
    """Sample assessments in the sample force's own words. Every line here describes the seeded picture — the FARP's fuel
    line, its TACSAT, the demonstration at the gate — so the ratings agree with what the other panels show."""
    from datetime import timedelta
    inds = indicators(profile)
    def R(i: int, place: str, loc: Optional[str], lat: float, lon: float, by: str, age_h: float, summary: str, ratings: Dict[str, tuple]) -> AreaRatingRow:
        rows = [{"indicator": k, "rating": v[0], "note": v[1]} for k, v in ratings.items()]
        return AreaRatingRow(id=f"area_{i:03d}", place=place, location_id=loc, lat=lat, lon=lon, ratings_json=json.dumps(normalize(rows, inds)), summary=summary,
                             assessed_by=by, assessed_at=now - timedelta(hours=age_h), updated_at=now - timedelta(hours=age_h))
    if dataset == "cab":
        s2 = "S2 Intelligence"
        return [
            R(1, "FARP Eagle", "loc_farp", 31.15, -93.35, s2, 26, "Established D-3 for the rotation. Fuel and the alternate net are the open items; the demonstration route passes the resupply convoy's turn.", {
                "perimeter": ("amber", "Temporary site; perimeter is the FARP team plus one ACP, no standoff to the treeline"),
                "unrest": ("amber", "Permit filed for Saturday at the Fort Johnson main gate, 200 expected; route passes the convoy's turn"),
                "routes": ("green", "MSR to Peason Ridge flown D-4: clear, one bridge weight-posted"),
                "medical": ("green", "C/4 GSAB air ambulance on strip alert at FOB Warrior, under 15 minutes flight time"),
                "comms": ("amber", "TACSAT antenna damaged on setup; on FM primary with HF as the only alternate until the convoy arrives"),
                "host_nation": ("green", "Installation MPs briefed; range control on the FM net"),
                "sustainment": ("red", "JP-8 at 8,000 of 20,000 gal required; tanker convoy CONV-0912 in transit"),
                "isr": ("amber", "UAS coverage tasked to S3 and accepted; nothing on station until the Shadow window opens"),
                "infrastructure": ("amber", "One of two generators down; fuel for the remaining one at 40%"),
                "weather": ("green", "No watch in effect for the exercise area; bird activity NOTAM on the range approach at dawn and dusk"),
            }),
            R(2, "FOB Warrior — JRTC", "loc_fob", 31.06, -93.20, s2, 30, "The brigade's forward base for the rotation. Comms is the exception: SIPR is down while the terminal is re-pointed.", {
                "perimeter": ("green", "Established FOB with hardened ACPs and a manned perimeter"),
                "unrest": ("green", "No permitted activity near the FOB; the Saturday demonstration is at the main gate, 8 km away"),
                "routes": ("green", "Two hardened routes to the FOB; both flown and driven"),
                "medical": ("green", "Role 2 on site; air ambulance on strip alert"),
                "comms": ("amber", "SIPRNET down 2 h while the satellite terminal is re-pointed; FM, TACSAT, HF up"),
                "host_nation": ("green", "JRTC and installation law enforcement on the FM net"),
                "sustainment": ("amber", "Water at 2,400 of 3,000 cases; Class I push held at the gate for the demonstration"),
                "isr": ("green", "JBC-P blue force tracking up; ATNAVICS covering the approaches"),
                "infrastructure": ("green", "Installation power with generator backup"),
                "weather": ("green", "No watch in effect"),
            }),
            R(3, "Peason Ridge Range Complex", "loc_range", 31.40, -93.25, s2, 50, "Table VI in five days. The range is a known quantity; the approach corridor has a bird hazard at the edges of the day.", {
                "perimeter": ("green", "Controlled range; access by range control only"),
                "unrest": ("green", "Nothing reported"),
                "routes": ("green", "MSR flown and cleared; one bridge weight-posted for heavy vehicles"),
                "medical": ("green", "Range medic on site during live fire; air ambulance under 15 minutes"),
                "comms": ("green", "Range control FM plus the brigade nets"),
                "host_nation": ("green", "Range control and installation MPs"),
                "sustainment": ("green", "Class V draw for Table VI approved; 30 mm at 40,000 of 60,000 rds brigade-wide"),
                "isr": ("green", "Not required for a range period"),
                "infrastructure": ("green", "Range infrastructure serviceable"),
                "weather": ("amber", "Migratory bird activity elevated on the approach corridor at dawn and dusk (NOTAM)"),
            }),
        ]
    an = "S2 Analyst"
    return [
        R(1, "Lisbon, Portugal", None, 38.7223, -9.1393, an, 40, "Candidate venue for the offsite. Transit is the open question: labor action is planned near the waterfront route.", {
            "perimeter": ("green", "Vaulted venue with a dedicated security desk"),
            "unrest": ("red", "Labor strikes planned near Praça do Comércio in the window; the primary transit route crosses it"),
            "transit": ("amber", "One bridge on the airport route; alternates are longer and less known"),
            "medical": ("green", "Level 1 trauma centre within a short ground move"),
            "cyber": ("green", "Subsea landing hub plus satellite failover available to the venue"),
            "law": ("green", "Direct liaison established with the PSP"),
            "logistics": ("green", "Secure supply to the venue confirmed"),
            "surveillance": ("green", "Thermal perimeter and PTZ coverage at the venue"),
            "infrastructure": ("amber", "Summer grid peak load; venue on an older substation feed"),
        }),
        R(2, "Porto, Portugal", None, 41.1579, -8.6291, an, 40, "Second candidate. Quieter, but the venue shares its perimeter and the telecom path has no redundancy.", {
            "perimeter": ("amber", "Commercial venue with a shared perimeter and a single gate"),
            "unrest": ("green", "No permitted activity within 5 km in the window"),
            "transit": ("green", "Air bridge from the airport; river egress as an alternate"),
            "medical": ("green", "Level 1 trauma centre within a short ground move"),
            "cyber": ("amber", "Terrestrial fibre only, no dedicated microwave; portable satellite would close it"),
            "law": ("green", "Regional GNR liaison established"),
            "logistics": ("amber", "Regional depot dependency, limited on-site storage"),
            "surveillance": ("red", "CCTV outage on the western cargo ramp; technician dispatched"),
            "infrastructure": ("green", "Hydroelectric grid with dual diesel backup"),
        }),
        R(3, "London Office", "loc_ldn", 51.5074, -0.1278, an, 70, "Elevated for the transit strike. The building itself is unchanged.", {
            "perimeter": ("green", "Badged access, lobby desk, and a manned loading dock"),
            "unrest": ("amber", "Transit strike this week; demonstrations expected near Westminster"),
            "transit": ("amber", "Rail alternates thin during the strike; car pool arranged for travelers"),
            "medical": ("green", "Major trauma centre within the borough"),
            "cyber": ("green", "Dual carrier, diverse routing"),
            "law": ("green", "Met liaison in place"),
            "logistics": ("green", "No dependency"),
            "surveillance": ("green", "Full CCTV and access logging"),
            "infrastructure": ("green", "Building UPS and generator tested this quarter"),
        }),
    ]
