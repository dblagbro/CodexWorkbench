# Resume scope and cross-host continuity

Current implementation: local native-ID resume and SSH access to the original state-owning host are installed on workstation and dev-host. Use `codex -cr --host dev-host [THREAD_UUID]` or the reverse host direction. The migration proposal below remains unimplemented; it is distinct from the working SSH access feature.

`codex resume` keeps native current-directory filtering. `codex resume --all` shows sessions beyond that directory in the active user's configured Codex state store. It does not enumerate other OS users' histories or automatically discover histories on other machines.

The requested shortcuts `codex -cr`, `codex --coderesume`, and `cxr` map to `codex resume --all`. They add no Workbench baseline, writable roots, sandbox, network, or browser overrides. Reload the wrapper in already-open shells after installation.

## Current shared-project behavior

| Item | Current location or owner | Shared solely through `/mnt/s/code`? |
| --- | --- | --- |
| Source and project documents | `/mnt/s/code/<project>/` | Yes, if the share exposes the same files |
| Native conversation transcripts/index/state | Configured Codex state locations, usually under `~/.codex` | No |
| Workbench instructions, state pointer, inventory, references | Local stable workflow session root | No |
| Installed wrapper/helper, configuration, skills, credentials | Per-host/user locations | No |
| Running services, processes, device handles, memory | Origin machine | No |

Even if a native conversation is made available on another host, saved instructions may contain absolute paths, old inventory, helper locations, and references to a stable session root absent on the destination. A matching project path alone does not repair those references. Native resume can ask whether to use the saved or current directory; custom state pointers must also agree with the intended project.

## Proposed handoff feature

Not implemented. To move execution onto a destination machine, an explicit handoff should:

1. Quiesce the source conversation and relevant background work; prevent accidental simultaneous ownership.
2. Record session identity, supported CLI version, project identity/path, Workbench state and instruction/reference snapshots, and necessary native conversation artifacts through a validated export/import mechanism.
3. Keep credentials and host configuration local. Do not copy an entire active Codex home as an assumed migration API. Rollout files alone do not preserve all database-only state.
4. Install Workbench on the destination, verify share mapping/access, restore supported session artifacts, and remap workflow pointers/helper references as required.
5. Preserve project decisions and conversation history while refreshing host inventory, paths, tool availability, permissions, and device/service identity. Treat old host evidence as historical.
6. Verify resume and project access in isolated two-host tests before claiming complete continuity. Report nonportable state explicitly.

Today, use shared project handoff documents with a new code-mode session on another host, or access the original machine's Codex remotely. Remote access keeps execution on the original machine; it does not move execution onto the new device.

Shared Codex state is another architecture, but locking, daemon behavior, authentication, and mount semantics need separate design and verification. Do not point live Codex homes at shared storage simply because source is shared.

Sources: [CLI resume](https://learn.chatgpt.com/docs/cli/reference), [transcript locations](https://learn.chatgpt.com/docs/reference/troubleshooting), and [NFS deployment guidance](https://learn.chatgpt.com/docs/environments/network-file-systems).
