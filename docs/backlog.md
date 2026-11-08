# Backlog

## Restore sessions after power loss or reboot

Requested 2026-11-07. Resume conversations that were open before power loss, reboot, shutdown, or halt, preserving native thread and session-tree IDs. Re-establish remote control and permit attachment from a local terminal, SSH, or supported app/web surface.

Track open/closed state durably, distinguish an intentionally closed session from an interrupted host, and restore only the previous open set. Restore conversations without automatically repeating the last command, pending approval, production mutation, or hardware action. Reconcile native daemon state to avoid launching duplicates. Refresh host/tool/mount evidence after startup. Retain failure status and a bounded retry policy, and provide opt-out and an inspectable recovery report.

Acceptance: simulated abrupt termination and reboot recovery tests preserve IDs/history, avoid duplicate ownership, retain approval boundaries, and allow local/remote attachment. Real reboot validation must be planned separately so active work is not interrupted. Restoring a conversation is different from automatically resuming every previously running external process.

Status: custom desired-open registry/journal and guarded restore planning are candidate-tested; a live native restoration supervisor remains pending. Native-managed daemon recovery can itself continue work and is not an idle-only guarantee; see native-recovery-compatibility.md. Remote-control supervision is implemented, but is not proof of safe full reboot restoration.

## Cooperative parallel teams and communication

First phase: one editor per shared working directory, concurrent readers, participant revision receipts and explicit recovery/reconciliation. Subsequent phases: isolated forks/worktrees with distinct task ownership; code review and meaningful test evidence; explicit integration/release approvals and integration ownership; then a scoped low-latency team channel for ideas, help requests and revision-linked updates. Messages do not grant edit ownership or production approval. Authenticated delivery, access controls, retention/privacy, merge conflicts and notification deduplication need their own tested contracts.

## Remaining delivery gates

Explicitly evaluate repository branch protection/review policy, comprehensive secret/dependency-vulnerability scanning and automated release/deployment promotion after current local/CI verification. Do not call these enforced until configured and verified. Browser UI QA becomes applicable when a real product UI exists. Market/open-source reassessment is milestone/trigger-driven; no calendar research worker is installed by writing guidance.

## P1 candidate: governance and recovery verification

Owner approved public professional name/Gmail attribution; the historical identity-cleanup item is closed without history rewrite. Actual credential detection remains required.

On feature/repository-governance-recovery: prepare explicit repository classifications and proposed settings for owner review; run both-direction provider-labelled protocol cases over three real SSH hosts, including correction/ack, stale evidence and cooperative ownership; test local journal, share/API fault handling and reboot registry with synthetic data. See governance proposal, test plan and results. The owner approved classifications, exact protections and scanner policy; both security jobs passed and main protections were applied/readback-verified. Next: explicit merge/release promotion, dependency installation locks/installed-environment audit, then a separately approved nonproduction model/native idle-restore pilot. No provider-account switch, boot supervisor, actual outage/reboot or production service change was performed.
