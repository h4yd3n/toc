# Staff workspaces and AI: implemented contract

Updated 2026-09-07. This describes the current web implementation. The broader backlog and coding-model allocations remain in [the implementation plan](IMPLEMENTATION_PLAN-ai-workspaces.md).

## Navigation and ownership

- `#/cop`: compact staff estimates, exceptions, released findings, and recent changes. The map remains mounted when a workspace opens.
- `#/workspace/{S1|S2|S3|S4|S6}/{tab}`: staff records and editing tools. S3 owns planning; there is no separate S5 workspace.
- `#/workspace/S2/cases?record={case_id}` and `#/workspace/S2/analysis?record={case_id}`: a case or its assigned analysis.
- `#/work/{section}/overview?record={run_id}`: shared taskings, AI assignments, and a selected result.

Coptoc owns personnel, activities, supplies, shipments, systems, taskings, and the COP. Sigtoc owns reports, case evidence, case review, and intelligence products. `sigtoc.work` currently hosts the shared analysis service using the same database; it reads authorized Coptoc records and writes its own draft results. It does not autonomously change operational records or send messages.

## Human workflows

S1 has manual person entry, a searchable roster (50 rows at a time), duty updates, import, task organization, and accountability. S2 has report entry, owned saved report drafts, report-to-case attachment, case review, link chart/timeline/time wheel, collection controls, existing products, and AI assignments. S3 has activity entry, schedule import, planning, and taskings. S4 has inventory and shipment entry/update/import plus support requests. S6 has system entry/update/import, editable PACE roles, outage views, and taskings.

New Coptoc endpoints:

| Request | Behavior |
| --- | --- |
| `POST /v1/cop/people` | S1 editors add a person to an existing team; duplicate email returns 409. |
| `PATCH /v1/cop/people/{id}/assignment` | S1 editors change `on_shift` and `shift_role`. The older `/shift` endpoint is retained for client compatibility. |
| `GET /v1/cop/activity` | Cursor-paginated activity; `limit` is 1–100, `before` is the previous `next_cursor`, `include_reads=true` adds access audits. Case-related entries retain case access controls. |
| `POST /v1/s2/reports/{id}/attach` | Attach an unassigned report to an accessible open case and extract suggestions. Repeating the same attachment is idempotent; moving a report out of another case returns 409. |

Existing APIs continue to handle stock, shipments, systems, estimates, activities, cases, products, requirements, and taskings. The new workspaces expose these APIs without changing the existing native-client payloads.

## Analysis service

All `/v1/work` routes require a resolved active user or an explicit recognized legacy role. A supplied invalid user ID fails closed. This is the prototype's existing selectable-identity mechanism, **not production authentication**.

| Request | Payload / response |
| --- | --- |
| `GET /v1/work` | Authorized assignments, up to 20 recent runs per assignment, and public provider configuration status. Evidence and results are filtered by every contributing section, case, and recorded site. |
| `POST /v1/work/assignments` | `section`, `instruction` (10–4,000 characters), optional `case_id` (S2 only), optional `location_id`, `cadence_minutes` (0–10,080). Saves the assignment and first queued run atomically. |
| `PATCH /v1/work/assignments/{id}` | `action`: `run`, `pause`, `resume`, `cancel`, or `edit`. Edit accepts `instruction` and `cadence_minutes`; it cancels older pending work and starts a new run. Cancelled assignments cannot restart. |
| `PATCH /v1/work/runs/{id}` | `revision`, `action` (`save`, `review`, `release`, `reject`), optional structured `result` and `note`. Stale revisions return 409. |
| `POST /v1/work/runs/{id}/taskings` | `index` and `to_section`. A human creates a suggested task after review. Same result, task text, and destination are idempotent. Case-derived tasks stay in S2 and use generic shared-board labels with a link to protected evidence. |
| `GET/PUT /v1/work/drafts/{section}/{key}` | An owned draft payload, up to 50,000 characters, with section/case checks. The reporting form uses this for explicit Save draft / restore. |

