# Task-sensitive project bootstrap

## Decisions from the supplied guidance

Keep the inventory, installed-version checks, reuse of existing tools, isolated project dependencies, distinct agent ownership, durable findings, and separation of development and runtime tools.

Replace automatic enablement with discovery followed by task-driven activation. Having research, browser, and subagent tools available does not justify modifying global configuration. The current session already exposes these tools; a review agent completed a bounded review successfully. Browser tool definitions are exposed, but browser connectivity has not been exercised.

Treat the long tool list as an optional catalog, not a prerequisite. Missing Ansible should not prevent writing a Python utility. A tool on PATH may still fail, lack authentication, point at the wrong host, or be inappropriate for the task.

Replace a universal preference for CLI over MCP with a fit decision. Prefer an existing supported connector when sufficient; otherwise choose CLI/API/browser access by reliability, reproducibility, permissions, and maintenance burden. MFA remains a user-controlled step when required.

Create domain skills when a recurring or fragile workflow warrants them. Do not pre-create UniFi, DNS, recovery, and WebUI skills for unrelated work. Use the installed skill-creation workflow for any new skill.

Delegation is available for this project: lead plus at most three specialists, with distinct ownership. It is a ceiling, not a staffing target. Only the lead coordinates shared production mutations, and task-specific authorization still applies. Future projects should establish their own delegation policy.

Use the session placement workflow and active project directory. The quoted `/mnt/s/code/unifi-controller-migration/` and UniFi/AWS starting roles do not apply here.

Keep essential maintenance, hardware stop mechanisms, and recovery executable without an active AI session. AI applications can legitimately depend on inference: document that runtime dependency and define failure behavior. Do not accidentally require Codex or an MCP session to operate the deployed product.

## Lightweight bootstrap contract

1. Identify the desired outcome, affected systems, project conventions, and current authorization.
2. Inventory only relevant capabilities. Record detected, configured, reachable, authenticated, and behaviorally verified as distinct evidence where needed, with timestamp and scope.
3. Select tools and skills for the task. Explain any required configuration or installation before making it; do not upgrade unrelated infrastructure.
4. For operational changes, define the target, intended mutation, success check, recovery path, and stopping condition proportional to risk. Ordinary reversible coding should proceed without approval ceremony.
5. Record findings, decisions, outstanding questions, status, and test evidence in the project. Continue useful work; ask for access only when a concrete next action depends on it.

Avoid a single permanent “bootstrap complete” marker. Capabilities change by host, project, session, credentials, and CLI version. Recheck evidence when it becomes relevant or stale.

## Select relevant capability groups

| Task | Candidate capabilities | Design emphasis |
| --- | --- | --- |
| General coding | Git, rg, language environment, project test runner | Reproducible setup and appropriate checks |
| Troubleshooting | Logs, timestamps, diagnostic CLI/API | Preserve evidence; test discriminating hypotheses |
| Reverse engineering | Hashing, format/disassembly tools as needed | Artifact provenance, copies, isolation for untrusted execution |
| Hardware control | Device SDK/protocol tools, simulator or bench harness | Device identity, units, output limits, interlocks, independent stop |
| Systems maintenance | SSH, rsync, service/container tools, Ansible if useful | Explicit target, recoverable state, bounded mutation, recovery evidence |
| Cloud/network | Scoped provider CLI/API, DNS/TLS tools | Account/region/zone identity and least necessary permissions |
| Web development | Node if relevant, browser automation, Playwright | Local behavior tests and supported deployment procedure |
| Repeated automation | Scheduler/runner and durable result recording | Safe repetition, bounded retries, partial failure, concurrency control |
| AI application | Supported model interface and evaluation examples | Explicit model overrides, representative evals, observable fallbacks |

## Implemented now

- `scripts/inventory.py`: Python 3.10+ standard-library inventory. Default mode detects executables and selected configuration names without running tools. `--probe` adds bounded local version/help commands, which may have ordinary tool-startup side effects. No installation, daemon connection, cloud call, or feature toggle is requested.
- `skills/project-bootstrap/SKILL.md`: reusable source, kept in this project. Code-mode launches now snapshot it privately into each workflow session; it is not installed into a global skill location. See `code-mode.md`.
- `AGENTS.md`: applies the principles to continuing work in CodexWorkbench.
- `tests/test_inventory.py`: checks credential-value omission, no subprocess execution by default, and failure handling.

Run from the project:

```bash
python3 scripts/inventory.py
python3 scripts/inventory.py --probe --output docs/bootstrap-inventory.json
python3 -m unittest discover -s tests -v
```

Output files are created exclusively; choose a new name for another snapshot. Reports contain local paths and capability names and should be reviewed before sharing. The script intentionally does not dump MCP commands, URLs, environment values, credentials, browser tabs, or history. It does not compute effective layered configuration or fully discover plugin/ancestor skills; use the actual session catalog alongside it.

## Evidence and next implementation

The local CLI help and `codex features list` are evidence for installed version 0.167.0. `--search`, `--model`, and `--profile` are present; `multi_agent` is stable and true. The installed help describes `--profile` as a named `<name>.config.toml` layer. Do not assume legacy inline profile tables are the correct deployment format.

Current official documentation was consulted for [configuration](https://learn.chatgpt.com/docs/config-file/config-reference), [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), and [skills](https://learn.chatgpt.com/docs/build-skills). Validate exact configuration against the installed CLI before writing it; current website documentation may describe a different release.

Next, import the existing launcher source for review and design a previewable deployment that can install selected skills and project-start behavior. Model routing should begin with explicit launch-time policy; no unsupported dynamic switching or speculative feature flags are needed.
