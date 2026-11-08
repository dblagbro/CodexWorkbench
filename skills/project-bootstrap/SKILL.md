---
name: project-bootstrap
description: Assess and prepare development capabilities when starting a project or explicitly reassessing its tooling.
---

Preserve the user's task and existing placement workflow. Bootstrap only what advances the work; do not make a missing optional tool a prerequisite.

Inspect relevant project instructions and conventions first. Use the bundled `scripts/inventory.py` for a names-only local inventory; add `--probe` when installed-version help and version evidence are needed. The script supports Python 3.10+; configuration parsing on Python 3.10 uses tomli when installed, otherwise reports that portion as unverified. Distinguish detected, configured, usable, and verified capabilities. Session tools and host CLI capabilities can differ. Record evidence and unresolved limits rather than inferring connectivity from configuration.

Choose tools for the actual task. Prefer an existing supported integration when it fits; otherwise compare CLI/API access and browser automation by reliability, permissions, and testability. Reuse authenticated browser profiles only within task scope; leave MFA or approval decisions to the user. Do not install a tool bundle or additional MCP servers by default.

Before changing Codex configuration, inspect installed-version help and relevant official documentation. Do not infer feature flags from another release. Treat experimental flags as opt-in project decisions. A model router must preserve explicit user model choices and explain fallback behavior; do not infer model availability from a static catalog.

Install only needed dependencies in project environments where practical. Separate developer tools from production dependencies. For an AI application, document required inference services and degraded behavior; for maintenance or recovery, keep essential recovery procedures executable without Codex or an active agent session.

Use delegation only when authorized and useful for independent work. Give each agent distinct ownership and evidence requirements. Keep shared production mutations with the lead; delegation does not grant new access or authorization.

For operational tasks, establish the target, current state, intended change, verification, and recovery path before mutation. Before physical actuation, establish authorized target actions, units and operating limits, and applicable interlocks and stop procedures. If these are unknown, continue read-only discovery or simulation. Troubleshooting should preserve evidence and test hypotheses. Reverse engineering should identify artifact provenance, unknowns, and reproducible observations. Select only the relevant controls.

Keep concise findings, decisions, status, and test evidence in the active project, using its existing format. Do not copy credentials or raw private configuration. Report what was found, what changed, and blockers tied to a concrete next action, then continue the task.

When the user asks to keep going or work unattended, load [unattended continuation](references/unattended.md). Ask only for missing scope, runtime/budget, self-check/report cadence and notification choices; continue authorized independent work while awaiting answers. Reuse an existing agreement rather than repeatedly asking. A request to add this behavior is not permission to start a scheduler. The bundled `scripts/unattended-plan.py` validates/persists an agreed plan only; install and verify an actual supported continuation mechanism before claiming unattended operation.

When a design feature adds tool/agent requirements or the owner asks to conserve context, load [capability preparation and context efficiency](references/context-efficiency.md). Prepare relevant capabilities early, reuse unchanged instructions and findings, and maintain a compact source/version/evidence record instead of preloading every skill or keeping idle agents. Never trade required verification, privacy or model quality for an unmeasured token-saving claim.

For collaboration between native sessions, providers or users, load [shared project handoff](references/shared-handoff.md). Keep portable project rules separate from host-local rendered session instructions. Read current project evidence, require per-participant revision acknowledgement and cooperative single-editor ownership, and reconcile interruptions without replaying uncertain effects. No account/credential or hidden reasoning transfer is implied.

At relevant design/QA/release checkpoints, or when recurring defects/complexity or upstream changes warrant reassessment, load [quality and adaptation](references/quality-loop.md). Keep refactoring, bug remediation, real-surface testing, help/docs and build-versus-adopt reviews proportional and evidence-led. Distinguish enforced CI checks from guidance and planned gates.

When entering a named project or a new discipline, read the small [role router](references/roles/index.md), then only the relevant module. Roles are perspectives and scoped procedures, not permission grants or automatically running agents.
