"""A real sign-in in front of the profile picker (README, "Before you deploy").

The prototype's identity is a profile the client names in `X-TOC-User`, which is exactly what a demo wants and exactly
what a deployment must not have. This module adds the layer in front, without taking the demo away:

* a password per user, hashed with scrypt and never returned;
* `POST /v1/auth/login` exchanges a password for a **bearer token** signed with `TOC_SECRET` and carrying an expiry;
* the identity middleware accepts that token and resolves the same `Actor` the rest of the API already checks, so
  every permission rule downstream is unchanged;
* `TOC_AUTH=on` closes the door: header-only identity stops working, and the API refuses to start with the dev secret
  or with an open CORS policy. Off by default, so the prototype, the phones and the test suite behave as before.

What this is not: an identity provider. There is no SSO, no refresh, no device binding, no lockout, and one shared
secret signs every token. It is a lock on the door of a building that still needs an alarm (README).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from .users import UserRow, current_actor, lookup, _out, _cache

router = APIRouter(prefix="/v1/auth", tags=["sign-in"])

DEV_SECRET = "dev-only-secret-change-me"
TOKEN_HOURS = 12                      # one watch; a longer one is a decision a deployment makes, not a default
SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}


def secret() -> bytes:
    return os.environ.get("TOC_SECRET", DEV_SECRET).encode()


def auth_required() -> bool:
    """Whether the door is closed. Off by default: the prototype signs in by picking a profile."""
    return os.environ.get("TOC_AUTH", "off").lower() in ("on", "1", "true", "required")


def allowed_origins() -> list[str]:
    raw = os.environ.get("TOC_ALLOWED_ORIGINS", "").strip()
    return [o.strip() for o in raw.split(",") if o.strip()] or ["*"]


def startup_guard() -> None:
    """Refuse to run a closed deployment on open defaults. Called at startup; it raises rather than warning, because a
    warning in a log nobody reads is how the dev secret ends up signing production tokens."""
    if not auth_required():
        return
    if secret() == DEV_SECRET.encode():
        raise RuntimeError("TOC_AUTH is on but TOC_SECRET is the dev default. Set a real secret before starting.")
    if allowed_origins() == ["*"]:
        raise RuntimeError("TOC_AUTH is on but TOC_ALLOWED_ORIGINS is unset. Name the origins that may call this API.")


# ---------------------------------------------------------------- passwords

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **SCRYPT)
    return "scrypt$%d$%d$%d$%s$%s" % (SCRYPT["n"], SCRYPT["r"], SCRYPT["p"], base64.b64encode(salt).decode(), base64.b64encode(digest).decode())


def verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored or not stored.startswith("scrypt$"):
        return False
    try:
        _, n, r, p, salt, digest = stored.split("$")
        want = base64.b64decode(digest)
        got = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=len(want))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got, want)


# ---------------------------------------------------------------- tokens

def issue(user_id: str, password_set_at: Optional[datetime], hours: int = TOKEN_HOURS) -> Dict[str, Any]:
    """A compact signed token: who, when it expires, and when the password it was issued against was set — changing a
    password invalidates every token issued before it, without a session table to keep."""
    # milliseconds, not seconds: two password writes inside one second must still produce different tokens
    payload = {"u": user_id, "exp": int(time.time()) + hours * 3600, "pw": int(password_set_at.timestamp() * 1000) if password_set_at else 0}
    body = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True).encode()).rstrip(b"=")
    sig = base64.urlsafe_b64encode(hmac.new(secret(), body, hashlib.sha256).digest()).rstrip(b"=")
    return {"token": (body + b"." + sig).decode(), "expires_at": datetime.fromtimestamp(payload["exp"], timezone.utc).replace(tzinfo=None).isoformat() + "Z"}


def read_token(token: str) -> Optional[Dict[str, Any]]:
    """The payload if the signature holds and it has not expired, else None. Never raises on malformed input."""
    try:
        body, sig = token.encode().split(b".")
        expected = base64.urlsafe_b64encode(hmac.new(secret(), body, hashlib.sha256).digest()).rstrip(b"=")
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + b"=" * (-len(body) % 4)))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    return payload if int(payload.get("exp", 0)) > time.time() else None


def user_for_token(token: str) -> Optional[Dict[str, Any]]:
    payload = read_token(token)
    if not payload:
        return None
    user = lookup(payload.get("u"))
    if not user:
        return None
    if int(payload.get("pw", 0)) != int(user.get("password_set_at_ts") or 0):
        return None   # the password changed after this token was issued
    return user


# ---------------------------------------------------------------- the endpoints

class Login(BaseModel):
    user_id: str
    password: str = Field(min_length=1, max_length=512)


class SetPassword(BaseModel):
    user_id: str
    password: str = Field(min_length=12, max_length=512)
    current_password: Optional[str] = None


async def session_dep():
    from .routes import sessions
    async with sessions()() as session:
        yield session


@router.get("/status")
def auth_status():
    """What the client needs to know before it shows a sign-in box or a profile list."""
    return {"required": auth_required(), "token_hours": TOKEN_HOURS, "scheme": "bearer"}


@router.post("/login")
async def login(body: Login, session: AsyncSession = Depends(session_dep)):
    row = await session.get(UserRow, body.user_id)
    ok = row is not None and row.active and verify_password(body.password, row.password_hash)
    if not ok:
        raise HTTPException(401, "Sign-in failed")   # never say which half was wrong
    token = issue(row.id, row.password_set_at)
    return {**token, "me": {k: _out(row)[k] for k in ("id", "name", "title", "preset", "perms", "battle_captain", "admin")}}


@router.post("/password")
async def set_password(body: SetPassword, session: AsyncSession = Depends(session_dep), x_toc_actor: Optional[str] = Header(None)):
    """An admin sets anyone's password; anyone sets their own by giving the current one. With the door open (the
    prototype's default) the first password on an account may be set by an admin profile, which is how a deployment
    bootstraps before it turns `TOC_AUTH` on."""
    actor = current_actor.get()
    row = await session.get(UserRow, body.user_id)
    if not row:
        raise HTTPException(404, "User not found")
    own = actor.user and actor.user["id"] == row.id
    if not actor.is_admin and not own:
        raise HTTPException(403, "An admin sets another user's password")
    if own and row.password_hash and not verify_password(body.current_password or "", row.password_hash):
        raise HTTPException(403, "The current password is required to change it")
    row.password_hash = hash_password(body.password)
    row.password_set_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.commit()
    _cache[row.id] = _out(row)
    from sigtoc.api import ledger
    await ledger().append_event(content_id=row.id, event_type="toc.user.password_set", actor_type="human",
                                actor_id=x_toc_actor or actor.name, reason=f"password set for {row.name}")
    return {"user_id": row.id, "password_set": True, "sessions_invalidated": True}
