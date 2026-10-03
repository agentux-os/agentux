# AgentUX

> **One control plane for every coding agent you already use.**

AgentUX orchestrates coding agents from different vendors — Claude Code, Codex, OpenCode, Antigravity and any other harness that speaks the [Agent Client Protocol](https://agentclientprotocol.com) — across multiple projects, from issue to reviewed pull request.

> **Status:** early design. No runnable code yet; decisions are being recorded in [`docs/adr/`](docs/adr/).

## Why

Running several agents in parallel worktrees is already a solved problem. What is missing:

- **Cross-vendor pipelines.** One vendor's agent implements, another vendor's agent reviews. Different models catch different mistakes.
- **Workflows as code.** The pipeline (plan → implement → test → review → PR) is declared in the repository and versioned with it.
- **Durable runs.** A rate limit, crash or reboot pauses a run; it does not lose it.
- **Headless first.** Runs on Linux, Windows and macOS, on a laptop or a server. The UI observes and approves; it is not required.

## How it works

1. You hand AgentUX an issue (or a prompt).
2. It creates a git worktree and branch for the task.
3. An implementer harness works in that worktree; its events stream to the CLI and cockpit.
4. Tests and linters gate the result; failures loop back to the implementer, up to a limit.
5. A reviewer harness from a different vendor reviews the diff.
6. AgentUX opens the pull request and asks you only for the decisions that are yours.

Inference stays with the providers, using your own logins and API keys. AgentUX is the orchestration layer.

## Repositories

| Repo | Contents |
|---|---|
| [agentux](https://github.com/agentux-os/agentux) | Specification, roadmap, ADRs |
| [agentux-core](https://github.com/agentux-os/agentux-core) | Daemon, `aux` CLI, workflow engine, harness adapters |
| [agentux-desktop](https://github.com/agentux-os/agentux-desktop) | Cockpit UI |
| [agentux-os](https://github.com/agentux-os/agentux-os) | Optional Linux flavor (planned) |

## Roadmap

- [ ] **MVP:** `aux run <issue>` drives one implementer and one cross-vendor reviewer to an open PR.
- [ ] Parallel runs across several projects, with a terminal dashboard.
- [ ] Cockpit UI: live status, diffs, approvals, token spend.
- [ ] Container-isolated command execution.
- [ ] Optional Linux flavor with AgentUX and the toolchain preinstalled.

## License

[Apache 2.0](LICENSE)
