# 0015. Organization definitions are versioned domain contracts

- **Status:** Accepted (2026-10-22), with the notes in [Acceptance](#acceptance)
- **Date:** 2026-10-15

## Context

Leadership must be able to define an organization, its areas, missions,
roles, workflows and approval boundaries without changing application code.
AgentUX Command executes that definition across remote nodes, while AgentUX
Office presents a safe operational view for leadership. Both products need a
stable contract, but neither should depend on the other's database schema.

## Decision

An organization definition is a versioned, immutable document. The canonical
v1 contract is documented in
[`docs/contracts/organization-definition-v1.md`](../contracts/organization-definition-v1.md).
Command stores and executes published versions. Office consumes projection
events and read models derived from those versions.

The contract has ten first-class objects:

| Object | Purpose | Mutable after publish? |
|---|---|---|
| Organization | Tenant and governance boundary | New version only |
| Area | Business or operational ownership boundary | New version only |
| Role | Human or agent responsibility template | New version only |
| Mission | Outcome with owner, scope and success criteria | New version only |
| Workflow | Ordered steps and transitions | New version only |
| Agent | Logical worker identity and capability claims | Runtime status only |
| Node | Execution location and trust boundary | Runtime status only |
| Gate | Check or policy before a transition | New version only |
| Approval | Human decision boundary | Runtime decision only |
| Artifact | Produced evidence or deliverable | Append-only metadata |

### Ownership and permissions

The organization owns all definitions and runs. Area owners may propose
changes within their area; only an organization administrator may publish a
definition or change approval policy. A role grants capabilities, but never
silently grants organization administration. Command enforces these rules;
Office displays them and never becomes an authorization authority.

The minimum permission vocabulary is:

`organization.read`, `organization.edit`, `organization.publish`,
`run.read`, `run.start`, `run.pause`, `run.cancel`, `approval.decide`,
`artifact.read`, and `node.manage`.

### Command boundary

Command exposes definition and execution APIs and emits durable events. The
minimum v1 events are:

`organization.definition.published`, `run.created`, `run.started`,
`run.step.started`, `run.step.blocked`, `run.step.completed`,
`approval.requested`, `approval.decided`, `artifact.recorded`,
`run.completed`, and `run.failed`.

Every event includes `event_id`, `event_type`, `occurred_at`,
`organization_id`, `definition_version` when applicable, `run_id` when
applicable, `actor`, `correlation_id`, and a schema version. Consumers must be
idempotent on `event_id`.

### Office boundary

Office consumes a read model, not Command's transactional tables. The read
model exposes organization hierarchy, current run state, active agents and
nodes, pending approvals, recent artifacts, and audit timeline. It may lag
behind Command and must show freshness (`projected_at`) and degraded state.
Office can request an approval or navigation action through Command, but it
cannot mutate a definition or execute a step directly.

### Migration and compatibility

Contract versions use `major.minor` semantics. A minor version adds optional
fields and keeps existing meanings. A major version requires an explicit
migration and a compatibility window. Definitions carry `schema_version` and
`definition_version`; events carry their own `schema_version`.

Command validates a definition before publishing, records the validation
result, and rejects unknown required fields. A migration tool must produce a
new draft and a diff; it must never rewrite a published definition.

## Consequences

- Leadership-created organizations are data, not code, and can be promoted
  through draft, review and publish states.
- Command and Office can be implemented independently against one contract.
- The audit trail has explicit actor, version and correlation boundaries.
- Office remains safe to expose remotely because it is a projection and an
  approval client, not the execution engine.
- The first implementation needs schema validation, event envelopes and a
  projection contract before claiming multi-tenant production readiness.

## Acceptance

Accepted on 2026-10-22, after AgentUX Command's authorization, enrollment and
Office projection were built, with these notes.

**Permissions.** The vocabulary above is canonical for organization
definitions (a role's `permissions`). AgentUX Command already authorizes
operators per organization with these capabilities, which relate to it so:

| Command capability today | In this vocabulary |
|---|---|
| `organization.read` | `organization.read` (and `run.read`, `artifact.read` until runs and artifacts exist in Command) |
| `approval.decide` | `approval.decide` |
| `node.enroll` | `node.manage` |
| `node.command` | `run.start`, `run.pause`, `run.cancel` on a node (AUXP commands) |
| `auth.admin` | not part of definitions: issuing and revoking operators' service tokens |

As definitions land in Command (agentux-command#5), the remaining names
(`organization.edit`, `organization.publish`, `run.read`, `artifact.read`) are
added with the same names, a published role's permissions grant capabilities
through the same per-organization principal, and `node.command` and
`node.enroll` are kept as aliases of the finer names they cover.

**Field names.** The names in this ADR (`event_id`, `organization_id`, …) are
logical. On the wire, AUXP and the Office projection use camelCase
(`eventId`, `organizationId`), as agentux-protocol's schemas do.

**Workflows.** Command runs an organization's workflows as state machines in
PostgreSQL with a transactional outbox, not on Temporal
([ADR 0020](0020-command-workflows-without-temporal.md)).

**Ownership.**

| Contract | Owner | Consumers |
|---|---|---|
| Organization definition v1 | this repository, [`docs/contracts/organization-definition-v1.md`](../contracts/organization-definition-v1.md) | agentux-command (stores, validates, publishes, runs), agentux-apps (Office shows, the editor drafts) |
| AUXP v1, Office projection, approval resolution | [agentux-protocol](https://github.com/agentux-os/agentux-protocol) schemas and fixtures, and its `auxp` crate | agentux-core (node gateway), agentux-command, agentux-apps |

**Changes.** A change to the definition contract is a pull request here; one
that changes a meaning also amends this ADR or replaces it. Minor versions add
optional fields and keep meanings; a major version needs a migration that
writes new drafts (never rewriting a published definition) and a
compatibility window in which Command accepts both. Command and Office
implement a change after it is merged here; agentux-protocol's schemas follow
the same rule for AUXP (additive within v1).

## Alternatives considered

- **Share Command database tables with Office** — couples deployments and
  makes remote read-only access unsafe.
- **Hard-code departments and workflows** — prevents leadership from defining
  a new organization without a release.
- **Use unversioned JSON blobs** — makes replay, migration and auditability
  ambiguous.

