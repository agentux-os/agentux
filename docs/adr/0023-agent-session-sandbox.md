# 0023. Agent sessions in a Bubblewrap sandbox

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

[ADR 0009](0009-container-isolation-for-checks.md) runs gate checks in rootless Podman, but left the agents themselves on the host: a harness CLI in an ACP session ([0002](0002-harness-integration-via-acp.md)) runs as the user running `agentuxd`. It can read the whole home directory (SSH keys, `gh` tokens, other harnesses' logins, browser profiles), reach any host and leave processes behind. Its tools run with the same access. That includes the MCP servers it starts ([agentux-core#68](https://github.com/agentux-os/agentux-core/issues/68)) and every shell command an `allow` permission rule lets through ([0021](0021-tool-permission-policies.md)). Permission rules decide *whether* a tool call runs, not *what it can reach*.

ADR 0009 kept agents out of containers because the CLIs need the user's logins and toolchain. A container image would have to carry every harness CLI and the project's toolchain, and the logins would have to be copied in. Agent frameworks treat sandboxed execution as a pluggable layer (AgentScope runs tools in Bubblewrap, Docker, Kubernetes or remote sandboxes). AgentUX owns the operating system, so it can sandbox every harness the same way without any vendor's cooperation.

[ADR 0022](0022-core-command-responsibility-boundary.md) makes sandbox setup and machine restrictions Core's on each node: AgentUX Command can ask for stricter settings but can never relax a machine's. This ADR decides what that sandbox is.

Two constraints shape the choice. The harness must keep **its own** login state and the host toolchain (`npx`, the CLIs, compilers). And sessions must still work with the cockpit, the agent bus and terminal handoff ([0007](0007-terminal-mode-is-a-session-handoff.md)).

## Decision

**Agent sessions can run in a [Bubblewrap](https://github.com/containers/bubblewrap) sandbox, opt-in per project and enforceable per machine.**

```yaml
isolation:
  mode: podman            # checks, as in ADR 0009
  agents:
    mode: bubblewrap      # none (default) | bubblewrap
    network: full         # full (default) | none
    read_only: [~/.cargo] # optional: more host paths the agents may read
```

### What a sandboxed session sees

agentuxd starts the harness's ACP command as `bwrap … -- <harness command>`:

- **Namespaces:** user, PID, IPC and UTS, plus `--unshare-net` with `network: none`. Also `--die-with-parent` and `--new-session`. The agent and everything it starts live in the sandbox's PID namespace.
- **System:** `/usr`, `/etc`, `/opt` and the other system directories read-only. The image's toolchain and the CLIs installed on the system work as on the host. `/proc`, `/dev` (minimal) and a private `/tmp`.
- **Home:** an **empty tmpfs** at `$HOME`, with only these mounted into it:
  - the run's **worktree**, read-write;
  - the repository's **git directory**, read-write so the agent can commit, except **`hooks/` and `config`, which are read-only**: a hook or `core.hooksPath` written by an agent would otherwise run outside the sandbox at the next `git` command on the host;
  - **the harness's own state**, read-write, and no other harness's (table below);
  - the harness's **install location**, read-only (for example `~/.local/bin/claude`, `~/.opencode`);
  - a **sandbox-only npm cache** (`~/.local/share/agentux/sandbox/npm`, as `NPM_CONFIG_CACHE`) so `npx` can fetch the ACP adapters without being able to poison the user's own cache;
  - the agentuxd **socket**, so `aux bus-stdio` reaches the bus;
  - the project's `isolation.agents.read_only` paths, read-only.
- **Credentials:** API keys are passed as environment variables, as today (from the secret service or systemd credentials, as agentuxd does now), and only the harness's own. The SSH agent, `gh`'s token and the D-Bus session bus are not passed. Pushing and opening pull requests stay with agentuxd's `pull_request` step, outside the sandbox.

| Harness | Its state (read-write) |
|---|---|
| claude-code | `~/.claude/`, `~/.claude.json` |
| codex | `~/.codex/` |
| opencode | `~/.config/opencode/`, `~/.local/share/opencode/`, `~/.local/state/opencode/` |
| antigravity | `~/.gemini/` (to verify with the CLI) |

The table lives in `agentux-harness` next to each harness's launch command and is tested like it.

### Network

`full` uses the host network. `none` unshares it, which only suits harnesses with a local model. Every hosted harness needs its provider's API. An **allow-list** (only the provider's API, the MCP servers' hosts and package registries) needs a filtering proxy. That is phase 3 below, not part of this decision's first implementation.

### Everything a session starts is inside

- **MCP servers** from the tool catalog are started by the agent, so they inherit the sandbox.
- **Terminal handoff** (`aux attach`, the cockpit's terminal) runs the vendor's TUI resume command under **the same profile**. A sandboxed session is never resumed unconfined.
- **Cancelling** a run or ending a session kills the sandbox's PID 1, which takes every process in it along.

### Policy and reporting

- **Per project:** `isolation.agents` in `agentux.yaml`, read from the commit the run started from (like `isolation` in ADR 0009). An agent cannot loosen its own sandbox.
- **Per machine:** `/etc/agentux/node-policy.yaml` can require it (`agents: { isolation: required }`), for example on nodes that take runs from AgentUX Command. A required sandbox wins over a project's `mode: none`. As in [0022](0022-core-command-responsibility-boundary.md), an organization's policy from Command can require it on its nodes but can't turn off a machine's requirement.
- **Reporting:** a run records the isolation each session ran with. The cockpit shows it on the session, `aux ps` prints it, and AUXP run events carry it, so Command can see unconfined runs.
- **Missing Bubblewrap is an error, never a silent fallback.** If `bwrap` is missing (it ships with the image as Flatpak's sandbox), the run fails with the reason instead of running unconfined.

### Rollout

1. **Phase 1:** `mode: bubblewrap` with `network: full`, opt-in. Per-harness state table and tests with scripted harnesses: the session cannot read a file planted in the home directory, cannot write `.git/hooks`, and leaves no processes after cancel. A documented manual check with each real CLI ([agentux#28](https://github.com/agentux-os/agentux/issues/28)'s workflow).
2. **Phase 2:** node policy `required`, AUXP reporting, and the default for runs started from Command.
3. **Phase 3:** a network allow-list through a local filtering proxy (`HTTPS_PROXY` inside, the proxy outside), per harness and per catalog entry.

## Consequences

- With two lines in `agentux.yaml`, an agent that goes wrong, or a malicious instruction in a repository, can reach only the worktree, its own login and the network. Before, it could reach everything the user can.
- The harness keeps working with the host toolchain and its login, with no image to build and no credentials to copy.
- Tools that expect the user's whole home fail inside: a compiler cache in `~/.cargo`, a language server's config in `~/.config`. Projects list such paths in `read_only`, and caches that need writing stay a known gap (a per-project writable cache is possible later).
- A harness that moves its state directory breaks until the table is updated. The table is tested against each CLI's documented paths and checked in the real-harness workflow.
- `network: full` still lets an agent send what it can read (the worktree, its own token) anywhere. Phase 3 closes that, but phase 1 already removes everything else in the home directory from its reach.
- Bubblewrap's user namespaces must be enabled. They are on Fedora, where Flatpak depends on them.

## Alternatives considered

- **Rootless Podman per session (like checks)**: strong isolation and a known tool, but each harness CLI, its adapter and the project's toolchain would have to be in the image, and logins copied in and out. Startup is per container. Checks are a good fit for it (one toolchain, no login); agents are not.
- **Landlock alone**: unprivileged and fine-grained for files, but no PID or mount namespace, so it can't kill everything a session started or hide `/proc`. Its rules depend on the kernel's ABI version. It may later be added inside the Bubblewrap sandbox for defense in depth.
- **systemd-run --user with sandboxing properties** (`ProtectHome`, `BindPaths`): most of those properties need privileges a user manager doesn't have, or user namespaces that it sets up less flexibly than Bubblewrap.
- **Each vendor's own sandbox** (Claude Code's and Codex's sandbox modes): useful, but different per CLI, configured in each CLI's own files, and not something AgentUX can enforce or report uniformly. They can stay on inside the AgentUX sandbox.
- **Firejail**: a setuid binary with a large profile language, a bigger attack surface than Bubblewrap, and not in the image.
