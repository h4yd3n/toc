# TOC: staff workspaces and AI implementation plan

Date: 2026-09-06

Planning update (2026-09-07): [AI Operations Center Plan](AI_OPERATIONS_CENTER_PLAN.md) supersedes this document's future interface direction and milestone order. It centers ingestion, reviewable record proposals, and unified mobile workspaces, and folds My Work into section workspaces. The phases below remain historical context; they are not all shipped requirements.

Status: Core workspace and AI workflow implementation delivered for local verification (2026-09-07). Live-provider validation and the remaining advanced automation are still open. See [the implemented contract and rollout notes](WORKSPACE_API.md) for the exact boundary; the phase exit criteria below remain the full roadmap.

## Outcome

Keep the COP readable while giving staff a place to enter information, perform analysis, maintain records, and release products. AI performs the initial processing and maintains assigned work; users inspect evidence, correct findings, and make decisions according to their authority.

The first complete milestone is: an analyst opens S2, enters a report, reviews cited AI analysis, edits a draft assessment, and completes the release workflow so the operational result appears on the COP.

## Development models

These assignments select the coding model used to build the application. They do not select the API models that run inside the product, and writing this table does not switch a running Codex task's model.

| Work | Model | Reasoning |
| --- | --- | --- |
| Architecture, navigation, data contracts, and AI workflow design | Astra (`gpt-6-astra`) | Extra High (`xhigh`) |
| S2 workspace, shared AI foundation, and workflow implementation | Astra (`gpt-6-astra`) | High (`high`) |
| Difficult integration failures and final system review | Astra (`gpt-6-astra`) | Extra High (`xhigh`) |
| Well-defined forms, tables, styling, and follow-up implementation | Sol (`gpt-5.6-sol`) | High (`high`) |

Default for a continuous implementation task: Astra / High. Use Astra / Extra High for the initial architecture pass and difficult cross-cutting decisions. Use Max only for a specific unresolved problem. Record the actual model used when starting an implementation phase; do not claim an assignment ran merely because it is in this plan. Phase boundaries are suitable handoff points if the user wants separate model-specific tasks.

