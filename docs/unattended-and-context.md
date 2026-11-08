# Unattended work and efficient context

## Asking to keep going

Code-mode guidance recognizes "keep going", "work unattended", "continue while I am away" and equivalents. It continues authorized work and offers missing unattended settings once:

1. How far through the current milestone/backlog; excluded or approval-gated actions.
2. Self-check frequency and separate user-facing status frequency.
3. Finite hours/days/deadline, per-attempt bound, owner host/thread, budget and stop conditions.
4. Blocker/status channel, explicitly approved destination/subject and deduplication policy.

Existing answers are reused. Setup questions do not prevent independent authorized work. A request to add this behavior does not schedule the current project or authorize email from an example. The durable procedure is bundled with the [bootstrap skill](../skills/project-bootstrap/SKILL.md) in [unattended.md](../skills/project-bootstrap/references/unattended.md).

The bundled `skills/project-bootstrap/scripts/unattended-plan.py` validates these settings. Without `--apply`, it previews them; with `--apply` after user agreement, it saves a private `workbench/unattended/plan.json` under the stable session. It records scope, host, deadline, cadence, per-attempt runtime, budget, notification policy and priority source. It refuses to overwrite an existing agreement and refuses redirected private state. To revise a plan, pause/stop its actual scheduler first, preserve the previous agreement/evidence privately, then record newly agreed limits.

**A saved plan is not a timer.** The agent must separately discover, install and verify an actual supported project continuation mechanism after the settings are agreed. No scheduler, inference request or email is activated merely by installing this guidance. No cross-provider continuation adapter is assumed. A scheduler must account for native busy state, ownership, overlap, uncertain launches, bounded retries, deadline/stop controls, mount availability and deduplicated notifications. Installed/queued/executed/progress/delivered are distinct outcomes. Reuse proven fixture evidence for unchanged mechanisms, then verify the actual installed wake path.

## Context and capability preparation

When a design feature enters scope, load its relevant skill and prepare necessary supported tools early. Keep a compact record of source/version, purpose, verification and findings using existing project conventions. Avoid rereading unchanged material already in context. Refresh changed sections, facts with freshness requirements and context missing after compaction. The detailed [context-efficiency procedure](../skills/project-bootstrap/references/context-efficiency.md) is loaded only when useful.

Prefer existing deterministic CLI/metadata/KB tools and concise project handoffs before more model calls or servers. Specialists need distinct tasks and focused handoffs; do not create idle agents to keep them warm. Review optional third-party tools for source/license, maintenance, privacy and measured benefit. Do not reduce model accuracy, omit required verification or assume prompt-cache hits to claim savings. Nothing here changes global memory settings or merges provider histories.

Official references: [skills and progressive disclosure](https://learn.chatgpt.com/docs/build-skills), [memories](https://learn.chatgpt.com/docs/customization/memories), [non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode), and [scheduled tasks](https://learn.chatgpt.com/docs/automations).

New code-mode sessions receive this guidance through their scoped policy snapshot. Existing sessions adopt it through `codex --code --upgrade`, followed by in-session relevance review and acknowledgement. Plain native launches remain unchanged.
