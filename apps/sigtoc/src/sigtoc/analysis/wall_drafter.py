"""S2 drafter for the wall, CLUE-style: the model drafts prose and picks estimative terms from a fixed
list; *code* selects the evidence, computes analytic confidence, attaches numeric bands, and refuses
when there is nothing to assess. PRD §4.1.8 — the model may draft; it may not grade its own confidence.

Model path is used when TOC_DRAFTER=ai or ANTHROPIC_API_KEY is set; otherwise a deterministic
heuristic drafts, so the wall works with no key at all."""
import json
import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

ICD203_TERMS: Dict[str, str] = {
    "almost no chance": "01–05%", "very unlikely": "05–20%", "unlikely": "20–45%", "roughly even chance": "45–55%",
    "likely": "55–80%", "very likely": "80–95%", "almost certain": "95–99%",
}
TERM_ORDER = list(ICD203_TERMS)
SEVERITY_TO_TERM = {"low": "very unlikely", "moderate": "unlikely", "elevated": "roughly even chance", "critical": "likely"}
CONF_RANK = {"low": 0, "moderate": 1, "high": 2}
PROXIMITY_BUFFER_KM = 5.0
STALE_DAYS = 7
MODEL = os.environ.get("TOC_MODEL", "claude-opus-5")


def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def resolve_subject(snap: Dict[str, Any], subject_type: str, subject_id: str) -> Tuple[str, float, float, str, List[str]]:
    """→ (title, lat, lon, context, confirmed_threat_ids). KeyError if not found."""
    if subject_type == "trip":
        t = next(x for x in snap["trips"] if x["id"] == subject_id)
        p = next((x for x in snap["people"] if x["id"] == t["person_id"]), None)
        return (f"{t['person_name']} — {t['dest_name']}", t["dest_lat"], t["dest_lon"],
                f"Trip {t['id']}: {t['person_name']} ({'VIP' if t['is_vip'] else 'staff'}) to {t['dest_name']}, {t['depart_at']} → {t['return_at']}. Purpose: {t['purpose']}. Status: {t['status']}.",
                p["confirmed_threat_ids"] if p else [])
    if subject_type == "event":
        e = next(x for x in snap["events"] if x["id"] == subject_id)
        return (f"{e['name']} — {e['venue_name']}", e["venue_lat"], e["venue_lon"],
                f"Event {e['id']}: {e['name']} ({e['event_type']}) at {e['venue_name']}, {e['start_at']} → {e['end_at']}, {e['attendee_count']} attendees ({e['vip_count']} VIP, {e['security_count']} security). {e['description']}", [])
    if subject_type == "location":
        l = next(x for x in snap["locations"] if x["id"] == subject_id)
        return (f"{l['name']}", l["lat"], l["lon"],
                f"Site {l['id']}: {l['name']} ({l['type']}) in {l['city']}, {l['country']}. Posture {l['posture']} (effective {l['effective_posture']}). {l['present']} present / {l['assigned']} assigned, {l['security_on_shift']} security on shift, {l['vips_present']} VIP.",
                l["confirmed_threat_ids"])
    if subject_type == "pir":
        pir = next(x for x in snap["pirs"] if x["id"] == subject_id)
        if not pir.get("subject_type") or not pir.get("subject_id"):
            raise LookupError("PIR has no geographic subject")
        title, lat, lon, ctx, conf = resolve_subject(snap, pir["subject_type"], pir["subject_id"])
        return (f"{pir['id']} — {title}", lat, lon, f"PIR {pir['id']}: {pir['question']}\n{ctx}", conf)
    raise KeyError(subject_type)


