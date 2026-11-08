import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('workbench_resume', ROOT / 'workflow/resume.py')
resume = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resume)
THREAD_ID = '019a5f00-1111-7111-8111-111111111111'


class FakeClient:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.requests = []

    def request(self, method, params):
        self.requests.append((method, params))
        return next(self.pages)


class ResumeTests(unittest.TestCase):
    def test_resume_preserves_exact_native_id_and_adds_no_baseline(self):
        self.assertEqual(resume.resume_command(THREAD_ID), ['codex', 'resume', '--all', THREAD_ID])
        self.assertEqual(resume.resume_command(), ['codex', 'resume', '--all'])

    def test_ssh_host_validation_rejects_options_and_shell_syntax(self):
        for value in ['-oProxyCommand=bad', 'host;bad', 'host name', 'host\nother', '$(bad)', '']:
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                resume.host_alias(value)
        self.assertEqual(resume.host_alias('user@dev-host'), 'user@dev-host')

    def test_ssh_resume_targets_original_host_with_safe_native_arguments(self):
        command = resume.resume_command(THREAD_ID, 'dev-host')
        self.assertEqual(command[:2], ['ssh', '-t'])
        self.assertEqual(command[-2:], ['dev-host', 'exec env PATH="$HOME/.local/bin:$PATH" codex resume --all ' + THREAD_ID])
        self.assertIn('--', command)

    def test_non_uuid_does_not_invent_or_fork_thread(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            resume.resume_command('a summary of the old conversation')

    def test_cli_executes_only_native_resume_or_explicit_ssh(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('codex', 'ssh'):
                executable = Path(folder) / name
                executable.write_text('#!' + sys.executable + '\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n')
                executable.chmod(0o755)
            env = dict(os.environ, PATH=folder + os.pathsep + os.environ['PATH'])
            native = subprocess.run([sys.executable, str(ROOT / 'workflow/resume.py'), 'resume', THREAD_ID],
                                    env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(native.returncode, 0, native.stderr)
            self.assertEqual(json.loads(native.stdout), ['resume', '--all', THREAD_ID])
            remote = subprocess.run([sys.executable, str(ROOT / 'workflow/resume.py'), '--host', 'dev-host', 'resume', THREAD_ID],
                                    env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(remote.returncode, 0, remote.stderr)
            self.assertEqual(json.loads(remote.stdout), resume.resume_command(THREAD_ID, 'dev-host')[1:])
            self.assertIn('execution remains on that host', remote.stderr)

    def test_list_uses_metadata_only_and_strips_private_bodies(self):
        client = FakeClient([{'data': [{'id': THREAD_ID, 'sessionId': THREAD_ID,
                                      'cwd': '/shared/project', 'name': 'test',
                                      'preview': 'PRIVATE', 'turns': ['PRIVATE']}], 'nextCursor': None}])
        result = resume.list_threads(client)
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertEqual(result['threads'][0]['id'], THREAD_ID)
        self.assertEqual(client.requests[0][0], 'thread/list')
        self.assertTrue(client.requests[0][1]['useStateDbOnly'])
        self.assertNotIn('includeTurns', client.requests[0][1])

    def test_pagination_is_bounded_and_reports_truncation(self):
        client = FakeClient([{'data': [], 'nextCursor': 'next'}])
        result = resume.list_threads(client, max_pages=1)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['nextCursor'], 'next')

    def test_repeated_cursor_fails_instead_of_looping(self):
        client = FakeClient([{'data': [], 'nextCursor': 'same'}, {'data': [], 'nextCursor': 'same'}])
        with self.assertRaises(resume.ResumeError):
            resume.list_threads(client)

    def test_native_jsonl_protocol_handles_notifications_without_reading_turns(self):
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / 'server.py'
            script.write_text('''import json, sys
for line in sys.stdin:
    req = json.loads(line)
    if 'id' not in req: continue
    print(json.dumps({'method':'server/notification','params':{}}), flush=True)
    if req['method'] == 'initialize': result = {'userAgent':'test'}
    elif req['method'] == 'thread/list': result = {'data': [], 'nextCursor': None}
    else: raise SystemExit('unexpected method')
    print(json.dumps({'id':req['id'],'result':result}), flush=True)
''')
            with resume.NativeClient([sys.executable, str(script)], timeout=2) as client:
                self.assertEqual(resume.list_threads(client)['threads'], [])

    def test_timeout_is_bounded(self):
        with self.assertRaises(resume.ResumeError):
            with resume.NativeClient([sys.executable, '-c', 'import time; time.sleep(2)'], timeout=.05):
                self.fail('Unresponsive transport should not initialize')


if __name__ == '__main__':
    unittest.main()
