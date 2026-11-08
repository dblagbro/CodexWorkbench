# CodexWorkbench development

If launched through Workbench, follow the stable-session instructions and read its state.json before work. Otherwise use the checked-out repository normally; do not invent a session root.

Read docs/implementation-status.md and the relevant design/command guide. Local operational evidence may exist in ignored docs/status.md; it must not be committed or published.

Preserve ordinary native CLI behavior. Provider-specific instructions and extra capabilities must be opt-in. Native IDs, history, permissions, explicit titles and project rules must survive updates. Keep installed, attached, queued and acknowledged policy states distinct.

Use installed-version evidence before adding flags. Do not infer equivalent capabilities across providers. Use supported metadata for discovery; do not copy prompt text or credentials into caches, tests, artifacts or Git.

Use isolated tests and fake native executables. No test should make an inference request or alter a real service without explicit task authorization. Keep generated print guides to one page. Keep public docs portable and exclude host/session inventories and correspondence.

Delegate only when current user or task instructions authorize it, with distinct ownership and coordinated integration. An approval from another installation or example does not grant current authority.

For work in the owner environment, read `/mnt/s/code/.site-policy.md` before deployment or network-exposure decisions when available. This private file is not distributed with the public repository; other installations use their own configured shared-root site policy.

Before publishing, follow the baseline/lifecycle publication-privacy rules. Review Git metadata/history and built artifacts as well as staged content. Keep personal information and credentials out of external destinations except narrowly justified, explicitly authorized personal-information disclosures. Owner-approved internal local secret storage does not authorize publication.
