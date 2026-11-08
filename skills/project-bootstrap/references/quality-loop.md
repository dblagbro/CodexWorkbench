# Continuous quality and evidence-led adaptation

Apply at relevant design, implementation and release checkpoints, scaled to the project. Do not turn a narrow fix into an entire lifecycle or claim every practice is automatically enforced.

## Refactor before maintenance becomes a blocker

Notice duplicated behavior, divergent provider adapters/docs, repeated defects, growing coupling, brittle tests, hard-to-review functions, unexplained complexity and recurring manual recovery. At the next sensible checkpoint, propose/implement a bounded project-local refactor when it reduces demonstrated risk or maintenance cost. Establish observable behavior first and test the relevant contracts. Preserve scope and compatibility; raise consequential architectural changes for a decision. Avoid unsolicited full rewrites, cosmetic churn and arbitrary line-count targets.

## QA and defect remediation

Use an explicit loop: record impact/severity and evidence, reproduce safely, diagnose competing explanations, fix the cause in a reviewable increment, add meaningful regression coverage, verify affected workflows, and document remaining uncertainty. Track unresolved defects and blockers in existing project records. A failing test or credible regression is work to resolve, not something to suppress by weakening the check. Use independent review for consequential changes when authorized, and preserve current permissions and rollout gates.

Select checks that exercise real surfaces: CLI argument/help/error handling, integration contracts, concurrency/interruption/recovery, packaging/install/upgrade and security boundaries. For an actual UI, use an installed supported browser automation tool or Playwright/headless interaction and inspect actual rendering/screenshots, loading/error/accessibility states and representative workflows. A successful build is not UI verification. For a CLI-only release, explicitly mark browser tests inapplicable rather than adding an unused browser dependency.

## Documentation, help and delivery

Update docs alongside changed behavior and interfaces. Keep onboarding, README/navigation, command help/error text, manuals/runbooks, configuration examples, test evidence and recovery/rollback instructions useful and consistent. Use inline help fields/tooltips only where they help a real interface user make a decision; do not add implementation detail to product flows. Run link/help/packaging checks when available; distinguish generated/reference docs from private operational evidence. Do not create redundant manuals or empty templates.

Discover the actual CI provider and repository protections. Automate appropriate syntax/lint/tests/build, installation/upgrade smoke, documentation checks, reproducible artifacts and relevant dependency/secret checks. Record any coverage gaps. Branch protection, required review, deployment approval, vulnerability scanning and effective secret detection are not established merely by writing a workflow file. Prepare tested changes and rollback before required deployment approval. Do not publish personal data or secrets to CI logs/artifacts.

## Revisit build versus adopt and product direction

Before a substantial custom feature, and again at release/milestone reviews or material upstream changes, compare a small relevant shortlist of maintained open-source/internal/commercial alternatives. Use current primary sources for versions, licensing, maintainership, security, interoperability, pricing and export/migration constraints. Note review dates and evidence quality. Consider concrete user adoption/value signals, ecosystem direction and operational cost, not popularity alone. Reuse prior findings that remain current; avoid endless repetitive research.

Record decisions as keep/integrate/adopt/pivot/defer with reasons, migration costs, affected workflows, compatibility/data implications and a reversible experiment where useful. Forecasts and trend predictions are assumptions with explicit review triggers, not evidence of demand or guaranteed outcomes. Recommend changing plans when evidence warrants it; do not silently rewrite scope, replace providers, migrate data, incur costs or publish because of a forecast. Calendar-based research/monitoring requires an agreed unattended schedule; milestone reviews do not imply a background worker exists.
