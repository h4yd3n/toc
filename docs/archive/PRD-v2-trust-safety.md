# TOC — Product Requirements Document

**Version:** 2.0 (travel-risk scope removed)
**Date:** 2026-08-29

> [!NOTE]
> **Every section is tagged with where it came from, so you know what you can defend:**
>
> - **[DOCTRINE]** — established intelligence tradecraft. Defensible from your own experience and from published standards (ICD 203, Admiralty/STANAG 2511).
> - **[BUILT]** — exists and runs in this repository today.
> - **[NEEDS RULING]** — a judgment call nobody has made yet. Do not ship it until you decide it.

---

## 1. What This Is

**TOC is a trust & safety decision support system that applies intelligence tradecraft to platform abuse.**

When an analyst investigates a suspected abuse campaign, TOC tracks where every piece of evidence came from, how good that evidence is, and how confident the resulting assessment can honestly be. When the evidence is too thin to support a conclusion, it says so instead of producing one.

The output is a decision an analyst can defend six months later: what was known, when, from which sources, and who signed it.

---

## 2. The Problem

Platform trust & safety teams make high-consequence decisions at speed, and the reasoning behind them is usually not preserved.

- Enforcement decisions get made and logged, but the *evidence* behind them does not survive in reviewable form
- Source quality and analytic confidence get collapsed into a single hedge — "we think this is coordinated" — which hides whether that came from one weak signal or five strong ones
- When AI assists, its judgments are indistinguishable from grounded ones, because nothing separates what was observed from what was inferred
- Nothing structurally prevents a confident-sounding conclusion built on nothing

Intelligence organizations solved these problems decades ago, and the solutions are published. They are not applied here.

---

## 3. Who It's For

**The Response Lead** — runs the watch floor. Handles escalations, owns decision quality across a shift, hands over to the next shift. Needs to know what's open, what changed, and what requires judgment now.

**The Investigator** — works cases. Needs to gather evidence, track what's missing, and produce an assessment that survives review by Legal and Policy.

**The Policy Owner** — turns findings into rules. Needs to know which evidence supports a proposed policy change and how confident that evidence is.

---

## 4. The Core Idea: Evidence Discipline

This is the whole product. Everything else is plumbing.

### 4.1 Three Confidence Axes **[DOCTRINE]**

Every claim carries three separate ratings. They are never collapsed into one.

**Axis 1 — Source Reliability (A–F).** A property of the *source*, from its track record.

| Grade | Meaning |
| :--- | :--- |
| A | Completely reliable |
| B | Usually reliable |
| C | Fairly reliable |
| D | Not usually reliable |
| E | Unreliable — history of being wrong |
| F | Cannot be judged — new or unknown source |

**Axis 2 — Information Credibility (1–6).** A property of *this specific report*.

| Grade | Meaning |
| :--- | :--- |
| 1 | Confirmed by independent sources |
| 2 | Probably true |
| 3 | Possibly true |
| 4 | Doubtful |
| 5 | Improbable — contradicted by other information |
| 6 | Cannot be judged |

Together: the standard two-character rating. A `B2` is a usually-reliable source reporting probably-true information.

`E` and `F` are different — a source with a record of being wrong is worse than an unknown one. `5` and `6` are different for the same reason.

**Axis 3 — Analytic Confidence (ICD 203).** A property of *our judgment*, not of any source. High / Moderate / Low / Insufficient.

### 4.2 Confidence Is Not Probability **[DOCTRINE]**

**Analytic confidence** describes the strength of our evidence and reasoning.
**Estimative probability** describes how likely the thing is.

They are independent. High confidence that something is unlikely is a normal, coherent assessment.

Forecast language uses only these terms, with fixed bands:

| Term | Range |
| :--- | :--- |
| almost no chance | 01–05% |
| very unlikely | 05–20% |
| unlikely | 20–45% |
| roughly even chance | 45–55% |
| likely | 55–80% |
| very likely | 80–95% |
| almost certain | 95–99% |

Every judgment states both axes:

> *"This account cluster is **likely** (55–80%) coordinated. **Moderate confidence** — three independent behavioral signals rated B2, C2, C3; no infrastructure linkage observed, which is the main gap."*

### 4.3 Refuse to Assess **[DOCTRINE]**

When the evidence cannot support a conclusion, TOC states the gap instead of producing one.

> *"Insufficient basis to assess coordination. Two of three required indicator categories have no qualifying evidence: shared infrastructure and temporal clustering."*

A claim with no evidence attached is `INSUFFICIENT` by definition — enforced by the data model (§7), not by discipline.

This is the most important behavior in the product. A system that produces a confident, well-formatted conclusion from thin evidence is worse than no system, because it launders a guess into something that looks like analysis.

> [!IMPORTANT]
> **[NEEDS RULING]** What threshold triggers refusal? "More than X% of required indicators unmet" needs a number, and it should be yours, not an invented one.

---

## 5. The Workflow

```
   Question / Case
         │
         ▼
   Break into what you'd need to know  ──────► what's missing
         │
         ▼
   Collect ──► Grade each item (A–F, 1–6)
         │
         ▼
   Draft assessment ──► or REFUSE if evidence is thin
         │
         ▼
   Human reviews and signs
         │
         ├──► Enforcement decision (routed by severity × confidence)
         ├──► Policy update
         └──► Ledger entry — tamper-evident record
```

