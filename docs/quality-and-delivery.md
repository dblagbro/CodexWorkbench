# Quality and delivery: implemented checks and remaining gates

## Enforced by the CI workflow

The GitHub workflow runs on pushes and pull requests with read-only repository permissions, pinned official action revisions and Python 3.10/3.12:

- Meaningful isolated tests for native argument handling, policy preservation/integrity/adoption, resume metadata, recovery controls, coordinator redaction, unattended-plan validation and cooperative handoff races/stale revisions.
- Bash syntax checks for both Codex and Claude wrappers.
- Reproducible one-page PDF generation against the tracked document.
- Allowlisted portable release build.
- Distribution verification: tracked local documentation links, current installer/release payload completeness and manifest integrity, unsafe/private archive entry rejection, extracted fresh-home installation and installed CLI `--help` smoke with native inference commands blocked.

These are automated verification steps, not proof of production behavior or enforced deployment approval. The filename-based private-artifact audit is not comprehensive secret detection. No real cloud account, production service, inference turn or live email is used by collected tests.

## Required agent workflow, not automatic code transformation

The scoped baseline and [quality-loop procedure](../skills/project-bootstrap/references/quality-loop.md) require proportional maintainability review at design/QA/release checkpoints, proactive bounded refactors when duplication/coupling/repeated defects justify them, safe bug reproduction, cause-oriented remediation, regression evidence and meaningful independent review for consequential work.

Changed interfaces require corresponding README/navigation, CLI/API help, configuration examples and operational/manual updates where relevant. The CI link/help checks catch some drift, not the semantic completeness of every manual. Human/agent review must assess actual usability, error handling and recovery. Refactors are not blindly applied on every commit, and code size alone does not justify a rewrite.

No product browser UI exists in this release. Playwright/headless browser verification is therefore not an active project test. When a real UI is added, include actual interaction/rendering evidence, representative loading/error/accessibility states and complete workflows before calling UI QA complete. Adding an unused browser dependency would not improve today's verification.

## Research and direction reviews

The lifecycle already calls for build/buy/integrate research before substantial custom features. It now explicitly revisits maintained open-source/internal alternatives and product direction at meaningful milestones or material changes in upstream support, security, capabilities, costs or user adoption. Use dated primary evidence, a short useful shortlist, migration/exit costs and a focused experiment when needed. Record keep/integrate/adopt/pivot/defer decisions and triggers for the next review.

Predictions and trend scenarios are assumptions, not evidence of demand or guaranteed future needs. Recommend justified pivots but preserve scope, provider/data migration, billing, publication and production approval boundaries. No calendar-based market-research worker is installed merely by adding this guidance; recurring research requires agreed scheduling.

## Explicit remaining gaps

- Branch protection, required external code reviews, merge/release approval policies and deployment promotion are not configured/verified by the workflow file.
- Comprehensive secret scanning, dependency vulnerability scanning and automatic security remediation require a selected, reviewed tool/configuration and measured false-positive/coverage limits.
- Cross-account live handoff, multi-OS-user ACL provisioning, cross-host NFS/partition behavior and app pairing require environment-specific validation.
- Parallel fork/worktree team workflow and real-time communication are roadmap features.

Keep these distinctions in release reports: guidance, configured automation, fixture evidence and actual production evidence are different levels of assurance. No blanket claim of "all best practices" replaces an applicable risk review.
