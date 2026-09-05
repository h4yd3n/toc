import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sigtoc.api import router as s2_router
from .routes import router as cop_router, startup as cop_startup


async def _intsum_clock() -> None:
    """Decision G: the INTSUM drafts itself at the fixed hour. Checks every ten minutes; idempotent per day."""
    from sigtoc.api import draft_if_due, sessions as s2_sessions
    while True:
        try:
            async with s2_sessions()() as session:
                await draft_if_due(session)
        except Exception:  # noqa: BLE001 — a failed draft must not kill the clock; the next tick retries
            pass
        await asyncio.sleep(600)


async def _escalation_clock() -> None:
    """Decision M: every minute, names with no response for 15 minutes go UNREACHABLE by rule."""
    from .routes import escalate_due, sessions
    while True:
        try:
            async with sessions()() as session:
                await escalate_due(session)
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await cop_startup()
    from shared import settings as _settings
    from .routes import _sessions as _S
    async with _S() as s:
        await _settings.load(s)
    clocks = []
    if os.environ.get("TOC_INTSUM_CLOCK", "on") != "off":
        clocks.append(asyncio.create_task(_intsum_clock()))
    if os.environ.get("TOC_ESCALATION_CLOCK", "on") != "off":
        clocks.append(asyncio.create_task(_escalation_clock()))
    yield
    for c in clocks: c.cancel()


app = FastAPI(title="Coptoc — Common Operating Picture API", version="0.3.0",
              description="S1 personnel, S3 operations, S6 accountability; S2 via sigtoc. Contract: COP_API_CONTRACT.md",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class MethodOverride:
    """Android's HttpURLConnection cannot send PATCH; it sends POST with X-HTTP-Method-Override: PATCH."""
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("method") == "POST":
            for k, v in scope.get("headers", []):
                if k == b"x-http-method-override" and v.upper() in (b"PATCH", b"DELETE", b"PUT"):
                    scope = dict(scope, method=v.decode().upper()); break
        await self.app(scope, receive, send)


app.add_middleware(MethodOverride)
app.include_router(cop_router)
app.include_router(s2_router)  # Sigtoc embedded (Decision 3a); also runs standalone via sigtoc.api:app


@app.get("/v1/health")
def health():
    return {"status": "ok", "service": "coptoc"}
