# Architecture Decision Records

Each ADR records one decision: the context, what was decided, and what it costs. ADRs are immutable once accepted; a later ADR supersedes or amends an earlier one instead of editing it, and the index below records the link.

| # | Title | Status |
|---|---|---|
| [0001](0001-linux-distribution-on-fedora-atomic.md) | AgentUX is a Linux distribution, built as a bootc image on Fedora Atomic | Accepted |
| [0002](0002-harness-integration-via-acp.md) | Integrate harnesses through ACP, with headless CLIs as fallback | Accepted |
| [0003](0003-workflow-engine.md) | Start with an embedded state machine, not Temporal | Accepted |
| [0004](0004-unified-interface-and-agent-bus.md) | Unified interface over existing CLIs, and an agent bus so they talk to each other | Accepted; terminal mode amended by [0007](0007-terminal-mode-is-a-session-handoff.md) |
| [0005](0005-agentux-yaml.md) | Pipelines are declared in `agentux.yaml` | Accepted; amended by [0009](0009-container-isolation-for-checks.md) |
| [0006](0006-rust-and-tauri.md) | Rust for agentuxd and aux; Tauri 2 with React and TypeScript for the cockpit | Accepted |
| [0007](0007-terminal-mode-is-a-session-handoff.md) | Terminal mode is a handoff of the vendor session, not a second driver | Accepted; amends [0004](0004-unified-interface-and-agent-bus.md) |
| [0008](0008-releases-and-image-pinning.md) | Releases and image pinning | Accepted; amended by [0010](0010-image-variants-and-system-identity.md) and [0011](0011-release-channels-and-iso-distribution.md) |
| [0009](0009-container-isolation-for-checks.md) | Optional container isolation for check commands | Accepted; amends [0005](0005-agentux-yaml.md) |
| [0010](0010-image-variants-and-system-identity.md) | Image variants and system identity | Accepted; amends [0008](0008-releases-and-image-pinning.md); amended by [0011](0011-release-channels-and-iso-distribution.md), [0012](0012-system-version-and-release-identity.md) and [0018](0018-retire-the-hyprland-variant.md) |
| [0011](0011-release-channels-and-iso-distribution.md) | Release channels, ISO distribution and the release gate | Accepted; amends [0008](0008-releases-and-image-pinning.md) and [0010](0010-image-variants-and-system-identity.md); amended by [0012](0012-system-version-and-release-identity.md), [0018](0018-retire-the-hyprland-variant.md) and [0019](0019-updates-without-reinstalling.md) |
| [0012](0012-system-version-and-release-identity.md) | System version, release identity and the branded installer | Accepted; amends [0010](0010-image-variants-and-system-identity.md) and [0011](0011-release-channels-and-iso-distribution.md) |
| [0013](0013-first-run-wizard.md) | A first-run wizard, and how developer tools install | Accepted |
| [0014](0014-installation-profiles-and-platform-services.md) | Installation profiles and optional platform services | Accepted; amended by [0020](0020-command-workflows-without-temporal.md) |
| [0015](0015-organization-command-office-contract.md) | Organization definitions are versioned domain contracts | Proposed |
| [0017](0017-help-mascot.md) | A help mascot that knows AgentUX, offline first | Accepted |
| [0018](0018-retire-the-hyprland-variant.md) | Retire the Hyprland variant | Accepted; amends [0010](0010-image-variants-and-system-identity.md) and [0011](0011-release-channels-and-iso-distribution.md) |
| [0019](0019-updates-without-reinstalling.md) | Updates without reinstalling: small, automatic image patches, and Flatpak for new apps | Accepted; amends [0011](0011-release-channels-and-iso-distribution.md) |
| [0020](0020-command-workflows-without-temporal.md) | AgentUX Command runs its workflows on PostgreSQL, with NATS for delivery, and is written in Rust | Accepted; amends [0014](0014-installation-profiles-and-platform-services.md) |

New ADRs copy [`template.md`](template.md) and take the next number.
