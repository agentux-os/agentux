# Office–Command Projection and Approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the AgentUX Office fixture-only experience with a typed Command projection and safe approval-decision flow while preserving fixtures for demos and tests.

**Architecture:** AUXP owns versioned envelope and payload schemas. AgentUX Command exposes an in-memory, storage-independent Office read model and an authorization-aware approval endpoint. AgentUX Apps consumes both through a `CommandApi` interface, keeps `FixtureApi` as an interchangeable adapter, and renders explicit freshness, degraded, empty and decision-conflict states.

**Tech Stack:** Go `net/http`, existing Command protocol/domain packages, JSON Schema fixtures, browser-native JavaScript/HTML/CSS, Node.js validation scripts and the existing repository test commands.

**Spec:** `docs/superpowers/specs/2026-10-17-office-command-operational-loop-design.md`

## Global Constraints

- Command remains authoritative for organization state, governance and approval decisions.
- Office never accesses Command storage or AgentUX Core local sockets.
- Fixtures remain available for local demos and deterministic tests.
- Every projection includes schema version, definition version, projected timestamp, freshness and source.
- Distributed records use organization/entity IDs, immutable definition versions, event IDs, node sequence cursors and idempotency keys.
- The in-memory store must model append-only events plus materialized projection state so a durable event log/read model can replace it without changing Office.
- Approval resolution is idempotent, permission-checked and auditable at the API boundary.
- A stale or unavailable projection must not be rendered as an empty organization.
- The first slice does not add PostgreSQL, production event streaming or the leadership editor.
- AUXP envelope conventions remain the compatibility boundary; breaking changes require a new major protocol version.

## Review Focus

- **Stale projection:** Office keeps the last known data visible and marks its age; test in the API adapter state machine.
- **Unavailable Command:** Office shows degraded/error state and retry; test with failed fetch and malformed JSON.
- **Approval replay:** the same idempotency key returns the original decision; test in Command handler.
- **Unauthorized/expired/already-decided approval:** API returns typed conflicts and UI does not show success; test across Go handler and fixture adapter.
- **Empty organization:** valid empty projection renders an explicit empty state, distinct from degraded data; test in Office rendering.

---

### Task 1: Define the Office projection and approval contract

**Files:**
- Create: `agentux-protocol/schemas/v1/office-projection.schema.json`
- Create: `agentux-protocol/schemas/v1/approval-resolution.schema.json`
- Create: `agentux-protocol/fixtures/v1/office-projection.json`
- Create: `agentux-protocol/fixtures/v1/approval-responses.json`
- Modify: `agentux-protocol/scripts/validate-fixtures.mjs`
- Test: existing protocol fixture validation command

**Interfaces:**
- Produces `OfficeProjection`, `ApprovalResolutionRequest`, `ApprovalResolutionResponse` and typed conflict values consumed by Command and Apps.
- Uses the existing AUXP IDs, timestamps, schema-version and correlation conventions.

- [ ] **Step 1: Write fixture cases** for populated, empty/stale and approval conflict payloads, including `schemaVersion`, `definitionVersion`, `projectedAt`, `freshness`, `source`, `organization`, `areas`, `missions`, `agents`, `nodes`, `runs`, `approvals`, `artifacts` and `events`.
- [ ] **Step 2: Extend `validate-fixtures.mjs`** to validate the new fixtures with dependency-free structural assertions and reject missing IDs, timestamps, freshness or unknown approval decisions.
- [ ] **Step 3: Add JSON Schemas** that pin required fields, enum values, IDs, ISO timestamps and the typed conflict envelope without coupling to Command persistence.
- [ ] **Step 4: Run** `node scripts/validate-fixtures.mjs`; expected: all existing and new fixtures pass.
- [ ] **Step 5: Commit** protocol schemas and fixtures as `feat: define Office projection contract`.

### Task 2: Implement the Command projection store and API

**Files:**
- Create: `agentux-command/internal/office/projection.go`
- Create: `agentux-command/internal/office/store.go`
- Create: `agentux-command/internal/office/office_test.go`
- Modify: `agentux-command/internal/server/server.go`
- Modify: `agentux-command/internal/server/server_test.go`
- Modify: `agentux-command/internal/protocol/protocol.go` only if shared envelope types are missing

**Interfaces:**
- Produces `GET /v1/office/projection` and `POST /v1/approvals/{approvalId}/resolve`.
- `OfficeStore.GetProjection(query) (OfficeProjection, error)` returns a projection with freshness and source.
- `OfficeStore.ResolveApproval(id string, request ApprovalResolutionRequest) (ApprovalResolutionResponse, error)` enforces idempotency and typed conflicts.

- [ ] **Step 1: Write failing Go tests** for projection success, organization filter, valid empty projection, stale projection, malformed authorization and each approval conflict.
- [ ] **Step 2: Implement deterministic in-memory store** seeded with the same semantic fixture data as AUXP, keeping the store behind interfaces so PostgreSQL can replace it later.
- [ ] **Step 3: Model distributed identity and replay metadata** in the store: organization/entity keys, `eventId`, `nodeId`, monotonic sequence, `lastEventId`, `projectedAt`, freshness and idempotency records; deduplicate repeated events before applying them.
- [ ] **Step 4: Implement authorization boundary** using a configured Bearer token/capability set for the first slice; return `401` for missing/invalid credentials and `403` when `organization.read` or `approval.decide` is absent.
- [ ] **Step 5: Implement projection handler** with query validation, JSON response, freshness metadata and `503`/typed degraded response when the store marks the projection unavailable.
- [ ] **Step 6: Implement approval handler** with decision/reason/idempotency parsing, idempotent replay and typed `409` conflicts for denied, expired, already-decided, not-found and stale-version cases.
- [ ] **Step 7: Run** `go test ./...`; expected: all Command tests pass, including endpoint, distributed identity/replay and authorization cases.
- [ ] **Step 8: Commit** Command implementation as `feat: expose Office projection and approval API`.