These settings are an engineering recommendation, not a repository-specific benchmark. Official references checked during planning: [Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) and [model comparison](https://developers.openai.com/api/docs/models/compare). Verify availability when execution begins.

## Starting baseline

- The React wall places S1 in the left rail, S2/S4/S6 in the right rail, and S3 in the bottom timeline. Multiple data sets and editing controls share long panels.
- S2 already exposes report entry, case creation, suggested-fact review, directed requirements, collection, area assessments, and INTSUM drafting. Its case graph is primarily displayed as text and lists.
- S1/S3/S4/S6 have existing import or update paths that should be reused and extended.
- Optional Anthropic paths exist for report extraction, assessment drafting, and spreadsheet mapping. Rules provide fallbacks. Provider connectivity and output quality still require live validation.
- Users and section permissions exist, but the prototype uses selectable identities and request headers. This is not production authentication. Background work must not inherit an unrestricted demo identity.
- Future planning currently belongs to S3. A distinct S5 is not part of the first release.
- Preserve existing uncommitted map and overlay work. Keep native API consumers compatible as the web workspace is introduced.

Relevant starting points: `coptoc/web/src/App.tsx`, `Cases.tsx`, `Requirements.tsx`, `Sections.tsx`, `Taskings.tsx`, `Upload.tsx`, `sigtoc/sigtoc/api.py`, `cases.py`, `analysis/wall_drafter.py`, and `coptoc/api/coptoc/users.py`.

## Phase 0: architecture and executable scope

Model: Astra / Extra High.

- Inventory existing read/write endpoints and distinguish working UI actions, missing entry points, and missing backend behavior.
- Establish routes for COP, Workspaces, My Work, sections, and individual records. Browser back/forward and direct links must work.
- Define shared record selection, operation/site/time filters, saved user preferences, and draft persistence.
- Define backend ownership for reports, evidence, products, assignments, runs, proposals, and review decisions. Extend existing case/product models where appropriate.
- Specify allowed transitions for drafts, reviewed findings, released products, and superseded versions.
- Define a small set of representative synthetic workflows with expected evidence and outcomes before choosing production AI models.

Exit: agreed screen structure, API/data contracts, acceptance scenarios, and a dependency-ordered implementation backlog. No feature is marked built based on a design document alone.

## Phase 1: simplify the COP and establish navigation

Model: Astra / High for state and navigation changes; Sol / High for isolated presentation work once contracts are settled.

Introduce three destinations:

| Destination | Purpose |
| --- | --- |
| COP | Current situation, material changes, and operational exceptions |
| Workspaces | Data entry, investigation, planning, and staff products |
| My Work | Assigned tasks, findings needing review, and dependencies on other sections |

Every COP section uses the same structure: current estimate with timestamp/author, prioritized exceptions, meaningful recent changes, and an Open workspace action. Show a short exception list plus total count and View all. Keep urgent released warnings visible.

- Move full rosters, collection matrices, case files, and product libraries into workspaces.
- Make section navigation consistent, including S3.
- Consolidate map controls in the overlay panel; make section presets explicit and preserve manually selected layers.
- Preserve map position, selection, and filters when users return from a workspace.
- Keep the complete battle log available through a dedicated activity view; show only operationally relevant recent activity in the compact wall.
- Use sentence case for content, readable spacing, keyboard focus, meaningful labels, and restrained status colors.
- Use searchable/filterable lists with stable selection; open detail on demand.
- Replace browser prompts with validated forms as each workflow is migrated. Preserve drafts on failure; show successful persistence before closing forms.
- Make destinations and actions respect the resolved user's permissions and enabled sections.

Exit: a user can identify a section exception, open its record directly, and return to the same map context. Verify desktop and narrow layouts, keyboard navigation, and user/profile changes.

## Phase 2: S2 workspace and shared workspace shell

Model: Astra / High. Sol / High may implement isolated list/form components after their behavior is specified.

Build a shared shell with section navigation, main work area, and optional evidence/detail pane. Support role-appropriate default destinations without hiding access to the COP.

| Section | Views | Main actions |
| --- | --- | --- |
| S1 Personnel | Overview, Personnel, Assignments, Accountability | Add person, import roster, update availability |
| S2 Intelligence | Overview, Reporting, Requirements & Collection, Cases, Products | Add report, open case, assign analysis |
| S3 Operations | Overview, Current Operations, Planning, Tasks | Create operation, schedule activity, request support |
| S4 Logistics | Overview, Inventory, Requests, Shipments | Update stock, request supplies, track shipment |
| S6 Communications | Overview, Systems, Contact Plans, Incidents | Update system, record outage, manage fallback plan |

Implement S2 first:

- Reporting inbox with source content, provenance, search, filters, and report-to-case/requirement attachment.
- Case workspace with source reading, persistent notes, review queue, link chart, timeline, and time wheel based on the existing graph contract.
- Clear visual distinction between suggested, confirmed, and rejected facts, with accessible evidence citations.
- Editable, versioned assessment drafts and a product library containing existing product types.
- Requirements and collection views that expose coverage, source health, gaps, and analyst actions.
- Overview showing Needs your decision, Work in progress, and Recent changes, backed by real state.
- Human and AI changes use the same application records; retain authorship and review history.

Exit: all existing S2 workflows are reachable from the workspace, and an analyst can manually complete report entry, case review, assessment editing, and the applicable release process. No placeholder buttons stand in for missing behavior.

## Phase 3: shared AI execution service

Model: Astra / Extra High for contracts and authority design; Astra / High for implementation.

Build alongside Phase 2 after Phase 0 contracts are settled:

- Provider adapters with validated structured outputs, configurable model/effort, timeouts, and explicit model/rules provenance. Consolidate existing provider calls and configuration behavior.
- Permission-aware retrieval across reports, cases, requirements, products, and relevant operational records. Enforce restrictions before content reaches a provider.
- Defined tools for reading records and creating drafts/proposals. Recheck authority at action time and after permission changes.
- Persistent assignments, runs, progress, proposals, and decisions; record evidence IDs and input versions.
- Durable background execution with bounded retries, cancellation, idempotency, and restart recovery. Prevent duplicate proposals or writes when events are replayed.
- Revision checks so delayed runs cannot silently overwrite newer analyst work.
- Visible source coverage, last successful check, failed/degraded state, and retry controls.
- Treat retrieved content as evidence, not instructions; validate tool arguments and keep authority outside model output.
- Keep credentials server-side and out of prompts, logs, and client state. Extend existing write-only settings.
- Capture provider/model, latency, token usage where available, outcome, and failure reasons with configurable run budgets.

Runtime model selection: evaluate economical models for extraction, mapping, and classification; evaluate stronger models for synthesis and competing explanations. Select providers and effort using the acceptance corpus, latency, and measured cost. Coding-model assignments above do not determine these choices.

Exit: a scoped assignment survives restart, returns inspectable evidence-backed results, respects permissions, and produces no duplicate writes on retry. Unconfigured or failing providers are clearly identified.

## Phase 4: complete the S2 AI workflow

Model: Astra / High; Astra / Extra High for integration review and unresolved failures.

1. A report is saved and triggers a scoped analysis run.
2. AI extracts facts with source citations and proposes relevant cases/requirements.
3. The system compares existing reporting, distinguishes repeats from possible independent corroboration, and surfaces contradictions.
4. AI suggests case links and events, explaining uncertainty and identifying potentially affected sites or activities.
5. AI prepares an editable assessment update and proposed collection or S3 follow-up tasks.
6. The analyst accepts, edits, rejects, or requests more work. Decisions remain available to later runs within the authorized case context.
7. The applicable reviewer releases the product; the COP displays the released finding and links to supporting evidence. Subsequent material changes create a new draft/version.

Each review item shows what changed, operational relevance, supporting and conflicting evidence, remaining gaps, prepared actions, and run status.

Preserve source reliability, information credibility, and analytic confidence as distinct concepts. Do not equate source count with independence or model confidence with evidentiary strength. Validate citations against accessible source passages. Thin evidence produces a visible gap, not an invented finding.

Reading, comparison, and drafting may run automatically within the assignment. Record changes, publication, operational commitments, and external communications follow configured authority. Existing release responsibilities remain explicit until deliberately changed.

Exit: the first complete milestone works through the UI against persisted records, with both live-provider and failure-path verification. A mocked model test does not count as live-provider validation.

## Phase 5: continuing assignments and My Work

Model: Astra / High for scheduler/workflow behavior; Sol / High for well-defined management screens.

- Create, edit, pause, resume, and cancel ongoing assignments scoped to sites, cases, requirements, or activities.
- Support event-driven analysis and scheduled checks, each with coverage and last successful run visible.
- Group related findings, suppress duplicates, and surface material changes or decisions rather than every processing event.
- Make My Work a permission-filtered view of actual tasks, proposals, and dependencies; avoid duplicating their state in a separate inbox database.
- Let users inspect completed AI actions and resume interrupted work.
- Maintain analyst feedback as scoped application context; do not imply automatic model retraining.

Exit: new relevant evidence advances an assignment without repeated manual collection/drafting; failures remain distinguishable from no new findings. Paused assignments stop producing work.

## Phase 6: extend working surfaces and AI across the staff

Model: Sol / High for specified forms/tables; Astra / High for cross-section reasoning, permissions, and state changes.

- S1: reconcile incoming rosters, propose duplicate/conflicting-record resolutions, explain availability gaps, and prepare updates.
- S3/planning: compare schedules, personnel availability, resource dependencies, and current assessments; propose taskings and options with assumptions visible.
- S4: connect shipment delays and recorded demand to shortages and affected activities; prepare support requests with traceable quantities.
- S6: connect system outages to affected sites/activities, check recorded fallback coverage, and prepare communications updates.
- Complete the workspace views in Phase 2's table using existing services where possible; fill missing create/edit workflows.
- Make cross-section handoffs link back to originating evidence/product and return status to the requesting section.

Exit: each section can enter data, review a relevant AI-prepared result, complete its authorized action, and see the correct shared operational effect.

## Phase 7: system verification and rollout

Model: Astra / Extra High for final system review; implement fixes using Astra / High or Sol / High according to scope.

- Frontend: run `npm --prefix coptoc/web run build` and `npm --prefix coptoc/web run lint`; visually exercise navigation, focus, forms, loading/errors, narrow layouts, and return-to-map behavior.
- Backend: use the relevant `make test-coptoc`, `make test-sigtoc`, and integration suites during implementation; run `make test` for integrated release verification.
- Add meaningful tests for authority, citations, replay/retry behavior, state transitions, stale writes, provider failure, and the end-to-end report-to-product workflow.
- Use synthetic evaluation cases covering duplicate reporting, contradictory evidence, insufficient evidence, unauthorized records, malicious document instructions, and operational relevance.
- Track time to reviewed assessment, citation support, missed material changes, unsupported links, analyst revision/rejection rate, notification volume, latency, and cost per completed workflow.
- Define acceptance thresholds against the Phase 0 corpus before enabling continuing automation. Treat unsupported publication, unauthorized access, and duplicate external actions as release blockers.
- Roll out behind reversible feature controls. Keep schema/API changes compatible with existing native clients; define native workspace parity as a subsequent explicitly scoped release.
- Update PRD and API contracts to the verified final behavior. Keep deferred features marked planned.

Exit: complete user workflows pass, limitations are documented, and the COP remains readable while users perform real staff work in the workspaces.

## Verified implementation slice — 2026-09-07

The web app now separates COP, Workspaces, and My Work. Staff can enter/update records, save reporting drafts, attach reports to cases, inspect case visuals, assign ongoing analysis, edit cited products, and use the review/release workflow. Released products link from the COP to evidence. Scheduled work is durable, has bounded retries, respects contributor permissions, and preserves review history. My Work includes task handoffs and paginated activity.

Development model allocations above are preserved as the execution plan. No separate Astra/Sol agent runs or runtime-model benchmarks are claimed by this implementation record.

Automated verification covers case/report access, draft ownership, manual personnel entry, citation validation, stale writes, release authority, provider adapters using synthetic responses, permission changes, bounded retries, duplicate task prevention, scheduled unchanged evidence, and activity pagination. Browser verification covers draft restoration, report entry, case attachment, timeline navigation, provider-off failure, analyst correction, Battle Captain release, and the released-product link on the COP. The result used for browser review was explicitly labeled synthetic; live-provider validation remains required.

The phase checkboxes below remain unchecked where their complete exit criteria include work beyond this implemented slice. This avoids marking live AI evaluation, advanced automation, or rollout complete on the strength of a UI or mocked test.

## Progress tracking

- [x] Record the integrated plan and development model assignments.
- [ ] Phase 0: architecture and contracts.
- [ ] Phase 1: COP organization and navigation.
- [ ] Phase 2: S2 and shared workspace shell.
- [ ] Phase 3: AI execution service.
- [ ] Phase 4: report-to-assessment workflow.
- [ ] Phase 5: continuing assignments and My Work.
- [ ] Phase 6: other staff workspaces and AI workflows.
- [ ] Phase 7: system verification and rollout readiness.
