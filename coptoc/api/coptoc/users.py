"""§9 users and permissions (2026-09-05). One app; what you see and what you can change follows your permissions.

A user has, per staff section, `edit`, `view`, or nothing; plus two flags — `battle_captain` (the floor: watch, roll calls,
FLASH release, DEFCON, operations) and `admin` (this directory). Presets name the common shapes (a supply sergeant is S4
edit and the COP), the grid is the truth. Sign-in for the prototype is picking a user from a list — no password; the
client sends `X-TOC-User`, and this module turns that into the role and actor the rest of the API already checks.
Requests without `X-TOC-User` keep working on `X-TOC-Role` alone (the test suite, curl), so nothing that exists breaks."""
from __future__ import annotations

import contextvars
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base

SECTIONS = ("S1", "S2", "S3", "S4", "S6")
LEVELS = ("view", "edit")

# preset → (permissions, battle_captain, admin). The role string the API already checks is derived from these.
PRESETS: Dict[str, Dict[str, Any]] = {
    "battle_captain": {"label": "Battle Captain",      "perms": {s: "edit" for s in SECTIONS}, "bc": True,  "admin": False},
    "analyst":        {"label": "S2 Analyst",          "perms": {"S1": "view", "S2": "edit", "S3": "view", "S4": "view", "S6": "view"}, "bc": False, "admin": False},
    "ea":             {"label": "Executive Assistant", "perms": {"S1": "view", "S3": "edit"}, "bc": False, "admin": False},
    "security":       {"label": "Security",            "perms": {"S1": "edit", "S2": "view", "S3": "edit"}, "bc": False, "admin": False},
    "ep":             {"label": "Executive Protection", "perms": {"S1": "edit", "S2": "view", "S3": "view"}, "bc": False, "admin": False},
    "logistics":      {"label": "S4 Logistics",        "perms": {"S1": "view", "S3": "view", "S4": "edit"}, "bc": False, "admin": False},
    "signal":         {"label": "S6 Signal",           "perms": {"S1": "view", "S6": "edit"}, "bc": False, "admin": False},
    "custom":         {"label": "Custom",              "perms": {}, "bc": False, "admin": False},
}
# what a section's edit rights unlock in the existing role checks
SECTION_ROLE = {"S1": "security", "S2": "analyst", "S3": "ea", "S4": "logistics", "S6": "signal"}


class UserRow(Base):
    __tablename__ = "toc_users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, default="")  # rank / duty position: "SSG · Supply Sergeant, A/5 ASB"
    team_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    preset: Mapped[str] = mapped_column(String, default="custom")
    perms_json: Mapped[str] = mapped_column(Text, default="{}")
    battle_captain: Mapped[bool] = mapped_column(Boolean, default=False)
    admin: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String, default="seed")
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Actor:
    """Who is asking, resolved once per request."""
    def __init__(self, user: Optional[Dict[str, Any]] = None, role: Optional[str] = None, name: Optional[str] = None):
        self.user = user
        self.perms: Dict[str, str] = dict(user["perms"]) if user else {}
        self.is_bc = bool(user and user["battle_captain"])
        self.is_admin = bool(user and user["admin"])
        self.role = (("battle_captain" if self.is_bc else user["preset"]) if user else (role or "")).lower()
        self.name = (user["name"] if user else name) or "watch_floor"

    def can(self, section: str, level: str = "view") -> bool:
        if self.is_bc or not self.user:  # nobody signed in: the role header alone, as before — the role checks still gate writes
            return True
        have = self.perms.get(section)
        return have == "edit" or (level == "view" and have == "view")

    def as_dict(self) -> Dict[str, Any]:
        return {"user_id": self.user["id"] if self.user else None, "name": self.name, "role": self.role, "perms": self.perms,
                "battle_captain": self.is_bc, "admin": self.is_admin, "sections_visible": [s for s in SECTIONS if self.can(s)]}


current_actor: contextvars.ContextVar[Actor] = contextvars.ContextVar("toc_actor", default=Actor())
_cache: Dict[str, Dict[str, Any]] = {}


def _out(u: UserRow) -> Dict[str, Any]:
    return {"id": u.id, "name": u.name, "title": u.title, "team_id": u.team_id, "preset": u.preset, "perms": json.loads(u.perms_json or "{}"),
            "battle_captain": u.battle_captain, "admin": u.admin, "active": u.active, "created_by": u.created_by,
            "created_at": u.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if u.created_at else None}


async def load(session: AsyncSession) -> int:
    _cache.clear()
    for u in (await session.execute(select(UserRow))).scalars():
        _cache[u.id] = _out(u)
    return len(_cache)


def lookup(user_id: Optional[str]) -> Optional[Dict[str, Any]]:
    u = _cache.get(user_id or "")
    return u if u and u["active"] else None


def directory() -> List[Dict[str, Any]]:
    return sorted(_cache.values(), key=lambda u: (not u["battle_captain"], not u["admin"], u["name"]))


def effective_perms(preset: str, perms: Optional[Dict[str, str]]) -> Dict[str, str]:
    base = dict(PRESETS.get(preset, PRESETS["custom"])["perms"])
    for k, v in (perms or {}).items():
        if k in SECTIONS and (v in LEVELS or v is None):
            if v: base[k] = v
            else: base.pop(k, None)
    return base


