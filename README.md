# CodexWorkbench

An Ubuntu CLI add-on for organized coding projects, searchable native sessions, and versioned, project-sensitive policies. Codex and Claude use provider-specific adapters over the same project and policy layer.

Workbench preserves native conversation identities and project conventions. Plain agent invocations keep native behavior. Opt-in code mode adds placement, lifecycle guidance, discovery, title handling and reviewable policy updates.

## Print the quick reference

[One-page PDF](docs/Codex-Workbench-One-Page.pdf) | [Editable guide](docs/one-page-guide.md)

## Install

Install and authenticate the native CLI separately. Python 3.10+ and Bash are required.

```bash
git clone https://github.com/dblagbro/CodexWorkbench.git
cd CodexWorkbench
python3 workflow/install-portable.py
python3 workflow/install-portable.py --apply
source ~/.local/share/codex-code/code-shell.bash
```

The first command previews changes. Select an existing external project root with `--project-root /path/to/code`; a fresh host otherwise uses `~/code`. Changed owned files are backed up. Existing global instructions, credentials and native history are preserved.

Optional Claude integration uses `--with-claude`, installing its official metadata SDK in an isolated environment. Native agent packages are not upgraded.

## Use

```bash
codex --code "Build a useful tool"
cx --one-off "Try a small experiment"
codex -cr
codex -cr --host dev-host
codex --code --upgrade
codex --code --upgrade --preview
```

Selecting a session applies and queues a relevance review by default; `--preview` is read-only. The upgrade chooser lists sessions behind the installed policy or awaiting adoption. Search with `/words`, select a number or exact native ID, and cancel with `q`. Explicit `--thread` and `--session` selectors remain available for scripts. Attachment, notification and agent acknowledgement are distinct states.

After optional Claude setup:

```bash
claude --code "Build a useful tool"
claude --resume
claude --code --upgrade
```

Claude's global picker uses official SDK metadata when available and falls back to its native picker if discovery is incomplete. Explicit UUID resumes and ordinary launches retain native behavior. Existing Claude conversations need an explicit policy read/acknowledgement; Workbench does not pretend that resumed prompt flags hot-reload rules.

## Documentation

- [Commands and installation](docs/commands-and-installation.md)
- [Existing-session policy upgrades](docs/policy-upgrades.md)
- [Codex/Claude architecture and capability boundaries](docs/unified-providers.md)
- [Code-mode persistence](docs/code-mode.md)
- [Guidance coverage](docs/guidance-coverage.md)
- [Implementation status](docs/implementation-status.md)
- [Backlog](docs/backlog.md)

## Verify

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build-one-pager.py
python3 scripts/build-release.py
```

Collected tests use isolated homes, fixtures and fake native executables. They do not start inference or alter production services. The optional `tests/native_resume_smoke.py` probes a temporary native thread without a model turn and explicitly reports persistence limits.

SSH resume keeps execution on the selected host. Provider histories are not merged. Shared cloud memory, live database migration, reboot replay and credential-vault access are not supplied by this add-on.

This repository distributes local CLI integration. A future plugin can package reusable skills, while shell integration still requires explicit local setup and trust. The source is MIT licensed; native CLIs and optional dependencies retain their own licenses.
