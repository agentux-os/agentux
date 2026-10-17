# SDD ledger — plan: docs/superpowers/plans/2026-10-17-office-command-projection.md

Pre-flight: worktree isolation is established for agentux, agentux-apps, agentux-command and agentux-protocol.

Pre-flight shared interfaces:
- Task 1 produces the Office projection and approval schemas consumed by Task 2 Command handlers and Task 3 Apps adapter.
- Task 2 produces HTTP response/error shapes consumed by Task 3 and the Task 5 smoke test.
- Task 3 produces the adapter interface consumed by Task 4 UI rendering.
- Task 4 and Task 5 depend on Task 1-3 contract stability.

Ruling: the distributed data model is a first-class constraint — the in-memory first slice must use durable-compatible IDs, event envelopes, idempotency keys, partition keys and projection freshness so PostgreSQL/event replay can replace it without changing Office.

Task 1: complete (commits 76231e0..7dd298d, tests: node scripts/validate-fixtures.mjs → validated 3 valid and 2 invalid AUXP fixtures)
Task 2: complete (Command commit b76154b, tests: GOCACHE=.gocache go test ./...)
