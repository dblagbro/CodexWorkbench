import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'workflow/remote-control.py'
spec = importlib.util.spec_from_file_location('remote_control', SCRIPT)
remote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote)


class RemoteControlTests(unittest.TestCase):
    def run_ensure(self, responses):
        def result(args, **kwargs):
            response = responses.get(tuple(args[1:]), ('', '', 0))
            if isinstance(response, BaseException):
                raise response
            out, err, code = response
            return subprocess.CompletedProcess(args, code, out, err)
        with patch.object(remote.shutil, 'which', return_value='/bin/codex'), \
                patch.object(remote.subprocess, 'run', side_effect=result) as run:
            report = remote.ensure(timeout=3)
        return report, run

    def responses(self):
        return {('--version',): ('codex-cli 0.167.0\n', '', 0),
                ('remote-control', '--help'): ('Commands:\n  start Start daemon\n', '', 0),
                ('app-server', 'daemon', '--help'): ('Commands:\n  enable-remote-control Enable\n', '', 0),
                ('remote-control', 'start', '--json'): ('{"pairingCode":"SECRET_PAIRING"}', '', 0),
                ('app-server', 'daemon', 'version'): (json.dumps({'status': 'running',
                     'appServerVersion': '0.167.0', 'authToken': 'SECRET_TOKEN'}), '', 0)}

    def test_ready_uses_supported_commands_without_restart_or_token_output(self):
        report, run = self.run_ensure(self.responses())
        self.assertEqual(report['status'], 'ready')
        self.assertTrue(report['remote_control_configured'])
        self.assertTrue(report['daemon_running'])
        self.assertEqual(report['remote_connection'], 'unverified')
        self.assertNotIn('SECRET', json.dumps(report))
        called = [call.args[0][1:] for call in run.call_args_list]
        self.assertIn(['app-server', 'daemon', 'enable-remote-control'], called)
        self.assertIn(['remote-control', 'start', '--json'], called)
        self.assertFalse(any('stop' in args or 'restart' in args or 'pair' in args for args in called))
        for call in run.call_args_list:
            self.assertEqual(call.kwargs['timeout'], 3)

    def test_unsupported_build_does_not_try_to_enable(self):
        responses = self.responses()
        responses[('remote-control', '--help')] = ('No start command', '', 0)
        report, run = self.run_ensure(responses)
        self.assertEqual(report['reason'], 'unsupported')
        self.assertFalse(any('enable-remote-control' in call.args[0] for call in run.call_args_list))

    def test_auth_failure_is_actionable_and_redacted(self):
        responses = self.responses()
        responses[('remote-control', 'start', '--json')] = ('SECRET_TOKEN', 'authentication required SECRET', 1)
        report, _ = self.run_ensure(responses)
        self.assertEqual(report['reason'], 'authentication_required')
        self.assertNotIn('SECRET', json.dumps(report))
        self.assertIn('sign-in', report['action'])

    def test_timeout_is_not_success(self):
        responses = self.responses()
        responses[('remote-control', 'start', '--json')] = subprocess.TimeoutExpired(['codex'], 3)
        report, _ = self.run_ensure(responses)
        self.assertEqual(report['reason'], 'timeout')
        self.assertFalse(report['daemon_running'])

    def test_start_success_requires_running_daemon_verification(self):
        responses = self.responses()
        responses[('app-server', 'daemon', 'version')] = ('{"status":"stopped"}', '', 0)
        report, _ = self.run_ensure(responses)
        self.assertEqual(report['reason'], 'daemon_not_running')

    def test_invalid_daemon_json_is_not_success(self):
        responses = self.responses()
        responses[('app-server', 'daemon', 'version')] = ('not-json SECRET', '', 0)
        report, _ = self.run_ensure(responses)
        self.assertEqual(report['reason'], 'invalid_response')
        self.assertNotIn('SECRET', json.dumps(report))

    def test_status_file_private_atomic_and_contains_only_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state/status.json'
            remote.write_status(path, {'status': 'ready'})
            self.assertEqual(json.loads(path.read_text()), {'status': 'ready'})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual([item.name for item in path.parent.iterdir()], ['status.json'])

    def test_missing_executable_does_not_run_commands(self):
        with patch.object(remote.shutil, 'which', return_value=None), \
                patch.object(remote.subprocess, 'run') as run:
            report = remote.ensure()
        self.assertEqual(report['reason'], 'unavailable')
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
