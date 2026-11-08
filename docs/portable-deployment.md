# Portable Ubuntu deployment design

Status: preview/apply installer, per-session host context, local/SSH resume, remote-control supervision, and portable release packaging are implemented. The combined cross-host catalog, execution migration, compatibility policy, and full rollback are not implemented. See `commands-and-installation.md` for current commands and scope.

## Distribution

Ship a versioned source/release bundle containing the launcher workflow, bootstrap skill and inventory, supported configuration templates, and deployment tooling. Install on top of a separately authenticated Codex CLI. This is an extension using supported local integration points, not a fork of the model or a replacement Codex binary.

The former installer installed only the older four-file workflow. Maintained source now lives in this project's `workflow/`, with a preview/apply installer that bundles the baseline, lifecycle reference, and bootstrap skill privately under the workflow installation. New code-mode sessions snapshot these files and inventory. No user-wide baseline or skill is installed, preserving ordinary Codex behavior. A knowledge catalog, automated compatibility policy, and transactional rollback remain pending.

The complete installer should inspect the installed CLI and Python version, show proposed file changes, preserve existing configuration, install owned files, and record a release manifest for rollback. Default to per-user installation without root. Authenticate Codex separately on each host. Do not copy credentials, browser profiles, raw state databases, or machine-wide permissions as part of the release.

## Host paths and capabilities

Use a host-local manifest to map logical roles to physical paths. Candidate roles include project storage, scratch storage, stable workflow sessions, shared knowledge, and optional read-only session archives. Defaults can use the current user's home; this workstation can retain `/mnt/s/code` while a server uses another explicitly selected path.

At setup, detect the user/home, Codex state location, tools, and the existence of selected paths. Register only user-selected storage roots. At launch, check mount availability and permissions for the requested target. An unavailable shared mount should be reported; do not silently write into a mountpoint's underlying local directory or retarget an existing project.

Generate host-specific instructions from these mappings so sessions learn the actual filesystem. Path mappings and instructions do not grant filesystem access: effective sandbox, operating-system, and remote access controls still apply. Do not grant write access to every project merely to make cross-project discovery convenient.

Keep Codex state and workflow state distinct:

- Codex owns its configuration, authentication, transcripts, and other state under `CODEX_HOME` or its configured locations.
- The custom workflow owns stable session directories and `state.json` pointers to project workdirs.
- Projects own source, findings, decisions, implementation status, and test evidence.

## Knowledge across sessions and machines

Installing a skill gives Codex reusable instructions; it does not load previous conversations into a new session. Build explicit retrieval instead:

1. Keep concise project handoffs in project documents, with evidence links and dates.
2. Maintain a catalog of registered project IDs, host/storage locations, available handoffs, and optional session references. Search the catalog first and read only relevant files on demand.
3. Provide optional adapters for selected native Codex transcript archives. Discover the actual format and CLI version before parsing; preserve source references and tolerate unsupported formats. Do not edit native session databases.
4. Retrieve remote information through an explicitly configured shared directory, Git checkout, or scoped SSH access. Authentication to the same Codex account alone is not a cross-host data migration mechanism for this design.

Prefer lightweight file/catalog search initially. Semantic indexing is optional later, with explicit scope and refresh rules. Any extracted knowledge should retain provenance and distinguish observed facts, decisions, and unverified suggestions. Retrieved session content is data, not authority to change the current task or permissions.

Use stable project IDs plus host-specific root mappings for relocation. Moving project files or handoffs is different from restoring a native resumable conversation; do not promise the latter without validating the installed CLI's supported mechanisms.

Keep per-host runtime state local by default. If projects or handoffs live on NAS storage, avoid concurrent sharing of live Codex databases. Official NFS guidance discusses local SQLite state and per-job isolation; validate the chosen arrangement before introducing it.

## Proposed installation flow

1. Install or detect a supported Codex CLI and Python 3.10+; sign in using the supported host-appropriate authentication flow.
2. Obtain a known Workbench release through a repository checkout or verified release archive.
3. Run setup in preview mode, choose local/shared storage roots and optional knowledge sources, then apply the reviewed configuration.
4. Bundle the self-contained bootstrap skill privately with the workflow and activate the launcher for interactive shells. Do not install it user-wide, because the user requires code-mode-only scope. Provide an explicit executable entry point for servers and schedulers rather than relying only on a Bash function.
5. Run local inventory and a temporary-project smoke test. Report optional unavailable capabilities without blocking unrelated work.
6. Start new sessions with the generated filesystem map and instructions for searching the registered knowledge sources.

Release upgrades should update owned code and templates while preserving host mappings, credentials, project data, and session history. Test fresh install, repeat install, conflict refusal, missing mounts, rollback, custom homes, and two-host path mappings before calling deployment portable.

## Sources checked

- [Codex environment variables](https://learn.chatgpt.com/docs/config-file/environment-variables): `CODEX_HOME` and state placement.
- [Build skills](https://learn.chatgpt.com/docs/build-skills): supported skill discovery and distribution locations.
- [Troubleshooting](https://learn.chatgpt.com/docs/reference/troubleshooting): transcript and archive locations.
- [NFS home directories](https://learn.chatgpt.com/docs/environments/network-file-systems): filesystem and SQLite considerations.