### Task 3: Add the typed Apps API adapter

**Files:**
- Create: `agentux-apps/apps/office/api.js`
- Create: `agentux-apps/apps/office/api.test.mjs`
- Modify: `agentux-apps/apps/office/app.js`
- Modify: `agentux-apps/scripts/validate-office.mjs`
- Modify: `agentux-apps/package.json` only if a test script entry is needed

**Interfaces:**
- `createCommandApi({ baseUrl, token, fetchImpl })` exposes `loadProjection(query)` and `resolveApproval(id, input)`.
- `createFixtureApi()` implements the same methods for demo/test mode.
- `loadProjection` returns `{ status, projection, error }` with statuses `ready`, `stale`, `empty`, `degraded`, `error`.
- `resolveApproval` returns `{ ok, decision }` or `{ ok: false, conflict }` without converting conflicts to success.

- [ ] **Step 1: Write failing adapter tests** for successful JSON, `401`, `403`, `409`, `503`, invalid payload and network failure.
- [ ] **Step 2: Implement `api.js`** with injected `fetchImpl`, typed response normalization and no browser-global dependency in tests.
- [ ] **Step 3: Move fixture data behind `createFixtureApi()`** so `app.js` no longer owns a second domain model.
- [ ] **Step 4: Update the validator** to execute adapter tests with the Node test runner and retain fixture validation.
- [ ] **Step 5: Run** `npm test`; expected: adapter and existing Office validation pass.
- [ ] **Step 6: Commit** Apps adapter as `feat: add Command projection adapter`.

### Task 4: Render real projection and decision states in Office

**Files:**
- Modify: `agentux-apps/apps/office/index.html`
- Modify: `agentux-apps/apps/office/app.js`
- Modify: `agentux-apps/apps/office/styles.css`
- Modify: `agentux-apps/apps/office/api.test.mjs` or create `agentux-apps/apps/office/render.test.mjs`

**Interfaces:**
- Consumes the adapter from Task 3 and renders its normalized projection.
- Produces visible connection/freshness status, filters, approval detail and decision result.

- [ ] **Step 1: Write failing render assertions** for loading, populated, empty, stale, degraded, retry and approval conflict states.
- [ ] **Step 2: Add runtime configuration** for Command base URL, organization ID and demo mode without embedding credentials in source.
- [ ] **Step 3: Refactor metrics, floor and events** to derive exclusively from the normalized projection; preserve area/mission/status filters.
- [ ] **Step 4: Add approval affordance** showing mission/run, requested action, evidence, expiry and reason; disable duplicate submits and show typed conflict messages.
- [ ] **Step 5: Add freshness/degraded UI** that preserves last-known data during refresh and distinguishes stale, empty and unavailable states.
- [ ] **Step 6: Run** `npm test` and `npm run serve`; manually verify demo mode, populated projection and failed Command mode.
- [ ] **Step 7: Commit** Office live states as `feat: connect Office projection and approvals`.

### Task 5: Cross-repository contract and integration verification

**Files:**
- Modify: `agentux-command/README.md`
- Modify: `agentux-apps/README.md`
- Modify: `agentux-protocol/README.md`
- Create or modify: repository CI workflow files only if existing checks cannot run the new tests

**Interfaces:**
- Documents the endpoint contract, demo mode, authorization requirements and current limitations.
- CI runs protocol validation, Command tests and Apps tests independently.

- [ ] **Step 1: Add contract examples and local integration instructions** to the three READMEs using version-free links.
- [ ] **Step 2: Add a cross-repository smoke script** that starts the in-memory Command server, loads the projection through the Apps adapter and resolves one approval with an idempotency key.
- [ ] **Step 3: Run** protocol validation, `go test ./...`, Apps `npm test` and the smoke script; expected: all pass with no external database or provider credentials.
- [ ] **Step 4: Commit** integration documentation and smoke verification as `test: verify Office Command vertical slice`.

### Task 6: Create and maintain the evolutionary issue backlog

**Files:**
- Modify: `agentux/docs/superpowers/specs/2026-10-17-office-command-operational-loop-design.md` if issue links are added after creation
- GitHub issues: `agentux-os/agentux-command`, `agentux-os/agentux-apps`, `agentux-os/agentux-protocol`

- [ ] **Step 1: Create issues** for durable projection storage, authenticated organization sessions, live updates/replay, operational drill-down, leadership definition editor, governance/audit center and accessibility/reliability hardening.
- [ ] **Step 2: Include in every issue** user outcome, boundary, data contract, authorization, failure states, compatibility/migration impact and tests.
- [ ] **Step 3: Link dependencies** so storage/authentication precede live updates and the editor, and link Issue #3/#4 to their successor issues.
- [ ] **Step 4: Update the specification with issue links** and verify the issue tracker represents every unimplemented evolution item.

### Task 7: Final verification and handoff

- [ ] **Step 1: Run fresh verification** in every changed repository and inspect diffs for unrelated changes.
- [ ] **Step 2: Verify the public contract** against the committed AUXP schemas and fixtures.
- [ ] **Step 3: Verify the demo path** works with no Command server and the live path fails visibly without credentials/server.
- [ ] **Step 4: Review open issues** and report what shipped, what remains and which issue is next in the loop.

