import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('handoff', ROOT / 'workflow/handoff.py')
handoff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handoff)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        (self.project / 'AGENTS.md').write_text('Local Codex rules.\n')
        (self.project / 'CLAUDE.md').write_text('Local Claude rules.\n')
        handoff.initialize(self.project, True)

    def state(self):
        return handoff.read_state(handoff.root(self.project))

    def join(self, provider):
        return handoff.change(self.project, 'join', label='test-' + provider, provider=provider,
                              host='fixture-host', native_id=provider + '-native-id')['participant']

    def sync(self, actor):
        s = self.state()
        return handoff.change(self.project, 'sync', actor, s['revision'], s['policy_revision'],
                              note='Reviewed policy, project changes and referenced evidence.')

    def edit(self, action, actor, **details):
        s = self.state()
        return handoff.change(self.project, action, actor, s['revision'], note='Test evidence note', **details)

    def test_provider_roundtrip_and_stale_chat_detection(self):
        codex, claude = self.join('codex'), self.join('claude')
        self.sync(codex)
        self.edit('claim', codex)
        self.edit('checkpoint', codex, phase='progress', next_action='Run integration checks', evidence='tests/results.md')
        self.edit('release', codex)
        self.assertTrue(handoff.brief(self.project, claude)['needs_sync'])
        self.sync(claude)
        self.edit('claim', claude)
        self.edit('checkpoint', claude, phase='progress', next_action='Review patch', evidence='docs/test-evidence.md')
        self.edit('release', claude)
        report = handoff.brief(self.project, codex)
        self.assertTrue(report['needs_sync'])
        self.assertEqual(report['checkpoint']['participant'], claude)
        self.assertEqual(report['participants'][claude]['provider'], 'claude')
        with self.assertRaises(handoff.HandoffError):
            self.edit('claim', codex)
        self.sync(codex)
        self.edit('claim', codex)
        self.assertEqual(self.state()['owner'], codex)

    def test_claim_race_and_stale_release_cannot_overwrite_owner(self):
        actors = [self.join('codex'), self.join('claude')]
        for actor in actors:
            self.sync(actor)
        before = self.state()['revision']
        processes = [subprocess.Popen([sys.executable, str(ROOT / 'workflow/handoff.py'),
                                      '--project', str(self.project), 'claim', '--participant', actor,
                                      '--expect-revision', str(before), '--note', 'Concurrent claim'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for actor in actors]
        codes = []
        for process in processes:
            process.communicate(timeout=10)
            codes.append(process.returncode)
        self.assertEqual(sorted(codes), [0, 1])
        owner = self.state()['owner']
        other = next(actor for actor in actors if actor != owner)
        with self.assertRaises(handoff.HandoffError):
            handoff.change(self.project, 'release', other, before, note='Stale release')
        self.assertEqual(self.state()['owner'], owner)

    def test_takeover_requires_stopped_owner_and_reconciliation(self):
        a, b = self.join('codex'), self.join('claude')
        self.sync(a)
        self.edit('claim', a)
        self.edit('checkpoint', a, phase='starting', next_action='Verify external action', evidence='Recorded operation intent')
        self.sync(b)
        with self.assertRaises(handoff.HandoffError):
            self.edit('claim', b)
        with self.assertRaises(handoff.HandoffError):
            self.edit('recover', b, confirmed_owner_stopped=False, evidence='Unknown native status')
        self.edit('recover', b, confirmed_owner_stopped=True, evidence='Owner stopped; native process absence verified')
        self.assertTrue(self.state()['recovery_required'])
        with self.assertRaises(handoff.HandoffError):
            self.edit('checkpoint', b, phase='progress', next_action='Repeat action', evidence='No verification')
        with self.assertRaises(handoff.HandoffError):
            self.edit('release', b)
        self.edit('reconcile', b, evidence='Read-only provider check established actual effect; no replay')
        self.assertFalse(self.state()['recovery_required'])
        self.edit('release', b)

    def test_preserves_project_rules_and_policy_has_no_native_session_paths(self):
        self.assertTrue((self.project / 'AGENTS.md').read_text().startswith('Local Codex rules.\n'))
        self.assertTrue((self.project / 'CLAUDE.md').read_text().startswith('Local Claude rules.\n'))
        initial = (self.project / 'AGENTS.md').read_bytes()
        handoff.initialize(self.project, True)
        self.assertEqual((self.project / 'AGENTS.md').read_bytes(), initial)
        rules = Path(handoff.brief(self.project)['policy_path']).read_text()
        self.assertNotIn('{{CONTEXT}}', rules)
        self.assertNotIn('/.local/share/codex-work/sessions/', rules)
        self.assertIn('regardless of native launcher', rules)
        self.assertNotIn('not ordinary Codex launches', rules)
        self.assertIn('/.workbench/', (self.project / '.gitignore').read_text())

    def test_policy_update_invalidates_per_participant_receipt(self):
        actor = self.join('codex')
        self.sync(actor)
        old = self.state()['policy_revision']
        original = handoff.policy_sources()
        with patch.object(handoff, 'policy_sources', return_value=dict(original, **{'lifecycle.md': b'Changed policy'})):
            handoff.initialize(self.project, True)
        self.assertNotEqual(self.state()['policy_revision'], old)
        self.assertTrue(handoff.brief(self.project, actor)['needs_sync'])
        with self.assertRaises(handoff.HandoffError):
            self.edit('claim', actor)

    def test_lock_and_snapshot_tamper_fail_closed(self):
        with handoff.transaction(self.project):
            with self.assertRaises(handoff.HandoffError):
                self.join('claude')
        snapshot = Path(handoff.brief(self.project)['policy_path'])
        snapshot.write_text('Changed immutable policy')
        with self.assertRaises(handoff.HandoffError):
            self.join('claude')
        self.assertEqual(self.state_raw()['participants'], {})

    def state_raw(self):
        return json.loads((handoff.root(self.project) / 'state.json').read_text())

    def test_optional_gemini_loader_and_single_common_entry_preserve_local_rules(self):
        (self.project / 'GEMINI.md').write_text('Local Gemini instructions.\n')
        (self.project / 'WORKBENCH.md').write_text('Local project overview.\n' +
                                                  (self.project / 'WORKBENCH.md').read_text())
        handoff.initialize(self.project, True, with_gemini=True)
        self.assertTrue((self.project / 'GEMINI.md').read_text().startswith('Local Gemini instructions.\n'))
        self.assertTrue((self.project / 'WORKBENCH.md').read_text().startswith('Local project overview.\n'))
        snapshot = Path(handoff.brief(self.project)['policy_path']).parent
        index = snapshot / 'skills/project-bootstrap/references/roles/index.md'
        self.assertTrue(index.exists())
        self.assertNotIn((index.parent / 'networking.md').read_text(), (snapshot / 'rules.md').read_text())

    def test_old_transaction_never_cleans_replacement_lock(self):
        import shutil
        with handoff.transaction(self.project):
            folder = handoff.root(self.project)
            shutil.rmtree(folder / 'lock')
            (folder / 'lock').mkdir()
            (folder / 'lock/owner.json').write_text(json.dumps({'token': 'replacement-owner'}))
        self.assertEqual(json.loads((folder / 'lock/owner.json').read_text())['token'], 'replacement-owner')

    def test_move_guard_requires_released_owner(self):
        actor = self.join('codex')
        self.sync(actor)
        self.edit('claim', actor)
        with self.assertRaises(handoff.HandoffError):
            with handoff.move_guard(self.project):
                self.fail('Active editor must block moving a shared project')
        self.assertEqual(self.state()['owner'], actor)

    def test_failed_atomic_state_write_preserves_old_revision(self):
        before = self.state_raw()
        with patch.object(handoff, 'atomic', side_effect=OSError('Simulated publication failure')):
            with self.assertRaises(OSError):
                self.join('claude')
        self.assertEqual(self.state_raw(), before)
        self.join('codex')

    def test_actual_replace_failure_cleans_temp_and_preserves_state(self):
        before = (handoff.root(self.project) / 'state.json').read_bytes()
        with patch.object(handoff.Path, 'replace', side_effect=OSError('replace unavailable')):
            # Inject at the Path boundary: Python 3.10 caches its os accessor,
            # while newer versions dispatch os.replace dynamically. The real
            # temporary-file write/flush and failure cleanup still execute.
            with self.assertRaises(OSError):
                self.join('claude')
        self.assertEqual((handoff.root(self.project) / 'state.json').read_bytes(), before)
        self.assertFalse(list(handoff.root(self.project).glob('.write-*')))
        self.assertFalse((handoff.root(self.project) / 'lock').exists())

    def test_interrupted_init_preserves_exclusion_and_can_resume(self):
        fresh = self.project / 'interrupted'
        fresh.mkdir()
        original = handoff.atomic
        def fail_agents(path, data):
            if path.name == 'AGENTS.md':
                raise OSError('Interrupted loader publication')
            original(path, data)
        with patch.object(handoff, 'atomic', side_effect=fail_agents):
            with self.assertRaises(OSError):
                handoff.initialize(fresh, True)
        self.assertIn('/.workbench/', (fresh / '.gitignore').read_text())
        self.assertFalse((handoff.root(fresh) / 'state.json').exists())
        self.assertFalse((handoff.root(fresh) / 'lock').exists())
        handoff.initialize(fresh, True)
        self.assertIsNone(handoff.brief(fresh)['owner'])

    def test_symlinked_private_state_is_refused(self):
        folder = handoff.root(self.project)
        outside = self.project / 'outside-state.json'
        outside.write_bytes((folder / 'state.json').read_bytes())
        (folder / 'state.json').unlink()
        (folder / 'state.json').symlink_to(outside)
        with self.assertRaises(handoff.HandoffError):
            handoff.brief(self.project)

    def test_init_preview_writes_nothing_and_does_not_scan_ancestor_repo(self):
        fresh = self.project / 'new-project'
        fresh.mkdir()
        report = handoff.initialize(fresh)
        self.assertEqual(report['status'], 'preview')
        self.assertEqual(list(fresh.iterdir()), [])
        self.assertEqual(handoff.git_evidence(fresh)['git'], 'no_repository_at_project_root')
