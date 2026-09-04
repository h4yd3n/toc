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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await cop_startup()
    clock = asyncio.create_task(_intsum_clock()) if os.environ.get("TOC_INTSUM_CLOCK", "on") != "off" else None
    yield
    if clock: clock.cancel()


app = FastAPI(title="Coptoc — Common Operating Picture API", version="0.3.0",
              description="S1 personnel, S3 operations, S6 accountability; S2 via sigtoc. Contract: COP_API_CONTRACT.md",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(cop_router)
app.include_router(s2_router)  # Sigtoc embedded (Decision 3a); also runs standalone via sigtoc.api:app


@app.get("/v1/health")
def health():
    return {"status": "ok", "service": "coptoc"}