The structured analysis contains `title`, `summary`, `findings`, `gaps`, and `proposed_tasks`. Every finding contains `claim`, `uncertainty`, and one or more citations with `source_id` and an exact source `quote`. Citation matching verifies the source passage, not whether the inference is correct. Human review remains necessary.

Run states: `queued → running → completed | failed | unchanged | cancelled`. Draft review states: `draft → review → released`, or `rejected`. Saving edits returns a result to draft. Only the Battle Captain can release; a result with no cited findings cannot be released. Released/rejected results are immutable. Later analysis creates another run, preserving earlier products. Original output, evidence snapshot, model/provider, duration/usage, instruction, revision, and review versions are retained.

The worker checks every 10 seconds. It claims runs atomically, permits at most one queued/running run per assignment, recovers leases older than five minutes, and caps processing at three attempts per run. Transport failures, HTTP 429, and HTTP 5xx retry after 20 and 40 seconds; validation and configuration failures remain visible. Pause/cancel prevents in-flight results from being saved. Owner and evidence permissions are checked again after the provider returns and when results are read or reviewed.

Scheduled runs compare evidence fingerprints. Unchanged evidence skips a new provider call. New filed reporting advances active scheduled S2 assignments. A one-shot assignment needs an explicit rerun. Human review history is supplied as bounded context on subsequent runs. Unavailable prior evidence is excluded, and retained feedback carries its original section/case/site restrictions into the new result and any follow-up. This is not model retraining.

## Retrieval and limits

S2 case assignments read that case's reports. S2 section assignments read accessible reporting, the shared threat picture, and authorized S3 activities. Other sections read their own records; S3 may also read authorized S1/S4/S6 records, and S4/S6 may read authorized S3 activities. These supporting sections are permission-checked before provider submission and on later reads. Large personnel rosters are summarized into team counts and accountability exceptions with source IDs. Contact phone/email fields are excluded.

Restricted sites are excluded. Assignments fail visibly above 100 reports or 180,000 source-text characters instead of silently truncating evidence. Responses use a 90-second request timeout, with limits of 8,000 output tokens for OpenAI and 6,000 for Anthropic. Model availability and reasoning support depend on the chosen provider account.

## Provider setup and rollout

In Settings → AI & Drafting, a Battle Captain selects `TOC_AI_PROVIDER` (`off`, `openai`, or `anthropic`), enters the exact `TOC_AI_MODEL`, and supplies `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`. OpenAI uses `TOC_AI_EFFORT` (default `high`) when supported by that model. Keys stay in the existing encrypted server-side settings store; environment variables take precedence. The new provider defaults to off. Existing extraction/INTSUM provider settings are separate and have not yet been consolidated.

The integrated Coptoc server starts the worker; `TOC_AI_WORKER=off` disables it. The standalone Sigtoc API exposes the routes but does not start the worker. Existing SQLite deployments add new columns at startup. Validate other database migrations separately before deploying there.

The development preview uses a separate database at `/tmp/toc-workspaces-preview.db` with API port 8003 and web port 5174. Synthetic test reporting and a clearly labeled synthetic review result were used to verify the browser flow. No live provider was invoked, and no production deployment or native-device rollout is claimed.

## Verification record

`make test`: 158 passed (10 existing datetime deprecation warnings). Frontend production build and lint complete with warnings; the bundle-size and React lint advisories remain. Browser checks used desktop width and a 390 × 844 viewport, then restored the normal viewport. Report draft/save/attach, source reading, analyst edit/review, Battle Captain release, COP back-link, S4 assignment defaults, and inventory entry were exercised against the isolated database. The S6 fallback editor, outage-only incidents view, and recorded activity log were also checked in the browser.

## Remaining plan items

Live-provider quality/cost evaluation and final runtime-model selection remain open. Other remaining items include consolidated extraction/drafting adapters; automatic case/requirement matching; typed proposals that update the case graph; operation/requirement-specific assignment scopes; shared saved filters across every view; semantic duplicate suppression across different assignments; and native workspace parity. Those are planned work, not implied by the existing Assign analysis button.
