<!-- WORKBENCH-ENTRY:BEGIN -->
# Workbench project entry

This project explicitly uses the shared Workbench workflow. Start with `.workbench/handoff/state.json`: it names the current policy revision, editor and checkpoints. Read that revision's `rules.md` and its `skills/project-bootstrap/references/roles/index.md`. Select only the role modules needed for the current task. Do not load every discipline or spawn agents just because a role exists.

Inspect the latest checkpoint, relevant changes and evidence before continuing, especially when returning from another provider/user/session. Synchronize your participant receipt and verify cooperative edit ownership before each write batch. Keep accounts, native histories, credentials and permissions separate. Preserve local rules and current authorization; report conflicts. Runtime state is private and must not be published.

If shared state or policy resources are absent/unreadable, resolve enrollment/access rather than pretending native history was transferred. Existing projects enroll explicitly; new named Workbench projects receive this entry point automatically. Quick one-offs retain their simpler workflow. See the installed handoff helper's `--help` for registration, briefing, sync, checkpoints and recovery.
<!-- WORKBENCH-ENTRY:END -->