def select_evidence(snap: Dict[str, Any], lat: float, lon: float, confirmed_ids: List[str]) -> List[Dict[str, Any]]:
    ev = []
    for t in snap["threats"]:
        d = _haversine(lat, lon, t["lat"], t["lon"])
        if d <= t["radius_km"] + PROXIMITY_BUFFER_KM or t["id"] in confirmed_ids:
            ev.append({"threat_id": t["id"], "title": t["title"], "source": t["source"], "confidence": t["confidence"],
                       "severity": t["severity"], "distance_km": round(d, 1), "observed_at": t["observed_at"],
                       "synthetic": t["synthetic"], "confirmed": t["id"] in confirmed_ids, "summary": t["summary"]})
    ev.sort(key=lambda e: (-{"low": 0, "moderate": 1, "elevated": 2, "critical": 3}[e["severity"]], e["distance_km"]))
    return ev


def compute_confidence(evidence: List[Dict[str, Any]], now: Optional[datetime] = None) -> Tuple[str, List[str]]:
    """Analytic confidence from the evidence chain — never from the model. Returns (level, reasons)."""
    if not evidence:
        return "insufficient", ["No qualifying collection inside the area of interest"]
    now = now or datetime.now(timezone.utc)
    sources = {e["source"] for e in evidence}
    best = max(CONF_RANK[e["confidence"]] for e in evidence)
    ages = []
    for e in evidence:
        try:
            ages.append((now - datetime.fromisoformat(e["observed_at"].replace("Z", "+00:00"))).days)
        except Exception:
            ages.append(0)
    reasons = [f"{len(evidence)} evidence item(s) from {len(sources)} independent source(s)",
               f"best source confidence: {['low', 'moderate', 'high'][best]}"]
    if min(ages) > STALE_DAYS:
        reasons.append(f"all evidence older than {STALE_DAYS} days — capped at low")
        return "low", reasons
    if len(sources) >= 3 and best == 2:
        return "high", reasons
    if len(sources) >= 2 and best >= 1:
        return "moderate", reasons
    return "low", reasons + ["single source or low-credibility reporting"]


def heuristic_term(evidence: List[Dict[str, Any]]) -> str:
    worst = max(evidence, key=lambda e: {"low": 0, "moderate": 1, "elevated": 2, "critical": 3}[e["severity"]])
    term = SEVERITY_TO_TERM[worst["severity"]]
    if worst["confirmed"]:
        term = TERM_ORDER[min(TERM_ORDER.index(term) + 1, len(TERM_ORDER) - 1)]
    return term


def _bump(term: str) -> str:
    return TERM_ORDER[min(TERM_ORDER.index(term) + 1, len(TERM_ORDER) - 1)]


