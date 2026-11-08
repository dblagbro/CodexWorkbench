# Native recovery compatibility and idle-resume limits

Read-only investigation2026-11-08. Installed Codex versions0.166.0/0.167.0 and Claude2.1.251/2.1.319 were inspected using help, schemas, documentation and exact-version official source. No real session/queue/goal/account/service was mutated and no inference was started for this investigation.

## Codex

An ordinary `thread/resume` is not a universal idle-only primitive. Exact0.167 source emits a completed idle lifecycle event after resume; the queue and active-goal extensions can start work from that event. `excludeTurns` reduces response hydration; it is not a queue/goal suppression flag. No supported `idleOnly`/`holdQueue` resume parameter was established in the inspected installed schemas.

Managed daemon restoration can explicitly start an inference continuation tagged `daemon_recovery` for interrupted work. Its restoration snapshot is written during controlled daemon shutdown, not continuously as an outage journal; hard power loss may bypass snapshot creation. Starting an existing supervised daemon may therefore have native recovery behavior before a new Workbench planner runs. The relevant0.166/0.167 queue/goal/daemon continuation source was compared and found identical. Existing daemons/timers were not changed by this work.

Safe pre-load inspection surfaces include stable metadata-only `thread/read` and persisted `thread/goal/get`. Experimental `thread/queue/list` can inspect persisted queue state without loading, but includes input bodies: retain counts/IDs only, not raw prompts. Feature errors are unknown state, not proof of no queue/goal. A queue count has a race with other producers; there is no established public queue-freeze primitive.

Native `thread/closed`/unsubscribe may reflect automatic unloading or disconnect rather than a deliberate user close. Workbench needs its own desired-open/explicit-close/uncertain lifecycle records. Both Codex and Claude also support SessionStart hooks on resume, which can execute handlers before a model turn.

## Claude

SessionStart hooks run on resume. Current hook documentation also describes deferred-tool resume behavior that can rerun a tool permission hook and execute the deferred call when allowed. The documented `-p --resume` deferred path does not restore the old stored permission mode. It is not an acceptable generic permission-preserving, idle-only recovery adapter. Undocumented environment controls in a binary are not a supported safety guarantee.

## Candidate policy

The data-only planner now requires `idle_resume_verified_safe` to be an exact true observation, plus explicit verified identities/location, unloaded/idle state and no pending/uncertain work. Missing, false or string-valued verification holds the candidate. Fixtures may explicitly model a safe adapter; that is not evidence that these native clients provide one universally.

For a real pilot, positively verify the same owner/account/provider/native ID and stored permissions; mount/project identity; completed last turn; no queue, goal or uncertain local operation; reviewed hooks; and exclusive/quiesced queue producers. Detect native-managed restoration before creating another worker. Otherwise keep an inspectable recovery list and require a reviewed per-session decision rather than claiming a fully restored idle runtime.

A future native supervisor must capture deliberate close versus disconnect, persist local records before loss, verify capabilities at the installed version and provide pause/stop/rollback. Then use an isolated nonproduction pilot with explicit limits; no active workstation/public gateway reboot or real pending production command is an appropriate initial test. No such supervisor or boot-service activation is included in this candidate.

## Primary evidence

- [Codex hooks](https://learn.chatgpt.com/docs/hooks), [Claude hooks/deferred calls](https://code.claude.com/docs/en/hooks).
- [Exact0.167 thread processor](https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/app-server/src/request_processors/thread_processor.rs).
- [Exact0.167 daemon continuation](https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/app-server/src/request_processors/daemon_continuation.rs) and [daemon snapshot](https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/app-server/src/request_processors/daemon_snapshot.rs).
- [Exact0.167 queue service](https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/ext/queue/src/service.rs) and [goal extension](https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/ext/goal/src/extension.rs).

See [P1 plan](p1-test-plan.md) and [results](p1-results.md). The limitation is a reason to design/test a controlled adapter, not to disable working native recovery or change permissions silently.
