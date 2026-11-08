# Backlog

## Restore sessions after power loss or reboot

Requested 2026-11-07. Resume conversations that were open before power loss, reboot, shutdown, or halt, preserving native thread and session-tree IDs. Re-establish remote control and permit attachment from a local terminal, SSH, or supported app/web surface.

Track open/closed state durably, distinguish an intentionally closed session from an interrupted host, and restore only the previous open set. Restore conversations without automatically repeating the last command, pending approval, production mutation, or hardware action. Reconcile native daemon state to avoid launching duplicates. Refresh host/tool/mount evidence after startup. Retain failure status and a bounded retry policy, and provide opt-out and an inspectable recovery report.

Acceptance: simulated abrupt termination and reboot recovery tests preserve IDs/history, avoid duplicate ownership, retain approval boundaries, and allow local/remote attachment. Real reboot validation must be planned separately so active work is not interrupted. Restoring a conversation is different from automatically resuming every previously running external process.

Status: backlog, not implemented. Remote-control supervision is implemented; restoring the previous open session set remains pending.

## Cooperative parallel teams and communication

First phase: one editor per shared working directory, concurrent readers, participant revision receipts and explicit recovery/reconciliation. Subsequent phases: isolated forks/worktrees with distinct task ownership; code review and meaningful test evidence; explicit integration/release approvals and integration ownership; then a scoped low-latency team channel for ideas, help requests and revision-linked updates. Messages do not grant edit ownership or production approval. Authenticated delivery, access controls, retention/privacy, merge conflicts and notification deduplication need their own tested contracts.

## Remaining delivery gates

Explicitly evaluate repository branch protection/review policy, comprehensive secret/dependency-vulnerability scanning and automated release/deployment promotion after current local/CI verification. Do not call these enforced until configured and verified. Browser UI QA becomes applicable when a real product UI exists. Market/open-source reassessment is milestone/trigger-driven; no calendar research worker is installed by writing guidance.
