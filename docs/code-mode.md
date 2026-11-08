# Persistent code-mode baseline

For current local/SSH resume, remote-control supervision, KB access, and fresh/existing installation commands, use [commands-and-installation.md](commands-and-installation.md). This document focuses on baseline persistence.

## Activation and scope

The Bash wrapper activates Workbench only when the first argument is `--code`:

```bash
codex --code
codex --code "Build a useful tool"
codex --code --one-off "Try a small script"
```

`cx` is an explicit convenience alias for starting the same workflow. Plain `codex`, `codex exec`, `codex resume`, and other ordinary invocations are forwarded with unchanged arguments. The explicitly requested resume shortcuts `codex --coderesume`, `codex -cr`, and `cxr` invoke native `codex resume --all`: all-directory selection without adding Workbench baseline, sandbox, browser, network, or writable-root overrides. Plain `codex resume` retains its native directory filtering.

Existing ordinary Codex configuration and integrations remain in effect. Native resume of an old code-mode conversation can restore that conversation's existing instructions; plain Codex launched inside a generated workflow directory can discover its local AGENTS.md normally. Argument passthrough does not erase prior conversation context or suppress native repository instruction discovery.

## Where persistent files live

Maintained source is in this project's `workflow/` and `skills/project-bootstrap/`. Installed files live in `~/.local/share/codex-code/`. Host settings live in `~/.config/codex-code/settings.json`; this workstation retains `/mnt/s/code` and `~/scratch`.

Every new code-mode start creates a stable directory under the configured `session_root` (default `~/.local/share/codex-work/sessions/`) containing:

- `AGENTS.md`: a short managed loader pointing at the pinned policy revision. Legacy sessions retain their original scaffold outside this block.
- `state.json`: the current project/draft/one-off pointer.
- `workbench/policy.json`: active revision, integrity data, notification and applicability acknowledgement.
- `workbench/policy-revisions/<fingerprint>/`: instructions, startup inventory, lifecycle reference, bootstrap skill, read-only KB adapter and source/integrity manifest. Older legacy `workbench/*` files are retained.

The launcher starts native Codex in that stable directory and explicitly asks it to follow AGENTS.md. Codex's supported local instruction loading supplies the persistent baseline. The baseline points to the saved inventory and references, which remain available throughout that conversation. These private skill snapshots are read through the baseline, not installed into global skill discovery.

No global AGENTS.md, user-wide skills, or broad project ancestor instructions are installed. Installing alone does not rewrite existing session roots. Use the explicit [policy upgrade](policy-upgrades.md) workflow to attach reviewed changes to an existing conversation while preserving local instructions and project state.

## Guidance adapted

Keep task classification, authorized discovery, acceptance criteria, proportional research/design, explicit assumptions, correct storage/backup methods, scoped authority, reviewable increments, relevant UI/test/release work, and durable handoff. Keep `docker compose`, vim when an editor is needed, and no em dashes as code-mode preferences.

Market analysis, public naming/IP checks, monetization, detailed architecture documents, CI, and independent reviewers are conditional on the actual project. Private utilities do not need startup paperwork. Quick questions do not need a project name. Existing projects retain their conventions; requested folder case is preserved rather than universally slugged to lowercase.

The advice to install global user instructions conflicts with the requested code-mode boundary, so use session-local instructions instead. A prompt in this chat is not the persistence mechanism. Startup inventory does not install missing tools, authenticate services, read unrelated session history, or prove capability from configuration alone.

The old launcher could bootstrap an unpinned browser MCP package; browser mode now reuses configured integrations. No package is downloaded by the wrapper. Optional tool functionality, mounts/locking, remote sources, authentication, and runtime storage semantics still need task-relevant verification.

## Installation

From a copy of this project on an Ubuntu host with Python 3.10+ and a compatible authenticated Codex CLI:

```bash
python3 workflow/install-portable.py
python3 workflow/install-portable.py --apply
source ~/.local/share/codex-code/code-shell.bash
```

The first command previews changes. The second applies them and backs up existing changed files under `~/.local/state/codex-code/backups/<timestamp>/`. It preserves unrelated settings, shell text, Codex config, credentials, project instructions, and session history. Applying the same release again makes no changes.

For a new workstation with a verified mounted share, explicitly select its root:

```bash
python3 workflow/install-portable.py --project-root /mnt/s/code --chrome off
python3 workflow/install-portable.py --project-root /mnt/s/code --chrome off --apply
```

New installations otherwise use `~/code` and `~/scratch`; existing host settings are retained. Browser mode off disables the workflow's named browser integration only during code-mode runs. Browser mode on inherits existing configuration and does not install or authenticate anything.

Open a new Bash shell after installation, or source the installed wrapper in each already-open shell. Replacing the file on disk does not replace a function already loaded into a running shell. The installer does not start Codex or modify an active conversation.

## Verification and limits

Regression tests use temporary homes and a fake Codex executable, so they make no model calls. They check native argument passthrough, absence of session creation on non-code calls, baseline snapshots, portable host paths, global configuration preservation, idempotent setup, native resume, and one-off placement. These are launcher/installer checks, not proof of model compliance or production device behavior.

Native-ID local/SSH resume and remote-control supervision are implemented; see the current command guide. Full execution-host migration, a combined cross-host session catalog, automated CLI compatibility policy, transactional rollback, and non-Bash command installation remain future work. Backups exist, but a full rollback command is not implemented.

Official references: [AGENTS.md discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md) and [skill discovery](https://learn.chatgpt.com/docs/build-skills).
