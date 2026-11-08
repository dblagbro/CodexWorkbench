# Approved security and repository governance

The owner approved the [classification matrix and solo-owner policy](repository-governance-proposal.md) on 2026-11-08. Public professional name/email attribution is authorized; credentials and unrelated private records remain excluded. This approval applies to the documented scope, not new production actions, native recovery activation or public releases.

## Automated checks

The candidate adds exact GitHub check names `security-secrets` and `security-dependencies`, alongside `test (3.10)` and `test (3.12)`. Protection activation follows successful candidate checks and a fresh settings comparison. The approved payload is [versioned here](../config/codex-workbench-protection.proposed.json). The `.proposed` filename preserves the original reviewed artifact; actual remote settings must be read back rather than inferred from its presence.

Secret checking uses the checksum-pinned Gitleaks CLI, full available Git history/reflogs, tracked outgoing export and built archives. It first checks synthetic detection and report redaction. Reports remain temporary and are not uploaded; failures withhold raw findings from CI output. Credential validity is never probed. Detection is heuristic, not proof that no secret exists. Public commit metadata is intentionally public professional attribution.

Dependency checking uses pip-audit 2.10.1 with `--disable-pip --no-deps`, no automatic fixes and no audited-package execution. Native Linux Python 3.10/3.12 wheel-only dry-run resolutions produced separate reviewed snapshots: 32 and 31 pins. A digest guard rejects changed dependency/workflow source inputs before querying the vulnerability service. Package/version metadata egress is approved for this public project; another repository needs its applicable classification policy. No report is uploaded to GitHub or an unrelated scanner service.

These are audit snapshots, not installation lockfiles. The optional SDK installer currently resolves transitive dependencies at installation time. This check does not attest to existing host environments, future resolver choices, vendored native CLI binaries, other platforms/Python versions or the scanner's own dependencies. An installation lock/installed-environment audit is separate follow-up work. The Python core has no third-party runtime dependencies; the snapshots cover the optional Claude SDK closure and CI's tomli pin.

## Reproducing and updating

Run `python3 scripts/build-release.py`, then `python3 scripts/security-check.py secrets --gitleaks /path/to/checksum-verified/gitleaks`. This reads Git's index for outgoing content, so stage the intended candidate first. CI uses its checked-out index. History coverage is limited to locally available refs and reflogs.

In a dedicated venv with pip-audit 2.10.1, run `python scripts/security-check.py dependencies`. The standalone `inventory` command performs the local digest/pin checks without network access. Nonzero status, missing advisory data, skipped packages or stale inventories fail the gate. Diagnose findings; do not add blanket ignores or auto-fix.

When dependency inputs change, perform wheel-only dry-run resolution on each actual supported Python version in an isolated environment. Review package names, versions, sources and licenses. Update `requirements-audit-310.txt`, `requirements-audit-312.txt` and `config/dependency-audit.json` together, then rerun the audits. Do not execute arbitrary untrusted requirements to obtain inventory. Retain detailed resolver reports privately, not in Git. Source hashes include the workflow intentionally, so workflow edits require rechecking the inventory.

## Operating the protected branch

Use a branch and pull request. Four exact successful checks, current branch freshness, resolved conversations and linear history are required. Force pushes and branch deletion are disabled. Administrators are included; no automatic agent bypass. The current solo-owner policy requires zero independent approving GitHub accounts; independent agent review does not count as a human approval. Configure one approval only when a real nonauthor reviewer exists.

Merge/release authorization remains distinct from successful CI. A necessary owner-directed break-glass change must record the exact settings diff, reason, scope, restoration and verification. Do not silently weaken protections to resolve a failing check. Recovery planning never replays an uncertain mutation, and [native resume safety](native-recovery-compatibility.md) remains a separate pilot.

For remote verification, read `gh api repos/OWNER/REPO/branches/main/protection` and compare the normalized settings to the approved payload. Confirm actual check names on the reviewed commit before activating required checks. No account-plan purchase or paid add-on is authorized.

Sources: [pip-audit](https://github.com/pypa/pip-audit/blob/v2.10.1/README.md), [Gitleaks](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1), [GitHub branch protection API](https://docs.github.com/en/rest/branches/branch-protection). Reviewed 2026-11-08.
