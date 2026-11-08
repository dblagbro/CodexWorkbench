# Shared project handoff: first version

Codex, Claude, different provider accounts and future adapters can continue the same project through a shared durable project record. This is project continuity, not native cross-provider session resume. Existing native chats remain independently resumable where their provider/storage/access permits it. Account switching does not imply a specific cloud-memory model: Claude CLI sessions are stored locally, and Codex instructions, memories and conversations are separate mechanisms.

## What is implemented

- A small WORKBENCH.md entry point and just-in-time role router for project lead, architecture, engineering, product/UX, UI, operations, networking, hardware, QA and research. Roles are perspectives, not automatic agents.
- One provider-neutral project policy, derived from installed baseline/lifecycle/bootstrap resources, with narrow `AGENTS.md`/`CLAUDE.md` loaders that preserve existing content.
- Pseudonymous participant/provider/host/native-ID registry, current cooperative editor and monotonic project revisions.
- Per-participant review receipts: returning chats detect changes since their last acknowledgement and inspect only relevant evidence.
- Checkpoints and next actions; explicit recovery/reconciliation for interrupted or uncertain external effects.
- Short transaction exclusion, stale-revision rejection, atomic state publication and immutable policy-integrity checks.
- Private runtime state under `.workbench/handoff`, excluded from publication. No transcripts, passwords or hidden reasoning are imported.

## Commands

New named projects placed by the Workbench helper enroll automatically when `project_bootstrap` is enabled (default). One-offs stay lightweight; adopting an existing project does not alter its instructions. From an existing project that explicitly opts in, after installing/updating Workbench:

```bash
codex --code --handoff --project . init
codex --code --handoff --project . init --apply
codex --code --handoff --project . join --label editor-a --provider codex --host dev-host --native-id NATIVE_ID
codex --code --handoff --project . brief --participant PARTICIPANT_ID
```

Review the displayed `policy_path`, local rules, checkpoint and actual Git/filesystem changes before acknowledging. Substitute the current revision/hash from `brief`:

```bash
codex --code --handoff --project . sync --participant PARTICIPANT_ID --expect-revision 1 --policy POLICY_HASH --note "Reviewed current rules, changes and evidence"
codex --code --handoff --project . claim --participant PARTICIPANT_ID --expect-revision 1 --note "Implement the next agreed item"
```

Use the revision returned by each mutation for subsequent commands. `checkpoint`, `release`, `recover` and `reconcile` require that revision; each command has `--help`. A second provider uses `claude --code --handoff` or the same Python helper, with its own native identity and a distinct account alias. Each user needs the helper and authorized filesystem/project access. Native ChatGPT/Claude accounts are never logged in or switched by these commands.

Before a consequential external operation, record a checkpoint with `--phase starting`; after observing the outcome, use `reconcile --evidence ...`. A failed/uncertain action is verified before retry, not automatically replayed. An old returning writer cannot use a stale revision to release/checkpoint another owner. Recovery requires explicit confirmation that the old writer/scheduler has stopped and verification evidence; the helper cannot independently authenticate that statement.

Refresh shared policy with `init --apply` after releasing ownership and updating the installed baseline. All participants then see the new revision and need to review/sync again. Updating a native session policy alone does not silently rewrite project-shared rules. A missing private policy on a separate clone requires explicit initialization/provisioning, not simulated history continuity.

## Verification and limits

Tests simulate Codex → Claude → Codex return, competing claims, stale writes, interrupted action recovery, tampered snapshots, redirected state, preservation of local instructions and failed state publication. They do not log into other accounts or run inference.

One editor per shared directory is advisory, not operating-system enforcement. A nonparticipating agent can ignore it. Shared NFS semantics, cross-host partitions and multi-OS-user group/ACL arrangements need deployment-specific tests. Private files default to restrictive permissions; group/ACL provisioning is explicit and is not performed automatically. Project files/remote effects and metadata are not one atomic transaction; a killed metadata writer can leave a short lock needing inspected recovery. No timeout automatically evicts a participant. Do not claim automatic outage takeover, authenticated team messaging or cross-provider native-history migration.

## Roadmap agreed with the owner

Next phases: isolated forks/worktrees for parallel teams, task ownership, code review and meaningful test evidence before integration, explicit approvals and integration ownership, then a scoped team channel for ideas/assistance and revision-linked messages. Enforce access and delivery guarantees separately from conversational coordination. A message must not replace ownership or production approval.

Primary references: [Claude sessions](https://code.claude.com/docs/en/sessions), [Claude project instructions](https://code.claude.com/docs/en/memory), [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md), and [Codex memories](https://learn.chatgpt.com/docs/customization/memories). Detailed operational procedure: [shared-handoff skill reference](../skills/project-bootstrap/references/shared-handoff.md).

## Additional instruction clients

`init --apply --with-gemini` optionally preserves/appends a narrow `GEMINI.md` loader to the same `WORKBENCH.md` entry. Cursor can use the generated `AGENTS.md` through its documented project-rule mechanism. These are instruction-file integrations, not tested native launcher/resume/account adapters. Gemini and Cursor commands were not launched against real models. No Grok/other-tool runtime support is inferred from model availability. See the [workflow research](agent-workflow-research.md) for standards, alternatives, versions and limitations.

The small router is [here](../skills/project-bootstrap/references/roles/index.md); detailed role bodies stay on disk until relevant. All modules are independently authored. No upstream methodology package, daemon or telemetry was installed. Disable automatic new-project enrollment with installer `--project-bootstrap off` if needed; established projects remain unchanged until explicitly enrolled. Release shared edit ownership before naming/moving an enrolled project. The placement helper holds metadata exclusion, copies/rebinds its private state, records relocation and invalidates old participant receipts; live processes/services must still be stopped separately.

Enrollment intentionally adds project instructions that native clients may read even when launched without Workbench shortcuts. It changes no global provider settings, credentials, CLI permissions or native histories. Remove/disable enrollment only through an explicit reviewed project change, not by ignoring existing ownership.
