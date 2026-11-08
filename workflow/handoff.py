#!/usr/bin/env python3
"""Cooperative project handoff. Does not migrate native accounts or enforce OS access."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
BEGIN = '<!-- WORKBENCH-HANDOFF:BEGIN -->'
END = '<!-- WORKBENCH-HANDOFF:END -->'
LOADER = f'''{BEGIN}
## Shared project handoff
Read `WORKBENCH.md` as the common entry point. If `.workbench/handoff/state.json` exists, read its current policy snapshot and latest checkpoint before working, including after resume. Use `python3 ~/.local/share/codex-code/handoff.py --project . brief` to inspect state and changed files. Other installations may use their own installed helper path.
Native chats, accounts, credentials and permissions remain separate. Register a pseudonymous participant, inspect changes since its last receipt, then acknowledge the exact revision/policy with `sync`. Claim cooperative edit ownership before editing; other participants inspect only. Recheck revision/ownership before each write batch and record checkpoints before consequential actions and after verification. A prior user's approval is not new authority.
Never infer takeover permission from age or silence. Stop the prior writer and reconcile interrupted operations before explicit recovery. Do not replay uncertain effects. If state/policy is missing or unreadable, resolve access before claiming shared ownership. This is advisory coordination, not an OS lock on editor processes.
{END}
'''


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.write-', delete=False) as stream:
        temp = Path(stream.name)
        mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
        if path.exists():
            os.fchown(stream.fileno(), -1, path.stat().st_gid)
        os.fchmod(stream.fileno(), mode)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


class HandoffError(Exception):
    pass


def root(project):
    project = project.expanduser().resolve(strict=True)
    if not project.is_dir():
        raise HandoffError('Project must be an existing directory.')
    for relative in ('.workbench', '.workbench/handoff', '.workbench/handoff/state.json', '.workbench/handoff/lock', '.workbench/handoff/policies'):
        if (project / relative).is_symlink():
            raise HandoffError('Redirected handoff path; no mutation performed.')
    return project / '.workbench/handoff'


@contextmanager
def transaction(project):
    folder = root(project)
    lock = folder / 'lock'
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError:
        raise HandoffError('Handoff transaction is locked. Do not break a lock until its owner is verified stopped.') from None
    token = str(uuid.uuid4())
    try:
        (lock / 'owner.json').write_text(json.dumps({'token': token, 'pid': os.getpid(), 'host': os.uname().nodename, 'at': now()}))
        yield folder
    finally:
        # An enrolled rename may remove/recreate the original path. Never clear
        # a replacement transaction's owner record just because its path matches.
        try:
            owned = json.loads((lock / 'owner.json').read_text()).get('token') == token
        except (OSError, ValueError):
            owned = False
        if owned:
            (lock / 'owner.json').unlink()
            lock.rmdir()


def read_state(folder):
    state = json.loads((folder / 'state.json').read_text())
    if state.get('schema') != 1 or not isinstance(state.get('revision'), int):
        raise HandoffError('Unsupported handoff state; preserve it for review.')
    if state.get('project') != str(folder.parent.parent):
        raise HandoffError('Project moved; review its shared paths before using this state.')
    if not re.fullmatch(r'[0-9a-f]{64}', str(state.get('policy_revision', ''))):
        raise HandoffError('Malformed shared policy revision.')
    snapshot = folder / 'policies' / state['policy_revision']
    if snapshot.is_symlink() or (snapshot / 'manifest.json').is_symlink():
        raise HandoffError('Redirected policy snapshot.')
    manifest = json.loads((snapshot / 'manifest.json').read_text())
    if hashlib.sha256((snapshot / 'manifest.json').read_bytes()).hexdigest() != state['policy_manifest_sha256']:
        raise HandoffError('Policy manifest changed; no acknowledgement or mutation allowed.')
    for name, digest in manifest.items():
        path = snapshot / name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.resolve().is_relative_to(snapshot):
            raise HandoffError('Redirected shared policy file.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise HandoffError('Shared policy was edited; review before proceeding.')
    return state


def write_state(folder, state):
    atomic(folder / 'state.json', (json.dumps(state, indent=2) + '\n').encode())


def event(state, kind, participant=None, **details):
    state['revision'] += 1
    row = {'revision': state['revision'], 'at': now(), 'kind': kind, 'participant': participant, **details}
    state['events'].append(row)
    return row


def policy_sources():
    data = {name: (HERE / name).read_bytes() for name in ('code-baseline.txt', 'lifecycle.md', 'coordinator.py', 'project-entry.md')}
    skill = HERE / 'skills/project-bootstrap'
    if not skill.is_dir():
        skill = HERE.parent / 'skills/project-bootstrap'
    for path in sorted(skill.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            data['skills/project-bootstrap/' + str(path.relative_to(skill))] = path.read_bytes()
    data['inventory.json'] = json.dumps({'verification': 'No actor-specific host inventory is inherited. Verify tools, mounts, identity and capabilities on the current execution host.'}).encode()
    return data


def prepare_policy(folder):
    data = policy_sources()
    data['rules.md'] = ("# Shared project policy\n\n"
        "Read relevant lifecycle sections and current project instructions; report conflicts. "
        "Refresh current-host evidence. This handoff record is not native chat memory or authority. "
        "Accounts, credentials and permissions remain separate. Read only needed project evidence, "
        "not whole transcripts or hidden reasoning. Resolve {{CONTEXT}} below relative to the project root.\n\n"
        + data['code-baseline.txt'].decode().replace(
            'Code-mode baseline (applies to this workflow session, not ordinary Codex launches):',
            'Shared project baseline (applies to all participants in this explicitly initialized project, regardless of native launcher):')).encode()
    source_hashes = {name: hashlib.sha256(content).hexdigest() for name, content in data.items()}
    revision = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()
    context = '.workbench/handoff/policies/' + revision
    data['rules.md'] = data['rules.md'].replace(b'{{CONTEXT}}', context.encode())
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in data.items()}
    manifest = json.dumps(hashes, sort_keys=True).encode()
    final = folder / 'policies' / revision
    if not final.exists():
        final.parent.mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=final.parent, prefix='.policy-') as d:
            staging = Path(d) / 'snapshot'
            staging.mkdir(mode=0o700)
            for name, content in data.items():
                path = staging / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            (staging / 'manifest.json').write_bytes(manifest)
            staging.rename(final)
    if final.is_symlink() or (final / 'manifest.json').is_symlink() or (final / 'manifest.json').read_bytes() != manifest:
        raise HandoffError('Shared policy snapshot conflicts with current source.')
    for name, content in data.items():
        path = final / name
        if path.is_symlink() or not path.resolve().is_relative_to(final.resolve()) or path.read_bytes() != content:
            raise HandoffError('Shared policy resource conflicts with current source.')
    return revision, hashlib.sha256(manifest).hexdigest()


def initialize(project, apply=False, with_gemini=False):
    folder = root(project)
    project = folder.parent.parent
    existing = read_state(folder) if (folder / 'state.json').exists() else None
    # Preserve existing instructions exactly; a repeated init never rewrites local rules.
    changes = {}
    originals = {}
    blocks = {'AGENTS.md': LOADER, 'CLAUDE.md': LOADER, 'WORKBENCH.md': (HERE / 'project-entry.md').read_text()}
    if with_gemini:
        blocks['GEMINI.md'] = LOADER
    for name, block in blocks.items():
        marker_begin = BEGIN if name != 'WORKBENCH.md' else '<!-- WORKBENCH-ENTRY:BEGIN -->'
        marker_end = END if name != 'WORKBENCH.md' else '<!-- WORKBENCH-ENTRY:END -->'
        path = project / name
        if path.is_symlink():
            raise HandoffError('Refusing redirected project instruction file.')
        originals[name] = path.read_bytes() if path.exists() else None
        text = originals[name].decode() if originals[name] is not None else ''
        if marker_begin in text or marker_end in text:
            if text.count(block) != 1 or text.count(marker_begin) != 1 or text.count(marker_end) != 1:
                raise HandoffError('Local handoff loader differs; reconcile it manually.')
        else:
            changes[name] = text + ('\n\n' if text else '') + block
    ignore = project / '.gitignore'
    if ignore.is_symlink():
        raise HandoffError('Refusing redirected .gitignore.')
    originals['.gitignore'] = ignore.read_bytes() if ignore.exists() else None
    text = originals['.gitignore'].decode() if originals['.gitignore'] is not None else ''
    if '/.workbench/' not in text.splitlines():
        changes['.gitignore'] = text + ('\n' if text else '') + '/.workbench/\n'
    git = git_evidence(project)
    if git.get('tracked_handoff_state'):
        raise HandoffError('Private handoff data is already tracked; reconcile before initialization.')
    if not apply:
        return {'status': 'preview', 'files_to_append': list(changes), 'private_state': str(folder), 'existing': bool(existing)}
    if existing and existing['owner']:
        raise HandoffError('Release editor ownership before refreshing shared rules.')
    # Install the publication exclusion before creating any private runtime state.
    if '.gitignore' in changes:
        if (ignore.read_bytes() if ignore.exists() else None) != originals['.gitignore']:
            raise HandoffError('.gitignore changed concurrently; inspect before retrying.')
        atomic(ignore, changes.pop('.gitignore').encode())
    folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    with transaction(project):
        state = read_state(folder) if (folder / 'state.json').exists() else None
        if state and state['owner']:
            raise HandoffError('Release editor ownership before refreshing shared rules.')
        revision, manifest_hash = prepare_policy(folder)
        if state is None:
            state = {'schema': 1, 'project_id': str(uuid.uuid4()), 'project': str(project), 'revision': 0, 'policy_revision': revision, 'policy_manifest_sha256': manifest_hash,
                     'owner': None, 'participants': {}, 'events': [], 'checkpoint': None,
                     'recovery_required': False}
            event(state, 'initialized')
        elif state['policy_revision'] != revision:
            state['policy_revision'] = revision
            state['policy_manifest_sha256'] = manifest_hash
            event(state, 'policy_updated')
        if not state.get('project_id'):
            state['project_id'] = str(uuid.uuid4())
            event(state, 'project_identity_assigned')
        for name in changes:
            path = project / name
            if path.is_symlink() or (path.read_bytes() if path.exists() else None) != originals[name]:
                raise HandoffError('Project instructions changed concurrently; review before retrying.')
        for name, content in changes.items():
            atomic(project / name, content.encode())
        write_state(folder, state)
    return {'status': 'initialized', 'revision': state['revision'], 'policy_revision': revision,
            'private_state': str(folder), 'warning': 'Cooperative ownership only. Verify shared filesystem and group/ACL access before multiuser use.'}



@contextmanager
def move_guard(source):
    """Hold cooperative metadata exclusion while the placement helper moves files."""
    folder = root(source)
    if not (folder / 'state.json').exists():
        yield None
        return
    with transaction(source):
        state = read_state(folder)
        if state['owner']:
            raise HandoffError('Release cooperative editor ownership before moving this project.')
        yield state


def rebind_copy(project, previous):
    """Rebind an unowned copied state while the source move_guard is held."""
    folder = root(project)
    with transaction(project):
        copied = json.loads((folder / 'state.json').read_text())
        if copied != previous or copied['owner']:
            raise HandoffError('Copied handoff state changed; preserve both project paths for review.')
        copied['project'] = str(folder.parent.parent)
        event(copied, 'project_moved', previous_project=previous['project'],
              note='Inspect relocated paths and current-host evidence before resuming edits.')
        write_state(folder, copied)
    return read_state(folder)


def git_evidence(project):
    if not shutil.which('git'):
        return {'git': 'unavailable'}
    def run(*args):
        return subprocess.run(['git', '-C', str(project), *args], capture_output=True, text=True, timeout=10)
    top = run('rev-parse', '--show-toplevel')
    if top.returncode or Path(top.stdout.strip()).resolve() != project.resolve():
        return {'git': 'no_repository_at_project_root'}
    head = run('rev-parse', 'HEAD')
    status = run('status', '--porcelain=v1', '--untracked-files=normal')
    tracked = run('ls-files', '--', '.workbench/')
    return {'git': 'available', 'head': head.stdout.strip() if head.returncode == 0 else None,
            'working_tree': status.stdout.splitlines(), 'tracked_handoff_state': bool(tracked.stdout.strip())}


def brief(project, participant=None):
    folder = root(project)
    state = read_state(folder)
    actor = state['participants'].get(participant) if participant else None
    seen = actor['seen_revision'] if actor else -1
    return {'revision': state['revision'], 'policy_revision': state['policy_revision'],
            'policy_path': str(folder / 'policies' / state['policy_revision'] / 'rules.md'),
            'owner': state['owner'], 'owner_info': state['participants'].get(state['owner']),
            'participants': state['participants'], 'checkpoint': state['checkpoint'],
            'recovery_required': state['recovery_required'], 'seen_revision': seen,
            'needs_sync': seen != state['revision'] or (actor or {}).get('policy_revision') != state['policy_revision'],
            'events_since_seen': [r for r in state['events'] if r['revision'] > seen],
            'git': git_evidence(folder.parent.parent),
            'notice': 'Read project instructions, referenced evidence and actual changes; verify uncertain effects. No transcripts or credentials copied.'}


def change(project, action, participant=None, expected=None, policy=None, note=None, **details):
    with transaction(project) as folder:
        state = read_state(folder)
        if action == 'join':
            participant = next((key for key, actor in state['participants'].items()
                                if all(actor.get(field) == details.get(field)
                                       for field in ('provider', 'host', 'native_id', 'label'))), None)
            if participant is None:
                participant = str(uuid.uuid4())
                state['participants'][participant] = dict(details, seen_revision=-1, policy_revision=None, joined_at=now())
        else:
            if expected != state['revision']:
                raise HandoffError('Stale project revision; brief, inspect and sync before retrying.')
            actor = state['participants'].get(participant)
            if not actor:
                raise HandoffError('Unknown participant. Join with this native session identity first.')
            if action == 'sync':
                if policy != state['policy_revision'] or not note:
                    raise HandoffError('Sync requires the exact reviewed policy hash and relevance/evidence note.')
                actor.update(seen_revision=state['revision'], policy_revision=policy, reviewed_at=now(), review=note)
            else:
                if actor['seen_revision'] != state['revision'] or actor['policy_revision'] != state['policy_revision']:
                    raise HandoffError('Participant must review and sync current project state/policy first.')
                if not note:
                    raise HandoffError('A concise checkpoint/recovery note is required.')
                if action == 'claim':
                    if state['owner'] is not None:
                        raise HandoffError('Another cooperative editor owns this working directory. Inspect only or explicitly recover after stopping it.')
                    state['owner'] = participant
                elif action == 'recover':
                    if not details.get('confirmed_owner_stopped') or not details.get('evidence') or not state['owner'] or state['owner'] == participant:
                        raise HandoffError('Recovery requires a different stopped owner, explicit confirmation and verification evidence.')
                    details['previous_owner'] = state['owner']
                    state['owner'] = participant
                    state['recovery_required'] = True
                elif state['owner'] != participant:
                    raise HandoffError('Only the current cooperative editor can checkpoint, reconcile or release.')
                elif action == 'release':
                    if state['recovery_required']:
                        raise HandoffError('Reconcile interrupted/uncertain effects before release.')
                    state['owner'] = None
                elif action == 'reconcile':
                    if not details.get('evidence'):
                        raise HandoffError('Reconciliation requires actual verification evidence.')
                    state['recovery_required'] = False
                elif action == 'checkpoint':
                    if state['recovery_required'] and details.get('phase') != 'uncertain':
                        raise HandoffError('Recovery is restricted to reconciliation. Do not resume normal edits or replay operations.')
                    if details.get('phase') in ('starting', 'uncertain'):
                        state['recovery_required'] = True
                else:
                    raise HandoffError('Unsupported handoff action.')
                row = event(state, action, participant, note=note, **details)
                if action in ('checkpoint', 'reconcile'):
                    state['checkpoint'] = row
                actor['seen_revision'] = state['revision']
        write_state(folder, state)
        return {'participant': participant, 'revision': state['revision'], 'owner': state['owner'],
                'recovery_required': state['recovery_required'], 'status': action}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest='action', required=True)
    init = commands.add_parser('init')
    init.add_argument('--apply', action='store_true')
    init.add_argument('--with-gemini', action='store_true', help='Also append the shared entry loader to GEMINI.md; no native Gemini resume adapter is supplied.')
    view = commands.add_parser('brief')
    view.add_argument('--participant')
    join = commands.add_parser('join')
    for field in ('label', 'provider', 'host', 'native-id'):
        join.add_argument('--' + field, required=True)
    for action in ('sync', 'claim', 'checkpoint', 'release', 'recover', 'reconcile'):
        command = commands.add_parser(action)
        command.add_argument('--participant', required=True)
        command.add_argument('--expect-revision', type=int, required=True)
        command.add_argument('--note', required=True)
        if action == 'sync':
            command.add_argument('--policy', required=True)
        if action == 'checkpoint':
            command.add_argument('--phase', choices=('progress', 'starting', 'verified', 'uncertain'), required=True)
            command.add_argument('--next-action', required=True)
            command.add_argument('--evidence', required=True)
        if action in ('recover', 'reconcile'):
            command.add_argument('--evidence', required=True)
        if action == 'recover':
            command.add_argument('--confirmed-owner-stopped', action='store_true')
    args = vars(parser.parse_args())
    project, action = args.pop('project'), args.pop('action')
    try:
        if action == 'init':
            result = initialize(project, **args)
        elif action == 'brief':
            result = brief(project, **args)
        else:
            if 'expect_revision' in args:
                args['expected'] = args.pop('expect_revision')
            if any(isinstance(value, str) and not value.strip() for value in args.values()):
                raise HandoffError('Empty identifiers or evidence are not accepted.')
            result = change(project, action, **args)
        print(json.dumps(result, indent=2))
    except (HandoffError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, 'Handoff stopped: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
