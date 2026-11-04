# 0022. Core executes locally; Command orchestrates organizations

- **Status:** Accepted; clarifies [0003](0003-workflow-engine.md), [0015](0015-organization-command-office-contract.md), [0020](0020-command-workflows-without-temporal.md) and [0021](0021-tool-permission-policies.md)
- **Date:** 2026-11-04

## Context

AgentUX Core and AgentUX Command are separate Rust projects that cooperate
through AUXP. Core runs `agentuxd` and `aux` on a workstation or node: it owns
project worktrees, local workflow runs, harness sessions, tool execution and
the local state needed to resume them. Command is the optional organizational
control plane: it owns operators, organizations, enrolled nodes, published
organization definitions and missions that span nodes.

Both products use words such as *run*, *workflow*, *agent* and *policy*. Without
an ownership boundary, the same execution could acquire two state machines,
local credentials could drift into the server, or an organization policy could
silently weaken a machine's safety rules. This decision defines the boundary
and the direction of authority; it does not claim that every follow-up below
has already been implemented.

## Decision

### Ownership

| Concern | Owner | Authority |
|---|---|---|
| Organization identity, operators and organization-scoped authorization | Command | Source of truth for the organization and its operators |
| Node enrollment, inventory and organization mission definitions | Command | Source of truth for desired organizational state |
| Cross-node mission lifecycle, scheduling, deadlines, retries, approvals and audit | Command | Source of truth for the organizational mission and its transitions |
| Dispatch of work to a node and aggregation of reported results | Command | Sends capability-negotiated AUXP commands; records what each node reports |
| Remote requests to a node: start or cancel a run, answer an approval, change agent preferences, apply a catalog or policy version | Command requests, Core decides | Command sends the request; the node's `/etc/agentux/node-policy.yaml` decides whether it runs, waits for someone at the machine to accept it, or is refused, and Core reports the outcome |
| Worktrees, local `agentux.yaml` pipelines, harness sessions and local run state | Core on each machine | Source of truth for the local execution and its resumable state |
| Local credentials, sandbox setup and enforcement of machine restrictions | Core on each machine | Credentials remain local; remote policy cannot relax a machine restriction |
| Agent-to-agent coordination within a local run | Core | Uses the local agent bus and the local run's state |
| Wire types, event envelopes, identifiers and capability negotiation | agentux-protocol (AUXP) | Shared versioned contract; neither service shares the other's database |

Command must not start harness processes, own a node's worktree, or receive
provider credentials. Everything it asks of a node is a request that the
node's policy may hold for local confirmation or refuse. Core must not become the source of truth for organization
membership, cross-node mission state or operator authorization.

### Two levels of workflow

An organization mission belongs to Command. It describes an organizational
outcome, its target nodes, cross-node ordering and governance. Command owns its
durable transitions, waits, retries and audit trail as specified by [0020](0020-command-workflows-without-temporal.md).

A step that requires agent work is dispatched to Core on a selected node as a
bounded local execution. Core owns that execution's worktree, harness session,
local pipeline state and process lifetime. A project `agentux.yaml` pipeline
remains a Core concern and may run on its own or be invoked as a Command mission
step. Command records the returned Core run identifiers and reported status;
it does not duplicate Core's local pipeline state machine.

The desktop-only product remains usable with Core alone. Installing Command
adds organization-wide identity, policy and cross-node orchestration; it is not
a prerequisite for a local agent session or project pipeline.

### Policy and credentials

Command owns versioned organization defaults and assignments to nodes or node
groups. Core translates those desired settings into its local policy model and
enforces the effective policy. Machine restrictions and explicit local denies
remain authoritative and cannot be weakened by a Command update. Command
records whether an assigned version is applied, pending, unsupported, in
conflict or failed; Core reports that status over AUXP.

Catalog entries may refer to secrets, but secret values and harness login
state stay on the node. Core resolves local references and does not place
credentials in AUXP events, Command projections or organization definitions.

The exact catalog format, policy merge rules and delivery commands are
specified by their implementation work: [Core #68](https://github.com/agentux-os/agentux-core/issues/68)
and [Command #57](https://github.com/agentux-os/agentux-command/issues/57).

### Events and correlation

Core reports local execution facts over the capability-negotiated AUXP event
contract. Events carry stable references that let Command correlate the
organization mission, mission step, target node, Core run, session, agent and
task or step when those values apply. A consumer uses event IDs, node sequence
cursors and the protocol's replay rules to deduplicate and resume; it must not
infer delegation or task trees from provider-specific text.

Core owns local execution state and emits the facts; Command owns durable
receipt, organization-level correlation and projections. Events expose safe
summaries and bounded artifact references, never private chain-of-thought or
credentials. The typed activity, handoff and replay contract is tracked in
[agentux-protocol #12](https://github.com/agentux-os/agentux-protocol/issues/12),
with the remote mission view in [agentux-apps #19](https://github.com/agentux-os/agentux-apps/issues/19).

### Implementation follow-ups

- Core isolation for agent sessions and reporting the isolation in effect:
  [agentux-core #67](https://github.com/agentux-os/agentux-core/issues/67).
- Shared tool catalog and local application of organization policy:
  [agentux-core #68](https://github.com/agentux-os/agentux-core/issues/68) and
  [agentux-command #57](https://github.com/agentux-os/agentux-command/issues/57).
- Typed activity, delegation, handoff and replay:
  [agentux-protocol #12](https://github.com/agentux-os/agentux-protocol/issues/12).

These follow-ups must preserve the ownership and authority defined here. Their
issues remain the implementation source of truth; acceptance of this ADR does
not close or imply completion of those issues.

## Consequences

- Core remains independently useful on a single desktop, while Command can
  coordinate multiple Core nodes without owning their processes or secrets.
- Command and Core can evolve independently as long as both honor the AUXP
  contract and its negotiated capabilities.
- A mission has one organizational state machine in Command and one local
  execution state in Core; IDs and events connect them without merging their
  databases.
- Organization policy can be centrally reviewed and assigned, while a node
  keeps the final authority to enforce stricter local restrictions.
- Reconnect, replay and status views depend on precise AUXP identifiers and
  event semantics; those remain protocol work, not UI inference.
- The boundary adds policy reconciliation and correlation work. Both services
  must expose unsupported capabilities and conflicts instead of silently
  treating a requested change as applied.

## Alternatives considered

- **Command runs harnesses directly.** This would centralize provider logins
  and project files in the control plane, and would not execute work on
  enrolled desktops or nodes.
- **Core owns organization missions.** Core has no organization-wide identity,
  operator authorization or durable cross-node view, and a desktop-only
  daemon cannot be the authority for a fleet.
- **Both services own the same workflow.** Duplicated transitions and retries
  would make one run's status ambiguous after reconnects or restarts.
- **Share a database or internal Rust crates as the runtime boundary.** This
  couples deployment and persistence. AUXP remains the versioned network
  contract, as established by [0015](0015-organization-command-office-contract.md).
