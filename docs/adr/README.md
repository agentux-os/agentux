# Architecture Decision Records

Each ADR records one decision: the context, what was decided, and what it costs. ADRs are immutable once accepted; a later ADR supersedes an earlier one instead of editing it.

| # | Title | Status |
|---|---|---|
| [0001](0001-linux-distribution-on-fedora-atomic.md) | AgentUX is a Linux distribution, built as a bootc image on Fedora Atomic | Accepted |
| [0002](0002-harness-integration-via-acp.md) | Integrate harnesses through ACP, with headless CLIs as fallback | Accepted |
| [0003](0003-workflow-engine.md) | Start with an embedded state machine, not Temporal | Accepted |
| [0004](0004-unified-interface-and-agent-bus.md) | Unified interface over existing CLIs, and an agent bus so they talk to each other | Accepted |
| [0005](0005-agentux-yaml.md) | Pipelines are declared in `agentux.yaml` | Accepted |
| [0006](0006-rust-and-tauri.md) | Rust for agentuxd and aux; Tauri 2 with React and TypeScript for the cockpit | Proposed |

New ADRs copy [`template.md`](template.md) and take the next number.
