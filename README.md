# TOC: Tactical Operations Center (Coptoc & Sigtoc)

[![CI](https://github.com/coptoc/toc/actions/workflows/test.yml/badge.svg)](https://github.com/coptoc/toc/actions)
[![Policy-Diff](https://github.com/coptoc/toc/actions/workflows/policy-diff.yml/badge.svg)](https://github.com/coptoc/toc/actions)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A unified **Tactical Operations Center (TOC)** combining:
- **`apps/coptoc`**: Trust & Safety / Policy-as-Code compiler, reach gates, and immutable audit ledger.
- **`apps/sigtoc`**: All-Source threat intelligence ingestion, STIX 2.1 entity resolution graph, and TOC alerts.
- **`packages/shared`**: Shared Pydantic schemas, telemetry, and STIX contracts.

## Architecture

```
TOC/
├── apps/
│   ├── cop-web/       # The wall — React + MapLibre common operating picture (S1/S2/S3/S6)
│   ├── cop-ios/       # Native iOS client — SwiftUI + MapKit, same /v1/cop contract
│   ├── coptoc/        # COP API (/v1/cop, contract in COP_API_CONTRACT.md) + Policy-as-Code moderation engine
│   └── sigtoc/        # S2 — live collectors (GDACS) and the CLUE-style drafter with refuse-to-assess
├── packages/
│   └── shared/        # Shared models, database layer, & constants
├── PRD.md             # Product requirements — staff-section structure, scope tags
└── tests/             # Unit and integration test suite
```

## Quickstart

```bash
# Run all tests
make test

# Run policy-diff eval harness
make diff

# Start the COP: API on :8000 and the wall on http://localhost:5173
make run-cop

# Or separately
make run-api
make run-web

# Native iOS on the booted simulator (needs xcodegen)
make ios-run

# Outbound SMS/Slack for roll calls and the S2 drafter are optional — copy .env.example and fill what you have.
# Unconfigured channels are recorded as SIMULATED, never as sent.

# Native clients build against apps/coptoc/COP_API_CONTRACT.md
```
