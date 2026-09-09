"""§3.4 the graphics object (2026-09-05): a control measure a section draws on the board by hand.

Requirements generate their NAIs and trips their legs; everything else on an overlay is drawn — a main supply route,
an air corridor, a boundary, an access control point, a target area of interest, a retrans site, a supply point, a
cordon. One object covers all of them: a point, a line, or a polygon; a type from a catalog that sets its color, its
glyph, and which section owns it; a name; an optional window; a note. Drawn by the owning section (or the Battle
Captain), on the ledger like everything else, shown on all three clients under the overlay rules — the owning section's
graphics forward, the rest dimmed. Retired, not deleted: a control measure that was on the board stays in the record.

The catalog speaks doctrine on a military desk and plain words on a corporate one; the object is the same."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base

KINDS = ("point", "line", "polygon")
STATUSES = ("planned", "active", "retired")

# type → owning section, allowed kinds, the doctrine name and the plain name, and how it is drawn
CATALOG: Dict[str, Dict[str, Any]] = {
    # S2
    "tai":         {"section": "S2", "kinds": ("polygon", "point"), "military": "TAI · target area of interest", "corporate": "Area of concern",      "color": "#ef4444", "dash": True,  "glyph": "◎"},
    "nai":         {"section": "S2", "kinds": ("polygon", "point"), "military": "NAI · named area of interest", "corporate": "Watch area",           "color": "#f59e0b", "dash": True,  "glyph": "◎"},
    "obs":         {"section": "S2", "kinds": ("point",),           "military": "OP · observation post",        "corporate": "Observation point",    "color": "#f59e0b", "dash": False, "glyph": "◬"},
    "danger_area": {"section": "S2", "kinds": ("polygon", "point"), "military": "Danger area",                  "corporate": "Danger area",          "color": "#ef4444", "dash": True,  "glyph": "!"},
    "ambush_site": {"section": "S2", "kinds": ("point", "polygon"), "military": "Likely ambush site",            "corporate": "Likely attack site",   "color": "#dc2626", "dash": True,  "glyph": "A"},
    "kill_zone":   {"section": "S2", "kinds": ("line", "polygon"),  "military": "Engagement / kill zone",       "corporate": "Attack zone",          "color": "#dc2626", "dash": False, "glyph": "KZ"},
    "attack_hotspot": {"section": "S2", "kinds": ("point", "polygon"), "military": "IED / attack hot spot",      "corporate": "Attack hot spot",      "color": "#f97316", "dash": True,  "glyph": "H"},
    "avenue_approach": {"section": "S2", "kinds": ("line", "polygon"), "military": "Avenue of approach",        "corporate": "Approach route",       "color": "#f97316", "dash": True,  "glyph": "AA"},
    "mobility_corridor": {"section": "S2", "kinds": ("line", "polygon"), "military": "Mobility corridor",       "corporate": "Movement corridor",    "color": "#f59e0b", "dash": True,  "glyph": "MC"},
    "no_go":       {"section": "S2", "kinds": ("polygon",),         "military": "No-go terrain",                "corporate": "No-go area",           "color": "#dc2626", "dash": False, "glyph": "X"},
    "slow_go":     {"section": "S2", "kinds": ("polygon",),         "military": "Slow-go terrain",              "corporate": "Slow-go area",         "color": "#f59e0b", "dash": True,  "glyph": "S"},
    "restricted_area": {"section": "S2", "kinds": ("polygon",),     "military": "Restricted area",              "corporate": "Restricted area",      "color": "#f97316", "dash": True,  "glyph": "R"},
    "obstacle":    {"section": "S2", "kinds": ("point", "line", "polygon"), "military": "Obstacle / UXO",       "corporate": "Obstacle",             "color": "#f97316", "dash": False, "glyph": "O"},
    "hostile_checkpoint": {"section": "S2", "kinds": ("point",),    "military": "Hostile checkpoint",           "corporate": "Hostile checkpoint",   "color": "#ef4444", "dash": False, "glyph": "CP"},
    "hostile_op":  {"section": "S2", "kinds": ("point",),           "military": "Hostile observation post",     "corporate": "Hostile observation",  "color": "#ef4444", "dash": False, "glyph": "OP"},
    "surveillance_detection_point": {"section": "S2", "kinds": ("point",), "military": "Surveillance detection point", "corporate": "Surveillance detection point", "color": "#ef4444", "dash": False, "glyph": "SD"},
    # S3
    "msr":         {"section": "S3", "kinds": ("line",),            "military": "MSR · main supply route",      "corporate": "Primary route",        "color": "#60a5fa", "dash": False, "glyph": "═"},
    "asr":         {"section": "S3", "kinds": ("line",),            "military": "ASR · alternate supply route", "corporate": "Alternate route",      "color": "#60a5fa", "dash": True,  "glyph": "─"},
    "corridor":    {"section": "S3", "kinds": ("line", "polygon"),  "military": "Air corridor",                 "corporate": "Air route",            "color": "#c084fc", "dash": True,  "glyph": "✈"},
    "boundary":    {"section": "S3", "kinds": ("line", "polygon"),  "military": "Boundary",                     "corporate": "Perimeter",            "color": "#e2e8f0", "dash": False, "glyph": "▭"},
    "phase_line":  {"section": "S3", "kinds": ("line",),            "military": "Phase line",                   "corporate": "Stage line",           "color": "#e2e8f0", "dash": True,  "glyph": "┃"},
    "acp":         {"section": "S3", "kinds": ("point",),           "military": "ACP · access control point",   "corporate": "Access control point", "color": "#3b82f6", "dash": False, "glyph": "⛨"},
    "checkpoint":  {"section": "S3", "kinds": ("point",),           "military": "Checkpoint",                   "corporate": "Checkpoint",           "color": "#3b82f6", "dash": False, "glyph": "◆"},
    "lz":          {"section": "S3", "kinds": ("point", "polygon"), "military": "LZ / PZ",                      "corporate": "Helipad",              "color": "#c084fc", "dash": False, "glyph": "H"},
    "assembly":    {"section": "S3", "kinds": ("point", "polygon"), "military": "Assembly area",                "corporate": "Rally point",          "color": "#22c55e", "dash": False, "glyph": "▲"},
    "range":       {"section": "S3", "kinds": ("polygon",),         "military": "Range · hot when in window",   "corporate": "Closed area",          "color": "#ef4444", "dash": False, "glyph": "⊗"},
    "cordon":      {"section": "S3", "kinds": ("polygon",),         "military": "Cordon",                       "corporate": "Cordon",               "color": "#f97316", "dash": False, "glyph": "◯"},
    # S4
    "supply_point": {"section": "S4", "kinds": ("point",),          "military": "Supply point",                 "corporate": "Supply point",         "color": "#f97316", "dash": False, "glyph": "⛽"},
    "ccp":         {"section": "S4", "kinds": ("point",),           "military": "CCP · casualty collection",    "corporate": "Medical point",        "color": "#22c55e", "dash": False, "glyph": "✚"},
    "maint":       {"section": "S4", "kinds": ("point",),           "military": "Maintenance collection point", "corporate": "Vehicle staging",      "color": "#f97316", "dash": False, "glyph": "⚙"},
    # S6
    "retrans":     {"section": "S6", "kinds": ("point",),           "military": "RRT · retrans site",           "corporate": "Relay site",           "color": "#2dd4bf", "dash": False, "glyph": "((·))"},
    "coverage":    {"section": "S6", "kinds": ("polygon",),         "military": "Net coverage",                 "corporate": "Radio coverage",       "color": "#2dd4bf", "dash": True,  "glyph": "◌"},
    "cp":          {"section": "S6", "kinds": ("point",),           "military": "CP · command post (jump)",     "corporate": "Command post",         "color": "#2dd4bf", "dash": False, "glyph": "◈"},
}

THREAT_GRAPHIC_TYPES = {
    "danger_area", "ambush_site", "kill_zone", "attack_hotspot", "avenue_approach", "mobility_corridor", "no_go",
    "slow_go", "restricted_area", "obstacle", "hostile_checkpoint", "hostile_op", "surveillance_detection_point",
}


def catalog(profile: str) -> List[Dict[str, Any]]:
    """What a section may draw, with the name this desk uses for it."""
    return [{"type": t, "section": c["section"], "kinds": list(c["kinds"]), "label": c["military" if profile == "military" else "corporate"], "color": c["color"], "dash": c["dash"], "glyph": c["glyph"], "threat_graphic": t in THREAT_GRAPHIC_TYPES} for t, c in CATALOG.items()]


class GraphicRow(Base):
    __tablename__ = "cop_graphics"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String)                 # a CATALOG key
    kind: Mapped[str] = mapped_column(String)                 # point | line | polygon
    section: Mapped[str] = mapped_column(String, index=True)  # the owning section, from the catalog
    name: Mapped[str] = mapped_column(String)
    geometry_json: Mapped[str] = mapped_column(Text)          # point: [lon, lat]; line / polygon: [[lon, lat], …]
    window_from: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    window_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")   # planned | active | retired
    note: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[str] = mapped_column(String, default="confirmed")   # confirmed | probable | possible | template
    basis: Mapped[str] = mapped_column(Text, default="")
    subject_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)   # what it is for: an event, a location, an operation
    subject_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def validate(type_: str, kind: str, geometry: Any) -> str:
    """The reason a graphic is malformed, or an empty string."""
    c = CATALOG.get(type_)
    if not c: return f"unknown type {type_!r}"
    if kind not in c["kinds"]: return f"a {type_} is drawn as {' or '.join(c['kinds'])}, not a {kind}"
    pts = [geometry] if kind == "point" else geometry
    if not isinstance(pts, list) or not pts: return "geometry is empty"
    if kind == "line" and len(pts) < 2: return "a line needs two points"
    if kind == "polygon" and len(pts) < 3: return "a polygon needs three points"
    for p in pts:
        if not (isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p) and -180 <= p[0] <= 180 and -90 <= p[1] <= 90):
            return "each point is [lon, lat]"
    return ""


def centroid(kind: str, geometry: Any) -> List[float]:
    pts = [geometry] if kind == "point" else geometry
    return [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)]


def out(g: GraphicRow, now: datetime, profile: str) -> Dict[str, Any]:
    c = CATALOG.get(g.type, {"section": g.section, "color": "#94a3b8", "dash": False, "glyph": "·", "military": g.type, "corporate": g.type})
    geom = json.loads(g.geometry_json)
    in_window = (g.window_from is None or g.window_from <= now) and (g.window_to is None or now <= g.window_to)
    return {"id": g.id, "type": g.type, "kind": g.kind, "section": g.section, "name": g.name, "label": c["military" if profile == "military" else "corporate"],
            "geometry": geom, "center": centroid(g.kind, geom), "window_from": _iso(g.window_from), "window_to": _iso(g.window_to), "in_window": in_window,
            "status": g.status, "note": g.note, "confidence": g.confidence, "basis": g.basis, "threat_graphic": g.type in THREAT_GRAPHIC_TYPES,
            "subject_type": g.subject_type, "subject_id": g.subject_id, "created_by": g.created_by, "created_at": _iso(g.created_at), "updated_at": _iso(g.updated_at),
            "color": c["color"], "dash": c["dash"], "glyph": c["glyph"]}


def seed(dataset: str, now: datetime) -> List[GraphicRow]:
    """A few control measures the sample force would have on its board, drawn where its sites are."""
    from datetime import timedelta
    d = lambda x: now + timedelta(days=x)
    def G(i, type_, kind, section, name, geom, wf=None, wt=None, status="active", note="", st=None, sid=None, by="S3 Operations", confidence="confirmed", basis=""):
        return GraphicRow(id=f"gfx_{i:03d}", type=type_, kind=kind, section=section, name=name, geometry_json=json.dumps(geom), window_from=wf, window_to=wt, status=status, note=note,
                          confidence=confidence, basis=basis, subject_type=st, subject_id=sid, created_by=by, created_at=now - timedelta(hours=20), updated_at=now - timedelta(hours=20))
    if dataset == "cab":
        return [
            G(1, "msr", "line", "S3", "MSR TIGER", [[-93.20, 31.06], [-93.27, 31.10], [-93.35, 31.15], [-93.30, 31.28], [-93.25, 31.40]], note="FOB Warrior → FARP Eagle → Peason Ridge. One bridge weight-posted north of the FARP.", st="event", sid="evt_ftx"),
            G(2, "corridor", "line", "S3", "Air corridor GREEN", [[-93.20, 31.06], [-93.30, 31.22], [-93.25, 31.40]], note="FOB to the range, 300 ft AGL and below; rotary wing only.", st="event", sid="evt_gunnery"),
            G(3, "range", "polygon", "S3", "Peason Ridge — Table VI (hot 0600–2200)", [[-93.30, 31.36], [-93.20, 31.36], [-93.19, 31.44], [-93.31, 31.44]], wf=d(5), wt=d(8), note="Hellfire and 30 mm. Surface danger zone as posted.", st="event", sid="evt_gunnery"),
            G(4, "acp", "point", "S3", "ACP 4 — Fort Johnson main gate", [-93.24, 31.09], note="Demonstration permitted Saturday; 200 expected."),
            G(5, "tai", "polygon", "S2", "TAI 1 — demonstration route at the gate", [[-93.255, 31.08], [-93.225, 31.08], [-93.225, 31.10], [-93.255, 31.10]], wf=d(1), wt=d(2), note="Where the demonstration route crosses the convoy's turn. Watch for blocking.", by="S2 Intelligence"),
            G(6, "retrans", "point", "S6", "RRT 1 — high ground between the FOB and the FARP", [-93.28, 31.11], note="FM retrans for the FARP net until the TACSAT antenna is replaced.", by="S6 Signal"),
            G(7, "supply_point", "point", "S4", "Class III/V point — FARP Eagle", [-93.345, 31.148], note="Tanker convoy CONV-0912 offloads here.", by="S4 Logistics", st="location", sid="loc_farp"),
            G(8, "ccp", "point", "S4", "CCP — FOB Warrior", [-93.198, 31.062], note="Air ambulance strip alert adjacent.", by="S4 Logistics", st="location", sid="loc_fob"),
            G(9, "boundary", "polygon", "S3", "Brigade AO — JRTC", [[-93.45, 31.00], [-93.10, 31.00], [-93.10, 31.50], [-93.45, 31.50]], note="The rotation's area of operations.", st="event", sid="evt_ftx"),
            G(10, "danger_area", "polygon", "S2", "Danger Area 2 — bridge north of FARP", [[-93.360, 31.135], [-93.332, 31.135], [-93.332, 31.168], [-93.360, 31.168]], note="Two reports place observation on both bridge approaches.", st="location", sid="loc_farp", by="S2 Intelligence", confidence="probable", basis="sgt_opfor_1; sgt_opfor_2"),
            G(11, "ambush_site", "point", "S2", "Likely ambush site — ACP 4 turn", [-93.240, 31.090], wf=d(1), wt=d(2), note="Choke point where demonstration traffic and convoy route converge.", st="event", sid="evt_ftx", by="S2 Intelligence", confidence="possible", basis="thr_demo; sgt_gate_1"),
            G(12, "avenue_approach", "line", "S2", "Avenue RED — west treeline to FARP", [[-93.39, 31.16], [-93.36, 31.15], [-93.345, 31.148]], note="Doctrinal approach from concealed terrain into FARP Eagle.", st="location", sid="loc_farp", by="S2 Intelligence", confidence="template", basis="doctrinal template"),
            G(13, "hostile_op", "point", "S2", "Hostile OP — ridge west of FARP", [-93.370, 31.153], note="Overlooks Class III/V point and MSR TIGER north approach.", st="location", sid="loc_farp", by="S2 Intelligence", confidence="probable", basis="sgt_opfor_2; sgt_opfor_3"),
        ]
    return [
        G(1, "msr", "line", "S3", "Motorcade route — HQ to SFO", [[-122.4194, 37.7749], [-122.4050, 37.7500], [-122.3960, 37.7100], [-122.3900, 37.6213]], note="Primary. Alternate via US-101 southbound if the 280 is closed.", by="Executive Assistant"),
        G(2, "cordon", "polygon", "S3", "Board dinner cordon — SF HQ block", [[-122.4215, 37.7735], [-122.4172, 37.7735], [-122.4172, 37.7762], [-122.4215, 37.7762]], wf=d(36), wt=d(37), note="Vehicle screening at both ends of the block.", by="Executive Assistant"),
        G(3, "assembly", "point", "S3", "Rally point — HQ garage level 2", [-122.4188, 37.7742], note="Evacuation rally point for the executive floor.", by="Security"),
        G(4, "tai", "point", "S2", "Watch — DC-East perimeter, loading dock", [-77.4870, 39.0442], note="Online threats named the operator; the dock is the soft side.", by="S2 Analyst", st="location", sid="loc_dc2"),
        G(5, "ccp", "point", "S4", "Medical point — SF HQ lobby", [-122.4190, 37.7752], note="AED and trauma kit at the desk.", by="Security"),
        G(6, "surveillance_detection_point", "point", "S2", "Surveillance point — SF HQ north gate", [-122.3989, 37.7897], note="Repeated evening observations from the seeded gate case.", by="S2 Analyst", st="case", sid="case_seed_gate", confidence="confirmed", basis="rpt_seed_1; rpt_seed_2"),
        G(7, "attack_hotspot", "polygon", "S2", "Hot spot — DC-East loading side", [[-77.494, 39.039], [-77.480, 39.039], [-77.480, 39.050], [-77.494, 39.050]], note="Online threat cluster named operator and soft-side dock.", by="S2 Analyst", st="location", sid="loc_dc2", confidence="probable", basis="thr_004; sgt_dc_1"),
    ]
