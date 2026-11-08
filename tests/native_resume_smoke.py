#!/usr/bin/env python3
"""Probe same-ID native continuation with an idle temporary thread, no model turn.

This deliberately does not fabricate a conversation or borrow authentication.
An empty thread may not materialize on disk until its first real turn. If so,
the report records that limit instead of claiming native resume succeeded.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('workbench_resume', ROOT / 'workflow/resume.py')
RESUME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESUME)


def metadata(thread):
    return {key: thread.get(key) for key in
            ('id', 'sessionId', 'historyMode', 'cwd', 'cliVersion', 'ephemeral')}


def smoke(timeout=20):
    executable = shutil.which('codex')
    if executable is None:
        return {'status': 'unavailable', 'reason': 'Codex executable is not on PATH.'}
    version = subprocess.run([executable, '--version'], capture_output=True, text=True,
                             timeout=10).stdout.strip()
    report = {'native_version': version, 'model_turns_submitted': 0,
              'scope': 'Fresh temporary HOME/CODEX_HOME, no credentials or existing sessions copied.'}
    with tempfile.TemporaryDirectory(prefix='codex-workbench-native-smoke-', dir='/tmp') as temporary:
        root = Path(temporary)
        for name in ('home', 'state', 'workspace', 'tmp'):
            (root / name).mkdir()
        # Pass no inherited provider credentials, sessions, shell startup files,
        # browser profiles, or per-user configuration into the native server.
        isolated = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
                    'HOME': str(root / 'home'), 'CODEX_HOME': str(root / 'state'),
                    'CODEX_SQLITE_HOME': str(root / 'state'), 'TMPDIR': str(root / 'tmp'),
                    'LANG': 'C.UTF-8', 'TERM': os.environ.get('TERM', 'xterm')}
        command = [executable, 'app-server', '--stdio']
        with patch.dict(os.environ, isolated, clear=True):
            try:
                with RESUME.NativeClient(command, timeout) as client:
                    started = client.request('thread/start', {
                        'cwd': str(root / 'workspace'), 'ephemeral': False,
                        'approvalPolicy': 'on-request', 'sandbox': 'read-only',
                    })
                    original = started.get('thread') if isinstance(started, dict) else None
                    if not isinstance(original, dict) or not original.get('id'):
                        report.update(status='unsupported_response', stage='thread/start')
                        return report
                    report['created'] = metadata(original)
                    identity = original['id']
                    client.request('thread/unsubscribe', {'threadId': identity})
            except RESUME.ResumeError as error:
                report.update(status='unverified', stage='thread/start_or_unsubscribe', reason=str(error))
                return report
            # Server and connection are genuinely new here. Neither thread/start
            # nor a synthetic history injection is repeated in this process.
            database = root / 'state/state_5.sqlite'
            if database.is_file():
                with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
                    report['idle_thread_metadata_persisted'] = bool(connection.execute(
                        'SELECT 1 FROM threads WHERE id = ?', (identity,)).fetchone())
            try:
                with RESUME.NativeClient(command, timeout) as client:
                    restored = client.request('thread/resume', {
                        'threadId': identity, 'excludeTurns': True,
                    })
                    thread = restored.get('thread') if isinstance(restored, dict) else None
                    if not isinstance(thread, dict):
                        report.update(status='unsupported_response', stage='thread/resume')
                        return report
                    report['resumed'] = metadata(thread)
                    report['same_thread_id'] = thread.get('id') == identity
                    report['same_session_id'] = thread.get('sessionId') == original.get('sessionId')
                    report['status'] = ('verified_idle_resume' if report['same_thread_id']
                                        and report['same_session_id'] else 'identity_mismatch')
                    client.request('thread/unsubscribe', {'threadId': identity})
            except RESUME.ResumeError as error:
                report.update(status='idle_thread_not_resumable', stage='thread/resume', reason=str(error),
                              limitation='No inference or fabricated history was used to force empty-thread persistence. '
                                         'This result does not verify continuation of a conversation with turns.')
        report['temporary_state_files'] = sorted(path.name for path in (root / 'state').iterdir())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=float, default=20)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 60:
        parser.error('--timeout must be between 1 and 60 seconds')
    result = smoke(args.timeout)
    print(json.dumps(result, indent=2))
    # A reported limitation is not a verification failure in this diagnostic.
    # Consumers must inspect status instead of treating exit zero as a resume proof.
    return 1 if result['status'] in ('identity_mismatch', 'unsupported_response') else 0


if __name__ == '__main__':
    raise SystemExit(main())
