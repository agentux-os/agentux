# 0001. AgentUX is an orchestration layer, not a Linux distribution

- **Status:** Proposed
- **Date:** 2026-10-03

## Context

The original concept was a lightweight Linux distribution (Alpine or Arch base, Hyprland, a Tauri HUD) acting as a control plane for coding agents. Once local inference was dropped in favor of cloud harnesses, the distribution stopped carrying the value: everything that makes AgentUX useful — orchestrating harnesses, worktrees, test gates, cross-vendor review, approvals — runs in user space and has no dependency on the operating system.

A distribution has high fixed costs: kernel and driver support, ISO builds, an update channel, hardware bugs. It also demands that users reinstall their machine before trying the product, which shrinks the audience to a niche of a niche. A tiling Wayland compositor narrows it further.

The space is crowded and moving fast. Conductor is macOS-only, Claude Squad is a terminal UI, Vibe Kanban shut down in April 2026. An opportunity that remains is a tool that runs headless on Linux, Windows and macOS, on laptops and servers alike.

## Decision

AgentUX ships as user-space software that installs on any mainstream OS:

- **`agentuxd`** — a daemon that owns runs, worktrees, harness processes and state.
- **`aux`** — a CLI to start, watch, approve and resume runs. Fully usable without a GUI.
- **Cockpit** — a UI that observes and approves runs through the daemon's API. Optional.

The Linux flavor (`agentux-os`) is deferred. If built, it is a thin image — for example a Fedora Atomic/bootc image or a dev container — that preinstalls AgentUX and the toolchain. It never contains logic that the installable version lacks.

## Consequences

- Anyone can try AgentUX with a single install, on the machine they already use.
- Windows support becomes a real requirement (path handling, process control, no POSIX-only assumptions).
- Desktop-level integration (global hotkeys, compositor layouts, status bar widgets) is no longer a core feature; it can return later as optional plugins.
- The `<800 MB RAM` target from the original concept is dropped. Harness CLIs run on Node or Bun and dominate memory use; AgentUX cannot control that.

## Alternatives considered

- **Full distribution (Alpine/Arch base)** — high cost and small audience. Alpine's musl libc also causes compatibility problems with prebuilt Node binaries and webview toolkits.
- **Desktop app only** — repeats what Conductor and others already do, and does not run on servers or in CI.
