# P1 candidate verification results

Status: fixture/transport foundations passed; governance approved and main protection activated/readback-verified; native reboot activation remains pending. Reviewed2026-11-08. Full communication/ownership run implementation SHA256: `c251b290a6afda3d72951a7da222cf7824fecf224511f12dba689511ef568959`.

| Verification | Observed result |
| --- | --- |
| Bidirectional communication |18 SSH exchanges:12 ordered cross-host and6 same-host provider-labelled cases passed. |
| Interpretation/correction | Injected constraint omission and operation drift rejected; bounded clarification and both acknowledgements succeeded. Old-offer acknowledgements and newer project/policy/checkpoint evidence rejected. Understanding never granted execution authority. |
| Cross-version transport | The same frozen implementation/JSON contracts ran across three actual Ubuntu SSH hosts with Python3.10/3.12. |
| Recovery fixtures |27 cases per host,81 total in the final targeted recovery run: real share identity checks, injected missing/wrong mount/project identity, local child-process loss, API status/backoff decision fixtures, registry/boot planning. |
| Shared NFS ownership | Two real SSH nodes competed; exactly one claimed. Reviewed release/sync/transfer succeeded and stale original-owner release was rejected. |
| Local targeted regressions |15 governance/protocol/recovery unit cases, including exact boolean ingress, account namespaces, ephemeral-path aliases, stale correction observations, unknown activity and failed parent fsync. |
| Secret detector | Gitleaks8.30.1 pinned archive checksum verified. Synthetic detection and report/log redaction passed; locally available ref/reflog history scan returned0 findings across10 commits on refs. |

The fixture run was repeated after independent review found and corrected truthiness, account namespace, path-alias and reviewed-content binding gaps. Do not count a happy-path run as evidence that those negative cases were safe before correction.

The final recovery preflight added an explicit idle-resume side-effect safety gate after native-client source inspection. Its three-host targeted rerun passed81 cases at implementation SHA256 `e43c70e670abfc94d04fb4831c3c0b4f53879bc74a366e6432eef4135ca3b93e`. Communication-contract and handoff module hashes were unchanged from the18-case full run; unrelated message cases were not rerun solely for this recovery delta. The earlier full run passed78 recovery cases; final results supersede those for recovery. All15 targeted regression cases also passed over SSH on each of the three hosts.

Local full test discovery passed124 tests. After the approved security implementation, CI passed128 tests on both Python versions plus both security jobs; the distribution verified87 files,66 documentation links and12 installed CLI helps. See [native compatibility](native-recovery-compatibility.md): native resume/restart can run queued/goaled/interrupted work or hooks, so an idle-only guarantee is not assumed.

## What these results do not prove

- Provider labels are deterministic fixtures. No actual Codex/Claude API conversation, model training, provider account switching or comparative language accuracy was tested.
- Correction patterns are tagged synthetic and cannot be used to teach live provider assumptions automatically. Real observed examples need an approved pilot and human/sender review; no adaptation may widen authority.
- Missing mount/API/boot conditions were injected. No real share was unmounted, internet disconnected, firewall altered or host rebooted. Local child processes were actually terminated; physical power-loss and disk-cache durability were not demonstrated.
- All SSH tests used existing authorized access and the existing user namespace. Multi-OS-user ACL provisioning, authenticated participant identity and network-partition fencing remain separate work.
- The recovery library journals and plans only. It never starts a model, replays a command, approves an action or automatically resumes unattended work. A native idle-restore supervisor/lifecycle capture still needs implementation and a separately approved nonproduction pilot.
- The owner-approved main settings payload is now applied/readback-verified with all four exact required checks. Reviewed dependency snapshots (32/31 pins) and secret scanning passed. These do not attest to existing host environments, future dependency resolution or native bundled binaries; no credential validity checks were made.
- Secret detection is heuristic and local coverage is bounded. No finding is not a guarantee of absence from unavailable refs, other copies, issues, all historical artifacts or third-party services.

Private raw evidence and per-host mount fingerprints are retained under `.workbench/p1-tests/` and `.workbench/security/`, excluded from Git/public artifacts. The public report uses node aliases and aggregate results. See the [test plan](p1-test-plan.md) and [governance proposal](repository-governance-proposal.md) for next decisions and activation order.
