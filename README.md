# AgentUX

> **The Linux distribution where every coding agent works as one team.**

AgentUX is a Linux distribution for developers who use coding agents from several vendors. It ships the providers' own CLI harnesses — Claude Code, Codex, OpenCode, Antigravity CLI — already installed and wired together: one interface on top of all of them, an agent bus so they can talk to each other, and an orchestrator that takes work from issue to reviewed pull request.

> **Status:** early design. No runnable code or image yet; decisions are being recorded in [`docs/adr/`](docs/adr/).

## Why

Running several agents in parallel worktrees is already solved by many tools. What is missing:

- **One interface for every vendor.** Sessions, diffs and permission requests from any harness look the same and land in one approval inbox. The original TUI is always one click away.
- **Agents that talk to each other.** An implementer can ask a reviewer from another vendor to check its diff, hand off a task, or escalate a decision to you — all through a mediated, auditable bus.
- **Workflows as code.** The pipeline (plan → implement → test → review → PR) is declared in the repository and versioned with it.
- **A system agents cannot break.** Immutable, image-based OS with one-step rollback; every task runs in its own git worktree.

## How it works

1. You hand AgentUX an issue (or a prompt) from the cockpit or the `aux` CLI.
2. It creates a git worktree and branch for the task.
3. An implementer harness works in that worktree; its session streams to the cockpit.
4. Tests and linters gate the result; failures loop back to the implementer, up to a limit.
5. A reviewer harness from a different vendor reviews the diff, talking to the implementer over the agent bus when needed.
6. AgentUX opens the pull request and asks you only for the decisions that are yours.

Inference stays with the providers, using your own logins and API keys. No GPU required.

## Architecture

| Layer | What it is |
|---|---|
| OS | Fedora Atomic built with bootc; KDE Plasma (Wayland); immutable with atomic rollback |
| Harnesses | Each provider's CLI, driven through the Agent Client Protocol (ACP) or its headless mode |
| `agentuxd` | Daemon: runs, worktrees, sessions, workflow state (SQLite), agent bus (MCP) |
| Cockpit / `aux` | Unified desktop interface and its terminal twin |
| Toolchain | `git`, `gh`, `mise`, `uv`, `bun`, `ripgrep`, `fd`, `ast-grep`, `delta`, `lazygit`, `just`, Podman |

## Repositories

| Repo | Contents |
|---|---|
| [agentux](https://github.com/agentux-os/agentux) | Specification, roadmap, ADRs |
| [agentux-core](https://github.com/agentux-os/agentux-core) | `agentuxd`, `aux` CLI, workflow engine, harness adapters, agent bus |
| [agentux-desktop](https://github.com/agentux-os/agentux-desktop) | Cockpit app and desktop configuration |
| [agentux-os](https://github.com/agentux-os/agentux-os) | `Containerfile`, image CI and ISO builds |

## Roadmap

- [ ] **Core MVP:** `aux run <issue>` drives one implementer and one cross-vendor reviewer to an open PR, on any Linux.
- [ ] **Agent bus:** agents message each other, request reviews and escalate to you.
- [ ] **Cockpit:** unified session view, approvals inbox, run board, token spend.
- [ ] **First image:** bootable AgentUX ISO with harnesses, toolchain and cockpit preinstalled.
- [ ] Container-isolated command execution; Hyprland image variant.

## License

[Apache 2.0](LICENSE)
