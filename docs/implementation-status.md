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
- Guided unattended-work agreement, private plan validation and context-efficiency procedures. Scheduling is configured and verified per project after settings are agreed; the helper does not run a timer.
- Automatic enrollment of new named projects with a shared WORKBENCH.md entry and on-demand role references; existing projects enroll explicitly and one-offs remain lightweight. Optional Gemini project loader and documented Cursor AGENTS mechanism do not imply native runtime adapters.
- Opt-in shared-project handoff with provider-neutral policies, participant review receipts, cooperative single-editor ownership and explicit recovery/reconciliation. Native histories/accounts stay separate; cross-host ACL/partition verification and team messaging are not supplied.
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

## Candidate branch: governance and recovery

The feature/repository-governance-recovery branch contains owner-approved repository classifications/settings, typed offer/interpret/correct/review/ack contracts, a verified-local journal/session registry and a guarded boot planner. Tests include three-host SSH/NFS/process fixtures and injected API/boot faults. Main protections are applied and readback-verified after all four required checks passed; security CI audits history/export/archives and reviewed Python dependency snapshots. The PR remains open; no merge/release/host install, provider login/API turn, boot supervisor or real outage/reboot was performed. See repository-governance-proposal.md, p1-test-plan.md, p1-results.md and native-recovery-compatibility.md. Public owner-approved name/email attribution is allowed; the prior historical identity-cleanup question is closed without a history rewrite.