async def upsert(session: AsyncSession, data: Dict[str, Any], actor: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    preset = data.get("preset") or "custom"
    if preset not in PRESETS:
        raise ValueError(f"preset must be one of {sorted(PRESETS)}")
    row = await session.get(UserRow, user_id) if user_id else None
    if user_id and not row:
        raise KeyError(user_id)
    if not row or "preset" in data:
        perms = effective_perms(preset, data.get("perms"))          # a preset (re)fills the row, then the grid's own changes apply
    elif "perms" in data:
        perms = effective_perms("custom", {**json.loads(row.perms_json), **{k: v for k, v in (data.get("perms") or {}).items()}})  # the grid edits what is there
    else:
        perms = json.loads(row.perms_json)
    if not row:
        row = UserRow(id=data.get("id") or f"u_{uuid.uuid4().hex[:8]}", created_by=actor, created_at=datetime.now(timezone.utc).replace(tzinfo=None))
        session.add(row)
    for k in ("name", "title", "team_id"):
        if k in data and data[k] is not None: setattr(row, k, data[k])
    row.preset = preset if ("preset" in data or row.preset is None) else row.preset
    row.perms_json = json.dumps(perms)
    p = PRESETS[preset]
    row.battle_captain = bool(data["battle_captain"]) if "battle_captain" in data else (row.battle_captain if user_id else p["bc"])
    row.admin = bool(data["admin"]) if "admin" in data else (row.admin if user_id else p["admin"])
    if "active" in data: row.active = bool(data["active"])
    await session.commit()
    _cache[row.id] = _out(row)
    return _cache[row.id]


async def remove(session: AsyncSession, user_id: str) -> bool:
    row = await session.get(UserRow, user_id)
    if not row: return False
    await session.delete(row); await session.commit(); _cache.pop(user_id, None)
    return True


class Identity:
    """ASGI middleware: `X-TOC-User` → the user's role and name in the headers the routes already read, and the actor in a contextvar."""
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            hdrs = {k: v for k, v in scope.get("headers", [])}
            uid = hdrs.get(b"x-toc-user", b"").decode()
            user = lookup(uid) if uid else None
            if user:
                actor = Actor(user=user)
                others = [(k, v) for k, v in scope["headers"] if k not in (b"x-toc-role", b"x-toc-actor")]
                scope = dict(scope, headers=others + [(b"x-toc-role", actor.role.encode()), (b"x-toc-actor", actor.name.encode())])
            else:
                actor = Actor(role=hdrs.get(b"x-toc-role", b"").decode() or None, name=hdrs.get(b"x-toc-actor", b"").decode() or None)
            token = current_actor.set(actor)
            try:
                await self.app(scope, receive, send)
            finally:
                current_actor.reset(token)
        else:
            await self.app(scope, receive, send)


def seed_users(dataset: str) -> List[Dict[str, Any]]:
    """The prototype's directory: everyone gets the shape of their job; the Battle Captain and the admin see everything."""
    if dataset == "cab":
        return [
            {"id": "u_bc", "name": "MAJ Dakota Vance", "title": "Battle Captain, Brigade TOC", "preset": "battle_captain", "admin": True},
            {"id": "u_admin", "name": "CW3 Reese Okafor", "title": "Knowledge Manager (admin)", "preset": "battle_captain", "admin": True},
            {"id": "u_s4", "name": "MAJ Harper Lindqvist", "title": "Brigade S4", "preset": "logistics", "perms": {"S1": "view", "S2": "view", "S3": "view", "S6": "view"}},
            {"id": "u_supply", "name": "SSG Jordan Reyes", "title": "Supply Sergeant, A/5 ASB", "preset": "logistics", "team_id": "t_5asb_a"},
            {"id": "u_s2", "name": "CPT Morgan Nakamura", "title": "S2, 1st Attack", "preset": "analyst", "team_id": "t_1atk_hhc"},
            {"id": "u_s3", "name": "MAJ Casey Whitfield", "title": "Brigade S3", "preset": "ea", "perms": {"S2": "view", "S4": "view", "S6": "view"}},
            {"id": "u_s6", "name": "SFC Quinn Haddad", "title": "Signal NCO, C/5 ASB", "preset": "signal", "team_id": "t_5asb_c"},
            {"id": "u_s1", "name": "CPT Taylor Moreau", "title": "Brigade S1", "preset": "security", "perms": {"S3": "view"}},
        ]
    return [
        {"id": "u_bc", "name": "Nora Vale", "title": "Battle Captain, Watch Floor", "preset": "battle_captain", "admin": True},
        {"id": "u_admin", "name": "Sam Achterberg", "title": "GSOC Manager (admin)", "preset": "battle_captain", "admin": True},
        {"id": "u_ep", "name": "Dana Whitfield", "title": "Executive Protection Lead", "preset": "ep"},
        {"id": "u_analyst", "name": "R. Kovac", "title": "S2 Analyst", "preset": "analyst"},
        {"id": "u_ea", "name": "EA — Office of the CEO", "title": "Executive Assistant", "preset": "ea"},
        {"id": "u_sec", "name": "Lee Castellano", "title": "Security Lead, SF", "preset": "security"},
    ]
