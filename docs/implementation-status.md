# Implementation status

## Implemented

- Scoped Codex and optional Claude launch adapters over shared project placement and policy snapshots.
- Native-ID resume, host-aware Codex SSH access, and a metadata-only shared terminal chooser.
- Interactive upgrade selection, direct selectors for scripts, source/attached/adopted policy tracking and applicability receipts.
- Managed-block preservation, immutable snapshots, conflict detection, policy rollback and guarded interrupted writes.
- Optional Claude metadata SDK in an isolated environment; native fallback when metadata is incomplete.
- Conditional lifecycle guidance, read-only coordinator KB adapter and explicit upcoming-vault boundary.
- Codex remote-control health reconciliation through supported native commands and a user timer.
- Portable preview/apply installer, versioned archives, one-page PDF and editable source.
- Offline automated tests and GitHub CI configuration.

## Verification scope

Tests use temporary homes, fake native executables and fixtures. Real metadata reads and host-local KB checks have also been exercised during development, with private evidence excluded from Git. No collected test starts model inference or mutates a live deployment.

Remote-control readiness verifies native enablement and daemon availability, not phone pairing or a complete app/web attachment. Claude launch behavior is verified with fake native executables; no billable model session is started merely to test flags.

## Current limits

- SSH continuation keeps execution on the selected owning host; full execution migration is separate.
- Native provider histories, memory stores and caches are not merged.
- Claude has no configured external notification queue; existing policy adoption is explicit in-session.
- Pre-Workbench Claude conversations are not silently imported or reconfigured.
- Vault enrollment/access, reboot restoration of open tasks, and full transactional launcher rollback remain pending.
- Public plugin/marketplace submission is separate from publishing the GitHub add-on.

See the [command guide](commands-and-installation.md), [upgrade guide](policy-upgrades.md), and [provider design](unified-providers.md). Local operational inventories, session IDs and correspondence are intentionally excluded.
