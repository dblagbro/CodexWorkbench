# P1 governance, communication and recovery test plan

Scope approved2026-11-08: use simulated data over existing SSH to the workstation and two server hosts, compare bidirectional handoff/correction and test recovery foundations. No actual reboot, network/share outage, firewall/PAT/routing change, model API request, login switch, controller mutation or new server service. Private evidence maps node aliases to real hosts; public results use node1/2/3. Both servers retain their existing gateway roles.

## Environment and isolation

Use a unique project under private `.workbench/p1-tests/RUN_ID/` on the actual shared filesystem, and temporary local journal/effect fixtures on each host. Verify actual filesystem and project UUID. The host-local journal refuses configured shared roots and ephemeral storage by default; tests explicitly opt into disposable paths. Never create local underlying fallback paths when a share is missing. No Docker or listening test service is needed.

Existing SSH access is used without adding keys, weakening host verification or changing authorized_keys. Direct workstation self-SSH is not configured correctly for the current agent identities. Its host key was checked against the local server's public key; the run instead uses the existing trusted server-to-workstation SSH path. This is a transport limitation, not evidence that direct self-SSH was fixed.

All worker/source code hashes are pinned for a run. A changed worker/module rejects the run rather than mixing implementations. Python3.10/3.12 serialization is exercised. Fixtures are deterministic provider labels and injected faults; they are not actual Codex/Claude conversations or measurements of model understanding/training.

## Acceptance matrix

| Area | Case | Pass condition |
| --- | --- | --- |
| Communication | All six ordered cross-host pairs × both Codex/Claude-labelled directions, plus six same-host switches |18 offer→interpret→review→correct→re-interpret→sender accept→receiver ack exchanges complete |
| Interpretation | Deliberately omitted constraint and operation drift | Sender rejects; exact typed constraints/scope are repeated, bounded correction is confirmed; no authority granted |
| Stale messages | Old-offer acknowledgement, newer project revision, policy hash or checkpoint digest | Old acceptance/receipt cannot be reused |
| Correction memory | Pattern provenance and version | Record only reviewed field mismatch metadata; synthetic observations never train live provider assumptions or change permissions |
| Shared ownership | Competing claims from two real SSH nodes on NFS | Exactly one owner; blocked peer does not take over on timeout; reviewed release/sync/transfer works; stale former owner cannot write/release |
| Share loss | Missing mount, wrong mount source, same path/wrong project UUID | Fail closed before dispatch; no local fallback write; restored share requires current revision/owner review |
| Internet/API | Offline/read timeout,408/429/5xx,401/403/permanent404, Retry-After and bounds | Read-only/pre-dispatch retries bounded; auth is not bypassed; lost mutation response is uncertain and never blindly repeated |
| Process loss | Kill fixture before intent, after intent, during local controller lock and after effect before response | Durable intent/effect inspected after restart; local kernel lock releases; fixture effect remains exactly once after reconciliation |
| Reboot simulation | Changed boot ID, desired-open versus closed, already loaded, wrong owner host/account and uncertain pending work | Only verified desired-open chat is a candidate for idle reattachment; commands, approvals and unattended work are not replayed |
| Publication | Fixture/journal/native/account/runtime data | Remain private/excluded; full source/publication scan performed separately |

## Executable fixture commands

`python3 scripts/run-p1-simulation.py --hosts HOST1 HOST2 HOST3 --first-host-via EXISTING_RELAY` orchestrates known SSH aliases. `scripts/p1_worker.py` accepts only the synthetic protocol actions and a project in the reserved fixture tree. Child crash processes use their own temporary directories. The code never calls native model CLIs or provider APIs.

`python3 -m unittest discover -s tests -p test_governance_recovery.py -v` exercises classification, type/stale-message rejection, journal state transitions, retries, storage refusal and boot planning locally. Existing handoff tests remain part of full CI. Use `workflow/repo_policy.py --facts config/repository-facts.example.json` for a proposal-only classification result.

## Recovery architecture candidate

1. Persist operation UUID, project UUID, expected revision/owner, intent digest and boot ID on verified local durable storage **before dispatch**. Fsync file and containing directory. Shared NFS metadata is not the emergency journal.
2. Mark mutation outcome unknown before request dispatch. After disconnect, use read-only evidence or a verified provider idempotency contract; never rerun just because no response arrived. Current prototype does not send requests.
3. On share return, verify per-host mount source/type/target and project UUID; read the newest shared generation/owner. Reconcile instead of applying stale queued state. No timeout grants distributed edit ownership.
4. Persist desired-open native session identity separately from task execution, including owning host/account alias and last observed boot. An idle conversation reattach must preserve its native provider/identity/permissions, not import another account's credentials or accept old approvals.
5. A real restoration supervisor still needs native lifecycle capture, intentional-close detection, current account/identity checks, pending-queue inspection, tested idle-resume adapter and user-service controls. Prefer supported native APIs when they can restore idle conversations; consider a private PTY/tmux only if the native interface requires one and the operator approves it. No public listener or new Docker role is implied.
6. Verify process restart first; then approve a dedicated nonproduction host/VM reboot pilot and rollback. Do not reboot active workstations or public gateways to prove this feature. Physical power-loss, cross-OS-user ACLs, NFS partitions/cache durability and real API/model behavior remain explicitly unproven by these fixtures.

The journal/registry and handshake libraries are candidate foundations. No boot service, live model reattachment, automatic production failover or live repository protection is activated by this test plan. Native-client investigation found concrete resume/restart side effects; see [compatibility findings](native-recovery-compatibility.md). The candidate must hold unsafe/unknown native resume capabilities rather than stack an unverified autolauncher.
