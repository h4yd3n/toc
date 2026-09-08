# AI Operations Center Plan

Revised: 2026-09-07

Status: Implementation in progress. The administrative intake/review pipeline, two-destination web navigation, and embedded native workspace entry points are implemented; see [the intake contract](INTAKE_API.md) for verified scope and open release gates. This revision adopts AntiGravity's automation-first direction and replaces the manual-entry-first interface direction in the earlier workspace plan. The [implemented contract](WORKSPACE_API.md) remains the source of truth for current behavior.

## Product outcome

Cop Talk is one application with authenticated, permission-based staff workspaces on mobile and desktop. People provide information naturally; the system organizes it, identifies changes, and prepares work for review. Success means less transcription, searching, and repeated checking, not more forms or more approval clicks.

The primary workflow is:

**Provide information → inspect evidence and proposed changes → resolve uncertainty → approve authorized changes → shared records and COP update.**

Manual editing remains available for corrections, missing information, and degraded connectivity. It is a supporting workflow, not the starting experience.

## Interface

### Two main destinations

- **COP:** shared picture, compact section summaries, important exceptions, and approved updates. Section overlays show a short summary and an Open workspace action; they do not contain the complete editing console.
- **Workspaces:** a full working screen that replaces the map while preserving its position and filters. The user's primary section opens by default; a section switcher exposes other authorized sections. Phone navigation uses full screens; larger screens show a list and selected item side by side.

Remove My Work as a separate main destination. Move its assignments, results, and review actions into the relevant workspace, with Assigned to me / All section work filters. Preserve old links through redirects. Cross-section notifications link directly to the originating record or proposal, subject to access checks.

### Workspace starting screen

1. **Provide an update:** paste text or attach a supported document. Voice follows in a later milestone. Show supported formats, processing status, and actionable failures.
2. **Needs your review:** proposed changes, unresolved matches, conflicting information, and prepared drafts. Group related changes by submission; prioritize meaningful differences rather than listing every extracted field.
3. **Monitoring:** authorized background checks, their scope, last successful evaluation, stale-data indicators, and findings that changed.
4. **Records:** searchable underlying records, source history, and manual correction tools.

Overview is deliberately short. Detailed lists open only when selected. AI actions stay beside their source records; the product does not require users to navigate to a separate chat app.

### First complete example

A user uploads a delivery manifest. The app matches existing shipments, identifies changed dates and quantities, and flags an ambiguous destination. A review card says: “Three shipments matched; two dates changed; one destination needs clarification.”

Opening the card shows the source beside a table of current and proposed values. The user resolves the destination, approves selected changes, and sees the updated records. An unchanged re-upload produces no duplicate shipment or repeated review request.

## Ingestion and proposal pipeline

1. Persist the original submission, its uploader, access restrictions, timestamp, content hash, and processing version. Apply file size/type limits and retention settings. Treat document text as untrusted input, never as tool instructions.
2. Extract supported facts with source references. Preserve unknown values; do not infer missing identities, locations, dates, or units as facts.
3. Match existing records using stable identifiers and validated lookup logic. Present ambiguous matches for resolution. Separate “not found” from “new record authorized.”
4. Produce typed proposals against allowlisted application operations. The model has no direct database or messaging authority.
5. Validate required fields, units, permissions, references, and business rules on the server. Use ordinary calculations for arithmetic and comparisons.
6. Present evidence and the exact proposed changes for human review.
7. Apply approved changes through existing domain services, recording provenance and resulting record versions. Update the COP from the canonical records.

Initial scope is administrative record maintenance using pasted text and delivery manifests. Do not include tactical routing, targeting, combat resource optimization, or autonomous command execution in this delivery sequence.

### Proposal contract

Each proposal records its source submission and references; target section, record and operation; base record version; current/proposed field values; extraction uncertainty; matching ambiguity; reviewer and decision; validation errors; and resulting record version.

States: processing → needs clarification / ready for review / failed; ready proposals → approved / rejected; approved proposals → applied / conflict / failed. A processing job completing does not mean its proposed changes were applied.

Users can accept a subset, edit values, reject a proposal with a reason, or defer it. Dependent changes form explicit atomic groups; independent changes may be approved separately. Recheck authorization and record versions at application time. A stale record returns a conflict for review rather than overwriting a newer update.

Use idempotency keys and transactional writes so retries cannot duplicate changes. Corrections create attributable history; reversals must account for subsequent edits rather than blindly restoring an old snapshot.

## Trust and authority

An exact quote proves that text occurs in a source, not that the source is correct or the inference valid. Keep extracted statements, calculated results, and interpretations distinct. Separate source reliability from extraction certainty; do not label an AI confidence score as confirmation.

References use text spans, document page locations, or recording timestamps as appropriate. Calculated results cite their input records and calculation version. Conflicting sources remain visible rather than being silently reconciled.

Use authenticated accounts with separate view, contribute, edit, review, release, and administer permissions. The existing selectable demo profiles are not production authentication. Background jobs run with explicit owners and bounded access. Recheck every contributing section/case/site restriction before processing, display, and application; do not leak restricted context through summaries or notifications.

Approving a record correction and publishing a product are separate actions. Section-authorized users approve routine record changes; existing release authority governs published products. No external notifications or consequential actions are automatically executed by this initial pipeline.

## Background assistance

Begin with configured administrative checks such as overdue shipment records, missing required fields, and conflicting dates. Show the rule, evidence window, freshness, and last successful run. Use event-driven updates where possible and bounded scheduled checks otherwise.

