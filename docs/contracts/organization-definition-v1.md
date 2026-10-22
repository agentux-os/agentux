# AgentUX organization definition v1

This is the implementation contract shared by AgentUX Command and AgentUX
Office. It is deliberately transport-neutral: repositories may expose it as
JSON over HTTP, an event payload, or a database projection, but the fields and
invariants remain the same.

## Envelope

```json
{
  "schema_version": "1.0",
  "organization_id": "acme",
  "definition_version": 3,
  "status": "published",
  "published_at": "2026-10-15T18:00:00Z",
  "published_by": { "kind": "user", "id": "user_ceo" },
  "organization": {},
  "areas": [],
  "roles": [],
  "missions": [],
  "workflows": [],
  "agents": [],
  "nodes": [],
  "gates": []
}
```

Drafts use `status: "draft"` and omit `published_at`. IDs are stable within
an organization. A published document must be self-contained and must pass
referential-integrity validation.

## Core objects

```json
{
  "organization": {
    "id": "acme",
    "name": "Acme Robotics",
    "timezone": "America/Sao_Paulo",
    "default_approval_policy": "human-required",
    "publication_policy": "review-required"
  },
  "areas": [
    { "id": "engineering", "name": "Engineering", "owner_role_id": "cto" }
  ],
  "roles": [
    {
      "id": "cto",
      "name": "CTO",
      "principal_kind": "human",
      "permissions": ["organization.read", "organization.publish", "run.read"]
    },
    {
      "id": "reviewer",
      "name": "Reviewer",
      "principal_kind": "agent",
      "permissions": ["run.read", "artifact.read"]
    }
  ],
  "missions": [
    {
      "id": "ship-release",
      "area_id": "engineering",
      "name": "Ship a release",
      "owner_role_id": "cto",
      "success_criteria": ["tests_green", "approval_recorded"]
    }
  ],
  "workflows": [
    {
      "id": "release-v1",
      "mission_id": "ship-release",
      "steps": [
        { "id": "implement", "kind": "agent", "role_id": "reviewer", "next": ["review"] },
        { "id": "review", "kind": "gate", "gate_id": "human-release", "next": ["publish"] },
        { "id": "publish", "kind": "action", "next": [] }
      ]
    }
  ],
  "gates": [
    {
      "id": "human-release",
      "kind": "approval",
      "required_permissions": ["approval.decide"],
      "policy": "human-required"
    }
  ],
  "agents": [
    { "id": "reviewer-1", "role_id": "reviewer", "capabilities": ["code.review"] }
  ],
  "nodes": [
    { "id": "node-sao-paulo", "kind": "workstation", "trust": "registered" }
  ]
}
```

`Approval` and `Artifact` are runtime records, not static definition objects.
They reference the definition version that created them:

```json
{
  "approval_id": "approval-123",
  "organization_id": "acme",
  "definition_version": 3,
  "run_id": "run-456",
  "gate_id": "human-release",
  "requested_by": { "kind": "agent", "id": "reviewer-1" },
  "decision": "pending"
}
```

```json
{
  "artifact_id": "artifact-789",
  "organization_id": "acme",
  "definition_version": 3,
  "run_id": "run-456",
  "kind": "pull_request",
  "uri": "https://github.com/acme/project/pull/42",
  "created_by": { "kind": "agent", "id": "reviewer-1" },
  "content_digest": "sha256:..."
}
```

## Publication

A definition changes as drafts. Each save of a draft is a new **revision**;
an editor saves against the revision they read and is refused if the draft
moved on (no silent overwrite). A **review** approves one revision or asks for
changes; nobody reviews their own edits, and reviewing needs
`approval.decide`. `organization.publication_policy` (optional):

- `review-required`: only a revision approved by someone other than its
  editor can be published; a later save needs a new approval.
- absent: whoever holds `organization.publish` publishes.

`default_approval_policy` is a different thing: the default for approvals
inside runs. A rollback is a new draft from an earlier version's document,
published like any other; published versions are never edited.

## Invariants

- Every referenced area, role, mission, workflow, gate, agent and node exists
  in the same published definition.
- A workflow cannot transition to a step outside its own workflow.
- A gate with `human-required` cannot be satisfied by an agent principal.
- A run, approval and artifact always retain the definition version they used.
- Node and agent identity is runtime state; a definition may declare desired
  capabilities but cannot assert that a node is currently healthy.
- Unknown optional fields may be preserved, but unknown required fields reject
  publication.

## Command event envelope

```json
{
  "event_id": "evt-123",
  "event_type": "approval.requested",
  "schema_version": "1.0",
  "occurred_at": "2026-10-15T18:02:00Z",
  "organization_id": "acme",
  "definition_version": 3,
  "run_id": "run-456",
  "actor": { "kind": "agent", "id": "reviewer-1" },
  "correlation_id": "run-456",
  "payload": { "approval_id": "approval-123", "gate_id": "human-release" }
}
```

Office should project these events into a read model with at least:
`organization`, `areas`, `active_runs`, `pending_approvals`, `agents`,
`nodes`, `recent_artifacts`, `audit_timeline`, and `projected_at`.

