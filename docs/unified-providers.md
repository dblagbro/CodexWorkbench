# Shared workflow, native provider adapters

Workbench shares project placement, lifecycle guidance, host discovery, policy snapshots, applicability receipts and the terminal chooser. Each adapter retains its provider's native session identity, storage and execution semantics.

| Capability | Codex adapter | Claude adapter |
| --- | --- | --- |
| Opt-in launch | `codex --code` | `claude --code`, enabled by installer option |
| Native identity | Existing native thread UUID | Native session UUID; new launches use supported `--session-id` |
| Session instructions | Managed session `AGENTS.md` loader | Managed session `CLAUDE.md` loader |
| Project placement | Shared state/helper | Shared state/helper |
| Resume metadata | Native stdio app-server metadata | Optional official Agent SDK metadata |
| Search/selection | Shared chooser for upgrades; native global resume picker | Shared chooser when full metadata is available |
| Partial discovery | Native metadata truncation reported | Index-only fallback explicitly incomplete; wrapper uses native picker |
| Existing policy adoption | Explicit queued safe-checkpoint review and acknowledgement | Explicit in-session read and acknowledgement; no external queue assumed |
| Title update | Current-session native title tool | Native mechanism when exposed; `/rename` fallback remains pending until confirmed |
| Remote-control supervision | Supported native daemon and user timer | Separate capability; Codex daemon controls are not reused |
| Shared project handoff | Cooperative project checkpoints/ownership and per-participant receipts | Same provider-neutral project protocol; native chat stays separate |
| History transfer between providers | Not supplied | Not supplied |

## The Claude resume investigation

A legacy installation intercepted bare `claude --resume` and searched every encoded project directory. It built a plaintext first-prompt cache, used numbers that could change between listing and selecting, guessed paths by replacing hyphens, lost forwarded flags and silently fell back to the home directory when a path was missing.

The useful behavior is an all-project searchable menu. The new adapter uses the official `claude_agent_sdk.list_sessions()` metadata API, filters out prompt fields, chooses from a stable in-memory snapshot, and resumes the original UUID in its exact recorded directory. It creates no first-prompt cache and never directly scans transcript bodies. The SDK may inspect native storage internally to provide metadata.

If the SDK is unavailable, `sessions-index.json` metadata can be listed but coverage is reported as incomplete. The wrapper then preserves the original native resume command and explains the native Ctrl+A all-project view. It does not present a partial custom list as complete.

Modern Claude already offers a native searchable picker: `command claude --resume`, then Ctrl+A for all projects and typing to search. The Workbench adapter adds an all-project default when complete metadata is available, stable selection, and a common interface. It does not need to replace the native client or its conversation format.

## Applying shared rules to Claude

Install with `--with-claude` to enable the scoped wrapper and isolated metadata SDK. Plain launches and explicit UUID resumes keep native behavior. New `claude --code` sessions receive a stable Workbench root, `CLAUDE.md`, state pointer, native UUID and a versioned policy snapshot, using Claude's supported flags and normal permission flow. No Codex sandbox or remote-control flags are passed to Claude.

Use `claude --code --upgrade` to review registered Claude Workbench sessions. Upgrades affect only their session-scoped managed loader and snapshots. They do not rewrite existing user/project `CLAUDE.md` files. The existing agent must explicitly read and acknowledge the attached revision. A `--notify` request is refused for Claude because an equivalent safe external queue adapter is not configured; the apply result provides a pasteable adoption prompt.

Historical Claude conversations that were not started through Workbench remain native. Use their native picker and an explicit in-session policy review rather than silently relabeling them as Workbench sessions or changing global rules. A full opt-in import/registration flow is a future adapter capability.

Claude prompt snapshots are a real compatibility boundary: changing `--append-system-prompt` at resume may not take effect until compaction. Workbench therefore does not claim that restarting with a changed flag hot-reloads existing rules. It also does not alter global instruction-file settings to force `AGENTS.md` support on older versions. A scoped `CLAUDE.md` works across the tested versions.

## Adapter contract for future engines

A new engine should supply capability-checked native launch/resume, metadata discovery, ID validation, instruction loading, and optional title/notification support. Discovery reports completeness. Selection retains exact IDs and paths. Unsupported operations are explicit, not mapped to another provider's unrelated flags.

Shared policy text should describe project outcomes, relevance and permissions. Provider-specific rendering should supply only mechanics: file name, native title mechanism, notification method and supported flags. Source-policy fingerprints stay separate from rendered host facts. Native transcripts, credentials, caches and provider memory stores remain under their original control.

## Distribution

The GitHub repository and portable archive distribute local CLI integration, source, tests and documentation. A native plugin may later distribute skills and connectors, but it does not automatically install shell functions on every host. Keep local installation explicit, versioned and reviewable. Optional dependencies retain their own licenses; the adapter code is MIT licensed.

## Primary references

- [Claude session management](https://code.claude.com/docs/en/sessions): native picker, search and all-project view.
- [Claude CLI reference](https://code.claude.com/docs/en/cli-reference): session IDs, append flags and prompt snapshot behavior.
- [Claude instructions/memory](https://code.claude.com/docs/en/memory): `CLAUDE.md`, `AGENTS.md` compatibility and precedence.
- [Official Python Agent SDK](https://github.com/anthropics/claude-agent-sdk-python): metadata adapter dependency.
- [Codex app-server](https://learn.chatgpt.com/docs/app-server): native metadata and same-ID resume.
- [Plugin packaging](https://developers.openai.com/plugins/build/plugins): optional future skill distribution.

See [shared project handoff](shared-project-handoff.md) for the opt-in first version and its ownership/recovery limits.
