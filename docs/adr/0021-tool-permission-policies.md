# 0021. Tool permission policies per project and role

- **Status:** Accepted
- **Date:** 2026-10-23

## Context

Agents ask before most tool calls: the harness sends an ACP permission
request, and agentuxd turns it into a request in the cockpit's inbox that
pauses the run until someone answers. There are only two settings: ask the
human every time, or `--auto-approve-permissions`, which lets every agent on
the machine do anything in its worktree.

Neither fits real projects. Reading and searching the code is almost never
worth an interruption; running commands often is; a reviewer has no reason to
edit files at all. People answer the same harmless requests dozens of times a
run, approve without reading, and the one request that mattered looks like
the rest. The roadmap also wants agents' own tool calls isolated, not only
gate checks ([0009](0009-container-isolation-for-checks.md)); deciding by
category is the first step of that, because isolation will be decided the
same way (which categories run where).

ACP tells us the category of every tool call (`read`, `edit`, `delete`,
`move`, `search`, `execute`, `fetch`, `think`, `other`), not what exactly it
does in vendor terms. That is the vocabulary a policy can rely on across
harnesses.

## Decision

A project's `agentux.yaml` gets a `permissions` section:

```yaml
permissions:
  default: ask          # every category not named below
  read: allow
  search: allow
  think: allow
  edit: allow
  execute: ask
  delete: ask
  fetch: deny
  roles:
    reviewer:           # a role's rules come first
      edit: deny
      execute: deny
```

- **Decisions.** Each category is `allow` (run it without asking), `ask` (the
  inbox, as today) or `deny` (the agent is told no, the run goes on).
- **Resolution.** For a tool call of category `c` by role `r`: the role's rule
  for `c`, else the project's rule for `c`, else the role's `default`, else the
  project's `default`, else `ask`. Without a `permissions` section nothing
  changes.
- **The machine can loosen `ask`, never `deny`.** `--auto-approve-permissions`
  turns what would be `ask` into `allow`; a project's or role's `deny` holds
  regardless. A machine administrator who wants to forbid more uses the node
  policy for remote commands and, later, isolation; a project cannot loosen
  what the machine does not allow (the machine allows nothing by itself today).
- **Fixed for the run.** The policy is part of the `agentux.yaml` a run keeps
  when it starts (as the pipeline is); changing the file affects new runs.
- **Audited.** Every decision the policy makes on its own is written to the
  run's log with the category, the role and the rule that decided
  (`permissions.roles.reviewer.edit`, `permissions.default`, …).
- **Validated.** Unknown categories and decisions, and roles the project does
  not have, are errors when the file is loaded.

## Consequences

- Fewer interruptions for what is safe, and requests that remain mean
  something; a reviewer that cannot edit, an implementer that cannot fetch.
- A repository's `agentux.yaml` now decides what agents may do without
  asking. A project could set `execute: allow`; that is its maintainers'
  call, as any build script in the repository is. The cockpit should show a
  project's policy before its first run (follow-up).
- The vocabulary is ACP's categories. A harness that reports `other` for
  everything gets the `other` rule (or the default); per-tool rules wait until
  harnesses report tools consistently.
- The same categories are where isolation will plug in: "execute runs in the
  container" is a rule of the same shape.

## Alternatives considered

- **A per-machine policy only.** Different projects need different answers,
  and roles inside one run differ; the project is where people already
  configure their pipeline.
- **Per-tool or per-command rules (`git push`, `npm install`).** ACP does not
  report the tool or command in a portable way; rules would differ by vendor
  and be easy to bypass by phrasing a command differently.
- **Remembering the human's answers ("always allow this").** Useful later, but
  it hides what is allowed in the cockpit's state instead of the project's
  file, where it can be reviewed and versioned.
