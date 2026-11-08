import importlib.util
import json
import os
import pty
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
THREAD = '019a5f00-1111-7111-8111-111111111111'


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        fake = self.bin / 'codex'
        fake.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args=sys.argv[1:]
if args==['--version']: print('codex-cli 0.167.0')
elif args==['--help']: print('native help')
elif args==['features','list']: print('multi_agent stable true')
elif args==['app-server','--stdio']:
 for line in sys.stdin:
  req=json.loads(line)
  if 'id' not in req: continue
  if req['method']=='initialize': result={}
  elif req['method']=='thread/read': result={'thread':{'id':req['params']['threadId'],'cwd':os.environ['TEST_SESSION']}}
  elif req['method']=='thread/list': result={'data':[{'id':'019a5f00-1111-7111-8111-111111111111','cwd':os.environ['TEST_SESSION'],'name':'Existing project','preview':'PRIVATE BODY'}, {'id':'other','cwd':'/unrelated/native/project','name':'Ordinary chat'}],'nextCursor':None}
  else: raise SystemExit(2)
  print(json.dumps({'id':req['id'],'result':result}),flush=True)
elif args and args[0]=='queue':
 Path(os.environ['TEST_QUEUE']).write_text(json.dumps(args))
 print('queued')
else: raise SystemExit(2)
''')
        fake.chmod(0o755)
        self.folder = self.home / '.local/share/codex-work/sessions/existing'
        self.env = dict(os.environ, HOME=str(self.home), CODEX_HOME=str(self.home / '.codex'),
                        CODEX_CODE_SETTINGS=str(self.home / '.config/codex-code/settings.json'),
                        PATH=str(self.bin) + os.pathsep + os.environ['PATH'], TEST_SESSION=str(self.folder),
                        TEST_QUEUE=str(self.home / 'queued.json'))
        result = subprocess.run([sys.executable, str(ROOT / 'workflow/install-portable.py'), '--home', str(self.home), '--apply'],
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.project = self.home / 'code/Existing'
        self.project.mkdir()
        (self.project / 'AGENTS.md').write_text('Project-specific safety rules.\n')
        self.folder.mkdir()
        self.state = {'workdir': str(self.project), 'kind': 'project', 'name': 'Existing',
                      'display_title': 'Custom title', 'display_title_mode': 'custom', 'native_id': THREAD}
        (self.folder / 'state.json').write_text(json.dumps(self.state))
        self.legacy = 'Legacy generated scaffold.\nLocal rule: never mutate production.\n\n'
        (self.folder / 'AGENTS.md').write_text(self.legacy)
        self.script = self.home / '.local/share/codex-code/policy.py'

    def run_policy(self, *args, target=True):
        command = [sys.executable, str(self.script)]
        if target:
            command += ['--session', str(self.folder)]
        return subprocess.run(command + list(args), env=self.env, cwd=ROOT,
                              capture_output=True, text=True, timeout=20)

    def applied(self):
        result = self.run_policy('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['session_revision']

    def receipt(self):
        return json.loads((self.folder / 'workbench/policy.json').read_text())

    def change_source(self):
        source = self.script.parent / 'code-baseline.txt'
        source.write_text(source.read_text() + '\nUpdated scoped policy for testing.\n')

    def test_preview_has_no_session_or_project_writes(self):
        result = self.run_policy('--check')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'update_available')
        self.assertFalse((self.folder / 'workbench').exists())
        self.assertEqual((self.folder / 'AGENTS.md').read_text(), self.legacy)

    def test_bare_upgrade_lists_outdated_code_sessions_without_history(self):
        result = self.run_policy('--list', target=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)['sessions']
        self.assertEqual([row['id'] for row in rows], [THREAD])
        self.assertEqual(rows[0]['project'], str(self.project))
        self.assertNotIn('PRIVATE BODY', result.stdout)
        self.assertFalse((self.folder / 'workbench').exists())

    def test_no_tty_no_selector_never_applies_to_arbitrary_session(self):
        result = self.run_policy('--apply', target=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['sessions'][0]['id'], THREAD)
        self.assertFalse((self.folder / 'workbench').exists())

    def interactive_upgrade(self, *args, selection='1'):
        master, slave = pty.openpty()
        try:
            os.write(master, (selection + '\n').encode())
            return subprocess.run([sys.executable, str(self.script), *args], env=self.env,
                                  cwd=ROOT, stdin=slave, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, timeout=20)
        finally:
            os.close(master)
            os.close(slave)

    def test_interactive_selection_applies_and_notifies_by_default(self):
        result = self.interactive_upgrade()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.receipt()['notification_status'], 'queued')
        self.assertEqual(self.receipt()['adoption_status'], 'pending')
        self.assertIn('Selection applies', result.stdout)

    def test_interactive_preview_and_check_do_not_mutate(self):
        for flag in ('--preview', '--check', '--diff'):
            result = self.interactive_upgrade(flag)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((self.folder / 'workbench').exists())
            self.assertFalse((self.home / 'queued.json').exists())

    def test_interactive_no_notify_attaches_without_queue(self):
        result = self.interactive_upgrade('--no-notify')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.receipt()['adoption_status'], 'pending')
        self.assertFalse((self.home / 'queued.json').exists())

    def test_interactive_cancel_never_applies(self):
        result = self.interactive_upgrade(selection='q')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.folder / 'workbench').exists())

    def test_acknowledged_current_sessions_are_hidden_unless_all_requested(self):
        revision = self.applied()
        self.assertEqual(self.run_policy('--ack', revision, '--applicable', 'baseline').returncode, 0)
        self.assertEqual(json.loads(self.run_policy('--list', target=False).stdout)['sessions'], [])
        rows = json.loads(self.run_policy('--list', '--all', target=False).stdout)['sessions']
        self.assertEqual(rows[0]['status'], 'acknowledged')

    def test_apply_preserves_legacy_project_state_and_is_idempotent(self):
        before_state = (self.folder / 'state.json').read_bytes()
        revision = self.applied()
        self.assertTrue((self.folder / 'AGENTS.md').read_text().startswith(self.legacy))
        self.assertEqual((self.folder / 'state.json').read_bytes(), before_state)
        self.assertEqual((self.project / 'AGENTS.md').read_text(), 'Project-specific safety rules.\n')
        self.assertEqual(self.receipt()['adoption_status'], 'pending')
        before_agents = (self.folder / 'AGENTS.md').read_bytes()
        before_receipt = (self.folder / 'workbench/policy.json').read_bytes()
        self.assertEqual(self.applied(), revision)
        self.assertEqual((self.folder / 'AGENTS.md').read_bytes(), before_agents)
        self.assertEqual((self.folder / 'workbench/policy.json').read_bytes(), before_receipt)

    def test_managed_local_edit_and_override_refuse_updates(self):
        self.applied()
        path = self.folder / 'AGENTS.md'
        edited = path.read_text().replace('# Current code-mode policy', '# Locally edited policy')
        path.write_text(edited)
        result = self.run_policy('--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_text(), edited)
        (self.folder / 'AGENTS.override.md').write_text('Local override\n')
        self.assertNotEqual(self.run_policy('--check').returncode, 0)

    def test_attached_snapshot_edits_block_check_apply_and_ack(self):
        revision = self.applied()
        instructions = self.folder / 'workbench/policy-revisions' / revision / 'instructions.md'
        edited = instructions.read_text() + '\nLocal changed snapshot requirement.\n'
        instructions.write_text(edited)
        for args in [('--check',), ('--apply',), ('--ack', revision, '--applicable', 'baseline')]:
            with self.subTest(args=args):
                self.assertNotEqual(self.run_policy(*args).returncode, 0)
                self.assertEqual(instructions.read_text(), edited)
        self.assertEqual(self.receipt()['adoption_status'], 'pending')

    def test_symlinked_workbench_is_not_followed(self):
        elsewhere = self.home / 'unrelated'
        elsewhere.mkdir()
        (self.folder / 'workbench').symlink_to(elsewhere, target_is_directory=True)
        result = self.run_policy('--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_activate_rechecks_managed_edits_after_snapshot_preparation(self):
        revision = self.applied()
        spec = importlib.util.spec_from_file_location('policy_late_edit', self.script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        agents = self.folder / 'AGENTS.md'
        edited = agents.read_text().replace('# Current code-mode policy', '# Edit made after initial preview')
        agents.write_text(edited)
        with self.assertRaises(module.PolicyError):
            module.activate(self.folder, revision, self.receipt()['source_hashes'])
        self.assertEqual(agents.read_text(), edited)

    def test_only_current_read_revision_can_be_acknowledged_with_applicability(self):
        revision = self.applied()
        self.assertNotEqual(self.run_policy('--ack', 'f' * 64, '--applicable', 'baseline').returncode, 0)
        self.assertNotEqual(self.run_policy('--ack', revision).returncode, 0)
        result = self.run_policy('--ack', revision, '--applicable', 'KB and title', '--skipped', 'commerce and UI')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.receipt()['adoption_status'], 'acknowledged')

    def test_conflict_acknowledgement_records_need_for_decision(self):
        revision = self.applied()
        result = self.run_policy('--ack', revision, '--conflict', 'Local production policy is stricter')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.receipt()['adoption_status'], 'needs_decision')

    def test_rollback_preserves_later_unmanaged_edits(self):
        old = self.applied()
        agents = self.folder / 'AGENTS.md'
        agents.write_text(agents.read_text() + '\nNew local instruction after upgrade.\n')
        self.change_source()
        new = self.applied()
        self.assertNotEqual(old, new)
        result = self.run_policy('--rollback', old, '--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.receipt()['revision'], old)
        self.assertIn('New local instruction after upgrade.', agents.read_text())
        self.assertTrue(agents.read_text().startswith(self.legacy))
        self.assertEqual(json.loads((self.folder / 'state.json').read_text()), self.state)

    def test_ambiguous_project_lookup_does_not_choose_newest(self):
        other = self.folder.parent / 'other'
        other.mkdir()
        (other / 'state.json').write_text(json.dumps(self.state))
        result = self.run_policy('--project', str(self.project), '--apply', target=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('exactly one', result.stderr)
        self.assertFalse((self.folder / 'workbench').exists())

    def test_notification_is_queued_without_claiming_adoption(self):
        result = self.run_policy('--thread', THREAD, '--apply', '--notify', target=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.receipt()['notification_status'], 'queued')
        self.assertEqual(self.receipt()['adoption_status'], 'pending')
        queued = json.loads((self.home / 'queued.json').read_text())
        self.assertEqual(queued[:3], ['queue', '--thread', THREAD])
        self.assertNotIn('--resume', queued)
        self.assertIn('only relevant changes', queued[-1])

    def test_notify_without_explicit_thread_refuses_before_mutation(self):
        result = self.run_policy('--apply', '--notify')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.folder / 'workbench').exists())

    def test_claude_policy_uses_own_loader_and_preserves_project_and_codex_rules(self):
        state = dict(self.state, engine='claude', native_id=THREAD)
        (self.folder / 'state.json').write_text(json.dumps(state))
        (self.folder / 'CLAUDE.md').write_text('Existing Claude local rules.\n')
        result = self.run_policy('--engine', 'claude', '--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.folder / 'AGENTS.md').read_text(), self.legacy)
        self.assertTrue((self.folder / 'CLAUDE.md').read_text().startswith('Existing Claude local rules.\n'))
        self.assertEqual(self.receipt()['engine'], 'claude')
        self.assertEqual(json.loads((self.folder / 'state.json').read_text()), state)

    def test_claude_candidates_use_registered_native_ids_and_no_external_queue(self):
        state = dict(self.state, engine='claude', native_id=THREAD)
        (self.folder / 'state.json').write_text(json.dumps(state))
        result = self.run_policy('--engine', 'claude', '--list', target=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['sessions'][0]['id'], THREAD)
        result = self.run_policy('--engine', 'claude', '--thread', THREAD, '--apply', '--notify', target=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no configured external queue', result.stderr)
        self.assertFalse((self.folder / 'workbench').exists())

    def test_interrupted_pointer_update_restores_previous_instructions(self):
        spec = importlib.util.spec_from_file_location('policy_test', self.script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.dict(os.environ, self.env):
            data = module.sources()
            revision, hashes = module.fingerprint(data)
            module.build_snapshot(self.folder, revision, data)
            original = module.atomic
            failed = False
            def interrupted(path, content):
                nonlocal failed
                if path.name == 'policy.json' and not failed:
                    failed = True
                    raise OSError('simulated interrupted write')
                original(path, content)
            with patch.object(module, 'atomic', side_effect=interrupted):
                with self.assertRaises(OSError):
                    module.activate(self.folder, revision, hashes)
        self.assertEqual((self.folder / 'AGENTS.md').read_text(), self.legacy)
        self.assertFalse((self.folder / 'workbench/policy.json').exists())

    def test_interrupted_write_never_rolls_back_over_concurrent_local_edit(self):
        spec = importlib.util.spec_from_file_location('policy_concurrent_edit', self.script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        agents = self.folder / 'AGENTS.md'
        with patch.dict(os.environ, self.env):
            data = module.sources()
            revision, hashes = module.fingerprint(data)
            module.build_snapshot(self.folder, revision, data)
            original = module.atomic
            def interrupted(path, content):
                if path.name == 'policy.json':
                    agents.write_text(agents.read_text() + '\nConcurrent local instruction.\n')
                    raise OSError('simulated write failure with concurrent edit')
                original(path, content)
            with patch.object(module, 'atomic', side_effect=interrupted):
                with self.assertRaises(module.PolicyError):
                    module.activate(self.folder, revision, hashes)
        self.assertIn('Concurrent local instruction.', agents.read_text())
        self.assertTrue(agents.read_text().startswith(self.legacy))


if __name__ == '__main__':
    unittest.main()
