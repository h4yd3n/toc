import os
from typing import Dict, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from shared.models import ContentItem, ModerationDecision, LedgerEvent
from coptoc.compiler.validator import PolicyValidator
from coptoc.engine.router import ModerationRouter
from coptoc.intake.report_aggregator import ReportAggregator, UserReport
from coptoc.ledger.event_stream import ImmutableEventLedger
from coptoc.cop.routes import router as cop_router, startup as cop_startup
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await cop_startup()
    yield

app = FastAPI(
    title="TOC API — COP + Trust & Safety Engine",
    version="0.1.0",
    description="Common Operating Picture (S1/S2/S3) plus Policy-as-Code moderation engine",
    lifespan=lifespan,
)

validator = PolicyValidator()
policy_file = os.path.join(os.path.dirname(__file__), "../../../policies/hate_speech.yaml")
policy = validator.validate_policy_file(policy_file)
ledger = ImmutableEventLedger()
router = ModerationRouter(policy=policy, ledger=ledger)
aggregator = ReportAggregator()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(cop_router)


class ModerateRequest(BaseModel):
    content_id: str
    author_id: str
    text: str
    view_count: int = 0


@app.get("/v1/health")
def health_check():
    return {"status": "ok", "policy_loaded": policy.get("policy_id"), "version": policy.get("version")}


@app.post("/v1/moderate", response_model=ModerationDecision)
def moderate_content(req: ModerateRequest):
    item = ContentItem(
        content_id=req.content_id,
        author_id=req.author_id,
        text=req.text,
        view_count=req.view_count,
    )
    decision = router.process_content(item)
    return decision


@app.post("/v1/report")
def submit_report(report: UserReport):
    aggregated = aggregator.ingest_report(report)
    return {"status": "received", "queue_item": aggregated}


@app.get("/v1/content/{content_id}/history", response_model=List[LedgerEvent])
def get_content_history(content_id: str):
    history = ledger.get_content_history(content_id)
    if not history:
        raise HTTPException(status_code=404, detail="No event history found for content_id")
    return history
