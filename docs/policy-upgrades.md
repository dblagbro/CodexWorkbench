# Updating existing code-mode sessions

Launcher installation and session-policy adoption are separate operations. Installing a release does not mean a running model has read new instructions. This feature preserves the native thread ID, history, project path, explicit title, permissions, and project-specific rules while attaching a reviewable baseline revision.

## From another terminal while the project is running

Reload the installed shell wrapper once, then preview the exact native thread:

```bash
source ~/.local/share/codex-code/code-shell.bash
codex --code --upgrade --thread THREAD_UUID
```

Attach the reviewed policy and queue a safe-checkpoint adoption request:

```bash
codex --code --upgrade --thread THREAD_UUID --apply --notify
```

The existing agent reads the new revision plus project instructions, applies only relevant changes, records relevant/skipped sections or conflicts, and continues its current task. It is told not to restart onboarding, replay commands, introduce unrelated ceremonies, or expand its access or task scope. Notification uses native `codex queue` without automatically resuming an inactive conversation. A successful queue means queued, not adopted.

Inspect the status afterward:

```bash
codex --code --upgrade --thread THREAD_UUID --check
```

`adoption_status: acknowledged` means the agent recorded its review of the exact attached revision. `pending` means it has not yet acknowledged; `needs_decision` means it recorded conflicts. The underlying receipt, including applicability notes, is at `<stable-session>/workbench/policy.json`. This records an agent review, not proof that every future behavior complies with policy.

## Within an existing agent session

The agent can use its known stable root without looking up history:

```bash
python3 ~/.local/share/codex-code/policy.py --session STABLE_SESSION_ROOT
python3 ~/.local/share/codex-code/policy.py --session STABLE_SESSION_ROOT --apply
```

The apply result includes an adoption prompt and exact acknowledgement command. The agent must read the attached instructions before acknowledging, adding concise notes such as `--applicable "title and KB updates" --skipped "commercial analysis and UI"`. Acknowledgement requires the currently attached revision; stale IDs and empty receipts are refused. Material conflicts use `--conflict` and remain unresolved rather than silently overridden.

`--project /mnt/s/code/PROJECT` can resolve a unique local workflow session. If multiple sessions point at that project, it refuses to guess. Prefer the native thread ID or exact stable root. Only recognized `--code` sessions are eligible; ordinary Codex sessions do not receive a baseline implicitly.

## Remote hosts

Install the release on the state-owning host first. Then use:

```bash
codex --code --upgrade --host dev-host --thread THREAD_UUID
codex --code --upgrade --host dev-host --thread THREAD_UUID --apply --notify
```

SSH uses the destination's installed helper, host settings, and native state. This does not migrate the conversation or credentials. No raw history is loaded to determine policy applicability.

## What changes

- A content fingerprint identifies the installed policy source separately from rendered host inventory and paths.
- A complete snapshot is created under `workbench/policy-revisions/<fingerprint>/`, including rendered instructions, relevant references/tools, inventory and an integrity manifest.
- A short marked block in the stable root's `AGENTS.md` points to that snapshot. Legacy unmarked scaffolds are preserved, and text outside the managed block stays intact.
- `workbench/policy.json` records active revision, source hashes, notification, applicability and acknowledgement state.
- Previous owned policy files are backed up under `workbench/policy-backups/`.

No repository instruction file, source/runtime data, native transcript/database, title, workdir pointer, service, sandbox, or MCP configuration is changed by this operation. Installing the launcher itself remains a separate command.

An edited managed block, edited snapshot, malformed marker, hiding instruction override, or redirected managed directory causes refusal. Reconcile deliberately rather than forcing replacement. Put project-specific standards in the project's established instructions/docs, or session-specific additions outside the managed block, rather than editing immutable snapshots.

## Future releases and rollback

New sessions start with a managed policy snapshot. Upgraded agents check for installed changes after resume or at a safe checkpoint. A newer revision is a review candidate; there is no silent rollout to every active project. Repository-specific requirements and the user's existing scope remain authoritative. If a new policy changes cost, compatibility, access, security, or production behavior materially, record the decision instead of treating an upgrade as authorization.

Preview text changes with `--diff`. A session can return to one of its previous snapshots:

```bash
codex --code --upgrade --session STABLE_SESSION_ROOT --rollback OLD_FINGERPRINT
codex --code --upgrade --session STABLE_SESSION_ROOT --rollback OLD_FINGERPRINT --apply
```

The agent must read and acknowledge the reverted revision too. Rollback changes the managed policy reference, not project files or native history, and preserves later unmanaged additions. Interrupted pointer writes attempt to restore owned files. If a concurrent editor changed them during a failed write, its changes are preserved and a reconciliation path is reported rather than overwritten.

## Validation

A real deployment had two sessions pointing at the same project. Native-ID selection resolved the intended session; its owning agent acknowledged the relevant policy without replacing project instructions, state or history. Identifiers and host evidence are retained locally, outside this repository.

57 tests passed on workstation and dev-host, including ambiguity, idempotency, preservation, immutable-snapshot drift, notification/adoption separation, stale acknowledgements, rollback, redirected paths and interrupted/concurrent writes.

Official references: [AGENTS.md loading](https://learn.chatgpt.com/docs/agent-configuration/agents-md) and [native queue](https://learn.chatgpt.com/docs/developer-commands). Editing files alone is not presented as hot-reloading active context.
