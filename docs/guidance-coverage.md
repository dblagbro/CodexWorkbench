# Supplied guidance coverage

Both guidance documents were reviewed. Instructions are scoped to code-mode session baselines and references; this is persistent configuration, not a promise that every recommendation is a deterministic enforcement mechanism.

| Supplied guidance | Applied location or deliberate adaptation |
| --- | --- |
| Bootstrap inventory, installed-version capability evidence | `workflow/code-workflow.py`, bundled inventory and `workbench/inventory.json` |
| Research/browser/subagent enablement | Discover and reuse; no guessed flags or automatic tool bundle; browser mode inherits configured integrations |
| Tool catalog and isolated dependencies | Bootstrap skill; optional missing tools do not block unrelated work; existing Python 3.10 is supported |
| CLI/API versus MCP and credentials | Choose supported tools by suitability; KB adapter uses host-local scoped authentication; no public Docker/app-server API |
| Domain skills | Reuse relevant skills; create new domain skills only for actual recurring needs |
| Lead plus a small specialist team | Conditional on the current user's authorization; distinct ownership, lead owns shared live mutations |
| UniFi starting roles and hard-coded project path | Excluded as earlier-project specifics; use active session state and project |
| Runtime independence | Maintenance, hardware stop, recovery independent of Codex; intentional model dependencies documented for AI apps |
| Standing workflow 1-2: task depth, discovery | Concise baseline; facts/decisions/assumptions/questions; no charter for quick tasks |
| 3-6: outcomes, viability, economics, public naming/IP/licenses | Conditional sections in `workflow/lifecycle.md`; internal tooling skips irrelevant monetization/branding |
| 7-8: useful first release and design | Lifecycle scope/acceptance/workflows and proportional design documentation |
| 9: filesystem, runtime, backups | Placement safeguards and lifecycle storage/restore requirements; no empty template directories |
| 10-11: authority and increments | Baseline and lifecycle; reuse authorization, preserve boundaries, reviewable vertical slices |
| 12-14: UI, meaningful QA, release/CI | Conditional lifecycle sections; do not assume GitHub/public registry or claim UI QA from builds |
| 15-16: persistence of work and specialists | Baseline/lifecycle; explicit verified scheduler for ongoing work and bounded operations |
| 17-19: hygiene, operational foresight, completion | Lifecycle and project status/handoff records |
| Ubuntu, shared root, Compose, editor, writing | Host mapping; `docker compose`; vim when needed; no em dashes in user-facing writing |
| Persistent global user instructions | Replaced by session-local AGENTS and scoped references to satisfy explicit plain-Codex isolation |

New code-mode sessions load these from installed workflow files. Global Codex AGENTS/configuration is not overwritten. Existing resumed conversations retain their own saved context; repository instructions continue to apply normally.
