import importlib.util
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/project-bootstrap/scripts/unattended-plan.py'
SPEC = importlib.util.spec_from_file_location('unattended_plan', SCRIPT)
plan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plan)


class UnattendedPlanTests(unittest.TestCase):
    def agreement(self, **overrides):
        args = dict(scope='Ready items in current milestone', hours=8, check_minutes=15,
                    report_minutes=60, budget='Existing subscription only; no purchases',
                    notification='In-chat only', stop_at='Done, deadline or required approval',
                    priority_source='docs/status.md', owner_host='fixture-host', max_attempt_minutes=30, now=datetime(2026, 11, 7, tzinfo=timezone.utc))
        return plan.make_plan(**dict(args, **overrides))

    def test_deadline_is_finite_utc_and_plan_never_claims_scheduling(self):
        data = self.agreement()
        self.assertEqual(data['deadline'], '2026-11-07T08:00:00+00:00')
        self.assertFalse(data['scheduler_verified'])
        self.assertEqual(data['status'], 'agreed_needs_scheduler_setup')
        for key in ('hours', 'check_minutes', 'report_minutes', 'max_attempt_minutes'):
            for value in (0, -1, math.inf, math.nan, True):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.agreement(**{key: value})
        with self.assertRaises(ValueError):
            self.agreement(hours=0.1, check_minutes=15)
        with self.assertRaises(ValueError):
            self.agreement(notification='')

    def test_private_no_clobber_plan_and_unresolved_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = Path(temporary)
            project = session / 'project'
            project.mkdir()
            (session / 'state.json').write_text(json.dumps({'workdir': str(project)}))
            path = plan.save_plan(session, self.agreement())
            first = path.read_bytes()
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertIn('resolve_exact_native_id', json.loads(first)['native_id_status'])
            with self.assertRaises(FileExistsError):
                plan.save_plan(session, self.agreement(scope='Different milestone'))
            self.assertEqual(path.read_bytes(), first)
            self.assertEqual(sorted(p.name for p in path.parent.iterdir()), ['plan.json'])

    def test_redirected_state_cannot_write_outside_session(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            session, outside = root / 'session', root / 'outside'
            session.mkdir()
            outside.mkdir()
            (session / 'state.json').write_text(json.dumps({'workdir': str(outside)}))
            (session / 'workbench').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                plan.save_plan(session, self.agreement())
            self.assertEqual(list(outside.iterdir()), [])

    def test_preview_never_creates_state_or_launches_tools(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = Path(temporary)
            result = subprocess.run([sys.executable, str(SCRIPT), '--session', str(session),
                                     '--scope', 'Current milestone', '--hours', '8',
                                     '--check-minutes', '15', '--report-minutes', '60',
                                     '--owner-host', 'fixture-host', '--max-attempt-minutes', '30',
                                     '--budget', 'No additional spend', '--notification', 'In-chat only',
                                     '--stop-at', 'Deadline or required approval', '--priority-source', 'docs/status.md'],
                                    env=dict(os.environ, PATH=''), capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'preview_not_authorized')
            self.assertEqual(list(session.iterdir()), [])
