import math
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class UserReport(BaseModel):
    report_id: str
    content_id: str
    reporter_id: str
    reported_category: str
    notes: Optional[str] = None


class AggregatedReportQueueItem(BaseModel):
    content_id: str
    total_raw_reports: int = 0
    weighted_score: float = 0.0
    top_category: str
    unique_reporters: List[str] = Field(default_factory=list)
    requires_human_triage: bool = False


class ReportAggregator:
    """
    Anti-Brigading & Report Aggregator Engine:
    1. Aggregates 100 reports into 1 weighted queue item (avoids queue flooding).
    2. Weights reports by reporter credibility (historical uphold rate).
    3. User reports ALONE below threshold never alter visibility without corroboration.
    """

    def __init__(self, reporter_credibility_db: Optional[Dict[str, float]] = None):
        # Maps reporter_id -> credibility score (0.0 to 1.0, default 0.50)
        self.credibility_db = reporter_credibility_db or {}
        # Maps content_id -> AggregatedReportQueueItem
        self.aggregated_items: Dict[str, AggregatedReportQueueItem] = {}

    def get_reporter_credibility(self, reporter_id: str) -> float:
        return self.credibility_db.get(reporter_id, 0.50)

    def update_reporter_credibility(self, reporter_id: str, was_upheld: bool):
        current = self.get_reporter_credibility(reporter_id)
        # Bayesian/EMA adjustment
        delta = 0.05 if was_upheld else -0.05
        self.credibility_db[reporter_id] = max(0.05, min(0.99, current + delta))

    def ingest_report(self, report: UserReport, threshold: float = 3.0) -> AggregatedReportQueueItem:
        cid = report.content_id
        if cid not in self.aggregated_items:
            self.aggregated_items[cid] = AggregatedReportQueueItem(
                content_id=cid,
                top_category=report.reported_category,
            )

        item = self.aggregated_items[cid]
        # Ignore duplicate reports from the same reporter
        if report.reporter_id not in item.unique_reporters:
            item.unique_reporters.append(report.reporter_id)
            item.total_raw_reports += 1
            weight = self.get_reporter_credibility(report.reporter_id)
            # Logarithmic anti-brigading curve: diminishing returns on mass-reporting
            item.weighted_score += weight * (1.0 / math.log2(item.total_raw_reports + 1))

        if item.weighted_score >= threshold:
            item.requires_human_triage = True

        return item
