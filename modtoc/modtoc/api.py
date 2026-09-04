import os
from typing import Dict, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from shared.models import ContentItem, ModerationDecision, LedgerEvent
from modtoc.compiler.validator import PolicyValidator
from modtoc.engine.router import ModerationRouter
from modtoc.intake.report_aggregator import ReportAggregator, UserReport
from shared.ledger import ImmutableEventLedger

app = FastAPI(
    title="Modtoc — Moderation Engine API",
    version="0.1.0",
    description="Policy-as-Code compiler, severity × confidence routing, reach gates, audit ledger",
)

validator = PolicyValidator()
policy_file = os.path.join(os.path.dirname(__file__), "..", "policies", "hate_speech.yaml")
policy = validator.validate_policy_file(policy_file)
ledger = ImmutableEventLedger()
router = ModerationRouter(policy=policy, ledger=ledger)
aggregator = ReportAggregator()



class ModerateRequest(BaseModel):
    content_id: str
    author_id: str
    text: str
    view_count: int = 0


@app.get("/v1/health")
def health_check():
    return {"status": "ok", "service": "modtoc", "policy_loaded": policy.get("policy_id"), "version": policy.get("version")}


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
