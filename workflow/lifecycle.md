# Code-mode lifecycle reference

Load only the sections relevant to the task. Existing project conventions and the user's current scope take precedence over this suggested structure. Do not copy this entire document into every project.

## Task depth and intended outcome

Quick questions, narrow fixes, scripts, troubleshooting, and disposable experiments need a direct result and proportionate verification. Use the session placement workflow when files are needed, without forcing a public product name or charter. Existing projects keep their established architecture unless the change warrants revisiting it.

For substantial work, establish the problem, users, primary workflows, intended release maturity, public/private/commercial use, constraints, acceptance criteria, and exclusions. Interpret MBT/version 1.0 as the first useful and testable release unless the user's meaning changes scope. Record a short brief when it helps the next implementer.

## Feasibility and economics

Compare a small useful shortlist of existing internal work, maintained products, open-source components, and custom development. Use current primary sources for changing facts; record dates, versions, uncertainty, and the build/buy/integrate decision. Stop researching once the decision has sufficient evidence. Resolve high-risk unknowns with focused experiments and recommend narrowing an unviable approach.

For internal tooling, consider operating cost, saved effort, reliability, and maintenance. For a commercial/public product where relevant, examine customer value, competitor pricing, development and recurring costs, usage economics, acquisition/support effort, and sensitivity to adoption or heavy use. Label estimates and scenarios; do not invent demand or forecasts. Do not provision billable resources outside the agreed scope and budget.

## Naming, licensing, and distribution

The placement workflow needs a useful directory name, not a branding exercise. Public product naming can justify dated domain, repository/package, competing-use, and preliminary trademark checks. Availability is not legal clearance; verify again before purchase/publication. Do not do this for a private utility unless requested.

For incorporated components/assets as applicable, record source, version, license, modifications, and distribution obligations. Include fonts, datasets, model weights, and non-code assets when relevant. Propose a project license if distribution requires one. Keep private work private; publishing requires authorization. Escalate a specific credible consequential IP issue rather than promising legal clearance from a web search.

## Publication privacy

Before pushing to Git hosting, container registries, CI, release storage or other external destinations, establish destination ownership, visibility and the intended disclosure. Treat external repositories as potentially exposed. Sanitize secrets and unnecessary personal information, including names/emails, private inventories, topology, transcripts and correspondence. Review staged files and relevant history/author metadata, generated documents, archives, Docker build contexts/layers and CI output. Ignore rules are useful but do not remove already tracked content or historical disclosures. Use explicit, narrowly justified disclosure exceptions; private visibility or owner control alone is not a blanket exception. Credentials stay out of external publication.

Consult private site policy for internal trust boundaries and local secret-storage permission. Store secret references in source and redacted examples in documentation. A future vault does not replace currently supported local storage until enrollment and scoped access are verified. If prior publication is found to contain sensitive data, report the affected surfaces without reproducing values; coordinate revocation/removal and any consequential history rewrite separately.

## First release and design

Group features into required now, useful next, future, and excluded. Complete important user workflows before expanding the roadmap. Consider onboarding, authorization, administration, errors, progress/cancellation, import/export, recovery, notifications, accessibility, and upgrades only where relevant. Resolve expensive architectural choices before dependent implementation; avoid speculative infrastructure.

Maintain enough design detail for implementation and operation: responsibilities and topology, data lifecycle/migrations, contracts/integrations, permissions, UI flows, secret references, failure handling, timeouts/retries, concurrency/idempotency, restore/rollback, tests, release process, costs, and ownership as needed. Use diagrams when they clarify relationships. Consolidate documents and keep them aligned with code rather than generating boilerplate.

## Filesystems and recoverability

Use the configured project root, preserving requested name case and existing locations. Before storage-dependent work, inspect mount source/type, permissions, relevant locking semantics, free space, and suitability for the workload. Missing mounts must not silently redirect existing project writes to local underlying directories.

Place live databases and sensitive runtime state on suitable storage with restrictive permissions; verify support before using shared mounts. Respect explicit owner/site permission to store local secret files on secure shared storage, while keeping them outside tracked source and publication/build contexts. This does not waive database filesystem checks or backup encryption requirements. Separate source, deployment config, runtime data, logs, artifacts, temporary files, and backups without creating empty directories. Exclude secrets, databases, caches, backups, large outputs, and transcripts from Git.

Use application-consistent backups, checksums, retention, and restore verification. Encrypt sensitive backups before writing them to a share, with recovery keys protected separately. Establish independent failure domains where recovery requires them. Do not equate a live directory mirror with a validated backup. Use managed safety copies, with retention, rather than accumulating old files in source directories.

## Authority and operations

Distinguish local development, remote discovery, host changes, cloud resources, deployment, DNS/certificates, communication, migration, and destructive actions. Honor existing authorization; ask only for material decisions, missing access, or required approval. Never use retries to bypass a denial. Prepare tested changes before a required production approval.

For troubleshooting, preserve evidence and test discriminating hypotheses. For reverse engineering, record artifact provenance/hashes and analyze copies; isolate untrusted execution. Before physical actuation, establish target actions, units, operating limits, interlocks, and stop procedures. Unknown limits permit discovery/simulation, not actuation.

## Implementation, UI, tests, and releases

Prefer appropriate maintained components, clear interfaces, boundary validation, explicit errors, bounded retries, safe repeated operations, versioned configuration, redacted logs, reproducible dependencies, and relevant health checks. Build a vertical slice early. Avoid premature abstractions and hidden manual steps. Follow repository policy for commits; do not assume publication or public hosting is authorized.

For UI work, define workflows before visual polish; reuse suitable components and make status/consequences/recovery clear. Cover keyboard use, accessibility, realistic data, long labels, responsive behavior, loading/empty/error/stale/disconnected states as relevant. Inspect actual browser behavior/screenshots, not only builds. Skip visual design for tasks without a UI.

Choose tests by risk: logic, contracts, permissions, migrations, interruptions, retries, concurrency, restore, deployment/restart, workflows, and security checks as applicable. Use isolated fixtures and prevent test systems from competing with production. Do not write trivial implementation-mirroring tests or rerun broad suites without a reason. Independent reviewers report evidence, changed files, tests, risks, and decisions.

For continuing projects, discover the actual Git/CI platform and visibility before choosing pipelines or registries. Add relevant lint/tests/build/security checks, versioned artifacts, separated environments, protected credentials, migrations, backups, smoke tests, and rollback. CI must not require the original home directory or an active agent session. A disposable script may need only a reproducible check.

## Continuity and completion

Keep objective/scope, verified environment, decisions, status, outstanding issues, next actions, and deployment/recovery state concise and current. Fix safe project-local housekeeping; propose consequential restructuring and do not delete another project's evidence.

Use appropriate session/process management for long operations, capture exit status, check at reasonable intervals, and report consequential progress. Track external dependencies and bounded retries. Persistent execution after the session requires an explicitly requested, configured, and verified scheduler/service; stop temporary workers when done. No timer supplies missing approval.

Apply concrete security needs such as least privilege, tenant boundaries, secret revocation, redaction/retention, privacy, abuse controls, capacity, timekeeping, shutdown/restart, ownership, and exit strategy proportionately.

Demonstrate the agreed acceptance criteria. For substantial work, hand off usage, tests, deployment state, limitations, safe backup references, release/recovery commands, ownership, and costs where relevant. Simple tasks need the result and relevant verification without a formal package.
