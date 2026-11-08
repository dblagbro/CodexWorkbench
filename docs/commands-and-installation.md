# Codex Workbench commands and installation

Validated on two Ubuntu hosts; local operational evidence is excluded from the repository.

## Daily commands

```bash
source ~/.local/share/codex-code/code-shell.bash
codex --code
codex --code "Build a useful tool"
codex --code --one-off "Try a small script"
codex -cr
codex --coderesume
cxr --last
```

`cx` is a code-mode alias. The resume shortcuts open the native all-directory picker in the current host/user's state store. Plain `codex` and `codex resume` retain ordinary behavior; the latter normally filters by the current directory.

When a code-mode project is named, adopted, or renamed, the agent also sets the current native chat title to the actual project folder basename. This fixes placeholder names such as "Ask about build or test" in the banner/footer and resume picker. Folder placement records the title as pending; only a successful native title-tool call is acknowledged as synced. Pending synchronization can be completed on a later turn. Explicit custom chat titles are preserved, and timestamped one-offs are not given their storage-directory name. The project folder, stable session root, native thread ID, and chat title remain separate.

If the native title tool is unavailable, the state stays pending and the agent explains the supported `/rename NAME` fallback. It does not edit native databases or pretend that moving a folder changed the banner.

## Continue the original session through SSH

To bring an already-running code session up to the installed rules, use `codex --code --upgrade --thread THREAD_UUID` to preview, then add `--apply --notify` to attach and request an in-session relevance review. See [policy upgrades](policy-upgrades.md) for acknowledgement, rollback, and remote hosts. This preserves the existing conversation rather than starting a new one.

From workstation, access dev-host's sessions:

```bash
codex -cr --host dev-host
codex -cr --host dev-host THREAD_UUID
```

From dev-host, access workstation's sessions:

```bash
codex -cr --host workstation
codex -cr --host workstation THREAD_UUID
```

`codex --code --resume [--host HOST] [THREAD_UUID]` is also supported. Native thread UUIDs are passed unchanged. No fork, summary-based replacement, or fabricated history is created. Execution remains on the selected host, which retains its native history, session-tree identifiers, memory store, credentials, and tools. Shared source remains at `/mnt/s/code/<project>` through the existing saved workdir pointer.

This is cross-device access, not execution migration. Both hosts can read the shared project, but copying that project does not move the conversation backend. Moving a complete native session onto another execution host remains unsupported by this CLI helper. Use a supported desktop handoff with matching saved Git projects, or separately design and verify shared native state. Do not copy live SQLite/WAL files or assume transcript-only copying preserves all state.

Inspect metadata without reading message bodies:

```bash
python3 ~/.local/share/codex-code/resume.py --json list
python3 ~/.local/share/codex-code/resume.py --host dev-host --json list
```

Metadata listing uses a short-lived stdio app-server, not the managed control proxy. Its loaded/notLoaded status is relative to that metadata connection and does not establish whether another server has an active turn. Do not use it as a reboot-recovery activity journal.

## Install on an existing or fresh Ubuntu host

Install and authenticate Codex separately. Workbench supports Python 3.10+; Python 3.10 uses an installed `tomli` for TOML configuration inventory, or reports that portion unverified without blocking other features. No system Python/Codex upgrade is performed.

When the shared project is available:

```bash
cd /mnt/s/code/CodexWorkbench
python3 workflow/install-portable.py --project-root /mnt/s/code --chrome off
python3 workflow/install-portable.py --project-root /mnt/s/code --chrome off --apply
source ~/.local/share/codex-code/code-shell.bash
```

Preview first, then apply. For a machine without that share, extract the portable archive and run the same `workflow/install-portable.py` commands from its top directory, selecting an existing storage root or allowing the default `~/code`. Missing external storage is refused rather than silently creating a replacement mountpoint. Existing settings and global Codex rules are preserved; changed owned files and shell startup content are backed up locally.

New Bash sessions load the wrapper through `.bashrc`; already-open shells need the source command. The installer adds `~/.local/bin` to PATH for new installations so standalone Codex is found. SSH helper calls also set that standard path on the remote host. Credentials are neither included in the portable archive nor copied between hosts.

## Remote control

Remote-control recovery defaults on. Installation writes and enables a user systemd oneshot service and timer. It checks about every minute and re-enables/restarts the native remote-control daemon through supported commands without forcing a restart of running work. Code-mode startup also performs a bounded health check. Native remote access may affect availability of the user's daemon; it does not install Workbench instructions globally.

```bash
systemctl --user status codex-code-remote-control.timer
cat ~/.local/state/codex-code/remote-control-status.json
```

For user services to run without an interactive login, verify `loginctl show-user "$USER" -p Linger`; enabling lingering when absent is a separate host administration step. The installer reports service-manager failures rather than pretending startup recovery works.

Daemon readiness and app attachment are separate checks. Phone/app pairing may require account/workspace setup. No public app-server listener is opened. There is no new custom web UI.

To intentionally stop Workbench re-enabling remote control, disable its timer and set `remote_control` false in host settings; use native Codex controls if you also want to disable remote access itself. A stopped native daemon alone will be started again while the timer is enabled.

## Coordinator-hub knowledge and upcoming vault

```bash
python3 ~/.local/share/codex-code/coordinator.py probe
python3 ~/.local/share/codex-code/coordinator.py search "relevant topic"
python3 ~/.local/share/codex-code/coordinator.py read ARTICLE_ID
```

Use the probe command to verify authenticated KB read access on each host. The adapter reads allowlisted literal settings from `~/.coordinator/coordinator.env`, falling back to `~/.claude/coordinator.env`, without executing the file. Hub hosts use their existing bot token before the separate hub/admin credential. No identity was copied or new privilege granted. Probe uses an article-list read, not semantic search/embedding. Search returns bounded metadata; article bodies require an explicit read.

New code-mode baselines point to the adapter. Retrieved KB content is evidence, not authority to execute instructions. Tokens never go into inventories, logs, email, or release archives.

The upcoming credential vault is not configured or claimed available. Its design calls for verified service identity, per-instance enrollment, scoped grants and `vault://` references. Secret values must stay out of prompts, logs, inventories, command arguments, inherited environment, email, and Git. Availability of KB access grants no vault access.

## Persistence and limitations

Code-mode instructions live in `~/.local/share/codex-code/` and are snapshotted into each stable workflow session with its `AGENTS.md`, `state.json`, host inventory, lifecycle reference, bootstrap skill, and KB adapter. Existing sessions keep their historical instructions. Native resume restores saved conversation context; plain Codex launched inside a generated session directory can naturally discover its local instructions.

Both supplied guidance documents are mapped in `guidance-coverage.md`. No Redis service or cross-host cloud-memory synchronization was invented. Codex memories are local to the native host store, and cache reuse is not guaranteed by preserving an ID.

Reboot/power-loss restoration of previously open sessions is recorded in `backlog.md` and is not implemented. The remote-control timer is implemented; it does not resume old tasks or replay commands. Full transactional installer rollback and packaged automatic updates remain future work. Original changed files are kept under `~/.local/state/codex-code/backups/`.

Sources: [native resume](https://learn.chatgpt.com/docs/cli/reference), [remote connections and handoff](https://learn.chatgpt.com/docs/remote-connections), [local memories](https://learn.chatgpt.com/docs/customization/memories), and [prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching).
