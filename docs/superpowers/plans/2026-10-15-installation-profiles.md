# Installation Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a versioned AgentUX OS profile contract that records installation intent, applies local capabilities idempotently, and leaves Command services container-ready without installing them into the immutable base.

**Architecture:** The OS ships a read-only profile catalog and a small `agentux profile` CLI. The installer writes a profile intent seed; first boot applies it and persists status under `/var/lib/agentux`. Local node/desktop capabilities remain image-provided, while the command capability only enables a guarded container bundle when a future image/configuration is available.

**Tech Stack:** Bash, JSON, systemd, Podman Quadlet, bootc/Anaconda kickstart, shell smoke tests.

**Spec:** `docs/adr/0014-installation-profiles-and-platform-services.md`

## Global Constraints

- One signed base image per desktop variant and architecture.
- Profile catalog is read-only at `/usr/share/agentux/profiles/catalog.json`.
- Selected/applied state is mutable at `/var/lib/agentux/profile.json`.
- PostgreSQL, Temporal, NATS and object storage are never installed as host RPMs.
- Applying an already-applied profile is idempotent.
- Command services must not start unless `command-server` is explicitly selected and configured.

## Review Focus

- Unknown profile and component names must fail without changing persisted state.
- Reapplying a profile must not duplicate units or corrupt the state file.
- A workstation/node profile must not enable Command services.
- An installer without a profile choice must preserve the current first-boot behavior.
- Interrupted or failed activation must remain visible as pending/failed state.

---

### Task 1: Ship the profile catalog and profile manager contract

**Files:**
- Create: `agentux-os/files/usr/share/agentux/profiles/catalog.json`
- Create: `agentux-os/files/usr/bin/agentux`
- Create: `agentux-os/tests/profile.sh`
- Modify: `agentux-os/Containerfile`

**Interfaces:**
- Produces `agentux profile show|plan|apply|remove`.
- Produces `/var/lib/agentux/profile.json` with `requested`, `applied`, `pending`, `failed` and `catalogVersion` fields.

- [x] Write the failing profile smoke test for catalog validation, unknown profile rejection, and idempotent `show`/`plan` using temporary `AGENTUX_PROFILE_ROOT` and `AGENTUX_PROFILE_STATE` paths.
- [x] Run the test; Windows execution is blocked by the sandbox's Bash/CreateFileMapping restriction.
- [x] Implement the catalog and CLI with dependency expansion for `workstation`, `node`, `command`, `executive`, `complete` and `custom`.
- [x] Add the CLI and catalog to the image and make the CLI validate JSON/catalog at build time.
- [ ] Run the focused smoke test and the image shellcheck target in Linux CI.

### Task 2: Connect installer intent and first boot

**Files:**
- Modify: `agentux-os/live/install.ks`
- Modify: `agentux-os/files/usr/libexec/agentux/first-login`
- Modify: `agentux-os/files/usr/lib/systemd/user/agentux-first-login.service`
- Modify: `agentux-os/tests/boot.sh`
- Modify: `agentux-os/tests/live.sh`

**Interfaces:**
- Installer may write `/var/lib/agentux/profile-intent.json` when a profile is supplied by the installer environment.
- First login applies the intent once, then leaves the existing per-user tool installation behavior intact.

- [x] Add tests proving a valid intent is consumed into profile state; absent intent is a no-op by the service condition.
- [x] Add an installer-safe intent hook driven by `AGENTUX_PROFILE` when present; do not make the offline installer depend on network services.
- [x] Add an idempotent first-boot system activation path; preserve user first-login downloads and their existing markers.
- [ ] Run focused tests and the relevant boot/live static checks in Linux CI.

### Task 3: Prepare guarded Command capability and documentation

**Files:**
- Create: `agentux-os/files/usr/share/agentux/profiles/README.md`
- Create: `agentux-os/files/usr/libexec/agentux/profile-command`
- Modify: `agentux-os/README.md`
- Modify: `agentux/README.md`
- Modify: `agentux/docs/adr/README.md`

**Interfaces:**
- `profile-command` refuses to enable the Command stack until an explicit image/configuration reference is present.
- Documentation explains profile selection, resource expectations and post-install changes.

- [x] Write a test for the guard: selecting `command-server` without configuration must fail closed and not enable Quadlet units.
- [x] Implement the guard and a stable location for future Quadlet units under `/etc/containers/systemd/agentux-command/` without shipping a non-functional service bundle.
- [x] Update OS and architecture documentation with the profile lifecycle and boundaries.
- [ ] Run all available focused tests, `git diff --check`, and the repository's static checks in Linux CI.

### Final verification

- [ ] Review the complete diff against ADR 0014.
- [ ] Run the full available OS shell/static test suite; record environment-limited tests separately.
- [ ] Run a self-review of the branch and note any deferred production work: actual Command images, migrations, health checks, backup/restore and remote registration.
