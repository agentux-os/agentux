# 0025. Speak A2A at AgentUX Command's edge

- **Status:** Proposed
- **Date:** 2026-11-04
- **Revisits:** the A2A alternative in [0004](0004-unified-interface-and-agent-bus.md); follows the ownership boundary in [0022](0022-core-command-responsibility-boundary.md) and sandbox constraints in [0024](0024-agent-sandbox-security-boundaries.md)

## Context

AgentUX needs a boundary for interoperating with independent, networked agents.
The [A2A specification](https://a2a-protocol.org/latest/specification/)
defines [agent cards](https://a2a-protocol.org/latest/specification/#44-agent-discovery-objects),
[durable tasks and lifecycle states](https://a2a-protocol.org/latest/specification/#41-core-objects),
messages, artifact updates, streaming and push notifications. Its
[authentication and authorization](https://a2a-protocol.org/latest/specification/#7-authentication-and-authorization)
model does not define
AgentUX organization authority or how an external task maps to an organizational
mission and a node's local run.

AgentUX already has two different boundaries. Command owns organizations,
operators, missions and cross-node audit; Core owns local runs and execution.
The versioned [AUXP contract](https://github.com/agentux-os/agentux-protocol)
is the Command-to-node contract and remains so. Typed execution activity,
delegation and replay semantics are being defined in
[agentux-protocol #12](https://github.com/agentux-os/agentux-protocol/issues/12).
Meanwhile, the local `agentuxd` API and agent bus are machine-scoped. Exposing
them directly as a network agent endpoint would cross both the organization
authority boundary and the local sandbox boundary in [0024](0024-agent-sandbox-security-boundaries.md).

ADR 0004 recorded A2A as an alternative because harness CLIs did not speak it
and AgentUX needed local agent coordination. A2A has a different use: a
network-facing adapter for independent agent services. Local agent-to-agent
coordination remains the Core agent bus.

## Decision

AgentUX adopts A2A as an optional **Command-edge interoperability adapter**.
Command may act as an A2A server for inbound requests and an A2A client for
outbound delegation. A2A is not a node protocol: Core, `agentuxd`, `aux`, and
node enrollment continue to use AUXP and local APIs. Command never tunnels an
A2A request to a node or gives an external peer direct access to `agentuxd`.

This decision establishes a boundary, not a release commitment or a claim that
the adapter is implemented. A deployment enables the adapter only when its
operator configures it and its security controls are available.

### Inbound requests

- Command publishes an Agent Card only for explicitly enabled, published
  organization skills. The card advertises only those skills and the
  authentication methods and protocol capabilities actually supported by the
  deployment. There is no default public card or anonymous task submission.
- A2A `SendMessage` creates a Command-owned external task associated with an
  organization, authenticated principal, and allowed skill. Command resolves
  the skill through the published organization definition and existing
  `run.start` authorization. It creates or advances a mission/run through
  Command's normal workflow and policy checks. A2A cannot select a node,
  workflow step, tool, local path, or policy override outside that definition.
- A2A task ID and context ID are external correlation identifiers, not
  Command mission or Core run IDs. Command persists the mapping. A2A task state
  is a projection of Command-owned state; it never becomes a second execution
  state machine. `GetTask`, `CancelTask`, streaming, and push are exposed only
  where the deployment can enforce the same principal, organization and
  resource checks as submission. Cancellation requests go through Command's
  `run.cancel` authorization and node policy; they do not bypass local
  confirmation or refusal.

### Outbound delegation

- Command may delegate a bounded mission step to a remote A2A agent only when
  an organization administrator has registered the peer and enabled the
  specific skill for that organization and use. Peer endpoints are
  administrator-controlled; agent-provided URLs and unrestricted discovery
  are not used to route requests.
- The delegation is a Command-owned mission step and external A2A task, linked
  by durable IDs. Command owns retries, deadlines, cancellation, approval and
  audit. A remote task result is evidence returned to that step, not a
  privileged command to a node. Further work on a node still requires a
  separately authorized AUXP command and the node's own policy decision.
- Only an explicit, minimized task prompt and approved input artifacts cross
  the boundary. Command does not forward operator tokens, node credentials,
  harness logins, machine paths, sandbox state, or unapproved mission history.
  Artifact transfer uses bounded, authorized references and controlled
  retrieval; untrusted remote URLs are not fetched automatically.

### Identity, authorization and policy

- Every inbound HTTP request is authenticated using a configured supported
  transport scheme over HTTPS. Command maps the authenticated client to an
  organization-scoped operator or service principal. A valid A2A credential
  alone grants no organization access. The identity must have the existing
  permission required for the operation (`run.start`, `run.read`,
  `run.cancel`, `artifact.read`, or the corresponding finer-grained
  permission when introduced).
- Outbound credentials are separately configured per registered peer and
  stored in the deployment's secret store. Credentials are audience-bound to that
  peer, never copied from an inbound caller, and never sent to a node.
- Organization policy controls which skills may be invoked inbound, which
  peers and skills may be called outbound, allowed data classes, and operation
  budgets. Node machine policy remains the final authority for execution and
  cannot be relaxed by an A2A caller, remote agent, or organization setting.
- No A2A message, artifact, Agent Card, or remote task status is trusted as
  policy or identity input. Treat remote content as untrusted data and validate
  size, media type, schema, and references before use.

### Mapping to AgentUX state and events

- An accepted inbound A2A task maps to one Command external-task record and a
  Command mission/run (or a mission step in an existing run); it does not map
  directly to a Core run. An outbound delegation maps to a mission step and a
  remote A2A task. Both directions retain protocol task/context IDs, peer or
  caller identity, organization, mission/run/step IDs, and correlation IDs.
- Command derives task progress from its durable mission/run state and the
  typed AUXP facts received from Core. Protocol #12 is the source for node
  activity, delegation, handoff and replay semantics. This ADR does not define
  AUXP event schemas or make an A2A task a new AUXP command. Until the required
  event semantics are available, Command must not claim detailed task
  progress: it may report only states supported by its authoritative records.
- Map terminal outcomes only when their meanings agree: successful completion
  to A2A `completed`, an unrecoverable failure to `failed`, and an authorized
  cancellation to `canceled`. Waiting on a Command approval or a node decision
  remains nonterminal. A2A messages and artifacts are recorded as bounded
  evidence with provenance; they do not become private reasoning or raw node
  telemetry.

### Scope, privacy, limits and audit

- Initial scope is task submission, task status, cancellation requests, and
  outbound task delegation for explicitly enabled skills. Support for
  streaming, push notifications, broad task listing, multi-turn contexts,
  extensions, and additional bindings is opt-in per capability and deferred
  until authorization, replay and resource ownership are specified for it.
- Enforce per-principal and per-organization request and concurrency quotas,
  payload and artifact size limits, task deadlines, and outbound connection
  timeouts. Apply backpressure and return standard errors when limits are
  reached. Limits are operator-configured with conservative defaults; clients
  cannot raise them.
- Audit authentication outcomes, principal and organization, skill, peer,
  task/context and mission/run correlation, authorization decision, policy
  version, lifecycle transitions, artifact references, quota decisions, and
  cancellation. Do not log bearer credentials, full prompts, artifact bodies,
  or other sensitive payloads by default. Retention follows the organization's
  audit and data policy.
- Publish and transmit only data authorized for the receiving principal and
  skill. Data minimization applies to Agent Cards, prompts, status, traces and
  artifacts. Propagate correlation identifiers for audit and tracing without
  using them as authorization.

### Revisit conditions

Revisit this ADR before enabling A2A on a production deployment if any required
control above is missing. Amend it when one of these conditions holds:

- Protocol #12 defines events or replay behavior that cannot express the
  correlation and progress mapping above, or Command needs to add a new
  AUXP-facing capability to support A2A.
- A concrete deployment needs a Core-hosted A2A endpoint, direct node-to-agent
  communication, anonymous discovery, or a workflow that bypasses Command's
  organization authorization. Such a need requires a new trust-boundary
  decision; it is not permitted by this ADR.
- A2A's stable specification or bindings change in a way that affects task
  semantics, authentication, authorization, artifact transfer, or security.
- Operational evidence shows that quotas, privacy controls, audit, or
  organization-scoped identity do not adequately contain abuse or data
  exposure.

The separate product decision about who interprets a goal in AgentUX Apps
([agentux-apps #20](https://github.com/agentux-os/agentux-apps/issues/20)) is
out of scope. This ADR assigns no goal interpretation or product behavior to
Apps.

## Consequences

- AgentUX can interoperate with external A2A agents at the service boundary
  while keeping Command's organization authority and AUXP's node contract
  intact.
- Command gains adapter, peer registration, identity mapping, durable task
  correlation, policy, quotas, artifact handling and audit responsibilities.
- A2A's task model does not replace Command missions or Core runs. Projection
  fidelity depends on Command's durable workflow and the event/replay contract
  in AUXP.
- Users must explicitly trust and configure each peer and permitted skill;
  sharing task content with a remote agent remains a data disclosure governed
  by organization policy.
- Deferring general discovery, arbitrary capabilities and direct Core access
  reduces interoperability breadth and keeps deployment/security work
  bounded.

## Alternatives considered

- **Expose A2A from each `agentuxd`:** rejected because a local daemon lacks
  Command's organization/operator authority and would expose a new network
  path across the machine and sandbox boundary in [0024](0024-agent-sandbox-security-boundaries.md).
- **Use A2A between Command and nodes:** rejected because it duplicates the
  Command-to-node contract, state and replay semantics. AUXP remains that
  versioned boundary ([0015](0015-organization-command-office-contract.md),
  [0022](0022-core-command-responsibility-boundary.md)).
- **Reject A2A entirely:** rejected because A2A addresses networked,
  independently operated agent services, a different interoperability need
  from the local agent bus considered in [0004](0004-unified-interface-and-agent-bus.md).
- **Defer all adoption:** rejected because the ownership boundary and the
  protocol's task model support a bounded Command adapter now; implementation
  remains gated on the controls and AUXP facts described above.
