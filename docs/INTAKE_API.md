# Administrative intake and embedded workspaces

Updated 2026-09-08. This records implemented behavior, not completion of every milestone in the [AI Operations Center Plan](AI_OPERATIONS_CENTER_PLAN.md).

## User flow

Open Workspaces → Logistics → Overview. Choose the submission's destination and paste a delivery update or attach a text-based PDF. The source is saved first; processing continues in the existing background worker. Provider failures are visible and can be retried after configuration is corrected.

The review screen places source text beside current/proposed values and page-linked quotations. Existing shipments match by reference within the selected destination. Ambiguous references and new records require explicit clarification. Edit / resolve saves a new comparison; Approve & apply is a separate action. Each shipment is one atomic proposal, so independent shipments can be approved or rejected separately. Questions can be deferred by leaving a proposal pending.

The extractor supports description, reference, quantity including units, ETA, delivery status, carrier, and note. It does not change inventory or route movements. New shipments require a reference, description, timezone-aware ETA, status, and explicit creation confirmation. Users can correct extracted values; originals and review history remain available. Source quotation matching is traceability, not proof of truth.

## Limits and permissions

- One existing, nonrestricted destination per submission. Multi-destination documents need separate submissions and human clarification.
- Pasted text: 10–60,000 characters. PDF: at most 2 MB, 20 pages, and 60,000 extracted characters. Encrypted PDFs, empty/scanned pages, and non-PDF uploads are rejected. OCR, images, voice and live streams are not implemented.
- Up to 30 extracted shipments per provider response; at most seven supported fields per shipment. Oversized or invalid model output fails rather than being partially applied.
- All intake reads require S4 view permission; submitting, retrying, and decisions require S4 edit permission. Original downloads have the same checks. Site restrictions are checked at submission, before and after the provider call, at review, and on later reads.
- Original source access is section/site scoped, not private to its uploader. Users must choose the appropriate scope for the supplied document. Documents and proposal history are persisted in the application database. Automated retention/purge and isolated parser resource controls remain release-hardening work.
- Prototype identities are still selectable profiles. The embedded `profile` URL parameter is a profile ID, not an authentication credential. Real sign-in and separate contribute/review/release permission levels remain open.

## Endpoints

| Request | Behavior |
| --- | --- |
| `POST /v1/intake/text` | JSON `{text, location_id}`. Saves source and queues extraction. Same content/destination returns the existing submission. |
| `POST /v1/intake/file` | Multipart `file` and `location_id`. Validates and extracts PDF pages before queueing. |
| `GET /v1/intake` | Most recent 100 submissions, filtered by access, with pending/applied counts and public provider status. |
| `GET /v1/intake/{id}` | Saved source pages, proposals, questions, evidence, and review history. |
| `GET /v1/intake/{id}/source` | Authorized original download with `Cache-Control: no-store`. |
| `POST /v1/intake/{id}/retry` | Requeues a failed submission under the requesting editor's current identity. |
| `PATCH /v1/intake/{id}/proposals/{proposal_id}` | `{revision, action: save|apply|reject, values?, target_id?, create_new?, note?}`. Corrections require a note and must be saved before applying. |
| `GET /v1/intake/monitor/findings` | Deterministic overdue-delivery record findings, last check, status and decision history. |
| `PATCH /v1/intake/monitor/findings/{id}` | `{revision, action: dismiss|snooze|reopen, note}`. Snooze lasts 24 hours. |

Submission processing states are queued, processing, failed, and review. Responses show resolved when every proposal is applied/rejected/unchanged. Proposals are needs_clarification, ready, applied, rejected, unchanged, or conflict. Applied/rejected/unchanged proposals are immutable. Repeating a successful apply with its prior revision returns the applied result without another write.

Applying updates compares the saved record snapshot with current fields and timestamps. Concurrent edits produce a conflict, requiring a refreshed comparison. Each proposal revision is claimed atomically. Reference claims serialize intake-created destination/reference identities across workers; failed application rolls its claim back. Shared shipment helpers are used by manual APIs and intake. Canonical changes and proposal history commit together. Intake decisions currently live in proposal history rather than the general battle log.

## Worker and monitoring

The existing Coptoc AI worker invokes intake and administrative checks. `TOC_AI_WORKER=off` disables these along with analysis jobs. Intake claims at most one submission per tick, recovers leases older than five minutes, and caps processing at three attempts. Transport errors, HTTP 429 and HTTP 5xx retry with delay. A stale worker cannot publish a recovered lease's result. The provider remains configurable and defaults off; there is no synthetic runtime fallback.

Monitoring checks whether a shipment's recorded ETA has passed while its status is planned, in transit, or delayed. It makes no provider call and does not claim physical delivery knowledge. Unchanged findings retain dismissals/snoozes. A changed ETA/status/site reopens the finding; arrival/cancellation resolves it. This is one administrative check, not the full planned monitoring library. Evaluation runs serially with existing analysis work; last-check timestamps reveal delays/staleness.

## In-app console

Build the web app **before starting the API**:

```sh
npm --prefix coptoc/web run build
make run-api
```

The integrated API serves the built console at `/console/`. Native iOS and Android clients open it inside Cop Talk using their configured API origin and selected demo profile. There is no second web-server address to enter on the phone. Rebuild/restart when adding the console to a previously API-only deployment.

The native wrapper provides Back to COP and restricts navigation to the configured origin. The embedded web header/profile selector is hidden, so profile switching happens in the native shell. Native system file selection supports PDF upload; full native editing parity, production SSO, offline queued capture and native source-download handling are not complete. Text entered but not submitted is not an offline saved record.

Web navigation now has COP and Workspaces. Old `#/work/{section}/overview?record=run_…` links resolve into that section's analysis view. Activity is available inside the workspace. Detailed records remain separate tabs; the S4 overview now leads with intake/review instead of manual record forms.

## Verification and evaluation

- Backend suite: 169 passed with 10 existing datetime deprecation warnings (2026-09-08).
- Web production build and lint passed with warnings; bundle size and existing React advisories remain.
- iOS simulator build and Android debug build/installation passed. iOS launch and the embedded workspace were visually verified. Full native upload/approval, native back-navigation edge cases, and interrupted-network tests remain open.
- Browser checks exercised source submission, visible provider-off failure, explicit creation clarification, comparison save, approval and persistence, and the embedded logistics profile at 390 × 844. Review used a clearly labeled synthetic fixture in `/tmp/toc-workspaces-preview.db`; no live provider was called.
- `scripts/evaluate_intake.py` validates a five-case synthetic starter corpus without a provider. `--live` explicitly runs it against the configured provider and writes extraction metrics. The corpus is a starting harness, not sufficient proof of production quality, matching accuracy, or human time savings.

Production sign-in provider selection, live-model evaluation, automatic source retention, broader input types and administrative workflows, budget controls, offline capture, and the remaining mobile acceptance tests are still open. No production deployment or physical-device rollout is claimed.
