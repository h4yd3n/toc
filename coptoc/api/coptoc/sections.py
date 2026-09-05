"""§7 S4 Logistics and §8 S6 Signal — the background staff sections, built for a generic operations center.

S4 tracks what the force has (supplies and equipment by site, against a required level) and what is inbound (shipments).
S6 tracks the systems the TOC depends on — comms nets by PACE role, networks, applications, power — and their status.
Both roll up to one status a Battle Captain reads at a glance: GREEN nothing to say, AMBER watch it, RED it is a problem now.
Management by exception: the wall shows the roll-up, the panel shows the detail, the handover brief and INTSUM carry the exceptions.

The section set itself is configuration (`TOC_SECTIONS`, `TOC_SECTION_TITLES`): a commercial security desk hides S4/S6 or renames
them; a military or police operations center keeps all five. Clients read `snapshot.sections` and show only what is enabled."""
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base

SECTION_TITLES = {"S1": "PERSONNEL", "S2": "INTELLIGENCE", "S3": "OPERATIONS", "S4": "LOGISTICS", "S6": "SIGNAL"}
SECTION_HINTS = {"S1": "Blue force", "S2": "Sigtoc", "S3": "Travel & events", "S4": "Supply & equipment", "S6": "Comms & systems"}
STATUS_RANK = {"green": 0, "amber": 1, "red": 2}
SUPPLY_CATEGORIES = ("fuel", "water", "rations", "medical", "ammunition", "parts", "equipment", "other")
SYSTEM_CATEGORIES = ("comms", "network", "application", "power", "sensor", "other")
PACE = ("primary", "alternate", "contingency", "emergency")


def sections_config() -> List[Dict[str, Any]]:
    """Which staff sections this deployment runs, in wall order. `TOC_SECTIONS=S1,S2,S3` for a commercial desk;
    `TOC_SECTION_TITLES=S4=SUPPLY,S6=COMMS` to rename. S1–S3 are always present: the COP is built on them."""
    enabled = [s.strip().upper() for s in os.environ.get("TOC_SECTIONS", "S1,S2,S3,S4,S6").split(",") if s.strip()]
    titles = dict(SECTION_TITLES)
    for pair in os.environ.get("TOC_SECTION_TITLES", "").split(","):
        if "=" in pair:
            k, v = pair.split("=", 1); titles[k.strip().upper()] = v.strip().upper()
    return [{"code": c, "title": titles[c], "hint": SECTION_HINTS[c], "enabled": c in enabled or c in ("S1", "S2", "S3")} for c in ("S1", "S2", "S3", "S4", "S6")]


class SupplyRow(Base):
    """A supply or equipment line at a site: what is on hand against what is required."""
    __tablename__ = "cop_supply"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    location_id: Mapped[Optional[str]] = mapped_column(ForeignKey("cop_locations.id"), nullable=True, index=True)  # None = the whole force
    category: Mapped[str] = mapped_column(String)  # fuel | water | rations | medical | ammunition | parts | equipment | other
    item: Mapped[str] = mapped_column(String)
    on_hand: Mapped[float] = mapped_column(Float)
    required: Mapped[float] = mapped_column(Float)  # the minimum to hold; below it is AMBER, below half of it RED
    unit: Mapped[str] = mapped_column(String, default="ea")
    note: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[str] = mapped_column(String, default="seed")
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(String, default="manual")


class ShipmentRow(Base):
    """Something inbound: a resupply, a replacement, a delivery the force is waiting on."""
    __tablename__ = "cop_shipments"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    description: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, default="other")
    quantity: Mapped[str] = mapped_column(String, default="")
    from_name: Mapped[str] = mapped_column(String, default="")
    to_location_id: Mapped[Optional[str]] = mapped_column(ForeignKey("cop_locations.id"), nullable=True, index=True)
    to_name: Mapped[str] = mapped_column(String, default="")
    eta: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String, default="planned")  # planned | in_transit | delayed | arrived | cancelled
    priority: Mapped[str] = mapped_column(String, default="routine")  # routine | priority | urgent
    carrier: Mapped[str] = mapped_column(String, default="")
    ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[str] = mapped_column(String, default="seed")
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(String, default="manual")


class SystemRow(Base):
    """A system the TOC depends on. Comms nets carry a PACE role (primary / alternate / contingency / emergency)."""
    __tablename__ = "cop_systems"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, default="comms")  # comms | network | application | power | sensor | other
    location_id: Mapped[Optional[str]] = mapped_column(ForeignKey("cop_locations.id"), nullable=True, index=True)  # None = enterprise-wide
    pace: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="up")  # up | degraded | down
    since: Mapped[datetime] = mapped_column(DateTime)
    note: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[str] = mapped_column(String, default="seed")
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(String, default="manual")


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def supply_status(on_hand: float, required: float) -> str:
    if required <= 0:
        return "green"
    if on_hand >= required:
        return "green"
    return "amber" if on_hand >= required / 2 else "red"


