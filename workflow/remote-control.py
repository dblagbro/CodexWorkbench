#!/usr/bin/env python3
"""Re-establish supported Codex remote control without restarting active work."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


class CommandFailure(Exception):
    def __init__(self, stage, reason):
        self.stage = stage
        self.reason = reason


NOTES = {
    'unavailable': 'Install a compatible Codex CLI and ensure it is on the service PATH.',
    'unsupported': 'This Codex build lacks the required remote-control commands; review its installed help.',
    'authentication_required': 'Complete Codex sign-in or required account/workspace remote-access verification on this host.',
    'permission_denied': 'Check this user has access to its Codex state and daemon control socket.',
    'timeout': 'The command timed out; check host connectivity and daemon health before the next scheduled attempt.',
    'command_failed': 'Check Codex daemon health and account eligibility using native commands; raw output was not saved.',
    'invalid_response': 'The daemon did not return recognized status JSON; inspect this installed version manually.',
    'daemon_not_running': 'Remote control was requested but a running daemon could not be verified.',
}


def command(executable, args, stage, timeout):
    try:
        result = subprocess.run([executable, *args], capture_output=True,
                                text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise CommandFailure(stage, 'timeout') from None
    except OSError:
        raise CommandFailure(stage, 'unavailable') from None
    if result.returncode:
        # Classify in memory only. Never persist stdout/stderr or pairing tokens.
        detail = (result.stdout + result.stderr).lower()
        if any(term in detail for term in ('permission denied', 'access denied', 'read-only file system')):
            reason = 'permission_denied'
        elif any(term in detail for term in ('sign in', 'sign-in', 'login', 'unauthenticated',
                                             'authentication', 'workspace admin', 'not eligible')):
            reason = 'authentication_required'
        elif any(term in detail for term in ('unrecognized subcommand', 'unexpected argument', 'unknown command')):
            reason = 'unsupported'
        else:
            reason = 'command_failed'
        raise CommandFailure(stage, reason)
    return result.stdout


def ensure(timeout=20):
    """Perform one bounded reconciliation. The caller owns retry scheduling."""
    report = {'schema_version': 1, 'checked_at': datetime.now(timezone.utc).isoformat(),
              'status': 'failed', 'remote_control_configured': False,
              'daemon_running': False, 'remote_connection': 'unverified',
              'note': 'No device pairing or end-to-end remote attachment is performed.'}
    executable = shutil.which('codex')
    if not executable:
        report.update(stage='discovery', reason='unavailable', action=NOTES['unavailable'])
        return report
    try:
        version = command(executable, ['--version'], 'version', timeout)
        match = re.search(r'\bcodex-cli\s+([0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?)\b', version)
        if not match:
            raise CommandFailure('version', 'invalid_response')
        report['cli_version'] = match.group(1)
        remote_help = command(executable, ['remote-control', '--help'], 'capability_check', timeout)
        daemon_help = command(executable, ['app-server', 'daemon', '--help'], 'capability_check', timeout)
        if not re.search(r'^\s+start\s', remote_help, re.MULTILINE) or 'enable-remote-control' not in daemon_help:
            raise CommandFailure('capability_check', 'unsupported')
        command(executable, ['app-server', 'daemon', 'enable-remote-control'], 'enable', timeout)
        report['remote_control_configured'] = True
        command(executable, ['remote-control', 'start', '--json'], 'start', timeout)
        output = command(executable, ['app-server', 'daemon', 'version'], 'verify', timeout)
        try:
            status = json.loads(output)
        except (ValueError, TypeError):
            raise CommandFailure('verify', 'invalid_response') from None
        if not isinstance(status, dict):
            raise CommandFailure('verify', 'invalid_response')
        if status.get('status') != 'running':
            raise CommandFailure('verify', 'daemon_not_running')
        report.update(status='ready', daemon_running=True, stage='verified')
        # Do not copy arbitrary daemon fields into logs or status files.
        for key in ('cliVersion', 'appServerVersion'):
            value = status.get(key)
            if isinstance(value, str) and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?', value):
                report[key] = value
    except CommandFailure as exc:
        report.update(stage=exc.stage, reason=exc.reason, action=NOTES[exc.reason])
    return report


def write_status(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.' + path.name + '.', delete=False) as handle:
            temporary = Path(handle.name)
            os.fchmod(handle.fileno(), 0o600)
            json.dump(report, handle, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['ensure'])
    default_state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state')))
    parser.add_argument('--status-file', type=Path,
                        default=default_state / 'codex-code/remote-control-status.json')
    parser.add_argument('--timeout-seconds', type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 60:
        parser.error('--timeout-seconds must be between 1 and 60')
    path = args.status_file.expanduser()
    if not path.is_absolute():
        parser.error('--status-file must be absolute')
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_name(path.name + '.lock')
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print(json.dumps({'status': 'already_checking'}))
                return 0
            report = ensure(args.timeout_seconds)
            write_status(path, report)
        print(json.dumps(report))
        return 0 if report['status'] == 'ready' else 1
    except OSError:
        print(json.dumps({'status': 'failed', 'reason': 'status_storage_failed',
                          'action': 'Check the local status directory permissions.'}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
