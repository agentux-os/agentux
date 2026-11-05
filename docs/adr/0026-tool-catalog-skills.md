# 0026. Tool-catalog skills are delivered per session, never into vendor directories

- **Status:** Proposed
- **Date:** 2026-11-04
- **Relates to:** [agentux-core#68](https://github.com/agentux-os/agentux-core/issues/68) (one tool catalog for every harness), [0002](0002-harness-integration-via-acp.md), [0007](0007-terminal-mode-is-a-session-handoff.md), [0022](0022-core-command-responsibility-boundary.md), [0023](0023-agent-session-sandbox.md) and [0024](0024-agent-sandbox-security-boundaries.md); requested in [agentux#49](https://github.com/agentux-os/agentux/issues/49)

## Context

The tool catalog of agentux-core#68 has three layers merged by name: the machine's `/etc/agentux/tools.yaml`, the user's `~/.config/agentux/tools.yaml` and the `tools` section of a project's `agentux.yaml`. Two of its kinds already reach every harness without touching a vendor file. MCP servers are passed in ACP's `session/new`, and instructions are added to the session prompt ([agentux-core#91](https://github.com/agentux-os/agentux-core/pull/91)). The remaining kind is **skills**.

A skill is a directory with a `SKILL.md` file: YAML frontmatter with at least `name` and `description`, Markdown instructions, and optional `scripts/`, `references/` and `assets/`. The format started at Anthropic and is published as the open [Agent Skills specification](https://agentskills.io/specification) ([repository](https://github.com/agentskills/agentskills), Apache-2.0 code and CC-BY-4.0 docs). Agents load only the name and description at startup and read the rest when a task matches ("progressive disclosure"). All four supported harnesses read this format, but each from its own directories, and ACP has no field that hands a session a skill.

What each harness reads, checked on 2026-11-04 against the vendors' documentation and, for the ACP adapters, against the versions agentux-harness pins:

| Harness (as agentuxd runs it) | User directories | Project directories | Can a launcher add a directory? | Through ACP? |
|---|---|---|---|---|
| Claude Code ([docs](https://code.claude.com/docs/en/skills)), via `claude-agent-acp` 0.85.1 | `~/.claude/skills/` (under `CLAUDE_CONFIG_DIR`); managed `/etc/claude-code/.claude/skills/`; plugins | `.claude/skills/` from the start directory up to the repository root, nested `.claude/skills/` on first use | Yes: `<dir>/.claude/skills/` for each `--add-dir` directory, and skills of local plugins ([Agent SDK skills](https://code.claude.com/docs/en/agent-sdk/skills), [plugins](https://code.claude.com/docs/en/agent-sdk/plugins)). No environment variable for skill paths | Yes. The adapter advertises `sessionCapabilities.additionalDirectories` and passes `session/new`'s `additionalDirectories` to the Agent SDK, which passes them as `--add-dir`. It also forwards `_meta.claudeCode.options` (including `plugins`) to the SDK, with `settingSources: ["user", "project", "local"]` |
| Codex CLI ([docs](https://learn.chatgpt.com/docs/build-skills)), via `codex-acp` 2.1.1 | `~/.agents/skills/`; `$CODEX_HOME/skills/` (deprecated, still read); admin `/etc/codex/skills/`; bundled system skills | `.agents/skills/` from the working directory up to the repository root; `.codex/skills/` of a trusted project | Yes, through the app-server's `skills/extraRoots/set`. No documented config key or environment variable | Yes. `codex-acp` 2.1.1 (`src/CodexAcpClient.ts`, `refreshSkills`) maps each `additionalDirectories` entry to `<dir>/.agents/skills` and sets those as extra roots. It also adds those directories to Codex's own sandbox policy |
| OpenCode ([docs](https://opencode.ai/docs/skills/)), `opencode acp` 1.18.34 | `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/` | `.opencode/skills/`, `.claude/skills/`, `.agents/skills/` from the working directory up to the worktree | Yes: the `skills.paths` (and `skills.urls`) config key in 1.18.34 (`packages/opencode/src/skill/index.ts`), and every config directory's `skill/` or `skills/`, which includes `OPENCODE_CONFIG_DIR`. Config can be given inline with `OPENCODE_CONFIG_CONTENT` ([config docs](https://opencode.ai/docs/config/)) | Indirectly. `opencode acp` turns `additionalDirectories` into file permissions only, not skill roots. The config key reaches the ACP server through the environment agentuxd starts it with |
| Antigravity ([docs](https://antigravity.google/docs/skills)), via `agy-acp-server` (experimental) | `~/.gemini/config/skills/`; the CLI also reads `~/.gemini/antigravity-cli/skills/` and `~/.gemini/skills/`; legacy `~/.gemini/antigravity/skills/` | `.agents/skills/` (and legacy `.agent/skills/`) up to the repository root | Not documented | Unknown. The ACP server is a proprietary binary ([registry entry](https://github.com/agentclientprotocol/registry/blob/main/antigravity-acp/agent.json)) and agentux-harness has not run it yet |

Three things follow. First, a per-session directory that agentuxd owns can reach Claude Code and Codex through one standard ACP field, `additionalDirectories` ([ACP session setup](https://agentclientprotocol.com/protocol/v1/session-setup)), and OpenCode through its config. Second, nothing documented reaches Antigravity without writing into its user or project directories. Third, in a sandboxed session ([0023](0023-agent-session-sandbox.md), [0024](0024-agent-sandbox-security-boundaries.md)) `$HOME` is an empty tmpfs and each CLI's state is sandbox-owned, so the user's personal skills are already invisible there. The catalog is the only way a user's skill reaches a sandboxed session.

The acceptance criteria of agentux-core#68 that apply: one entry reaches every supported harness; a run that falls back to another harness gets the same skills or records which are unavailable; removing an entry removes it from everything agentuxd manages and leaves what the user added by hand untouched; secrets never appear in logs; the format is documented and validated.

## Decision

**agentuxd builds a read-only skills directory for each session, from content-addressed copies it verified, and points each harness at it through ACP or the harness's own launch configuration. It never writes into a user's or a project's vendor directories. A harness it can't point at a directory gets an index of the skills in its session prompt instead.**

### Catalog format

Skills join `mcp` and `instructions` in the same three layers, merged by name:

```yaml
skills:                          # tools.yaml, or under `tools:` in agentux.yaml
  - name: release-notes          # Agent Skills name: 1-64 chars, a-z, 0-9, single hyphens
    path: ~/skills/release-notes # a local directory
    harnesses: [claude-code, codex]   # optional: every harness when left out
  - name: pdf
    git: https://github.com/anthropics/skills
    rev: 0123456789abcdef0123456789abcdef01234567   # a full commit id
    subdir: skills/pdf           # optional: the skill's directory in the repository
    digest: sha256:9f2c…         # optional here, required from Command
```

- **Exactly one source:** `path` or `git` with `rev`. `rev` must be a full commit id. Branch and tag names are rejected, because they move. `aux tools skills update NAME --ref main` resolves a ref to a commit and writes the commit.
- **Git URLs** are `https://` or `ssh://` and may not carry credentials (no user information in the URL). agentuxd fetches with the user's own Git configuration and credential helpers, outside any sandbox, and the URL is logged without query strings.
- **Project layer:** a `path` must be relative and stay inside the repository, read from the commit the run started from, like `isolation` in [0009](0009-container-isolation-for-checks.md). Absolute paths, `~`, `..` that leaves the repository, and symlinks that resolve outside it are rejected. This applies 0024's rule that projects cannot add host paths: a skill copied from an arbitrary host path would disclose that path's contents to the agent. `git` sources are allowed in every layer.
- **Validation** (`aux tools` and the cockpit's Tools section report errors, the run log says which entries were left out and why): the directory has a `SKILL.md` whose frontmatter parses, has a `description` of 1-1024 characters, and a `name` that is absent or equal to the entry's `name`; at most 8 MiB and 1,000 files per skill; only regular files and directories (no symlinks, devices or FIFOs); the name doesn't collide with another entry after merging.
- **No secrets in skills.** A skill is plain files. The catalog format has no secret references for skills, and agentuxd never logs a skill's contents, only its name, source, commit and digest.

### Pinning and integrity

- agentuxd copies each resolved skill into a content-addressed store, `~/.local/share/agentux/skills/sha256-<digest>/`, with files and directories made read-only. On an AgentUX Command node, the machine layer's store is under `/var/lib/agentux/skills/`.
- The **digest** is SHA-256 over a canonical listing of the tree: each entry's relative path in byte order, whether it is executable, and its contents' SHA-256. File times, owners and other modes are not part of it. `aux tools skills digest DIR` prints it, so an author can pin a local directory too.
- If an entry has a `digest`, a copy that doesn't match is an error and the skill is left out of the session. Without one, agentuxd records the computed digest in the run.
- `git` sources are fetched when they are added or updated and on first use, then served from the store. Starting a session needs no network for a skill already in the store. `path` sources are hashed at every session start, so the user's edits apply to the next session and the run records which version it got.
- Every run records, per session, each skill's name, layer, source, commit (for `git`), digest and delivery (below). AUXP run events carry the same, without paths from the user's home.

### Delivery per session

At session start agentuxd creates `$XDG_RUNTIME_DIR/agentux/sessions/<session>/skills/`, owned by agentuxd and outside the worktree, with:

```
<session dir>/
  .claude/skills/<name>/   # for Claude Code
  .agents/skills/<name>/   # for Codex, OpenCode and the index
```

Each `<name>` is a copy of the skill from the store (a reflink where the filesystem supports it), made read-only. Copies, not symlinks: the vendors don't all document following symlinks, and a symlink would make the session's view depend on the store staying unchanged. The directory holds only the skills for that session's harness, and it is removed when the run is cleaned up, not when a turn ends, so terminal handoff ([0007](0007-terminal-mode-is-a-session-handoff.md)) can resume with it.

Per harness:

| Harness | Delivery | Notes |
|---|---|---|
| claude-code | The session directory in `session/new`'s `additionalDirectories` (the adapter advertises the capability). Claude Code loads `<dir>/.claude/skills/` like an `--add-dir` directory | Claude Code treats added-directory skills as project skills: a personal or managed skill of the same name takes precedence. agentuxd checks the user's and the worktree's skill directories for the same name and records the conflict. Terminal handoff passes the same directory as `claude --resume <id> --add-dir <dir>`. The adapter's `_meta.claudeCode.options.plugins` would namespace the skills as `agentux:<name>`, but it is an adapter extension, not ACP, so it is not used |
| codex | The same `additionalDirectories` entry; `codex-acp` sets `<dir>/.agents/skills` as an extra skills root | `codex-acp` also adds the directory to Codex's own sandbox write roots. The files are read-only and agentuxd rebuilds the directory from the store for every session, so a write can affect only that session. Whether `codex resume` in the terminal can be given the same root is not verified; until it is, a handoff records that catalog skills are not loaded in the TUI |
| opencode | `skills.paths: [<dir>/.agents/skills]` in the configuration agentuxd passes through `OPENCODE_CONFIG_CONTENT`, merged with any value already in agentuxd's environment. `additionalDirectories` also carries the directory so OpenCode's permissions allow reading it | The key is `skills.paths` in 1.18.34. OpenCode's main branch has since changed `skills` to a list of paths or URLs, so the key belongs to the version-pinned entry in agentux-harness and is tested per version. The merge with a user's own `OPENCODE_CONFIG_CONTENT` and `skills` setting must be confirmed against 1.18.34 before release |
| antigravity | The **skill index** (below), with the session directory in `additionalDirectories` if the ACP server advertises the capability | No documented way to add a skill directory. When the ACP server is verified, a native route replaces the index, through a later amendment |
| Any harness whose route fails | The skill index | For example, an adapter that stops advertising `additionalDirectories`. The run records the change |

**The skill index** is the fallback for harnesses without a route. agentuxd adds a section to the session prompt, through the instructions channel of agentux-core#91: "Skills from the AgentUX tool catalog", and for each skill its name, its `description` and the absolute path of its `SKILL.md` in the session directory, with one sentence telling the agent to read the file when a task matches. This keeps progressive disclosure and the 16 KiB instruction budget: the index is about one line per skill, and the agent reads the rest with its file tools. It is weaker than native loading (no `/name` command, no `allowed-tools`, and it relies on the model following the instruction), so it is used only where native delivery is unavailable. An entry can set `fallback: none` to have the session go without the skill instead; the run then records it as unavailable.

A run that falls back to another harness rebuilds the session directory for the new harness from the same resolved entries and digests, so it gets the same skills, natively or through the index, and the run records which.

### What agentuxd never does

- It never writes, links or removes anything in `~/.claude/skills/`, `~/.agents/skills/`, `~/.codex/`, `~/.config/opencode/`, `~/.gemini/` or a repository's `.claude/`, `.agents/`, `.codex/` or `.opencode/`. Skills the user or the project added there stay as they are and keep loading the vendor's own way.
- So removing a catalog entry needs no cleanup in vendor files: the next session's directory doesn't contain it. Store entries no run refers to are removed by `aux tools skills prune` and by agentuxd's periodic cleanup.

### In the sandbox

- The session directory is bind-mounted **read-only** at the same absolute path, so the paths in `additionalDirectories`, `skills.paths` and the index are valid inside. Nothing else from the store is mounted.
- The store, the user's catalog file and the sources (`path` directories, Git checkouts) are not mounted. Fetching and hashing happen in agentuxd, outside the sandbox. This keeps 0024's rule: the only host content a session sees is what agentuxd copied for it.
- The user's personal skills in their home stay invisible inside, as 0023 and 0024 already decide. A user who wants a personal skill in sandboxed sessions adds it to their catalog, where it is pinned and recorded.
- A skill's scripts run with the agent's access: confined in a sandboxed session, as the user otherwise. Pinning and digests decide *which* code runs; they don't make running it safe. This is why the machine policy below can restrict sources.

### Machine policy and AgentUX Command

- `/etc/agentux/node-policy.yaml` can restrict skills:

  ```yaml
  skills:
    sources: [git]               # allowed source kinds; path, git, or both (default)
    git_hosts: [github.com/acme] # allowed host and path prefixes for git sources
    require_digest: true         # every entry must carry a digest
  ```

  A project or user entry that the policy denies is left out with the reason. As in [0022](0022-core-command-responsibility-boundary.md), an organization's policy from Command can tighten these settings on its nodes but cannot loosen a machine's.
- **Command-managed catalogs** ([agentux-command#57](https://github.com/agentux-os/agentux-command/issues/57)) may push skills into the machine layer, through the AUXP catalog command, under three conditions: each entry is a `git` source with a full `rev` and a `digest`; the node fetches it itself, from a host its policy allows, and checks the digest before use; and no `path` entries, since an organization can't know a node's paths. Command never sends skill contents or credentials in AUXP payloads. The node reports, per entry, whether it is applied, pending or failed, and why.
- An organization's skill is trusted because its catalog version was reviewed and published in Command and its digest matches, not because of where it is hosted. Signing digests (for example with Sigstore) is left for later; a digest in a reviewed, audited catalog version already ties the content to that review.
- Merging by name stays as decided in agentux-core#68: a user or project entry of the same name replaces a machine entry. Whether a machine or organization can lock an entry against replacement is not decided here.

### Rollout

1. Catalog format, validation, the store and digests, `aux tools skills`, and delivery to Claude Code and Codex through `additionalDirectories`, with tests that use scripted ACP agents to check the `session/new` parameters and the session directory's contents and modes.
2. OpenCode through `OPENCODE_CONFIG_CONTENT`, the skill index, sandbox mounts, and the real-harness check ([agentux#28](https://github.com/agentux-os/agentux/issues/28)'s workflow): each CLI lists the catalog's skills and a session with a removed entry no longer does.
3. Node policy and Command-pushed catalogs, after agentux-command#57's AUXP schema.

## Consequences

- One catalog entry reaches all four harnesses: natively for Claude Code, Codex and OpenCode, through the index for Antigravity. A fallback run gets the same skills and the run says how.
- Users' and projects' own skill directories are never modified, so there is no marker file to keep in sync, nothing to clean up after a crash, and nothing to commit by mistake.
- Every session records which skill content it ran with, by digest. A skill that changes upstream doesn't change a pinned catalog.
- The delivery depends on adapter behavior that is not part of ACP: Codex mapping `additionalDirectories` to `.agents/skills`, Claude Code loading skills from added directories, and OpenCode's config key. Each is pinned with the adapter's version in agentux-harness and tested; an adapter update can move a harness to the index until the route is fixed.
- On Claude Code, a personal skill with the same name wins over the catalog's. agentuxd can detect and report this but not prevent it without writing into the user's directory.
- `additionalDirectories` also widens the agent's file roots to the session directory. It contains only the session's read-only skills, so the cost is small.
- Antigravity users get a weaker form of skills until its ACP server is verified.
- agentuxd takes on a fetcher, a store, a tree hash and pruning, all small but new.

## Alternatives considered

- **Write into the user's vendor directories with a managed marker** (for example `~/.claude/skills/agentux-<name>/` and a manifest of what agentuxd wrote): every vendor would load them with no adapter dependency, but agentuxd would share directories the user and other tools also write. A crash leaves stale skills, every session sees every catalog skill regardless of `harnesses` and project, a non-AgentUX session gets them too, and the acceptance criterion about hand-added entries depends on a marker never being edited. It also doesn't help sandboxed sessions, whose home is empty.
- **Write into the run's worktree** (`.claude/skills/`, `.agents/skills/`, excluded through `.git/info/exclude`): every vendor reads project skills, including Antigravity. But the worktree is the project's tree: a project's own `.agents/skills/` would be mixed with catalog skills, Codex and OpenCode would also read `.claude/skills/` or `.agents/skills/` copies meant for another harness, an agent could edit or commit them, and `.git/info/exclude` is shared with the user's checkout. Excluded files also survive into later runs reusing the worktree. Kept as a possible route for Antigravity only if its ACP server turns out to read nothing else, through an amendment.
- **Instructions channel for every harness** (the index, or the full `SKILL.md` text in the prompt): uniform and already built. The full text would exceed the 16 KiB budget with a few skills and defeat progressive disclosure, and the index loses the vendors' native invocation and tool rules. It is the fallback, not the default.
- **A per-session `CLAUDE_CONFIG_DIR`, `CODEX_HOME` or `XDG_CONFIG_HOME` with the skills in it**: this is what the sandbox already does for state, but outside the sandbox it would also move the user's login, history and settings away from the session. Inside the sandbox those directories persist across sessions, so per-session skills there would need cleanup. A dedicated directory passed through `additionalDirectories` works the same in both modes.
- **Claude Code plugins through `_meta.claudeCode.options.plugins`**: namespaced names (`agentux:<name>`) avoid clashes with personal skills, but it is an extension of one adapter, and plugins can also carry hooks and MCP servers that agentuxd would have to keep out. It can replace `additionalDirectories` for Claude Code later if the shadowing proves to matter.
- **Symlinks from the session directory into the store**: cheaper than copies, but vendor support for following them is documented only by Codex, and in the sandbox the store would have to be mounted too.
- **Floating refs (branches, tags) or no digests**: simpler to write, but a run's skills would change without a catalog change and an organization's review would not bind the content its nodes run.