def heuristic_draft(title: str, context: str, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    term = heuristic_term(evidence)
    top = evidence[0]
    judgments = [{"claim": f"Adverse security impact on {title} from '{top['title']}' during the window", "likelihood": term}]
    if len(evidence) > 1:
        judgments.append({"claim": f"Compounding effect from {len(evidence) - 1} additional reported threat(s) in area", "likelihood": "unlikely"})
    gaps = []
    if not any(e["confirmed"] for e in evidence):
        gaps.append("No analyst-confirmed linkage — all evidence is proximity-suggested")
    if all(e["synthetic"] for e in evidence):
        gaps.append("All evidence is synthetic seed data — no live collection on this subject")
    if len({e["source"] for e in evidence}) < 2:
        gaps.append("Single source — no corroboration")
    bluf = (f"Adverse impact on {title} is {term} ({ICD203_TERMS[term]}), driven by {top['title'].lower()} "
            f"({top['severity']} severity, {top['distance_km']} km). " + ("Standard protocols apply." if term in ("almost no chance", "very unlikely", "unlikely") else "Enhanced protocols recommended."))
    return {"bluf": bluf, "key_judgments": judgments, "gaps": gaps, "author": "rule:heuristic-drafter"}


SYSTEM = """You are the S2 duty intelligence analyst on a corporate security watch floor, drafting for a human reviewer.
Draft an assessment of the subject using ONLY the evidence provided. Rules you must not break:
- Every likelihood you state must be EXACTLY one of these terms: almost no chance, very unlikely, unlikely, roughly even chance, likely, very likely, almost certain.
- Do NOT state analytic confidence anywhere. Confidence is computed by the system from the evidence chain, not by you.
- Do NOT introduce facts, actors, or events that are not in the evidence. If the evidence is thin, say so in gaps.
- Bottom line first. Keep the BLUF to two sentences.
Respond with a single JSON object and nothing else:
{"bluf": string, "key_judgments": [{"claim": string, "likelihood": string}], "gaps": [string]}"""


async def model_draft(title: str, context: str, evidence: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Returns a draft dict or None if the model is unavailable/refuses/returns junk."""
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        return None
    payload = {"subject": title, "context": context,
               "evidence": [{k: v for k, v in e.items() if k in ("threat_id", "title", "summary", "source", "severity", "distance_km", "observed_at", "confirmed", "synthetic")} for e in evidence]}
    try:
        client = AsyncAnthropic()
        resp = await client.messages.create(
            model=MODEL, max_tokens=2048, system=SYSTEM,
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        )
        if resp.stop_reason == "refusal":
            return None
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start:end + 1])
        judgments = []
        for j in data.get("key_judgments", []):
            term = str(j.get("likelihood", "")).strip().lower()
            if term not in ICD203_TERMS:  # the model may not invent estimative language — fall back to the rubric
                term = heuristic_term(evidence)
            judgments.append({"claim": str(j.get("claim", "")).strip(), "likelihood": term})
        if not judgments:
            judgments = [{"claim": f"Adverse security impact on {title}", "likelihood": heuristic_term(evidence)}]
        return {"bluf": str(data.get("bluf", "")).strip() or heuristic_draft(title, context, evidence)["bluf"],
                "key_judgments": judgments, "gaps": [str(g) for g in data.get("gaps", [])], "author": f"ai:{MODEL}"}
    except Exception:  # noqa: BLE001 — any failure falls back to the deterministic drafter
        return None


def use_model() -> bool:
    return os.environ.get("TOC_DRAFTER", "").lower() == "ai" or bool(os.environ.get("ANTHROPIC_API_KEY"))


async def draft_for_subject(snap: Dict[str, Any], subject_type: str, subject_id: str) -> Dict[str, Any]:
    try:
        title, lat, lon, context, confirmed = resolve_subject(snap, subject_type, subject_id)
    except StopIteration:
        raise KeyError(subject_id)
    except LookupError as e:
        return _refusal(f"{subject_type} {subject_id}", [str(e)])
    evidence = select_evidence(snap, lat, lon, confirmed)
    confidence, reasons = compute_confidence(evidence)
    if confidence == "insufficient":
        return _refusal(title, reasons + [f"No threats within their reported radius (+{PROXIMITY_BUFFER_KM:.0f} km) of {title}"])
    draft = (await model_draft(title, context, evidence)) if use_model() else None
    if draft is None:
        draft = heuristic_draft(title, context, evidence)
    primary = draft["key_judgments"][0]["likelihood"]
    for j in draft["key_judgments"]:
        j["band"] = ICD203_TERMS[j["likelihood"]]
        j["confidence"] = confidence  # code-assigned, one level for the whole product
    return {"title": title, "likelihood": primary, "band": ICD203_TERMS[primary], "confidence": confidence,
            "confidence_basis": reasons, "bluf": draft["bluf"], "key_judgments": draft["key_judgments"],
            "evidence": [{k: v for k, v in e.items() if k != "summary"} for e in evidence], "gaps": draft["gaps"],
            "author": draft["author"], "refused": False}


def _refusal(title: str, reasons: List[str]) -> Dict[str, Any]:
    return {"title": title, "likelihood": "—", "band": "—", "confidence": "insufficient", "confidence_basis": reasons,
            "bluf": f"Insufficient basis to assess {title}. " + reasons[0] + ". This is a collection gap, not a finding.",
            "key_judgments": [], "evidence": [], "gaps": reasons, "author": "rule:refuse-to-assess", "refused": True}
