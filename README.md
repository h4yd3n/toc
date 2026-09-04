# TOC: Tactical Operations Center (Coptoc & Sigtoc)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/h4yd3n/toc/actions/workflows/test.yml/badge.svg)](https://github.com/h4yd3n/toc/actions/workflows/test.yml)

A unified **Tactical Operations Center (TOC)** combining:
- **`apps/coptoc`**: Trust & Safety / Policy-as-Code compiler, reach gates, and immutable audit ledger.
- **`apps/sigtoc`**: All-Source threat intelligence ingestion, STIX 2.1 entity resolution graph, and TOC alerts.
- **`packages/shared`**: Shared Pydantic schemas, telemetry, and STIX contracts.

## Layout — three modules, one repo

```
toc/
├── coptoc/            # The COP — the wall a Battle Captain runs a shift from
│   ├── api/           #   FastAPI: S1 personnel, S3 travel/events, S6 roll calls (contract: api/COP_API_CONTRACT.md)
│   ├── web/           #   React + MapLibre — the wall
│   └── ios/           #   SwiftUI + MapKit — the same wall on a phone
├── sigtoc/            # S2 — live collectors (GDACS), the CLUE-style drafter with refuse-to-assess, the intel→policy bridge
├── modtoc/            # Moderation engine — policy-as-code, severity × confidence routing, reach gates, evals. Separate tool.
├── shared/            # Models, database, the hash-chained ledger both APIs write to
├── tests/             # One folder per module + integration
├── PRD.md             # Product requirements — staff-section structure, decisions log
└── docs/archive/      # Superseded PRDs and the v1 MVP walkthrough (kept for the record)
```

**Coptoc** and **Sigtoc** are the product: the operations center. **Modtoc** is a different tool that shares the repo and the ledger — a content-moderation engine for a company that also runs a consumer platform. Sigtoc's `PolicyOverlayBridge` can feed it threat-driven policy updates; nothing in the COP depends on it.

## Quickstart

```bash
# Run all tests
make test

# The COP: API on :8000 and the wall on http://localhost:5173
make run-cop

# The moderation engine on :8001, and its policy-diff eval harness
make run-mod
make diff

# Or separately
make run-api
make run-web

# Native iOS on the booted simulator (needs xcodegen)
make ios-run

# Outbound SMS/Slack for roll calls and the S2 drafter are optional — copy .env.example and fill what you have.
# Unconfigured channels are recorded as SIMULATED, never as sent.

# Native clients build against coptoc/api/COP_API_CONTRACT.md
```
