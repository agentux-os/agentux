# 0023. Agent sessions in a Bubblewrap sandbox

- **Status:** Proposed (revised after review; see [agentux#43](https://github.com/agentux-os/agentux/pull/43#issuecomment-6621064640))
- **Date:** 2026-11-04

## Context

[ADR 0009](0009-container-isolation-for-checks.md) runs gate checks in rootless Podman, but left the agents themselves on the host: a harness CLI in an ACP session ([0002](0002-harness-integration-via-acp.md)) runs as the user running `agentuxd`. It can read the whole home directory (SSH keys, `gh` tokens, other harnesses' logins, browser profiles), reach any host and leave processes behind. Its tools run with the same access. That includes the MCP servers it starts ([agentux-core#68](https://github.com/agentux-os/agentux-core/issues/68)) and every shell command an `allow` permission rule lets through ([0021](0021-tool-permission-policies.md)). Permission rules decide *whether* a tool call runs, not *what it can reach*.

ADR 0009 kept agents out of containers because the CLIs need the user's logins and toolchain. A container image would have to carry every harness CLI and the project's toolchain, and the logins would have to be copied in. Agent frameworks treat sandboxed execution as a pluggable layer (AgentScope runs tools in Bubblewrap, Docker, Kubernetes or remote sandboxes). AgentUX owns the operating system, so it can sandbox every harness the same way without any vendor's cooperation.

[ADR 0022](0022-core-command-responsibility-boundary.md) makes sandbox setup and machine restrictions Core's on each node: AgentUX Command can ask for stricter settings but can never relax a machine's. This ADR decides what that sandbox is.

Two constraints shape the choice. The harness must keep **its own** login (and nothing else of the user's) and the host toolchain (`npx`, the CLIs, compilers). And sessions must still work with the cockpit, the agent bus and terminal handoff ([0007](0007-terminal-mode-is-a-session-handoff.md)).

## Decision

**Agent sessions can run in a [Bubblewrap](https://github.com/containers/bubblewrap) sandbox, opt-in per project and enforceable per machine.**

```yaml
isolation:
  mode: podman            # checks, as in ADR 0009
  agents:
    mode: bubblewrap      # none (default) | bubblewrap
    network: outbound     # outbound (default) | none
```

A project can turn the sandbox on and tighten its network. It cannot widen what the sandbox sees: there is no per-project list of host paths (see *Extra host paths* below).

### What a sandboxed session sees

agentuxd starts the harness's ACP command as `bwrap … -- <harness command>`:

- **Namespaces:** user, PID, IPC, UTS and **network**, with `--die-with-parent` and `--new-session`. The agent and everything it starts live in the sandbox's PID namespace.
- **System:** `/usr`, `/etc`, `/opt` and the other system directories read-only, so the image's toolchain and the CLIs installed on the system work as on the host. Also `/proc`, a minimal `/dev`, and a private `/tmp` and `/run` (with only the resolver's stub file mounted in, for DNS). `/run/user/<uid>` is not mounted, so there's no D-Bus session bus, keyring, SSH agent or Wayland socket.
- **Home:** an **empty tmpfs** at `$HOME`, with only these mounted into it:
  - the run's **worktree**, read-write;
  - the repository's **git directory**, read-write so the agent can commit, except **`hooks/` and `config`, which are read-only** (see *Git* below);
  - the harness's **sandbox state** and its **credential file** (see *Credentials* below);
  - the harness's **install location**, read-only (for example `~/.local/bin/claude`, `~/.opencode`);
  - a **sandbox-only npm cache** (`~/.local/share/agentux/sandbox/npm`, as `NPM_CONFIG_CACHE`), so `npx` can fetch the ACP adapters without being able to poison the user's own cache;
  - the session's **bus socket** (see *The bus, not the daemon* below).

### The bus, not the daemon

agentuxd's control socket (`0600`, owned by the user) serves every RPC method: starting and cancelling runs, approving requests, terminals. A session token protects `bus.call`, but nothing stops a process running as the user from calling the other methods directly. **The control socket is never mounted in a sandbox.**

Each sandboxed session instead gets its **own bus socket**, created by agentuxd for that session and removed when it ends:

- It serves only `bus.hello` and `bus.call`, and only for the session it was made for. The session's token is still checked, and a token for another session is refused.
- `aux bus-stdio` inside the sandbox connects to it (`--socket` names it). Nothing else of the daemon's API is reachable from inside.

### Credentials, precisely

Mounting a harness's whole state directory read-write would give the agent more than its login. These files hold session tokens and the CLI's own settings, hooks and MCP configuration. A sandboxed agent could rewrite them and have them run **unconfined** the next time the user starts that CLI on the host. So:

- Each harness gets a **separate sandbox state directory** (`~/.local/share/agentux/sandbox/state/<harness>/`), mounted at the paths the CLI expects. Its session history, caches and settings live there and persist across sandboxed sessions, so the terminal handoff can resume them. The host's settings, hooks and MCP configuration are not visible and can't be changed. The tool catalog ([agentux-core#68](https://github.com/agentux-os/agentux-core/issues/68)) supplies MCP servers.
- Only the **credential file** is mounted from the host, read-write so the CLI can refresh its token, and it shares the login with the host:

| Harness | Credential mounted from the host | What the agent can do with it |
|---|---|---|
| claude-code | `~/.claude/.credentials.json` (OAuth access and refresh tokens), or `ANTHROPIC_API_KEY` | Read and use the Claude login or key; rewrite the file (at worst, sign the user out) |
| codex | `~/.codex/auth.json` (API key or ChatGPT tokens), or `OPENAI_API_KEY` | Same, for the OpenAI login |
| opencode | `~/.local/share/opencode/auth.json` (provider keys), or the providers' variables | Same, for every provider configured in OpenCode |
| antigravity | to verify with the CLI before it is supported in the sandbox | — |

- **Accepted risk:** a sandboxed agent can read, use and send its own harness's tokens. They are scoped to that vendor's account. It cannot read any other harness's tokens, SSH keys, `gh`'s token or the keyring.
- **Validated by tests**, per harness, with scripted harnesses: the session cannot read a file planted in the host home or in another harness's state; a write to the CLI's settings inside the sandbox leaves the host's settings unchanged; and the credential file is the only host file it can write outside the worktree and git directory. The real-harness workflow ([agentux#28](https://github.com/agentux-os/agentux/issues/28)) checks the paths against each CLI's actual version.
- API keys from the secret service or systemd credentials keep reaching the harness as environment variables, only its own, as today.

### Git

- **No user configuration inside.** `GIT_CONFIG_GLOBAL=/dev/null`: the user's `~/.gitconfig` (credential helpers, aliases, includes) isn't visible.
- **Identity from outside.** agentuxd reads `user.name` and `user.email` from the host's configuration for the repository and passes them as `GIT_AUTHOR_*` and `GIT_COMMITTER_*`.
- **Unsigned commits.** Commits inside are unsigned (`commit.gpgsign=false`), since no signing key is reachable. Signing, pushing and opening the pull request stay with agentuxd's `pull_request` step, outside the sandbox.
- **Read-only `hooks/` and `config`** in the git directory. Otherwise a hook, or a `core.hooksPath`, written by the agent would run outside at the next `git` command on the host.
- **Hooks in the worktree.** If the repository already sets `core.hooksPath` to a directory *in the worktree*, the agent can edit those hooks. agentuxd runs its own `git` commands with `core.hooksPath=/dev/null`, and `aux`/the cockpit warn about such repositories, since a user who commits in that worktree on the host would run them.

### Network

`outbound` gives the sandbox its **own network namespace**, connected outward through [pasta](https://passt.top/) (installed with Podman) with **no route to the host's loopback** (`--no-map-gw`). Services listening on the host's `localhost` (databases, development servers, the Podman API) can't be reached. `none` gives no network at all, which only suits harnesses with a local model.

**What phase 1 still allows (explicit limitations):**
- the LAN, link-local addresses and cloud metadata endpoints (`169.254.169.254`), and any host on the internet;
- sending out what the agent can read: the worktree and its own harness's credentials.

Phase 1 is therefore suited to workstations and to repositories the user is willing to run agents on, **not yet to production nodes** taking work from Command. Those need phase 3: an allow-list proxy outside the sandbox (only the provider's API, the catalog's MCP hosts and package registries), with link-local and private ranges blocked.

### Extra host paths

Tools that expect parts of the home directory (`~/.cargo` for a build cache, a language server's configuration) need a way in. A **project can't add them**, because a repository is untrusted input and a read-only mount still discloses the content. Only the **machine** can:

- `/etc/agentux/node-policy.yaml` (or the user's `~/.config/agentux/sandbox.yaml`, which agents can't write) lists allowed extra paths.
- Credential locations are **always refused**, even if listed: `~/.ssh`, `~/.gnupg`, `~/.local/share/keyrings`, `~/.config/gh`, `~/.aws`, `~/.kube`, `~/.docker`, `~/.netrc`, `~/.git-credentials`, browser profiles, and any harness's state.

### Everything a session starts is inside

- **MCP servers** from the tool catalog are started by the agent, so they inherit the sandbox.
- **Terminal handoff** (`aux attach`, the cockpit's terminal) runs the vendor's TUI resume command under **the same profile**. A sandboxed session is never resumed unconfined.
- **Cancelling** a run or ending a session kills the sandbox's PID 1, which takes every process in it along.

### Policy and reporting

- **Per project:** `isolation.agents` in `agentux.yaml`, read from the commit the run started from (like `isolation` in ADR 0009). An agent cannot loosen its own sandbox.
- **Per machine:** `/etc/agentux/node-policy.yaml` can require it (`agents: { isolation: required }`), for example on nodes that take runs from AgentUX Command. A required sandbox wins over a project's `mode: none`. As in [0022](0022-core-command-responsibility-boundary.md), an organization's policy from Command can require it on its nodes but can't turn off a machine's requirement.
- **Reporting:** a run records the isolation each session ran with. The cockpit shows it on the session, `aux ps` prints it, and AUXP run events carry it, so Command can see unconfined runs.
- **Missing Bubblewrap or pasta is an error, never a silent fallback.** Both ship with the image (Bubblewrap as Flatpak's sandbox, pasta with Podman). If either is missing, the run fails with the reason instead of running unconfined.

### Rollout

1. **Phase 1 (workstations):**
   - `mode: bubblewrap` with `network: outbound | none`, opt-in;
   - the per-session bus socket;
   - sandbox state and credential mounts per harness (claude-code, codex, opencode);
   - git identity from outside;
   - machine-only extra paths.

   Tests with scripted harnesses check that the session:
   - cannot reach the control socket or the host's loopback;
   - cannot read a planted file in the host home or another harness's state;
   - cannot write `.git/hooks`, `.git/config` or the host's CLI settings;
   - commits with the host's identity;
   - leaves no processes after cancel.

   A documented manual check with each real CLI.
2. **Phase 2:** node policy `required`, AUXP reporting, and the default for runs started from Command.
3. **Phase 3 (production nodes):** the allow-list proxy, with private and link-local ranges blocked, per harness and per catalog entry.

## Consequences

- With two lines in `agentux.yaml`, an agent that goes wrong, or a malicious instruction in a repository, can no longer reach:
  - the user's files outside the worktree, the git directory and its own harness's sandbox state and credential;
  - the daemon's control API;
  - services on the host's loopback.

  It can still reach the network outward, and its own harness's login.
- The harness keeps working with the host toolchain and its login, with no image to build and no credentials to copy.
- Sandboxed sessions don't see the user's own CLI settings, hooks or MCP servers. That is intended. The tool catalog is how they get tools.
- Tools that expect the user's whole home fail inside until the machine allows the paths. Writable caches outside the worktree stay a known gap (a per-project writable cache is possible later).
- A harness that moves its state or credential file breaks until the table is updated. The table is tested against each CLI's documented paths and checked in the real-harness workflow.
- Commits made inside are unsigned. Repositories that require signed commits need agentuxd to sign outside (not in phase 1).
- Bubblewrap's user namespaces must be enabled. They are on Fedora, where Flatpak depends on them.

## Alternatives considered

- **Rootless Podman per session (like checks)**: strong isolation and a known tool, but each harness CLI, its adapter and the project's toolchain would have to be in the image, and logins copied in and out. Startup is per container. Checks are a good fit for it (one toolchain, no login); agents are not.
- **Landlock alone**: unprivileged and fine-grained for files, but no PID or mount namespace, so it can't kill everything a session started or hide `/proc`. Its rules depend on the kernel's ABI version. It may later be added inside the Bubblewrap sandbox for defense in depth.
- **systemd-run --user with sandboxing properties** (`ProtectHome`, `BindPaths`): most of those properties need privileges a user manager doesn't have, or user namespaces that it sets up less flexibly than Bubblewrap.
- **Each vendor's own sandbox** (Claude Code's and Codex's sandbox modes): useful, but different per CLI, configured in each CLI's own files, and not something AgentUX can enforce or report uniformly. They can stay on inside the AgentUX sandbox.
- **Firejail**: a setuid binary with a large profile language, a bigger attack surface than Bubblewrap, and not in the image.
