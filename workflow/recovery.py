#!/usr/bin/env python3
"""Local recovery journal and restart planning; never resumes a model or replays work."""
import argparse
from contextlib import contextmanager
import fcntl
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
from pathlib import Path
import tempfile
import uuid


def utc():
    return datetime.now(timezone.utc).isoformat()


def durable_write(path, value):
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError('Redirected recovery state is not accepted.')
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.journal-', delete=False) as stream:
        temporary = Path(stream.name)
        os.fchmod(stream.fileno(), 0o600)
        stream.write((json.dumps(value, sort_keys=True, indent=2) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    try:
        temporary.replace(path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def verify_location(expected, observed):
    """Use per-host mount identity AND project sentinel, not only a pathname."""
    fields = ('mount_target', 'filesystem', 'source_sha256', 'project_id', 'project_path')
    if set(expected) != set(fields) or any(not expected[k] for k in fields):
        raise ValueError('Complete pinned per-host storage identity is required.')
    if observed.get('mounted') is not True:
        return {'ready': False, 'reason': 'share_unavailable_no_local_fallback'}
    if any(expected[k] != observed.get(k) for k in fields):
        return {'ready': False, 'reason': 'mount_or_project_identity_changed'}
    return {'ready': True, 'reason': 'identity_verified'}


def retry_decision(kind, dispatched, attempts, maximum, status, elapsed, deadline_seconds, retry_after=0):
    if type(attempts) is not int or type(maximum) is not int or not 0 <= attempts < maximum <= 100:
        return {'retry': False, 'reason': 'attempt_limit'}
    if elapsed < 0 or deadline_seconds <= 0 or elapsed >= deadline_seconds:
        return {'retry': False, 'reason': 'deadline'}
    if kind not in ('read', 'mutation'):
        raise ValueError('Operation kind must be read or mutation.')
    if kind == 'mutation' and dispatched:
        return {'retry': False, 'reason': 'outcome_unknown_reconcile_before_replay'}
    if status in (401, 403):
        return {'retry': False, 'reason': 'authentication_or_authorization_required'}
    if status not in (None, 408, 429, 500, 502, 503, 504):
        return {'retry': False, 'reason': 'not_transient'}
    delay = max(min(2 ** attempts, 60), max(0, retry_after))
    return {'retry': elapsed + delay < deadline_seconds, 'delay_seconds': delay,
            'reason': 'bounded_read_or_not_dispatched_retry'}


class Journal:
    """One immutable file per operation; never create a distributed fallback journal."""
    def __init__(self, directory, boot_id, shared_roots=('/mnt/s',), allow_ephemeral=False):
        if type(allow_ephemeral) is not bool or not isinstance(boot_id,str) or not boot_id:
            raise ValueError('Explicit boot identity and fixture flag required.')
        raw = Path(directory).expanduser().absolute()
        if '..' in raw.parts or any(p.is_symlink() for p in (raw,*raw.parents)):
            raise ValueError('Journal path must not use traversal or symlink aliases.')
        self.directory = raw.resolve(strict=False)
        if not allow_ephemeral and any(self.directory == Path(s) or self.directory.is_relative_to(Path(s)) for s in ('/tmp', '/run', '/dev/shm')):
            raise ValueError('Ephemeral paths are fixture-only, not power-loss recovery storage.')
        if any(self.directory == Path(s).absolute().resolve(strict=False) or self.directory.is_relative_to(Path(s).absolute().resolve(strict=False)) for s in shared_roots):
            raise ValueError('Recovery journal must be local, outside configured shared roots.')
        if any(p.is_symlink() for p in (self.directory, *self.directory.parents)):
            raise ValueError('Recovery path must not traverse symlinks.')
        existing = self.directory
        while not existing.exists():
            existing = existing.parent
        probe = subprocess.run(['findmnt', '-n', '-o', 'FSTYPE', '-T', str(existing)], capture_output=True, text=True, timeout=10)
        supported = ('ext2','ext3','ext4','xfs','btrfs','zfs','f2fs') + (('tmpfs','overlay') if allow_ephemeral else ())
        if probe.returncode or probe.stdout.strip() not in supported:
            raise ValueError('Local filesystem verification failed; do not fall back to a shared journal.')
        self.boot_id = boot_id
        if self.directory.is_symlink():
            raise ValueError('Journal must not be redirected.')
        missing=[];candidate=self.directory
        while not candidate.exists():
            missing.append(candidate);candidate=candidate.parent
        for directory in reversed(missing):
            directory.mkdir(mode=0o700,exist_ok=True)
            if directory.is_symlink() or not directory.is_dir():
                raise ValueError('Recovery directory creation was redirected.')
            parent_fd=os.open(directory.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:os.fsync(parent_fd)
            finally:os.close(parent_fd)
        # Also persist existing ancestors: a previous failed creation may have
        # left a namespace entry not yet committed in its parent.
        for directory in (self.directory,*self.directory.parents):
            directory_fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:os.fsync(directory_fd)
            finally:os.close(directory_fd)
        self.guard = self.directory / 'transaction.lock'

    def _path(self, operation):
        return self.directory / (str(uuid.UUID(operation)) + '.json')

    @contextmanager
    def _locked(self):
        # Local POSIX flock is released by the kernel on process death/reboot.
        # Never use this controller lock on the NFS/shared project itself.
        fd = os.open(self.guard, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def _save(self, path, value):
        with self._locked():
            durable_write(path, value)

    def begin(self, project_id, revision, owner, kind, intent_digest):
        uuid.UUID(project_id)
        if kind not in ('read', 'mutation') or not owner or not intent_digest or type(revision) is not int:
            raise ValueError('Explicit owner/revision/operation intent required.')
        operation = str(uuid.uuid4())
        value = {'schema': 1, 'id': operation, 'project_id': project_id, 'expected_revision': revision,
                 'owner': owner, 'kind': kind, 'intent_digest': intent_digest, 'boot_id': self.boot_id,
                 'phase': 'not_dispatched', 'at': utc(), 'evidence': None}
        self._save(self._path(operation), value)
        return value

    def read(self, operation):
        path = self._path(operation)
        if path.is_symlink():
            raise ValueError('Redirected operation record.')
        return json.loads(path.read_text())

    def mark(self, operation, phase, evidence=None):
        allowed = {'not_dispatched': {'dispatched_outcome_unknown'},
                   'dispatched_outcome_unknown': {'observed_applied', 'reconciled'},
                   'observed_applied': {'reconciled'}, 'reconciled': set()}
        with self._locked():
            value = self.read(operation)
            if phase not in allowed[value['phase']]:
                raise ValueError('Illegal/replayed operation transition.')
            if phase in ('observed_applied', 'reconciled') and not evidence:
                raise ValueError('Actual observation/reconciliation evidence is required.')
            value.update(phase=phase, evidence=evidence, updated_at=utc())
            durable_write(self._path(operation), value)
        return value

    def save_sessions(self, records):
        fields = {'id','provider','host','account_alias','native_id','project_id','project_path','boot_id','desired_open'}
        ids = set()
        for record in records:
            if set(record) != fields or type(record['desired_open']) is not bool:
                raise ValueError('Session registry requires exact metadata fields and explicit desired-open state.')
            uuid.UUID(record['id']); uuid.UUID(record['project_id'])
            if record['id'] in ids or any(not isinstance(record[k], str) or not record[k] for k in fields - {'desired_open'}):
                raise ValueError('Duplicate/empty registry identity.')
            ids.add(record['id'])
        self._save(self.directory / 'sessions.json', records)

    def sessions(self):
        path = self.directory / 'sessions.json'
        if path.is_symlink():
            raise ValueError('Redirected registry.')
        return json.loads(path.read_text())

    def recovery(self, operation):
        value = self.read(operation)
        return dict(value, reboot_detected=value['boot_id'] != self.boot_id,
                    action='inspect_before_dispatch' if value['phase'] == 'not_dispatched' else
                    'read_only_reconcile' if value['phase'] != 'reconciled' else 'nothing_to_replay',
                    automatic_replay=False)


def restore_plan(records, boot_id, observations, owner_host):
    """Plan desired-open chat restoration only. A supervisor is a separate adapter."""
    result = []
    seen = set()
    for record in records:
        identity = (record['provider'], record['host'], record['account_alias'], record['native_id'])
        if identity in seen:
            continue
        seen.add(identity)
        observed = observations.get(record['id'], {})
        reason = 'eligible_for_verified_idle_reattach'
        if type(record['desired_open']) is not bool:
            raise ValueError('Desired-open state must be explicit boolean.')
        if record['host'] != owner_host:
            reason = 'different_owner_host_no_migration'
        elif not record['desired_open']:
            reason = 'intentionally_closed'
        elif record['boot_id'] == boot_id:
            reason = 'same_boot_no_duplicate_restore'
        elif any(observed.get(k) is not True for k in ('location_verified','native_identity_verified','account_verified')):
            reason = 'storage_or_native_identity_unverified'
        elif observed.get('idle_resume_verified_safe') is not True:
            reason = 'native_resume_side_effects_unverified'
        elif observed.get('native_loaded') is True:
            reason = 'already_loaded'
        elif observed.get('pending_or_uncertain_work') is True or observed.get('native_state') in ('busy','needs_approval'):
            reason = 'reconcile_pending_work_before_restore'
        elif observed.get('native_loaded') is not False or observed.get('pending_or_uncertain_work') is not False or observed.get('native_state') not in ('idle','not_loaded'):
            reason = 'native_activity_unverified'
        result.append({'id': record['id'], 'provider': record['provider'], 'native_id': record['native_id'],
                       'reason': reason, 'restore_candidate': reason == 'eligible_for_verified_idle_reattach',
                       'replay_commands': False, 'resume_unattended_work': False})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--journal', type=Path, required=True)
    parser.add_argument('--boot-id', required=True)
    commands = parser.add_subparsers(dest='action', required=True)
    inspect = commands.add_parser('inspect', help='Inspect an operation after interruption; no execution.')
    inspect.add_argument('--operation', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(Journal(args.journal, args.boot_id).recovery(args.operation), indent=2))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, 'Recovery inspection stopped: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
