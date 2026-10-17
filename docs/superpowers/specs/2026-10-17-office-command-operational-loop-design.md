# Office–Command operational loop design

**Status:** Draft for implementation
**Date:** 2026-10-17
**Scope:** AgentUX Office, AgentUX Command and the AUXP projection boundary

## Outcome

AgentUX Office becomes the trusted remote operating surface for people who are
accountable for organizational outcomes, while AgentUX Command remains the
authority for organization state, governance and remote decisions. A leader
should be able to answer three questions without opening a node or reading a
database:

1. What is happening across the organization right now?
2. What is blocked, unhealthy or waiting for a human decision?
3. What decision can I safely make, why is it needed and what will it affect?

The first production-shaped slice is a real projection read plus an
authorization-aware approval decision. Fixtures remain available for local
demos and deterministic tests, but the live path must use Command APIs.

## Users and business needs

### Executive leader

Needs a fast, trustworthy summary of active work, risk, capacity and decisions
without technical details. The interface must distinguish healthy progress
from stale or incomplete data and show the business impact of a blocked run.

### Operations or area owner

Needs to locate a mission, run, agent or node, understand the current step and
trace the latest event/artifact. Filters and drill-down must preserve the
organization and mission context instead of becoming a generic monitoring
screen.

### Approver

Needs a clear approval request, requested capability, affected mission/run,
evidence and expiry before deciding. Approval actions must be explicit,
idempotent, permission-checked and auditable. A denied, expired, already
decided or unavailable request must never look successful.

### Auditor or security reviewer

Needs to know who saw or decided what, against which organization definition
version, from which correlation context and with what result. Office displays
this evidence; Command owns the audit record.

### Node operator

Needs the remote view to expose node health and degraded connectivity without
pretending that a missing heartbeat means a failed run. Local execution remains
owned by AgentUX Core and the node.

## Product principles

- **Trust before density:** a stale or partial projection is visibly marked.
- **Decision before navigation:** pending approvals and blocked work are first
  class entry points.
- **Command is authoritative:** Office never writes transactional state or
  decides authorization locally.
- **Least privilege:** read, inspect and decide are separate capabilities.
- **Replayable state:** events and projections carry IDs, timestamps, schema
  versions and correlation IDs so clients can recover safely.
- **Progressive integration:** fixtures, snapshot reads, event refresh and
  durable streaming are compatible adapters, not separate product models.

## First vertical slice

### Command API

Add a projection boundary independent of Command storage:

- `GET /v1/office/projection`
  - requires `organization.read`;
  - accepts organization and optional area/mission filters;
  - returns `schemaVersion`, `organization`, `definitionVersion`,
    `projectedAt`, `source`, `freshness`, `areas`, `missions`, `agents`,
    `nodes`, `runs`, `approvals`, `artifacts` and `events`;
  - returns a degraded response when the projection is stale, never silently
    converting unavailable data into an empty organization.
- `POST /v1/approvals/{approvalId}/resolve`
  - requires `approval.decide`;
  - accepts `decision`, optional `reason` and an idempotency key;
  - returns the authoritative decision or a typed conflict (`denied`,
    `expired`, `already_decided`, `not_found`, `stale_version`).

For the first slice, the Command projection may be an in-memory adapter seeded
with deterministic data, but its response and error shapes must be the stable
contract used by Office. Persistence and real node event ingestion are later
increments, not hidden assumptions in the UI.

### Office client

Introduce a typed `CommandApi` adapter with:

- `loadProjection(query)`;
- `resolveApproval(id, input)`;
- `FixtureApi` implementing the same interface for demo/tests;
- explicit states: `loading`, `ready`, `stale`, `empty`, `degraded`, `error`;
- refresh/retry behavior that keeps the last known projection visible while
  marking its age and connection status;
- approval UI that disables duplicate submission and renders every typed
  conflict distinctly.

The existing floor, metrics, filters and event timeline are projections of the
adapter result, not owners of a second data model.

### Protocol boundary

Reuse AUXP envelope conventions (`protocolVersion`, IDs, timestamps,
correlation and schema version). Do not make Office depend on Command database
tables. Add schema/fixture definitions only where the projection or approval
payload is not already represented by the protocol.

## Evolution after the first slice

The implementation loop must create or update an issue whenever a boundary is
encountered. The initial backlog is:

1. **Projection API and approval vertical slice** — this specification's first
   delivery.
2. **Durable Command projection store** — PostgreSQL read model, event offsets,
   replay and idempotent projection updates.
3. **Authenticated organization sessions** — OIDC/session integration,
   organization membership, capability claims and token rotation.
4. **Live Office updates** — outbound node events into Command, Command event
   stream/WebSocket or SSE, reconnect and replay cursors.
5. **Operational drill-down** — run detail, step history, artifacts, costs,
   incidents and correlation navigation.
6. **Leadership definition editor** — drafts, validation, reviewable diffs,
   immutable publication and history, based on ADR 0015.
7. **Governance and audit center** — decision history, policy changes,
   access trail, retention and export.
8. **Reliability and accessibility hardening** — contract tests, browser
   tests, keyboard navigation, screen-reader semantics, localization and
   performance budgets for large organizations.

Each issue must state the user outcome, capability boundary, data contract,
authorization behavior, failure states, migration/compatibility impact and
tests. A feature is not complete when only the happy-path screen works.

## Acceptance criteria

- A real Office session loads a Command projection through a typed adapter.
- The fixture path still works without a Command server.
- Projection freshness and degraded connectivity are visible.
- Leadership can resolve an authorized pending approval exactly once.
- Unauthorized, expired, already-decided, stale and unavailable decisions are
  distinguishable in the UI and API.
- No Office code accesses Command storage or AgentUX Core local sockets.
- Contract tests pin the projection and approval shapes.
- The README and issue tracker describe the current integration level without
  hard-coded release claims.

## Non-goals for this slice

- Full organization editor.
- PostgreSQL migration or production event bus.
- Provider credentials or direct node execution from Office.
- Replacing the local AgentUX desktop cockpit.
- Treating a visual 2D floor as the source of truth.
