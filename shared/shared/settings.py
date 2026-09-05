"""Operator settings and keys, entered from the wall (PRD §11.3).

Where a key comes from, in order: the process environment (12-factor, wins always), then this store (entered by a
Battle Captain from the SETTINGS panel, kept encrypted at rest). Values are write-only: the API reports whether a key
is set and by whom, never the value. The ledger records that a key was set, never what it was.

Encryption is Fernet keyed from `TOC_SECRET` — the same secret that signs the check-in links — so a deployment that
changed that one value (README, "Before you deploy") has protected these too. The dev default is not a secret."""
from __future__ import annotations

import base64
import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

# What the wall can set. `secret` values are never echoed; `needed_by` ties a key to the source or channel it unlocks.
KNOWN: List[Dict[str, Any]] = [
    {"name": "ACLED_API_KEY",      "label": "ACLED API key",        "group": "sources", "secret": True,  "needed_by": ["acled"],  "help": "Free key from acleddata.com; pairs with ACLED_EMAIL."},
    {"name": "ACLED_EMAIL",        "label": "ACLED account email",  "group": "sources", "secret": False, "needed_by": ["acled"],  "help": "The email the ACLED key was issued to."},
    {"name": "CLSTR_API_KEY",      "label": "CLSTR API key",        "group": "sources", "secret": True,  "needed_by": ["clstr"],  "help": "Free key, 100 requests/day."},
    {"name": "ANTHROPIC_API_KEY",  "label": "Anthropic API key",    "group": "drafter", "secret": True,  "needed_by": ["drafter"], "help": "Turns on the S2 drafter for assessments and INTSUM prose. Off = human drafts only."},
    {"name": "TOC_MODEL",          "label": "Drafter model",        "group": "drafter", "secret": False, "needed_by": ["drafter"], "help": "Default claude-opus-5."},
    {"name": "TWILIO_ACCOUNT_SID", "label": "Twilio account SID",   "group": "comms",   "secret": True,  "needed_by": ["sms"],    "help": "With the auth token and a From number, roll-call SMS goes out for real."},
    {"name": "TWILIO_AUTH_TOKEN",  "label": "Twilio auth token",    "group": "comms",   "secret": True,  "needed_by": ["sms"],    "help": ""},
    {"name": "TWILIO_FROM",        "label": "Twilio From number",   "group": "comms",   "secret": False, "needed_by": ["sms"],    "help": "E.164, e.g. +14155550100."},
    {"name": "SLACK_WEBHOOK_URL",  "label": "Slack incoming webhook", "group": "comms", "secret": True,  "needed_by": ["chat"],   "help": "Roll-call broadcasts to a channel."},
    {"name": "TOC_PUBLIC_URL",     "label": "Public URL",           "group": "comms",   "secret": False, "needed_by": ["sms", "chat"], "help": "Where check-in links point. Must be reachable from a phone."},
    {"name": "TOC_SECTIONS",       "label": "Staff sections",       "group": "sections", "secret": False, "needed_by": [],       "help": "Comma list. S1,S2,S3 always on; add S4,S6 for an operations center."},
    {"name": "TOC_SECTION_TITLES", "label": "Section titles",       "group": "sections", "secret": False, "needed_by": [],       "help": "Renames, e.g. S4=SUPPLY,S6=COMMS."},
]
KNOWN_BY_NAME = {k["name"]: k for k in KNOWN}


class SettingRow(Base):
    __tablename__ = "toc_settings"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    value_enc: Mapped[str] = mapped_column(Text)
    set_by: Mapped[str] = mapped_column(String, default="operator")
    set_at: Mapped[datetime] = mapped_column(DateTime)


_overlay: Dict[str, str] = {}      # decrypted stored values, loaded at startup and kept current by store()/clear()
_meta: Dict[str, Dict[str, Any]] = {}


def _fernet():
    from cryptography.fernet import Fernet
    secret = os.environ.get("TOC_SECRET", "dev-only-secret-change-me").encode()
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret).digest()))


def get(name: str, default: Optional[str] = None) -> Optional[str]:
    """The environment first, then the store. Empty strings count as unset."""
    v = os.environ.get(name)
    if v:
        return v
    return _overlay.get(name) or default


def source_of(name: str) -> Optional[str]:
    if os.environ.get(name):
        return "env"
    if _overlay.get(name):
        return "stored"
    return None


async def load(session: AsyncSession) -> int:
    """Read every stored value into the overlay. A value that will not decrypt (TOC_SECRET changed) is dropped and reported as unset."""
    f = _fernet()
    _overlay.clear(); _meta.clear()
    for row in (await session.execute(select(SettingRow))).scalars():
        try:
            _overlay[row.name] = f.decrypt(row.value_enc.encode()).decode()
            _meta[row.name] = {"set_by": row.set_by, "set_at": row.set_at.strftime("%Y-%m-%dT%H:%M:%SZ")}
        except Exception:
            _meta[row.name] = {"set_by": row.set_by, "set_at": None, "error": "will not decrypt under the current TOC_SECRET"}
    return len(_overlay)


async def store(session: AsyncSession, name: str, value: str, actor: str) -> None:
    if name not in KNOWN_BY_NAME:
        raise KeyError(name)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row = await session.get(SettingRow, name)
    enc = _fernet().encrypt(value.encode()).decode()
    if row:
        row.value_enc, row.set_by, row.set_at = enc, actor, now
    else:
        session.add(SettingRow(name=name, value_enc=enc, set_by=actor, set_at=now))
    await session.commit()
    _overlay[name] = value
    _meta[name] = {"set_by": actor, "set_at": now.strftime("%Y-%m-%dT%H:%M:%SZ")}


async def clear(session: AsyncSession, name: str) -> bool:
    row = await session.get(SettingRow, name)
    if row:
        await session.delete(row); await session.commit()
    _overlay.pop(name, None); _meta.pop(name, None)
    return row is not None


def status() -> List[Dict[str, Any]]:
    """What the wall shows: never a value. For non-secrets the value is shown; for secrets only that it is set."""
    out = []
    for k in KNOWN:
        src = source_of(k["name"])
        out.append({**k, "set_in": src, "value": (get(k["name"]) if not k["secret"] and src else None),
                    "hint": (f"…{get(k['name'])[-4:]}" if k["secret"] and src and len(get(k["name"]) or "") >= 8 else None),
                    **({"set_by": _meta[k["name"]].get("set_by"), "set_at": _meta[k["name"]].get("set_at"), "error": _meta[k["name"]].get("error")} if k["name"] in _meta else {})})
    return out
