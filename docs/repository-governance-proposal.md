# Repository governance proposal

Owner approved this matrix, exact solo-owner protection payload and scanner/metadata-egress policies on 2026-11-08. Implementation and verification are tracked in [security and governance](security-and-governance.md).

Status: **owner approved; main protections applied and verified after green security/test prerequisites**. Prepared2026-11-08. No remote protection, visibility, access, review or release settings are changed by the proposal tool. The owner has approved public professional attribution using their own name/Gmail. That is not a secret finding and no historical identity rewrite is proposed. Credentials and unrelated private records remain excluded.

## Classify independent facts

Record hosting trust, actual ownership/authority, visibility, data sensitivity, deployment criticality and solo/team context separately. A private external service is not internal trusted storage. A public repository physically hosted internally still needs public-data restrictions. Unknown or conflicting facts block publication/governance changes until resolved. A contributor's technical API permission does not establish the repository owner's authorization.

| Profile | Allowed within existing task authority | Not allowed by classification | Recommended gates |
| --- | --- | --- | --- |
| Owner-managed external public, publishable, solo | Sanitized branches/PRs, fixtures, approved public attribution; public dependency metadata queries | Credentials, private journals/backups, silent releases/deployments, automatic bypass/history rewrite | PR + green checks + resolved conversations; zero mandatory independent GitHub approvals until a real reviewer exists; explicit owner merge/release approval |
| Owner-managed public team | Same public-data restrictions; distinct branches/worktrees and assigned integration | Agent self-review counted as independent GitHub approval; concurrent edits to one shared directory | At least one real nonauthor reviewer, stale approvals dismissed, checks, owner-approved release/tag policy |
| Owner/org external private/internal, restricted data | Authorized source edits/collaboration and approved CI/scanners | Public forks/mirrors/artifacts, report uploads or package-inventory egress without data approval | Verify paid/account feature availability; scoped runners/tokens; local scans; offline vulnerability DB or explicitly approved metadata queries |
| Controlled internal restricted repository | Approved internal runners/review and local secret files outside tracked/build/publication inputs | Assuming internal placement grants internet egress, broad permissions or plaintext credential commits | Internal gates and retention; restricted access; local/offline scanning; explicit approved external synchronization |
| Client/upstream-controlled repository | Authorized read, reviewed isolated fixtures, contributions permitted by that owner's rules | Changing their protections/visibility/access/release policy; publishing confidential code in a personal fork | Follow their governing policy and reviewer requirements; obtain their authority for changes |
| Unknown/conflicting classification | Read-only discovery and self-authored isolated fixtures without executing untrusted repository code | Publication, credential grants, live protections or untrusted-code execution | Resolve missing facts; fail closed |

Production/safety-critical deployment is a separate axis: require a tested rollback/recovery packet, evidence and explicit authorized production approval. Safety-critical work needs an agreed independent review arrangement before release. Do not silently apply a two-reviewer requirement where no such reviewers exist. Scoped local secret files are allowed under the owner's secure internal-storage policy; that does not authorize secret commits or public build contexts.

## Concrete proposal for this repository

Observed read-only from GitHub: personal owner-managed, public, main branch, administrator permission, no active rulesets and no main branch protection at inspection. Proposed classification is external/public/publishable/development/solo. The executable `workflow/repo_policy.py` emits a digest-bound proposal from [example facts](../config/repository-facts.example.json); it has no apply operation.

Proposed main protections, represented in [the candidate payload](../config/codex-workbench-protection.proposed.json):

- Require PRs and exact successful check contexts `test (3.10)`, `test (3.12)`, `security-secrets`, `security-dependencies`; strict branch freshness and conversation resolution.
- Block force-push/deletion and require linear integration history.
- Independent approving-review count0 for the current solo owner; agent independent review is useful evidence but does not become a GitHub approving person. Change to1 when an actual nonauthor reviewer is configured.
- Apply rules to administrators; no automatic bot bypass. The owner retains administrative ability to make an explicit, narrowly scoped, recorded break-glass settings change if needed, followed by restoration/verification. Confirm this policy before activation.
- Release/tag promotion requires explicit owner authorization and the tested commit/artifact hashes. Do not give an agent unrestricted administrative/cloud credentials for convenience.

**Activation order:** approve this classification and exact settings payload; implement and prove the proposed security jobs on a candidate branch; verify check names, account entitlements and overlapping rules against current state; apply the approved payload only when its prerequisites hold and there is no material drift. Ask again only for a changed scope/diff, not the same authorization. Security job names in the payload are proposals, not presently enabled required checks. An impossible/missing check must not lock the owner out. No branch setting is applied by these files.

## Selected scanning approach

| Need | Selected candidate | Data/privacy and limitations |
| --- | --- | --- |
| Secrets in history and actual outgoing source/artifacts | Gitleaks CLI8.30.1, MIT, pinned release archive/checksum | Local/redacted report; no PR comment or report upload; no credential validity checks. Scan all locally available refs/reflogs plus outbound export/artifacts. A clean scan is not proof of absence. Do not scan all approved local secret storage and call every intentionally stored secret a leak. |
| Python dependencies | pip-audit2.10.1, Apache-2.0 | Audit explicitly reviewed resolved pins with `--disable-pip --no-deps`; no automatic fix. Do not resolve/build arbitrary untrusted requirements to audit them. Vulnerability queries send package/version metadata, so restricted repos need explicit approval or offline alternative. No complete transitive audit is claimed yet. |
| Broader stacks/restricted inventory | OSV-Scanner2.7.0, Apache-2.0, when justified | Full offline mode with a preapproved DB; do not mistake `--offline-vulnerabilities` for no network. Defaults may transmit package/version/hash data. Pin/review before adding it; do not install redundant scanners by default. |
| Platform features | GitHub secret/push protection, dependency alerts/review where available | Availability/plan and issuer-validation behavior must be checked. Public support is not proof a specific feature is enabled. No new paid add-on is authorized. |

The Gitleaks CLI is selected instead of blindly using `gitleaks-action`, whose license/organization-key requirements and report/comment defaults differ. Scanner configuration/allowlists must be reviewed; do not blanket-ignore tests or known-secret-looking files. False positives need exact, justified suppression and regression coverage. Actual exposure requires notification without values, scoped revocation/rotation, then separately approved history cleanup if warranted.

## Results and pending decisions

The pinned CLI passed a synthetic secret-detection and redaction test. The local-history scan covered10 commits on available refs plus reflogs and reported0 findings. It did not validate credentials, upload reports, enumerate missing remote refs, inspect issue text or prove every existing artifact is clean. Detailed reports and tool hashes stay in private `.workbench/security/`.

Owner approval recorded for the classifications, exact solo-main policy, admin enforcement/break-glass behavior and chosen scanner/metadata-egress rules. Main protections were applied and read back exactly after all four checks passed. Explicit merge/release authorization is still separate. Native runtime recovery activation and real reboot tests remain separate operational approvals after their tested plan and [native compatibility review](native-recovery-compatibility.md).

Primary sources reviewed2026-11-08: [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), [rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets), [secret scanning](https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning), [push protection](https://docs.github.com/en/code-security/concepts/secret-security/push-protection), [Gitleaks8.30.1](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1), [pip-audit2.10.1](https://github.com/pypa/pip-audit/releases/tag/v2.10.1), [OSV2.7.0 offline behavior](https://github.com/google/osv-scanner/blob/v2.7.0/docs/offline-mode.md), and [separate Gitleaks action](https://github.com/gitleaks/gitleaks-action).
