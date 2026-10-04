# Architecture Decision Records

Each ADR records one decision: the context, what was decided, and what it costs. ADRs are immutable once accepted; a later ADR supersedes or amends an earlier one instead of editing it, and the index below records the link.

| # | Title | Status |
|---|---|---|
| [0001](0001-linux-distribution-on-fedora-atomic.md) | AgentUX is a Linux distribution, built as a bootc image on Fedora Atomic | Accepted |
| [0002](0002-harness-integration-via-acp.md) | Integrate harnesses through ACP, with headless CLIs as fallback | Accepted |
| [0003](0003-workflow-engine.md) | Start with an embedded state machine, not Temporal | Accepted |
| [0004](0004-unified-interface-and-agent-bus.md) | Unified interface over existing CLIs, and an agent bus so they talk to each other | Accepted; terminal mode amended by [0007](0007-terminal-mode-is-a-session-handoff.md) |
| [0005](0005-agentux-yaml.md) | Pipelines are declared in `agentux.yaml` | Accepted; amended by [0009](0009-container-isolation-for-checks.md) |
| [0006](0006-rust-and-tauri.md) | Rust for agentuxd and aux; Tauri 2 with React and TypeScript for the cockpit | Accepted |
| [0007](0007-terminal-mode-is-a-session-handoff.md) | Terminal mode is a handoff of the vendor session, not a second driver | Accepted; amends [0004](0004-unified-interface-and-agent-bus.md) |
| [0008](0008-releases-and-image-pinning.md) | Releases and image pinning | Accepted |
| [0009](0009-container-isolation-for-checks.md) | Optional container isolation for check commands | Accepted; amends [0005](0005-agentux-yaml.md) |

New ADRs copy [`template.md`](template.md) and take the next number.