### 5.1 Framing the Question **[DOCTRINE]**

A question is decomposed before collection starts:

```
Question:  "Is this a coordinated campaign or organic activity?"
   └── What would I need to know?
        └── Observable indicators
             └── Which source could show me that
```

An indicator has to be specific enough that you know what you're looking for. "Suspicious behavior" is not an indicator. "Accounts created within the same 48-hour window posting identical media hashes" is.

**The unanswered indicators are the collection gap**, and they are what drives §4.3.

---

## 6. What the AI May and May Not Do **[DOCTRINE]**

The AI drafts. Humans decide.

**May:**
- Extract structured facts from unstructured text
- Cluster and classify observed behavior
- Draft assessments in the standard format
- Select an estimative term from the seven in §4.2 — only from that list
- Identify which indicators have no evidence

**May not:**
- Assign source reliability grades — that's a track record, set by an analyst
- Grade its own analytic confidence — computed from the evidence chain
- Override a refusal by filling the gap with its own knowledge
- Invent estimative language outside the fixed list
- Make the enforcement decision
- Publish anything without a human signature

**Why:** when someone asks "why did we take this down," the answer has to trace to dated evidence and a named human — not to "the model thought so."

---

## 7. Decision Routing **[BUILT]**

Already working in `apps/coptoc`:

- **Policy-as-code** — policies written as YAML, compiled into classifier prompts and a routing table
- **Severity × confidence routing** — the decision matrix resolves severity and confidence into an enforcement action
- **Reach gates** — escalating mandatory review as content spreads: 300 → 3K → 30K → 300K → 3M views. Higher reach forces stronger verification, up to mandatory human sign-off. This structurally bounds worst-case harm at viral scale.
- **Immutable ledger** — hash-chained, append-only. Every decision and state transition recorded with `prev_hash` chaining.
- **Report aggregation** — anti-brigading logic so mass reporting can't drive enforcement on its own

This half of the repo works, has tests, and needs no redesign.

---

## 8. Output Products

All follow: **bottom line first, evidence second, gaps last.**

| Product | Purpose |
| :--- | :--- |
| **Case Assessment** | The finding on one investigation, with confidence stated per §4.2 |
| **Escalation Narrative** | What happened, what we know, what we recommend — written for Legal and Policy |
| **Shift Summary** | What changed, what's open, what needs judgment — for handover |
| **Policy Recommendation** | A proposed rule change, with the evidence supporting it |

---

## 9. Data Model

**Collection — append-only, never edited:**

| Entity | Key Fields |
| :--- | :--- |
| `Source` | `source_id`, `name`, `reliability` (A–F) |
| `Signal` | `signal_id`, `source_id`, `credibility` (1–6), `raw_text`, `url`, `observed_at`, `collected_at`, `content_hash`, `origin_key` |

`origin_key` collapses duplicate reporting of the same underlying fact, so "three independent sources" means three, not one story repeated.

**Investigation:**

| Entity | Key Fields |
| :--- | :--- |
| `Case` | `case_id`, `question`, `status`, `owner`, `opened_at` |
| `Indicator` | `indicator_id`, `case_id`, `description`, `status` (unmet / met) |
| `Assessment` | `assessment_id`, `case_id`, `analytic_confidence`, `status` (draft → review → approved), `author`, `reviewer_id`, `approved_at` |
| `Judgment` | `assessment_id`, `claim`, `estimative_term`, `analytic_confidence` |
| **`Evidence`** | `judgment_id`, `signal_id`, `quote`, `retrieved_at` |

`Evidence` is the join table that makes the whole thing honest. **A `Judgment` with zero `Evidence` rows cannot be published.** Traceability is enforced by schema, not by good intentions.

**Decision:** `ModerationDecision`, `LedgerEvent` — both **[BUILT]**.

---

## 10. Explicitly Out of Scope

Cut deliberately, not deferred:

- Executive travel risk assessment
- Common Operating Picture, map, blue force tracker
- Physical and geopolitical threat scoring
- METT-TC and PMESII-PT frameworks
- The eight risk dimensions, half-lives, proximity math, mitigation credits — **all of it was invented, none of it survives**
- Country and region profiles

Physical risk assessment is human analyst work and does not need this system.

---

## 11. Open Decisions

Yours to make. Nothing ships until they're answered.

1. **What triggers a refusal?** (§4.3) — how much missing evidence is too much
2. **What's the first case type?** Coordinated inauthentic behavior, or something narrower
3. **Which sources, and what does each get graded?** Source reliability is a judgment call from track record — yours
4. **Does the AI draft at all in v1,** or does it only collect and grade while you write the assessment
5. **Is `Case` or `Assessment` the primary object** — do you work cases, or answer questions

---

## Appendix: What Changed From v1

v1 (archived as `PRD-v1-travel-risk-ARCHIVE.md`) described a corporate security platform for executive travel risk, with a map-based common operating picture. That scope is removed.

The tradecraft — confidence axes, refusal to overstate, evidence traceability, the AI boundary — carried forward unchanged, because that part was doctrine and not invention. The scoring mathematics did not carry forward, because it was invented.
