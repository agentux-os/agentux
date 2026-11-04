# Working on AgentUX with more than one coding agent

AgentUX is developed by the owner together with coding agents (Claude Code and Codex). These rules keep them from working over each other. They apply to every repository in the `agentux-os` organization.

## Who works where

Work is split **by repository**, so two agents never change the same branch.

| Agent | Repositories | Current focus |
|---|---|---|
| **Claude** | agentux-core, agentux-os, agentux-desktop | core#67 (agent sandbox, ADRs [0023](docs/adr/0023-agent-session-sandbox.md) and [0024](docs/adr/0024-agent-sandbox-security-boundaries.md)), the rest of core#68, OS image issues, cockpit #84/#85 |
| **Codex** | agentux-command, agentux-protocol, agentux-apps, new ADRs in agentux | command #49–#59, protocol#12, apps#19, agentux#40 |

Shared work crosses repositories through issues. Once protocol#12 settles the contract, Claude emits the new events in agentux-core and Codex persists and projects them in agentux-command.

Only the owner:

- pushes release tags;
- writes secrets;
- changes repository settings;
- decides open product questions, such as who interprets a goal in apps#20.

## Rules

1. **Claim before starting.** Comment "taking this" on the issue, and name the branch. An issue someone else claimed is theirs until they say otherwise.
2. **Never push to another agent's branch.** Suggestions go in a review comment or a separate pull request. Branches start with the agent's name: `claude/…`, `codex/…`.
3. **ADR numbers are claimed too.** Say the number in the claim comment ("taking ADR 0025"), and check the open pull requests in this repository first. Accepted ADRs aren't rewritten; a later ADR amends them, as 0024 amends 0023.
4. **Changes in another agent's repositories start as an issue there**, not a pull request, unless that agent asks for one.
5. **Cross-review.** Each agent reviews the other's pull requests when asked, or when they touch security, the protocol or an ADR. The author addresses the review before merging.
6. **Merge only green.** A pull request merges when every check passes. This repository has no CI, so documentation merges after review.
7. **Release order matters.** Component releases (core, desktop, command, apps) come before the OS bump that pins them. The OS release tag comes after main's image build is green.

## House style

- English for code, documentation, commit messages and pull requests.
- Commit messages say why; no trailers attributing authorship to an agent.
- Never print a secret's value in logs, pull requests or comments.
