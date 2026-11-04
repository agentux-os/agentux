# 0024. Security boundaries for agent session sandboxes

- **Status:** Proposed; amends [0023](0023-agent-session-sandbox.md)
- **Date:** 2026-11-04

## Context

[ADR 0023](0023-agent-session-sandbox.md) selects Bubblewrap for agent sessions. Review of the implementation boundary found that mounting the daemon's full control socket, allowing project-selected host paths, and sharing the host network would leave important ways for an agent to affect the host or disclose data. ADRs are immutable once accepted, so this ADR adds security constraints without rewriting the accepted decision. Where the two decisions differ, this ADR takes precedence.

## Decision

### Daemon access is session-scoped

- A sandbox never receives the `agentuxd` control socket. That socket serves privileged local RPC methods and is accessible to processes running as its owner, including the harness.
- Core creates a separate bus endpoint for each sandboxed session. It exposes only `bus.hello` and `bus.call`, validates that session's token, rejects tokens for other sessions, and is removed when the session ends.
- `aux bus-stdio` inside the sandbox connects only to this endpoint. No RPC method for starting or cancelling runs, resolving approvals, or controlling terminals is reachable from the sandbox.

### Projects cannot add host paths

- `agentux.yaml` cannot request additional host mounts, including read-only mounts. A read-only mount still discloses the file contents.
- Extra paths, if needed, are selected only by machine policy and mounted read-only. Core resolves and validates them against the administrator's allowlist before mounting; symlinks or paths that resolve outside an approved root are rejected.
- Credential stores and other sensitive locations are denied even if a broader path is allowlisted. This includes SSH and GPG material, keyrings, GitHub, cloud and Kubernetes credentials, Docker credentials, browser profiles, Git credential files, and every harness's credentials or state except the explicitly selected harness credential file described below.
- A machine policy cannot be changed by a sandboxed session. If a requested path is not explicitly allowed, Core fails closed and reports the reason.

### Harness state and credentials are separate

- Each supported harness gets a separate sandbox-owned state directory for settings, history, hooks, caches and MCP configuration. It is mounted at the paths expected by that harness; the host's CLI state is not mounted.
- Only the credential file or credential environment variables required by that harness are exposed. The harness table documents each path, token type and write access. A sandboxed agent can use and exfiltrate its own harness credentials; this is an explicit residual risk, not a claim that those credentials are protected from the agent.
- Harnesses whose credential paths and behavior have not been verified are unavailable in sandbox mode until validated. Tests verify that host settings and another harness's state remain inaccessible and unchanged.

The initial credential inventory is:

| Harness | Credential source to verify | Exposure | File write access |
|---|---|---|---|
| Claude Code | `~/.claude/.credentials.json` or `ANTHROPIC_API_KEY` | Claude access/refresh token or API key; file is writable only if refresh requires it |
| Codex | `~/.codex/auth.json` or `OPENAI_API_KEY` | OpenAI API key or ChatGPT token; file is writable only if refresh requires it |
| OpenCode | `~/.local/share/opencode/auth.json` or provider environment variables | Credentials for configured providers; file is writable only if refresh requires it |
| Antigravity | Not supported until its credential path and behavior are verified | None |

If a CLI needs to refresh a mounted credential file, the required write access is explicit in its harness entry and tests; the rest of its host state remains unavailable.

### Network access is isolated and bounded by rollout phase

- The `full` host-network mode described in ADR 0023 is withdrawn. The project setting is `network: outbound` (the default) or `network: none`; any other value fails closed. Sandbox sessions use a separate network namespace. The `outbound` mode must not map the host loopback or host gateway into the sandbox; `none` provides no network. Missing network isolation support fails the run rather than falling back to the host network.
- With `outbound`, the namespace is connected through pasta configured with `--no-map-gw`; loopback packets are dropped instead of translated to the host. The implementation must test this behavior against the shipped pasta version ([passt manual](https://passt.top/builds/latest/web/passt.1.html)).
- Phase 1 may allow outbound access to the LAN and internet. The agent can still send out the worktree and its own harness credentials. This phase is for opt-in workstation use with repositories the user is willing to run; it is not suitable for production nodes accepting work from Command.
- Because phase 1 permits LAN access, services bound to a host's non-loopback interface may still be reachable. The isolation claim is specifically that the host loopback is not mapped; it does not claim that all host services are unreachable.
- Production use requires the filtering proxy from phase 3. It allows only configured provider, catalog and package-registry destinations, and blocks loopback, private, link-local and cloud metadata ranges. The proxy policy is controlled by the machine and cannot be relaxed by a project.

### Git configuration stays controlled

- The host's global Git configuration and credential helpers are not mounted. Sandboxed Git uses an empty global config and receives the repository's effective author and committer identity from Core.
- Commits made in the sandbox are unsigned unless a later design provides a signing service outside the sandbox. Signing, pushing and opening pull requests remain outside the sandbox.
- `.git/config` and `.git/hooks` remain read-only. Core's own Git operations disable hooks. If a repository's existing `core.hooksPath` points into the worktree, the cockpit and CLI warn that a host-side commit could execute worktree-controlled hooks.

### Phase 1 acceptance checks

Before enabling the sandbox for a harness, automated tests must verify that its session:

- cannot connect to the daemon control socket or invoke non-bus RPC methods;
- can call the bus only with its own session token;
- cannot read host-home files, another harness's credentials/state, or machine-policy files;
- cannot gain host paths through project configuration, path traversal or symlinks;
- cannot reach host loopback services, and fails closed if the isolated network cannot be established;
- cannot modify host CLI settings, `.git/config` or `.git/hooks`, and creates commits with the intended identity;
- leaves no child processes after cancellation.

Tests also cover each supported harness's credential paths. The real-harness workflow confirms those paths against the tested CLI version. Production-node rollout waits for the proxy policy and its private/link-local/metadata blocking checks.

## Consequences

- The daemon control API, host credentials outside the selected harness, and arbitrary host files remain outside the session's view.
- Workstation opt-in still carries the risk that an agent can exfiltrate its worktree and its own harness login over allowed outbound connections.
- Some tools that depend on unapproved host configuration or caches will not work until an administrator explicitly allows safe paths.
- Sandboxed commits are unsigned, and repositories with hooks stored inside the worktree require care when a person later commits on the host.
- The per-session bus endpoint, isolated harness state, network filtering and credential-path checks add work to Core; these controls are prerequisites for relying on the sandbox's isolation claims.

## Alternatives considered

- **Mount the daemon socket and rely on `aux bus-stdio`:** rejected because a harness can connect to the socket directly and invoke methods beyond the bus.
- **Let each project declare read-only host paths:** rejected because repository-controlled paths can disclose secrets even when they cannot be modified.
- **Keep host networking for convenience:** rejected because it exposes host-local services and permits unrestricted exfiltration. Workstation outbound access remains a documented phase 1 risk; production nodes require the proxy.
- **Mount the harness's full host state:** rejected because settings, hooks and MCP configuration could be altered and later run outside the sandbox.
