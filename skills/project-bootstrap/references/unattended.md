# Unattended continuation setup

Use this when the owner asks to keep going, work unattended, continue while away, or equivalent. A request to add or discuss this behavior is not itself a request to schedule the current project. Distinguish ordinary ongoing work from a persistent unattended run.

## Ask once, reuse the answers

Read existing continuation records, newest project priorities and relevant authorization first. If the request already supplies a setting, do not ask for it again. If no unattended agreement exists, offer a concise grouped setup using available question tools; continue useful work within current authorization while answers are pending. Do not wait to continue a plainly authorized next task just because unattended settings are incomplete. Do not turn every subsequent "keep going" into new onboarding.

Collect the missing choices:

- **How far:** current task/milestone, highest-priority ready backlog items, or the authorized roadmap. State excluded actions and existing deployment/production/hardware gates. Identify the durable priority source, native provider/thread ID and owning execution host; retain existing model choices.
- **How often:** separate self-check cadence from user-facing status cadence. Offer a starting suggestion such as check every 15 minutes/report hourly, clearly unapproved until answered. Status includes actual progress/evidence, current priority/backlog, blockers, useful alternatives, last/next check, and time remaining. Avoid duplicate/no-change status spam.
- **How long and at what cost:** hours/days or an explicit UTC end time, maximum run duration, approved model/API spending or existing subscription-only usage and resource bounds, plus stop conditions. "Until done" needs a finite runtime cap or a separately agreed renewal process. Do not auto-renew or buy quota on expiry.
- **When help is needed:** in-chat only, an explicitly authorized email/integration, or both; obtain the destination and desired subject where needed, whether routine status uses that channel, and notification frequency. Never inherit another project's recipient, subject or credentials. An example is not authorization to send. Do not send test mail without explicit test-message permission.

Confirm the compact agreement once all missing material choices are resolved. Existing explicit answers authorize their agreed scope; do not add a redundant approval round. Persist a private plan under the stable session's `workbench/unattended/` using the bundled `scripts/unattended-plan.py`, and keep a concise project-local status/backlog reference using established conventions. The helper intentionally refuses to overwrite a plan. To change/renew one, first inspect and pause/stop its actual scheduler, preserve the previous agreement and run evidence as a dated private record, then save the newly agreed plan. Do not renew a deadline automatically. The helper saves a plan only: it does not create a timer, run inference or send messages. Do not publish private plan contents, notifications or credentials.

## Install and verify the continuation mechanism

Inspect installed-provider documentation/help and existing project automation before implementing anything. Prefer an existing supported scheduler/continuation integration; an Ubuntu user systemd timer is an option, not a mandatory platform. Scope changes to this project and reuse existing scoped notification infrastructure. For Codex, official starting points are [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode) and [scheduled tasks](https://learn.chatgpt.com/docs/automations). The CLI and app may support different scheduling surfaces. Claude and future engines need their own verified continuation adapters.

The agreement authorizes setting up the necessary supported scheduler within its scope, not bypassing permissions. If scheduling is unavailable, report that explicitly and continue only while the live session can work. A sleep call, drafted unit file, or saved plan is not a persistent scheduler. Do not claim a timer exists until installed and verified.

Before starting recurrence, establish these invariants and prove them with isolated fixtures (reuse applicable evidence for an unchanged verified mechanism):

- One owner for the actual native thread. Check busy/running/pending native state before a wake; skip busy work without interrupting it. Use an exclusive lock and durable in-flight/uncertain state, not only process names. Two invocations must not create concurrent turns or competing writers. Do not blindly launch exec-resume alongside an active interactive owner.
- Check deadline, paused/stopped state, limits, mounted paths and current authorization before each launch and again in the resumed agent. Do not replay an interrupted command or stale approval. Respect production, DNS, firewall, publication and hardware gates.
- Bound each attempt, retries and backoff. An ambiguous launch response must trigger inspection of actual native state before retry, never another speculative launch. Avoid accumulating queued reminders. Native queue success, including a request to resume, does not prove execution or progress.
- Record scheduled/actual runs, last/next check, status and evidence. Verify the first real scheduler wake and its outcome. State explicitly which host must remain powered/awake, whether logout/boot continuation works, and what happens if storage or networking is absent. A different user's service must not race this one. Reboot restoration of arbitrary open sessions remains a separate feature.
- Provide real status, pause, resume and stop controls; distinguish disabling future wakes from interrupting active work. At deadline/completion/explicit stop, disable recurrence and remove temporary workers safely. No timer supplies missing approval. Keep enough evidence to diagnose failure.

## Each continuation cycle

Refresh the newest authorized priority list and relevant evidence. Review what actually changed, test results, pending dependencies and previous failed approaches. Advance the highest-priority useful ready item; if one item is blocked, work on independent items rather than declaring the whole project blocked. Avoid repeated tests, empty status churn and new speculative scope. Continue through reviewable increments while within the agreed time/resource limits.

At the agreed reporting interval, update project status and send only the configured status notification. When no useful authorized work remains, establish whether the project is complete, waiting for a bounded external dependency, or blocked on the owner. For external waits, record next check, bounded retry policy and escalation condition rather than busy-looping.

For an all-work blocker, describe what stopped progress, what independent work was exhausted, practical choices, the recommended response and how to reply to the correct project/session. Use the explicitly approved channel and destination. Persist a stable blocker fingerprint and notification intent/result; do not repeatedly send the same blocker on every tick. Allow changed or resolved/reopened blockers only under the agreed notification policy. Bound transport retries and mark uncertain delivery rather than duplicating blindly. SMTP/API acceptance is not inbox delivery. If the notification channel also fails, expose that failure in durable local status without pretending help was reached.

## Handoff

Record actual mechanism/unit names, owner host/thread, deadline/timezone, check/report cadence, scope/budget, controls, last/next run, first-wake evidence, notification verification and remaining limitations. Keep runtime development automation separate from the deployed product. Do not describe proposed or simulated behavior as an installed unattended service.