Deduplicate unchanged findings, group related issues, support dismissal/snooze with reasons, and avoid regenerating work from already resolved inputs. Apply retry limits, cost ceilings, cancellation, and visible failure states. AI can explain a detected change or prepare a draft; deterministic checks should establish quantities, dates, and thresholds.

Conversational access comes after these typed workflows. Initially it retrieves authorized records and prepares proposals; approval occurs in the same visible review interface. It must not bypass normal permissions or update rules.

## Unified application and ownership

Cop Talk provides one login and module navigation. Coptoc continues to own personnel, activities, logistics, systems, and the COP. Sigtoc continues to own intelligence evidence, cases, and products. Shared ingestion/proposal infrastructure calls those owners' services instead of duplicating their records.

Web and native clients use the same proposal APIs and permissions. Native clients now have an embedded workspace entry point; full native workflows, authentication and offline acceptance gates remain open. An embedded web review screen can be an interim delivery option if authentication and phone usability are verified; the product must not require opening a separate app. Offline capture is explicitly queued and marked unsynced; approval/application requires current server validation in the first release.

## Delivery sequence and exit criteria

### M0 — Contracts and interface prototype

Define proposal schemas, source storage, authorization, transactional groups, conflict behavior, and notification privacy. Prototype phone and desktop flows for upload, clarification, review, correction, and return to COP. Baseline the equivalent manual task with representative sample documents.

Exit: the full manifest example is understandable without navigating to My Work or filling an equivalent set of manual fields. No runtime automation is claimed from a mockup.

### M1 — Text/document to reviewable proposals

Support pasted text and text-based PDF delivery manifests with explicit size limits. Scanned PDFs, images, voice, and live streams remain unsupported until separately tested. Implement extraction, matching, evidence display, clarification, failures, and original-source retention using synthetic administrative examples.

Exit: supported, incomplete, ambiguous, contradictory, malformed, and repeated inputs produce the expected proposals or visible failures. No canonical records change during extraction. Unsupported content does not generate plausible-looking substitute data.

### M2 — Apply approved changes reliably

Connect proposals to shipment domain APIs. Implement partial approval, transactional dependencies, idempotency, concurrent-edit conflicts, permission revocation, history, and correction. Verify that the COP reflects the resulting canonical records.

Exit: duplicate retries create zero duplicate records; stale approvals overwrite zero newer edits; revoked permissions allow zero unauthorized applications. All applied fields trace to their submission and reviewer. Establish these through automated integration tests.

### M3 — Background checks and prepared updates

Add a small set of administrative checks, changed-input triggers, deduplicated review items, and evidence-backed draft updates. Reuse the existing worker/review foundation where appropriate rather than creating parallel job systems.

Exit: unchanged inputs do not generate repeated review items; failures and stale sources remain visible; cost and retry limits hold under test.

### M4 — Unified mobile workflow

Bring capture, proposal review, clarification, and approval into Cop Talk, backed by real authentication. Replace the separate My Work destination with workspace review queues and preserve deep links. Test on actual iOS and Android devices, including interrupted uploads and expired sessions.

Exit: a permitted user completes the administrative example without leaving Cop Talk. Unauthorized modules and records remain inaccessible through both UI and API. Pending uploads and unsynced notes are clearly distinguished from saved records.

### M5 — Expand only from measured results

Evaluate additional administrative record types, scanned documents, voice capture, and authorized conversational retrieval/proposal preparation. Give each input and action type its own quality tests. Continuous camera/radio ingestion and broad autonomous execution are not implied by this milestone.

## Evaluation and release gates

Use a versioned synthetic administrative corpus with held-out examples covering clean and messy manifests, duplicate submissions, ambiguous names, unit/date differences, contradictions, and embedded instruction attempts. Separate extraction accuracy, record matching accuracy, and proposal application correctness.

Provisional pilot targets, to validate against the M0 baseline:

- At least 50% lower median human handling time for supported manifest updates, including corrections and approvals.
- At least 95% accuracy for supported extracted fields on the held-out corpus; report ambiguous/abstained fields separately so rejection cannot inflate accuracy.
- Zero unauthorized writes, duplicate writes under retry, or silent overwrites in the integration test suite.
- Every applied change has retrievable source and reviewer provenance.
- Report correction rate, unresolved matches, review items per submission, latency, provider cost per accepted submission, and user-dismissed alerts. Set a cost budget before enabling recurring live checks.

These are proposed gates, not measured results. Provider-backed quality testing is required; mocked responses and a passing software suite do not establish live AI quality. Review the pilot results before expanding supported formats or automation authority.

## Development models and current baseline

Retain the previously agreed development allocation: Astra / Extra High for architecture and difficult integration review; Astra / High for core pipeline implementation; Sol / High for bounded UI and documentation tasks. These are coding allocations, not runtime provider selections, and do not themselves launch or switch models.

Choose runtime provider/model configurations through the held-out evaluation, considering accuracy, abstention, latency, and cost. Require explicit provider/model/key configuration; show failures honestly and never substitute synthetic results for a live run.

Already implemented: domain record APIs and web editing, cited analysis drafts, assignment worker, review/release history, evidence access controls, single-destination administrative manifest intake and shipment proposals, an overdue-delivery check, revised web navigation, and embedded native workspace entry points. Production authentication, live quality/cost evaluation, retention policy enforcement, offline capture, broader administrative ingestion, and full native acceptance remain open. See [WORKSPACE_API.md](WORKSPACE_API.md) for the verified baseline.

The earlier [workspace implementation plan](IMPLEMENTATION_PLAN-ai-workspaces.md) remains historical context and a record of development allocations. This document governs the next product direction and milestone order.