def shipment_status(s: ShipmentRow, now: datetime) -> str:
    if s.status in ("arrived", "cancelled"):
        return "green"
    if s.status == "delayed" or (s.status in ("planned", "in_transit") and s.eta < now):
        return "red" if s.priority == "urgent" else "amber"
    return "green"


def system_status(s: SystemRow) -> str:
    if s.status == "down":
        return "red" if s.pace == "primary" or s.category == "power" else "amber"
    if s.status == "degraded":
        return "amber"
    return "green"


def worst(statuses: List[str]) -> str:
    return max(statuses, key=lambda x: STATUS_RANK[x]) if statuses else "green"


def s4_summary(supplies: List[SupplyRow], shipments: List[ShipmentRow], loc_name: Dict[str, str], now: datetime) -> Dict[str, Any]:
    sup_out = []
    for s in sorted(supplies, key=lambda x: (STATUS_RANK[supply_status(x.on_hand, x.required)] * -1, x.location_id or "", x.category, x.item)):
        st = supply_status(s.on_hand, s.required)
        sup_out.append({"id": s.id, "location_id": s.location_id, "location_name": loc_name.get(s.location_id or "", "Force-wide"), "category": s.category, "item": s.item,
                        "on_hand": s.on_hand, "required": s.required, "unit": s.unit, "pct": round(100 * s.on_hand / s.required) if s.required > 0 else 100,
                        "status": st, "note": s.note, "updated_by": s.updated_by, "updated_at": _iso(s.updated_at), "source": s.source})
    ship_out = []
    for s in sorted(shipments, key=lambda x: x.eta):
        if s.status in ("arrived", "cancelled") and (now - s.updated_at).total_seconds() > 86400:
            continue  # yesterday's arrivals leave the board
        ship_out.append({"id": s.id, "description": s.description, "category": s.category, "quantity": s.quantity, "from_name": s.from_name,
                         "to_location_id": s.to_location_id, "to_name": s.to_name or loc_name.get(s.to_location_id or "", ""), "eta": _iso(s.eta),
                         "hours_to_eta": round((s.eta - now).total_seconds() / 3600, 1), "status": s.status, "priority": s.priority, "carrier": s.carrier, "ref": s.ref,
                         "health": shipment_status(s, now), "note": s.note, "updated_by": s.updated_by, "updated_at": _iso(s.updated_at)})
    exceptions = [f"{x['item']} at {x['location_name']}: {x['on_hand']:g}/{x['required']:g} {x['unit']} ({x['status'].upper()})" for x in sup_out if x["status"] != "green"] + \
                 [f"{x['description']} → {x['to_name']}: {x['status'].replace('_', ' ')}, ETA {x['eta'][:16].replace('T', ' ')}Z ({x['health'].upper()})" for x in ship_out if x["health"] != "green"]
    return {"status": worst([x["status"] for x in sup_out] + [x["health"] for x in ship_out]), "supplies": sup_out, "shipments": ship_out, "exceptions": exceptions,
            "counts": {"red": sum(1 for x in sup_out if x["status"] == "red"), "amber": sum(1 for x in sup_out if x["status"] == "amber"),
                       "inbound": sum(1 for x in ship_out if x["status"] in ("planned", "in_transit", "delayed")), "late": sum(1 for x in ship_out if x["health"] != "green")}}


def s6_summary(systems: List[SystemRow], loc_name: Dict[str, str], now: datetime) -> Dict[str, Any]:
    out = []
    for s in sorted(systems, key=lambda x: (x.location_id or "", PACE.index(x.pace) if x.pace in PACE else 9, x.category, x.name)):
        out.append({"id": s.id, "name": s.name, "category": s.category, "location_id": s.location_id, "location_name": loc_name.get(s.location_id or "", "Enterprise"),
                    "pace": s.pace, "status": s.status, "health": system_status(s), "since": _iso(s.since), "hours": round((now - s.since).total_seconds() / 3600, 1),
                    "note": s.note, "updated_by": s.updated_by, "updated_at": _iso(s.updated_at), "source": s.source})
    # PACE per site: the best working net, so the Battle Captain knows how to reach each site right now
    pace: Dict[str, Dict[str, Any]] = {}
    for x in out:
        if not x["pace"]:
            continue
        site = x["location_id"] or "enterprise"
        p = pace.setdefault(site, {"location_name": x["location_name"], "nets": {}, "in_use": None})
        p["nets"][x["pace"]] = x["status"]
    for p in pace.values():
        p["in_use"] = next((r for r in PACE if p["nets"].get(r) == "up"), None) or next((r for r in PACE if p["nets"].get(r) == "degraded"), None)
    exceptions = [f"{x['name']} ({x['location_name']}): {x['status'].upper()} {x['hours']:g}h" + (f" — {x['note']}" if x["note"] else "") for x in out if x["health"] != "green"]
    return {"status": worst([x["health"] for x in out]), "systems": out, "pace": pace, "exceptions": exceptions,
            "counts": {"down": sum(1 for x in out if x["status"] == "down"), "degraded": sum(1 for x in out if x["status"] == "degraded"), "total": len(out)}}
