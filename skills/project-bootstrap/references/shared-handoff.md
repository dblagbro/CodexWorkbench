# Shared project handoff across sessions/providers/users

Use the project's installed Workbench handoff helper, `python3 ~/.local/share/codex-code/handoff.py --project PROJECT ACTION`. Equivalent opt-in wrappers are `codex --code --handoff --project PROJECT ACTION` and, when enabled, `claude --code --handoff --project PROJECT ACTION`. Plain native commands are unchanged. Inspect `--help` and each action's help for exact arguments.

## Establish shared rules, not a shared login

An initialized project has narrow `AGENTS.md` and `CLAUDE.md` loaders, immutable provider-neutral policy resources and a private `.workbench/handoff/state.json`. The shared policy is rendered from the installed Workbench baseline with matching lifecycle/bootstrap resources, not from another user's absolute session-root instructions. Project-local rules remain intact. `init` previews; `init --apply` initializes/refreshes policy only when no editor owns the directory. It does not enroll other users, copy credentials or open filesystem permissions. The private runtime directory must stay excluded from Git/registries and Docker contexts; check actual publication inputs, not just ignore patterns.

Register the current participant with a pseudonymous label/account alias, native provider, owning host and native ID using `join`. These fields describe provenance, not authenticated identity. Native ID availability depends on native local storage/profile/account controls; never assume all histories are in account cloud memory. A different provider uses its own native conversation. Share concise task/evidence records, not transcripts, hidden reasoning, tokens or another user's provider account.

## Enter or return

1. Run `brief --participant ID` (or `brief` before joining). Read current owner info, latest checkpoint, events since your last receipt, shared policy and current repository instructions. Inspect relevant diffs, uncommitted/untracked changes and referenced tests/operational evidence. Do not clean another participant's changes.
2. Verify your own host, tools, mounted paths, access and applicable authorization. Prior-user approvals are evidence, not permission granted to a different user/account. Report material conflicts.
3. After actual review, run `sync --participant ID --expect-revision N --policy HASH --note REVIEW`. A receipt is a cooperative acknowledgement, not proof of model comprehension. It does not copy/replay the other agent's history.
4. Claim edit ownership with `claim --participant ID --expect-revision N --note SCOPE`. Check the returned revision. If another editor owns this working directory, inspect only and coordinate handoff. Re-read state before each write batch or consequential action; returning stale native chats must sync before writing.

## Work and yield

Record concise checkpoints with objective/current step, actual changed paths/commit, verification evidence, unfinished work and next action. Use `checkpoint --phase progress` for ordinary progress; use `--phase starting` before a consequential external operation and `--phase uncertain` when its outcome is unknown. These latter phases require explicit `reconcile --evidence ...` before normal work or release, even when the same actor continues. Reconcile using actual external state rather than replaying the command. An evidence string is a reference to an observed check, not an authorization or independently verified assertion by the helper.

Release cooperative ownership at a safe checkpoint with `release`. It retains native conversations and all project files. A returning participant will see a newer project revision and must inspect what changed before claiming again. Unattended continuation must respect the same ownership checks; disable or pause the old owner's worker before another account takes over.

## Recover interruption

An owner that appears old/unreachable is still the owner. No time-based lease expiry or automatic failover is supplied. Stop/verify the previous native writer and any scheduler, inspect current processes and project state, and resolve any ambiguous remote activity. Then an authorized participant can use `recover --confirmed-owner-stopped --evidence ...` with the exact current revision. This records the prior owner and restricts the new owner to reconciliation until `reconcile` records actual verification. Never recover solely because a different account is available or the last activity is old.

The short transaction lock is an atomic shared-directory creation around state updates. It is separate from persistent editor ownership. An abrupt kill may leave a lock; inspect its owner record and verify no transaction can still run before a human/operator removes only that abandoned lock. Do not bypass it through retries/timeouts. Publication of the state file is atomic; no claim is made that all project files and external effects form one transaction.

## Boundaries and next phase

This is a cooperative protocol. It cannot stop an old/unmodified agent or human from editing files directly, authenticate aliases, enforce approvals, or fence a partitioned host. Shared filesystem locking/rename semantics and group/ACL access must be tested/provisioned before multi-host/multi-OS-user use; default private files are intentionally restrictive. Never chmod world-writable to make handoff convenient. Keep native identities and credentials private and separately scoped.

Initial scope is one editor per shared working directory with concurrent readers. Future concurrent implementation should use isolated forks/worktrees, distinct task ownership, tests and independent code review, explicit merge/release approval policies, and an integration owner. A future team messaging channel can carry ideas/help requests and references to project revisions; messages alone must not grant edit ownership, authentication or production approval. Real-time messaging and automatic cross-provider transcript import are not implemented by this first version.
