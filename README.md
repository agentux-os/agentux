# AgentUX

> **The Linux distribution where every coding agent works as one team.**

AgentUX is a Linux distribution for developers who use coding agents from several vendors. It ships the providers' own CLI harnesses — Claude Code, Codex, OpenCode, Antigravity CLI — already installed and wired together: one interface on top of all of them, an agent bus so they can talk to each other, and an orchestrator that takes work from issue to reviewed pull request.

> **Status:** pre-release (0.3). A bootable image exists, with `agentuxd`, `aux`, the cockpit and every vendor CLI installed; runs go from prompt to pull request through real harness sessions over ACP, agents talk over the agent bus, and any session opens in its vendor's TUI. Cross-vendor runs with real Claude Code, Codex and Antigravity sessions have not been validated end to end yet. Decisions are recorded in [`docs/adr/`](docs/adr/).

## Try it

Install the image from the ISO, or switch an existing Fedora Atomic / bootc system to it:

```sh
sudo bootc switch ghcr.io/agentux-os/agentux:latest
systemctl reboot
```

Details, the ISO download and rollback are in the [agentux-os README](https://github.com/agentux-os/agentux-os#install). After the first login, follow [Getting started](docs/getting-started.md): log in to the vendor CLIs, take the cockpit tour and start a first run.

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

Done:

- [x] **Core MVP:** `aux run` drives a planner, an implementer and a cross-vendor reviewer through gates to an open PR, as a persisted state machine in its own worktree ([agentux-core](https://github.com/agentux-os/agentux-core)).
- [x] **Agent bus:** agents message each other, request reviews, hand off and escalate to you; you can post on the bus and talk to a live session.
- [x] **Cockpit:** run board, unified session view, approvals inbox, agent bus feed and spend, on the real daemon ([agentux-desktop](https://github.com/agentux-os/agentux-desktop)).
- [x] **First image:** bootable AgentUX image and ISO with harnesses, toolchain, daemon, cockpit and Plasma defaults; pinned component releases, nightly image and boot test ([agentux-os](https://github.com/agentux-os/agentux-os), [ADR 0008](docs/adr/0008-releases-and-image-pinning.md)).
- [x] **Terminal mode:** any session opens in its vendor's TUI on the same conversation, from the cockpit or `aux attach` ([ADR 0007](docs/adr/0007-terminal-mode-is-a-session-handoff.md)).

Next:

- [ ] End-to-end validation with real harnesses: Claude Code, Codex and Antigravity sessions driven through a full run (OpenCode has been tried).
- [ ] Container-isolated command execution: gate checks in rootless Podman, opt-in per project, designed in [ADR 0009](docs/adr/0009-container-isolation-for-checks.md) ([agentux-core#13](https://github.com/agentux-os/agentux-core/pull/13)); agents' own tool calls next.
- [ ] Hyprland image variant.
- [ ] Signed RPMs and images.
- [ ] `aarch64` builds.

## License

[Apache 2.0](LICENSE)
