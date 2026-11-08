#!/usr/bin/env python3
"""Scoped code-mode project workflow with provider-specific native launches."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import runpy
import subprocess
import uuid

HOME = Path.home()
HERE = Path(__file__).resolve().parent
SETTINGS_FILE = Path(os.environ.get('CODEX_CODE_SETTINGS', str(HOME / '.config/codex-code/settings.json'))).expanduser()
SETTINGS = json.loads(SETTINGS_FILE.read_text()) if SETTINGS_FILE.exists() else {}


def setting_path(key, default):
    value = Path(SETTINGS.get(key, str(default))).expanduser()
    if not value.is_absolute():
        raise ValueError(f'{key} must be an absolute path or start with ~/.')
    return value


SESSION_ROOT = setting_path('session_root', HOME / '.local/share/codex-work/sessions')
PROJECT_ROOT = setting_path('project_root', '/mnt/s/code')
SCRATCH_ROOT = setting_path('scratch_root', HOME / 'scratch')
CHROME = SETTINGS.get('chrome', False)


def save_state(folder, state):
    temporary = folder / 'state.json.tmp'
    temporary.write_text(json.dumps(state, indent=2) + '\n')
    temporary.replace(folder / 'state.json')


def slug(name):
    value = re.sub(r'[^A-Za-z0-9._-]+', '-', name.strip()).strip('.-_')
    if not value or value in {'.', '..'} or len(value) > 100:
        raise ValueError('Use a meaningful name of at most 100 filename characters.')
    return value


def load_session(folder):
    folder = folder.resolve()
    if folder.parent != SESSION_ROOT.resolve():
        raise ValueError('Expected a session directory created by the code-mode launcher.')
    return folder, json.loads((folder / 'state.json').read_text())


def plan_title(state, project):
    if state.get('display_title_mode') == 'custom':
        return
    desired = project.name
    state['desired_title'] = desired
    state['display_title_mode'] = 'project'
    if state.get('display_title') != desired:
        state['title_sync'] = 'pending'


def adopt(folder, project):
    """Point at an explicitly selected existing project, without moving its files."""
    folder, state = load_session(folder)
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise ValueError('Existing project directory is missing; no state changed.')
    state.update(workdir=str(project), kind='project', name=project.name)
    plan_title(state, project)
    save_state(folder, state)
    print(f'Work directory: {project}')
    print('Display title synchronization: ' + state.get('title_sync', 'unchanged'))


def acknowledge_title(folder, title, custom=False, follow_folder=False):
    """Record a successful owner-tool rename; this command does not rename the agent."""
    folder, state = load_session(folder)
    if not title.strip() or len(title) > 200 or any(ord(c) < 32 for c in title):
        raise ValueError('Use a nonempty display title of at most 200 characters without controls.')
    if follow_folder:
        if state.get('kind') != 'project' or title != Path(state['workdir']).name:
            raise ValueError('Folder-following title must match the current project basename.')
        state.update(desired_title=title, display_title_mode='project')
    elif custom:
        state.update(desired_title=title, display_title_mode='custom')
    elif state.get('desired_title') != title:
        raise ValueError('Title does not match the pending project title; no acknowledgement recorded.')
    state.update(display_title=title, title_sync='synced')
    if state.get('engine', 'codex') == 'claude' and state.get('native_id'):
        state['display_title_thread_id'] = state['native_id']
    elif os.environ.get('CODEX_THREAD_ID'):
        state['display_title_thread_id'] = os.environ['CODEX_THREAD_ID']
    save_state(folder, state)
    print(f'Verified display title recorded: {title}')


def finish(folder, name=None, one_off=False):
    folder, state = load_session(folder)
    source = Path(state['workdir'])
    if source.is_symlink() or not source.is_dir():
        raise ValueError('Work directory is missing or is a symlink; inspect it first.')
    if source != folder / 'draft' and source.parent.resolve() not in (
            PROJECT_ROOT.resolve(), SCRATCH_ROOT.resolve()):
        raise ValueError('Refusing to move a workdir outside managed project/scratch storage.')
    if (source / '.git').is_file() or (source / '.git/worktrees').exists():
        raise ValueError('Refusing to move a repository with linked worktrees or an external git directory.')
    target = (SCRATCH_ROOT / folder.name) if one_off else (PROJECT_ROOT / slug(name))
    if source == target:
        if not one_off:
            plan_title(state, target)
            save_state(folder, state)
        print(f'Already using {target}')
        return
    if target.exists() or target.is_symlink():
        raise FileExistsError(f'{target} already exists. Choose another name; no files moved.')
    target.parent.mkdir(parents=True, exist_ok=True)
    # copytree refuses existing destinations. Keep the source intact if copying fails.
    # Copying rather than renaming also works across the local disk and NAS.
    handoff = runpy.run_path(str(HERE / 'handoff.py'))
    try:
        with handoff['move_guard'](source) as shared:
            managed_folder = source / '.workbench/handoff'
            def ignore_transaction(path, names):
                return ['lock'] if Path(path) == managed_folder and 'lock' in names else []
            shutil.copytree(source, target, symlinks=True, ignore=ignore_transaction)
            if shared:
                handoff['rebind_copy'](target, shared)
            elif not one_off and state.get('kind') in ('draft', 'one-off') and SETTINGS.get('project_bootstrap', True):
                handoff['initialize'](target, apply=True)
            state.update(workdir=str(target), kind='one-off' if one_off else 'project', name=name)
            if not one_off:
                plan_title(state, target)
            else:
                for key in ('desired_title', 'display_title', 'display_title_mode', 'title_sync', 'display_title_thread_id'):
                    state.pop(key, None)
            save_state(folder, state)
            shutil.rmtree(source)
    except Exception as exc:
        # Preserve the existing copy-failure contract and identify both paths.
        raise RuntimeError(f'Placement could not finish: {exc}. Inspect source {source} and destination {target}; neither is automatically cleaned up.') from None
    print(f'Work directory: {target}')
    if state.get('title_sync') == 'pending':
        print('Display title pending: use the current-session title tool, then acknowledge it.')


def codex_command():
    executable = shutil.which('codex')
    if executable is None:
        raise RuntimeError('codex executable was not found on PATH.')
    return executable


def claude_command():
    executable = shutil.which('claude')
    if executable is None:
        local = HOME / '.local/bin/claude'
        executable = str(local) if local.is_file() and os.access(local, os.X_OK) else None
    if executable is None:
        raise RuntimeError('claude executable was not found; install/authenticate Claude separately.')
    try:
        result = subprocess.run([executable, '--help'], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError('Cannot verify the installed Claude launch capabilities.') from None
    if result.returncode or not all(flag in result.stdout for flag in ('--session-id', '--add-dir', '--append-system-prompt')):
        raise RuntimeError('Installed Claude lacks required code-mode flags; no session was created.')
    return executable


def access_args():
    args = ['--add-dir', str(SCRATCH_ROOT),
            '--sandbox', 'workspace-write', '--ask-for-approval', 'on-request',
            '-c', 'sandbox_workspace_write.network_access=true']
    if not CHROME:
        # Also disables an inherited server with this workflow's server name.
        args += ['-c', 'mcp_servers.workstation_chrome.enabled=false']
    if PROJECT_ROOT.is_dir():
        args += ['--add-dir', str(PROJECT_ROOT)]
    else:
        print(f'Project storage unavailable: {PROJECT_ROOT}. Draft remains local.', file=sys.stderr)
    return args


def ensure_remote_control():
    if not SETTINGS.get('remote_control', True):
        return
    # Use the managed daemon so code-mode threads are available to remote clients.
    # Never force a restart of an existing daemon or echo authentication material.
    try:
        result = subprocess.run([sys.executable, str(HERE / 'remote-control.py'),
                                 'ensure', '--timeout-seconds', '10'],
                                capture_output=True, text=True, timeout=75)
        report = json.loads(result.stdout)
        if report.get('status') not in ('ready', 'already_checking'):
            print('Remote control is not ready. Check ~/.local/state/codex-code/remote-control-status.json.', file=sys.stderr)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print('Remote-control health check failed; local work can continue. Inspect its status file.', file=sys.stderr)


def resume(extra):
    executable = codex_command()
    # Native resume owns restoration. Do not inject code-mode access into other sessions.
    os.execv(executable, [executable, 'resume'] + extra)


def prepare_baseline(folder, context=None):
    """Snapshot code-mode instructions and names-only host data into this session."""
    context = context or folder / 'workbench'
    context.mkdir()
    shutil.copy2(HERE / 'lifecycle.md', context / 'lifecycle.md')
    shutil.copy2(HERE / 'coordinator.py', context / 'coordinator.py')
    shutil.copytree(HERE / 'skills/project-bootstrap', context / 'skills/project-bootstrap',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    inventory_script = context / 'skills/project-bootstrap/scripts/inventory.py'
    module = runpy.run_path(str(inventory_script))
    state = json.loads((folder / 'state.json').read_text())
    engine = state.get('engine', 'codex')
    codex_home = Path(os.environ.get('CODEX_HOME', str(HOME / '.codex'))).expanduser()
    claude_home = Path(os.environ.get('CLAUDE_CONFIG_DIR', str(HOME / '.claude'))).expanduser()
    report = module['inventory'](Path(state['workdir']), codex_home)
    # Only the CLI is probed automatically. Optional tools remain task-driven.
    commands = {
        'codex_version': ['codex', '--version'],
        'codex_help': ['codex', '--help'],
        'codex_features': ['codex', 'features', 'list'],
    } if engine == 'codex' else {
        'claude_version': ['claude', '--version'], 'claude_help': ['claude', '--help']}
    report['engine'] = engine
    report['probes'] = {name: module['probe'](args) for name, args in commands.items()}
    report['workflow_paths'] = {key: str(value) for key, value in {
        'project_root': PROJECT_ROOT, 'scratch_root': SCRATCH_ROOT,
        'session_root': SESSION_ROOT, 'current_session': folder,
    }.items()}
    report['instruction_files_present'] = [str(p) for p in (
        codex_home / 'AGENTS.md', codex_home / 'AGENTS.override.md', HOME / 'AGENTS.md',
        claude_home / 'CLAUDE.md',
    ) if p.is_file()]
    report['knowledge_sources'] = {
        'project_findings_root': str(PROJECT_ROOT),
        'workflow_records_root': str(SESSION_ROOT),
        'native_transcripts': str(codex_home / 'sessions') if engine == 'codex' else str(claude_home / 'projects'),
        'native_archives': str(codex_home / 'archived_sessions') if engine == 'codex' else None,
        'scope': 'Locations only. Search relevant project records first; do not bulk-load transcripts.',
        'limits': 'Remote sources require explicit host mappings/access. No cross-session catalog is implemented.',
    }
    report['coordinator'] = {
        'kb_adapter': str(context / 'coordinator.py'),
        'credential_references_present': [str(p) for p in (
            HOME / '.coordinator/coordinator.env', HOME / '.claude/coordinator.env') if p.is_file()],
        'kb_access': 'check with adapter probe; not inferred from file presence',
        'vault_access': 'not_configured; requires verified deployment, per-host enrollment and scoped grants',
    }
    report['storage'] = {}
    for name, path in [('project_root', PROJECT_ROOT), ('scratch_root', SCRATCH_ROOT)]:
        entry = {'exists': path.is_dir(), 'path': str(path)}
        if path.is_dir():
            try:
                entry['free_bytes'] = shutil.disk_usage(path).free
            except OSError:
                entry['free_bytes'] = None
        report['storage'][name] = entry
    (context / 'inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    baseline = (HERE / 'code-baseline.txt').read_text()
    return baseline.replace('{{CONTEXT}}', str(context))


def launch(prompt, one_off=False, engine='codex'):
    if engine not in ('codex', 'claude'):
        raise ValueError('Unsupported code-mode engine.')
    executable = claude_command() if engine == 'claude' else codex_command()
    if engine == 'codex':
        ensure_remote_control()
    SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-')
    folder = Path(tempfile.mkdtemp(prefix=stamp, dir=SESSION_ROOT))
    draft = folder / 'draft'
    draft.mkdir()
    state = dict(workdir=str(draft), kind='draft', name=None, engine=engine)
    if engine == 'claude':
        state['native_id'] = str(uuid.uuid4())
    save_state(folder, state)
    if one_off:
        finish(folder, one_off=True)
    policy = runpy.run_path(str(HERE / 'policy.py'))
    data = policy['sources']()
    revision, hashes = policy['fingerprint'](data)
    policy['build_snapshot'](folder, revision, data)
    policy['activate'](folder, revision, hashes)
    instruction_file = 'CLAUDE.md' if engine == 'claude' else 'AGENTS.md'
    message = (f'Follow {instruction_file} in this session directory. This is a new coding task; '
               'resolve the project/one-off location using that workflow.\n\n'
               + (prompt or 'Ask what I would like to build or test.'))
    if engine == 'codex':
        args = [executable, '--cd', str(folder)] + access_args()
    else:
        # Claude has no Codex --cd/sandbox flags. Keep its normal permissions.
        args = [executable, '--session-id', state['native_id'], '--append-system-prompt',
                f'This explicitly opted-in code-mode session uses {folder / instruction_file}. Read it before work; preserve project-specific instructions and native permissions.']
        for directory in (SCRATCH_ROOT, PROJECT_ROOT):
            if directory.is_dir():
                args += ['--add-dir', str(directory)]
        # --add-dir accepts multiple paths; terminate options before the prompt.
        args += ['--']
        os.chdir(folder)
    print(f'Session: {folder}\nDrafts stay saved until explicitly moved or deleted.', flush=True)
    os.execv(executable, args + [message])


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'resume':
        resume(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description='Start an automatically organized Codex coding session.')
    sub = parser.add_subparsers(dest='action', required=True)
    start = sub.add_parser('start')
    start.add_argument('--engine', choices=['codex', 'claude'], default='codex')
    start.add_argument('--one-off', action='store_true')
    start.add_argument('prompt', nargs='*')
    move = sub.add_parser('place')
    move.add_argument('--session', type=Path, required=True)
    choice = move.add_mutually_exclusive_group(required=True)
    choice.add_argument('--name')
    choice.add_argument('--one-off', action='store_true')
    existing = sub.add_parser('adopt')
    existing.add_argument('--session', type=Path, required=True)
    existing.add_argument('--project', type=Path, required=True)
    title = sub.add_parser('ack-title')
    title.add_argument('--session', type=Path, required=True)
    title.add_argument('--title', required=True)
    title_mode = title.add_mutually_exclusive_group()
    title_mode.add_argument('--custom', action='store_true', help='Record an explicitly chosen custom title, preserved across folder renames.')
    title_mode.add_argument('--follow-folder', action='store_true', help='Return to matching the folder after an explicit user request.')
    args = parser.parse_args()
    if args.action == 'start':
        launch(' '.join(args.prompt), args.one_off, args.engine)
    elif args.action == 'place':
        finish(args.session, args.name, args.one_off)
    elif args.action == 'adopt':
        adopt(args.session, args.project)
    else:
        acknowledge_title(args.session, args.title, args.custom, args.follow_folder)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc))
