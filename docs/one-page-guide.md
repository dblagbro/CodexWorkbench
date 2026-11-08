# Codex Workbench: daily commands
Ubuntu add-on for project setup, native session resume and scoped policy updates.

ACTIVATE in an already-open Bash terminal (new terminals load this automatically)
  source ~/.local/share/codex-code/code-shell.bash

START WORK
  codex --code                         Start with the Workbench baseline
  cx "your task"                       Same workflow, with an initial task
  cx --one-off "small experiment"      Disposable work without project ceremony
Quick tasks stay quick. Existing projects keep their conventions. Substantial work
loads only relevant lifecycle guidance. Plain codex retains normal behavior.

FIND / RESUME SESSIONS
  codex -cr                            All-directory native picker on this host
  codex --coderesume                   Same as -cr; cxr is also an alias
  cxr --last                           Latest native session across directories
  codex -cr --host HOST                Picker on an SSH-accessible host
  codex -cr --host HOST THREAD_UUID    Continue that original native thread
Workbench resume uses the saved session directory. SSH keeps work on that host.
Shared project files alone
do not migrate conversation history, credentials, memory or running processes.

UPGRADE EXISTING CODE-MODE SESSIONS
  codex --code --upgrade               Choose, apply and queue a relevance review
  codex --code --upgrade --preview
                                       Choose a session for a read-only preview
In the menu: /words searches, a number or exact ID selects, q cancels.
For scripts: add --thread THREAD_UUID. Add --host HOST to target another host.
  codex --code --upgrade --thread THREAD_UUID --check
Only an agent's acknowledgement confirms its review. It records applicable,
skipped or conflicting rules, preserving the task, history and local requirements.

INSTALL / UPDATE THE ADD-ON (Codex is installed/authenticated separately)
  python3 workflow/install-portable.py --project-root /mnt/s/code --chrome off
Review the preview, then repeat with --apply. Missing external storage is refused.
Python 3.10+; existing tomli helps configuration inventory on Python 3.10.

REMOTE CONTROL / KNOWLEDGE
  systemctl --user status codex-code-remote-control.timer
  python3 ~/.local/share/codex-code/coordinator.py probe
  python3 ~/.local/share/codex-code/coordinator.py search "topic"
Remote-control recovery is enabled by default; pairing may require account setup.
KB uses each host's existing scoped identity. Vault access awaits separate rollout.

CLAUDE (OPTIONAL: install with --with-claude)
  claude --code "task"                 Shared baseline, native Claude permissions
  claude --resume                      All-project metadata menu; native fallback
  claude --code --upgrade              Choose registered Claude policy updates
Native fallback: command claude --resume, then Ctrl+A for all projects and search.
Existing Claude chats require an explicit policy read; provider histories stay native.

SHARED PROJECTS (new named code projects enroll automatically)
  codex --code --handoff --project . init   Preview existing-project enrollment
Read WORKBENCH.md; load only needed role modules. Add --apply to enroll.

FILES / LIMITS
Installed helpers: ~/.local/share/codex-code/   Settings: ~/.config/codex-code/
Stable sessions: ~/.local/share/codex-work/sessions/   Project files: /mnt/s/code/
Policy snapshots and receipts stay in the selected session's workbench/ directory.
Source/docs: github.com/dblagbro/CodexWorkbench | docs/commands-and-installation.md
Reboot session restoration, execution-host migration and full vault access are pending.
