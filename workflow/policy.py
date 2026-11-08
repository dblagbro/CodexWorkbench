#!/usr/bin/env python3
"""Preview, attach, acknowledge, or roll back scoped policies for existing code sessions."""
import argparse
from datetime import datetime, timezone
import difflib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
BEGIN = '<!-- CODEX-WORKBENCH-POLICY:BEGIN -->'
END = '<!-- CODEX-WORKBENCH-POLICY:END -->'


class PolicyError(Exception):
    pass


def helper():
    return runpy.run_path(str(HERE / 'code-workflow.py'))


def sources():
    skill = HERE / 'skills/project-bootstrap'
    if not skill.is_dir():
        skill = HERE.parent / 'skills/project-bootstrap'
    data = {name: (HERE / name).read_bytes() for name in (
        'code-workflow.py', 'code-workflow-instructions.txt', 'code-baseline.txt',
        'lifecycle.md', 'coordinator.py', 'policy.py', 'handoff.py', 'project-entry.md')}
    for path in sorted(skill.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            data['skills/project-bootstrap/' + str(path.relative_to(skill))] = path.read_bytes()
    return data


def fingerprint(data):
    hashes = {name: hashlib.sha256(value).hexdigest() for name, value in sorted(data.items())}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(), hashes


def atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.is_file() else 0o600
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.policy-', delete=False) as stream:
        temporary = Path(stream.name)
        os.fchmod(stream.fileno(), mode)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def read_policy(folder):
    path = folder / 'workbench/policy.json'
    return json.loads(path.read_text()) if path.is_file() else {}


def engine_for(folder):
    state = json.loads((folder / 'state.json').read_text())
    engine = state.get('engine', 'codex')
    if engine not in ('codex', 'claude'):
        raise PolicyError('Unsupported session engine; no policy file was changed.')
    return engine


def instruction_path(folder):
    return folder / ('CLAUDE.md' if engine_for(folder) == 'claude' else 'AGENTS.md')


def guard_managed_paths(folder):
    for name in ('state.json', 'workbench', 'workbench/policy-revisions',
                 'workbench/policy-backups', 'workbench/policy.json', 'workbench/policy.lock'):
        if (folder / name).is_symlink():
            raise PolicyError('Refusing a redirected managed path: ' + name)


def validate_snapshot(folder, revision, expected_manifest=None):
    guard_managed_paths(folder)
    if not re_revision(revision):
        raise PolicyError('Attached policy revision is malformed.')
    final = folder / 'workbench/policy-revisions' / revision
    manifest_path = final / 'manifest.json'
    if final.is_symlink() or manifest_path.is_symlink() or not manifest_path.is_file():
        raise PolicyError('Attached policy snapshot is missing or redirected; review locally.')
    if expected_manifest and hashlib.sha256(manifest_path.read_bytes()).hexdigest() != expected_manifest:
        raise PolicyError('Policy snapshot manifest was edited; no update or acknowledgement performed.')
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('revision') != revision or not isinstance(manifest.get('snapshot_hashes'), dict):
        raise PolicyError('Policy snapshot manifest is invalid.')
    for name, digest in manifest['snapshot_hashes'].items():
        relative = Path(name)
        path = final / relative
        if relative.is_absolute() or '..' in relative.parts or path.is_symlink() or not path.resolve().is_relative_to(final.resolve()):
            raise PolicyError('Policy snapshot contains a redirected path.')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise PolicyError('Immutable policy snapshot was edited; preserve/reconcile local changes before upgrading.')
    source = final / 'sources'
    data = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    if fingerprint(data)[0] != revision:
        raise PolicyError('Policy snapshot source fingerprint is invalid.')
    return manifest


def block_bounds(text):
    if BEGIN not in text and END not in text:
        return None
    if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
        raise PolicyError('Managed policy markers are malformed; review locally before upgrading.')
    return text.index(BEGIN), text.index(END) + len(END)


def managed_block(folder, revision):
    instructions = folder / 'workbench/policy-revisions' / revision / 'instructions.md'
    command = shlex.join(['python3', str(HERE / 'policy.py'), '--session', str(folder)])
    return '\n'.join([
        BEGIN, '# Current code-mode policy', f'Policy revision: {revision}',
        f'Read {instructions} and state.json before substantive work or after resume.',
        'Preserve the existing objective, project path, thread identity, explicit title, authorization, and project-specific instructions.',
        'Apply only relevant lifecycle sections. Do not restart onboarding, replay commands, or add unrelated project ceremony.',
        'This revision updates Workbench mechanics; retain local rules and report material conflicts instead of silently overriding them.',
        f'Check for installed policy changes at a safe checkpoint with: {command} --check',
        'A newer installed policy is a review candidate, not authorization for new access, costs, deployment, or production changes.',
        END,
    ])


def resolve_session(session=None, project=None, thread=None, engine=None):
    module = helper()
    root = module['SESSION_ROOT'].resolve()
    if thread and engine == 'claude':
        native = runpy.run_path(str(HERE / 'claude.py'))
        try:
            identity = native['session_id'](thread)
        except native['ClaudeError'] as exc:
            raise PolicyError(str(exc)) from None
        matches = []
        for path in root.glob('*/state.json'):
            try:
                state = json.loads(path.read_text())
                if state.get('engine') == 'claude' and state.get('native_id') == identity:
                    matches.append(path.parent)
            except (OSError, ValueError):
                continue
        if len(matches) != 1:
            raise PolicyError('Expected exactly one registered Claude code session for that UUID; use --session.')
        session = matches[0]
    elif thread:
        native = runpy.run_path(str(HERE / 'resume.py'))
        try:
            native['thread_id'](thread)
            with native['NativeClient'](native['transport_command'](), timeout=12) as client:
                response = client.request('thread/read', {'threadId': thread, 'includeTurns': False})
        except (argparse.ArgumentTypeError, native['ResumeError']) as exc:
            raise PolicyError(str(exc)) from None
        metadata = response.get('thread', {}) if isinstance(response, dict) else {}
        if metadata.get('id') != thread or not metadata.get('cwd'):
            raise PolicyError('Native thread metadata did not match the requested ID.')
        session = Path(metadata['cwd'])
    if session is None:
        project = (project or Path.cwd()).expanduser().resolve()
        if (project / 'state.json').is_file() and project.parent == root:
            session = project
        else:
            candidates = []
            for state_file in root.glob('*/state.json'):
                try:
                    state = json.loads(state_file.read_text())
                    if Path(state.get('workdir', '')).resolve() == project and (engine is None or state.get('engine', 'codex') == engine):
                        candidates.append(state_file.parent)
                except (OSError, ValueError):
                    continue
            if len(candidates) != 1:
                raise PolicyError('Expected exactly one matching code session; use --thread or --session. Candidates: ' + ', '.join(str(p) for p in candidates))
            session = candidates[0]
    session = session.expanduser().resolve()
    if session.parent != root or not (session / 'state.json').is_file():
        raise PolicyError('Target is not a recognized code-mode stable session root.')
    guard_managed_paths(session)
    state = json.loads((session / 'state.json').read_text())
    if not isinstance(state, dict) or not isinstance(state.get('workdir'), str):
        raise PolicyError('Session state has no valid workdir pointer.')
    if not Path(state['workdir']).is_dir():
        raise PolicyError('The saved project workdir is unavailable; no upgrade was applied.')
    if engine and state.get('engine', 'codex') != engine:
        raise PolicyError('Selected session belongs to a different engine.')
    return session, state


def upgrade_candidates(include_current=False, engine='codex'):
    """Join native thread metadata to recognized workflow roots, without history."""
    native = runpy.run_path(str(HERE / 'resume.py'))
    data = sources()
    revision, _ = fingerprint(data)
    root = helper()['SESSION_ROOT'].resolve()
    if engine == 'claude':
        threads = []
        for path in root.glob('*/state.json'):
            try:
                state = json.loads(path.read_text())
                if state.get('engine') == 'claude' and state.get('native_id'):
                    threads.append({'id': state['native_id'], 'cwd': str(path.parent), 'name': state.get('name')})
            except (OSError, ValueError):
                continue
        metadata = {'threads': threads, 'truncated': False}
    else:
        try:
            with native['NativeClient'](native['transport_command'](), timeout=12) as client:
                metadata = native['list_threads'](client, limit=100, max_pages=10)
        except native['ResumeError'] as exc:
            raise PolicyError(str(exc)) from None
    rows = []
    for thread in metadata['threads']:
        folder = Path(thread.get('cwd') or '').resolve()
        if folder.parent != root or not (folder / 'state.json').is_file():
            continue
        try:
            folder, state = resolve_session(session=folder, engine=engine)
            report = review(folder, data, revision)
            status = report['status']
            if status == 'current':
                status = report['adoption_status']
                if status == 'acknowledged' and not include_current:
                    continue
            row = {'id': thread['id'], 'title': thread.get('name') or state.get('name') or folder.name,
                   'project': state['workdir'], 'session': str(folder), 'status': status,
                   'session_revision': report['session_revision'], 'installed_revision': revision}
        except (PolicyError, OSError, ValueError) as exc:
            row = {'id': thread.get('id'), 'title': thread.get('name') or folder.name,
                   'project': str(folder), 'session': str(folder), 'status': 'blocked', 'reason': str(exc)}
        rows.append(row)
    return {'sessions': rows, 'truncated': metadata['truncated'], 'installed_revision': revision,
            'scope': f'Recognized {engine} code sessions on this host; no message bodies read.'}


def review(folder, data, revision):
    guard_managed_paths(folder)
    override = folder / ('CLAUDE.local.md' if engine_for(folder) == 'claude' else 'AGENTS.override.md')
    if override.is_symlink():
        raise PolicyError('Session instruction override is redirected; review locally.')
    if override.is_file() and override.read_text().strip():
        raise PolicyError('Session instruction override requires local review before upgrading.')
    path = instruction_path(folder)
    if path.is_symlink():
        raise PolicyError('Refusing to replace a symlinked session instruction file.')
    text = path.read_text() if path.is_file() else ''
    current = read_policy(folder)
    if current.get('revision'):
        validate_snapshot(folder, current['revision'], current.get('snapshot_manifest_sha256'))
    bounds = block_bounds(text)
    if bounds:
        if not current.get('block_sha256'):
            raise PolicyError('Managed block has no ownership record; review it before replacing.')
        actual = hashlib.sha256(text[bounds[0]:bounds[1]].encode()).hexdigest()
        if actual != current['block_sha256']:
            raise PolicyError('Locally edited managed policy block detected; no changes applied.')
    elif current.get('revision'):
        raise PolicyError('Managed block was removed locally; no changes applied.')
    old_hashes = current.get('source_hashes', {})
    _, new_hashes = fingerprint(data)
    changed = sorted(name for name in set(old_hashes) | set(new_hashes) if old_hashes.get(name) != new_hashes.get(name))
    return {'session': str(folder), 'engine': engine_for(folder), 'installed_revision': revision, 'session_revision': current.get('revision'),
            'status': 'current' if current.get('revision') == revision else 'update_available',
            'adoption_status': current.get('adoption_status', 'not_attached'), 'changed_files': changed,
            'legacy_instructions_preserved': bounds is None and bool(text),
            'scope': 'Session policy only; project files, thread/history, permissions, services and MCP configuration are unchanged.'}


def build_snapshot(folder, revision, data):
    guard_managed_paths(folder)
    final = folder / 'workbench/policy-revisions' / revision
    if final.exists():
        validate_snapshot(folder, revision)
        return final
    final.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.staging-', dir=final.parent) as staging:
        context = Path(staging) / 'snapshot'
        module = helper()
        baseline = module['prepare_baseline'](folder, context)
        template = data['code-workflow-instructions.txt'].decode()
        engine = engine_for(folder)
        title_guidance = ('Use the available current-session title tool, such as codex_tui.set_thread_title with title only and no hard-coded thread ID.'
                          if engine == 'codex' else
                          'Use a supported current-session Claude title mechanism if exposed; otherwise request the native /rename command and keep title synchronization pending until confirmed. Never call Codex title tools for a Claude session.')
        for key, value in {'SESSION': folder, 'HELPER': HERE / 'code-workflow.py',
                           'POLICY_HELPER': HERE / 'policy.py',
                           'LAUNCH_COMMAND': engine + ' --code', 'TITLE_GUIDANCE': title_guidance,
                           'PROJECT_ROOT': module['PROJECT_ROOT'], 'SCRATCH_ROOT': module['SCRATCH_ROOT']}.items():
            template = template.replace('{{' + key + '}}', str(value))
        instructions = (template + '\n\n' + baseline).replace(str(context), str(final))
        (context / 'instructions.md').write_text(instructions)
        inventory = context / 'inventory.json'
        inventory.write_text(inventory.read_text().replace(str(context), str(final)))
        for name, content in data.items():
            destination = context / 'sources' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        hashes = {str(p.relative_to(context)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in context.rglob('*') if p.is_file()}
        (context / 'manifest.json').write_text(json.dumps({'revision': revision, 'snapshot_hashes': hashes}, indent=2) + '\n')
        context.rename(final)
    return final


def activate(folder, revision, source_hashes, thread=None):
    # Snapshot preparation may take time. Validate ownership again immediately
    # before reading the text we will replace, retaining fresh unmanaged edits.
    review(folder, {}, revision)
    agents = instruction_path(folder)
    old_agents = agents.read_bytes() if agents.is_file() else None
    policy_path = folder / 'workbench/policy.json'
    old_policy = policy_path.read_bytes() if policy_path.is_file() else None
    current = read_policy(folder)
    text = (old_agents or b'').decode()
    bounds = block_bounds(text)
    block = managed_block(folder, revision)
    updated = text[:bounds[0]] + block + text[bounds[1]:] if bounds else text + ('\n\n' if text else '') + block + '\n'
    backup = folder / 'workbench/policy-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup.mkdir(parents=True)
    (backup / agents.name).write_bytes(old_agents or b'')
    if old_policy is not None:
        (backup / 'policy.json').write_bytes(old_policy)
    history = list(current.get('history', []))
    if current.get('revision'):
        history.append(current['revision'])
    policy = {'revision': revision, 'engine': engine_for(folder), 'source_hashes': source_hashes,
              'snapshot_manifest_sha256': hashlib.sha256((folder / 'workbench/policy-revisions' / revision / 'manifest.json').read_bytes()).hexdigest(),
              'block_sha256': hashlib.sha256(block.encode()).hexdigest(),
              'adoption_status': 'pending', 'notification_status': 'not_requested',
              'history': history, 'tracking': current.get('tracking', 'review'),
              'updated_at': datetime.now(timezone.utc).isoformat()}
    if thread or current.get('thread_id'):
        policy['thread_id'] = thread or current['thread_id']
    if (agents.read_bytes() if agents.is_file() else None) != old_agents or (policy_path.read_bytes() if policy_path.is_file() else None) != old_policy:
        raise PolicyError('Session policy changed during preparation; retry the preview.')
    new_agents = updated.encode()
    new_policy = (json.dumps(policy, indent=2) + '\n').encode()
    try:
        atomic(agents, new_agents)
        atomic(policy_path, new_policy)
    except BaseException:
        diverged = False
        for path, old, new in ((agents, old_agents, new_agents), (policy_path, old_policy, new_policy)):
            present = path.read_bytes() if path.is_file() else None
            if present == new:
                if old is None:
                    path.unlink()
                else:
                    atomic(path, old)
            elif present != old:
                diverged = True
        if diverged:
            raise PolicyError('Interrupted policy write encountered concurrent edits; preserved them. Reconcile with backup at ' + str(backup)) from None
        raise
    return policy


def adoption_prompt(folder, revision):
    engine_flags = ['--engine', 'claude'] if engine_for(folder) == 'claude' else []
    return (f'At the next safe checkpoint, review the updated code-mode policy at '
            f'{folder}/workbench/policy-revisions/{revision}/instructions.md and the current project instructions. '
            'Preserve the ongoing objective, project path, native thread ID, explicit title and permissions. '
            'Do not restart onboarding or repeat commands. Apply only relevant changes; skip irrelevant lifecycle sections. '
            'Record any material conflicts instead of overriding local requirements. Then acknowledge this exact revision with '
            + shlex.join(['python3', str(HERE / 'policy.py'), *engine_flags, '--session', str(folder), '--ack', revision])
            + ' and concise --applicable, --skipped, or --conflict notes. Continue the existing authorized task.')


def acknowledge(folder, revision, applicable, skipped, conflicts):
    current = read_policy(folder)
    if revision != current.get('revision'):
        raise PolicyError('Cannot acknowledge a stale or unattached policy revision.')
    if not (applicable or skipped or conflicts):
        raise PolicyError('Record at least one applicability, skipped-section, or conflict note after reading the policy.')
    current.update(adoption_status='needs_decision' if conflicts else 'acknowledged',
                   applicability={'applicable': applicable, 'skipped': skipped, 'conflicts': conflicts},
                   acknowledged_at=datetime.now(timezone.utc).isoformat())
    atomic(folder / 'workbench/policy.json', (json.dumps(current, indent=2) + '\n').encode())
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group()
    target.add_argument('--session', type=Path)
    target.add_argument('--project', type=Path)
    target.add_argument('--thread')
    parser.add_argument('--host')
    parser.add_argument('--engine', choices=['codex', 'claude'])
    parser.add_argument('--list', action='store_true', help='List upgrade candidates without selecting or modifying them.')
    parser.add_argument('--all', action='store_true', help='Also show sessions already current and acknowledged.')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--preview', action='store_true', help='Preview only, including when choosing interactively.')
    parser.add_argument('--no-notify', action='store_true', help='Attach without queuing a review message.')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--diff', action='store_true')
    parser.add_argument('--notify', action='store_true')
    parser.add_argument('--rollback', help='An existing revision in this session; use --apply to activate it.')
    parser.add_argument('--ack')
    parser.add_argument('--applicable', action='append', default=[])
    parser.add_argument('--skipped', action='append', default=[])
    parser.add_argument('--conflict', action='append', default=[])
    args = parser.parse_args()
    if args.host:
        native = runpy.run_path(str(HERE / 'resume.py'))
        native['host_alias'](args.host)
        forward = []
        skip = False
        for item in sys.argv[1:]:
            if skip:
                skip = False
            elif item == '--host':
                skip = True
            elif not item.startswith('--host='):
                forward.append(item)
        command = 'exec env PATH="$HOME/.local/bin:$PATH" python3 "$HOME/.local/share/codex-code/policy.py" ' + shlex.join(forward)
        interactive = not (args.session or args.project or args.thread or args.list) and sys.stdin.isatty()
        os.execvp('ssh', ['ssh', '-t' if interactive else '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', '--', args.host, command])
    if args.preview and (args.apply or args.notify or args.ack or args.rollback):
        parser.error('--preview is read-only')
    if args.no_notify and args.notify:
        parser.error('--notify and --no-notify cannot be combined')
    if args.notify and not args.apply:
        parser.error('--notify requires --apply; preview never sends messages')
    if args.ack and (args.apply or args.rollback or args.notify or args.diff):
        parser.error('--ack cannot apply, roll back, or notify')
    if args.check and (args.apply or args.ack or args.rollback):
        parser.error('--check is read-only')
    try:
        if args.list or not (args.session or args.project or args.thread):
            if args.list and (args.apply or args.notify or args.ack or args.rollback):
                parser.error('--list is read-only; choose a session before applying')
            if not (args.session or args.project or args.thread) and (args.ack or args.rollback):
                parser.error('--ack and --rollback require an exact --session or --thread')
            candidates = upgrade_candidates(args.all, args.engine or 'codex')
            if args.list or not sys.stdin.isatty():
                print(json.dumps(candidates, indent=2))
                return 2 if args.apply else 0
            if not candidates['sessions']:
                print('No code sessions need an upgrade or adoption review.')
                return 0
            if candidates['truncated']:
                print('Native metadata reached its page limit; the picker may be incomplete.', file=sys.stderr)
            automatic_upgrade = not (args.preview or args.check or args.diff)
            if automatic_upgrade:
                print('Selection applies the policy; adoption requires acknowledgement.')
                if (args.engine or 'codex') == 'codex' and not args.no_notify:
                    print('A relevance-review message will be queued to the selected Codex thread.')
                if args.engine == 'claude':
                    print('Claude has no external queue; use the returned review prompt in that chat.')
            else:
                print('Preview only; selection will not change the session.')
            selected = runpy.run_path(str(HERE / 'session_picker.py'))['choose'](candidates['sessions'])
            if selected is None:
                print('Cancelled; no session changed.')
                return 0
            if selected['status'] == 'blocked':
                raise PolicyError(selected['reason'])
            args.thread = selected['id']
            if automatic_upgrade:
                args.apply = True
                args.notify = (args.engine or 'codex') == 'codex' and not args.no_notify
        folder, state = resolve_session(args.session, args.project, args.thread, args.engine)
        data = sources()
        revision, hashes = fingerprint(data)
        if args.rollback:
            if not re_revision(args.rollback):
                raise PolicyError('Rollback requires a complete policy fingerprint from this session.')
            manifest = folder / 'workbench/policy-revisions' / args.rollback / 'manifest.json'
            if not manifest.is_file():
                raise PolicyError('Rollback revision does not exist in this session.')
            revision = args.rollback
            old_source = manifest.parent / 'sources'
            data = {str(p.relative_to(old_source)): p.read_bytes() for p in old_source.rglob('*') if p.is_file()}
            actual, hashes = fingerprint(data)
            if actual != revision:
                raise PolicyError('Rollback snapshot source fingerprint does not match.')
        report = review(folder, data, revision)
        notification_thread = None
        if args.notify:
            if engine_for(folder) == 'claude':
                raise PolicyError('Claude has no configured external queue adapter. Apply without --notify and paste the returned adoption prompt into the existing Claude chat.')
            notification_thread = args.thread or read_policy(folder).get('thread_id')
            if not notification_thread:
                raise PolicyError('Notification requires --thread to identify the exact native conversation; no upgrade applied.')
            matched, _ = resolve_session(thread=notification_thread)
            if matched != folder:
                raise PolicyError('Native thread does not belong to the selected stable session; no upgrade applied.')
        if args.diff and report['session_revision']:
            old_source = folder / 'workbench/policy-revisions' / report['session_revision'] / 'sources'
            for name in report['changed_files']:
                if name.endswith(('.txt', '.md')):
                    before = (old_source / name).read_text() if (old_source / name).is_file() else ''
                    print(''.join(difflib.unified_diff(before.splitlines(True), data.get(name, b'').decode().splitlines(True), fromfile='session/' + name, tofile='installed/' + name)))
        if not (args.apply or args.ack):
            print(json.dumps(report, indent=2))
            return 0
        local = folder / 'workbench'
        local.mkdir(exist_ok=True)
        lock_fd = os.open(local / 'policy.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(lock_fd, 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            report = review(folder, data, revision)
            if args.ack:
                current = acknowledge(folder, args.ack, args.applicable, args.skipped, args.conflict)
            elif report['status'] == 'current':
                current = read_policy(folder)
            else:
                build_snapshot(folder, revision, data)
                current = activate(folder, revision, hashes, args.thread)
            if args.notify:
                message = adoption_prompt(folder, current['revision'])
                result = subprocess.run(['codex', 'queue', '--thread', notification_thread, '--message', message], capture_output=True, text=True, timeout=20)
                current['notification_status'] = 'queued' if result.returncode == 0 else 'failed'
                atomic(local / 'policy.json', (json.dumps(current, indent=2) + '\n').encode())
            report.update(status='attached', session_revision=current['revision'],
                          adoption_status=current['adoption_status'], notification_status=current['notification_status'],
                          adoption_prompt=adoption_prompt(folder, current['revision']))
            print(json.dumps(report, indent=2))
            return 1 if current['notification_status'] == 'failed' else 0
    except (PolicyError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f'Policy update stopped: {exc}\n')


def re_revision(value):
    return len(value) == 64 and all(c in '0123456789abcdef' for c in value)


if __name__ == '__main__':
    sys.exit(main())
