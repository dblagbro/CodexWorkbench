import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / 'workflow/install-portable.py'


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        self.capture = self.home / 'captured.json'
        fake = self.bin / 'codex'
        fake.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
if args == ['--version']:
    print('codex-cli test-version')
elif args == ['--help']:
    print('test help: --cd --sandbox --ask-for-approval')
elif args == ['features', 'list']:
    print('multi_agent stable true')
else:
    Path(os.environ['CAPTURE']).write_text(json.dumps(args))
''')
        fake.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home),
                        CODEX_HOME=str(self.home / '.codex'),
                        CODEX_CODE_SETTINGS=str(self.home / '.config/codex-code/settings.json'),
                        CAPTURE=str(self.capture), PATH=str(self.bin) + os.pathsep + os.environ['PATH'])

    def setup_install(self, *extra):
        return subprocess.run([sys.executable, str(INSTALLER), '--home', str(self.home), *extra],
                              env=self.env, cwd=ROOT, capture_output=True, text=True, timeout=20)

    def shell(self, *args):
        shell = self.home / '.local/share/codex-code/code-shell.bash'
        return subprocess.run(['bash', '--noprofile', '--norc', '-c',
                               'source "$1"; shift; codex "$@"', 'test', str(shell), *args],
                              env=self.env, cwd=self.home, capture_output=True, text=True, timeout=20)

    def test_preview_does_not_install(self):
        result = self.setup_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.home / '.local').exists())
        self.assertFalse((self.home / '.bashrc').exists())

    def test_installer_preserves_global_rules_and_is_idempotent(self):
        codex = self.home / '.codex'
        codex.mkdir()
        (codex / 'AGENTS.md').write_text('Existing global instructions\n')
        (codex / 'config.toml').write_text('model="existing-model"\n')
        (self.home / '.bashrc').write_text('# existing shell content\n')
        for _ in range(2):
            result = self.setup_install('--apply')
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((codex / 'AGENTS.md').read_text(), 'Existing global instructions\n')
        self.assertEqual((codex / 'config.toml').read_text(), 'model="existing-model"\n')
        text = (self.home / '.bashrc').read_text()
        self.assertIn('# existing shell content', text)
        self.assertEqual(text.count('# Codex portable project workflow'), 1)
        self.assertFalse((self.home / '.agents').exists())
        self.assertEqual(len(list((self.home / '.local/state/codex-code/backups').iterdir())), 1)

    def test_every_non_code_call_is_exact_passthrough(self):
        self.assertEqual(self.setup_install('--apply').returncode, 0)
        cases = [[], ['--help'], ['exec', 'a prompt', ''], ['resume', '--last'],
                 ['--unknown', 'a b', '$literal'],
                 ['--model', 'chosen', '--code']]
        for args in cases:
            with self.subTest(args=args):
                # --help is handled specially by the fake CLI, like the real executable.
                if self.capture.exists():
                    self.capture.unlink()
                result = self.shell(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                if args != ['--help']:
                    self.assertEqual(json.loads(self.capture.read_text()), args)
                self.assertEqual(list((self.home / '.local/share/codex-work/sessions').iterdir()), [])

    def test_code_launch_snapshots_baseline_and_host_context(self):
        self.assertEqual(self.setup_install('--apply').returncode, 0)
        result = self.shell('--code', 'Build a useful utility')
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(self.capture.read_text())
        folder = Path(args[args.index('--cd') + 1])
        self.assertEqual(folder.parent, self.home / '.local/share/codex-work/sessions')
        state = json.loads((folder / 'state.json').read_text())
        self.assertEqual(state['kind'], 'draft')
        self.assertEqual(Path(state['workdir']), folder / 'draft')
        receipt = json.loads((folder / 'workbench/policy.json').read_text())
        snapshot = folder / 'workbench/policy-revisions' / receipt['revision']
        self.assertIn(str(snapshot / 'instructions.md'), (folder / 'AGENTS.md').read_text())
        instructions = (snapshot / 'instructions.md').read_text()
        self.assertIn('Code-mode baseline', instructions)
        self.assertIn(str(self.home / 'code'), instructions)
        self.assertNotIn('{{', instructions)
        self.assertIn('docker compose', instructions)
        inventory = json.loads((snapshot / 'inventory.json').read_text())
        self.assertEqual(inventory['probes']['codex_version']['output'], 'codex-cli test-version')
        self.assertEqual(inventory['workflow_paths']['project_root'], str(self.home / 'code'))
        self.assertTrue((self.home / 'code').is_dir())
        self.assertIn(str(self.home / 'code'), [args[i + 1] for i, arg in enumerate(args) if arg == '--add-dir'])
        self.assertTrue((snapshot / 'lifecycle.md').is_file())
        self.assertTrue((snapshot / 'skills/project-bootstrap/scripts/inventory.py').is_file())
        self.assertNotIn('chrome-devtools-mcp@latest', ' '.join(args))

    def test_resume_shortcuts_use_saved_directory_without_baseline_overrides(self):
        self.assertEqual(self.setup_install('--apply').returncode, 0)
        for shortcut in ['-cr', '--coderesume']:
            with self.subTest(shortcut=shortcut):
                result = self.shell(shortcut, 'session with spaces', '')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(self.capture.read_text()),
                                 ['resume', '--all', '-c', 'tui.resume_cwd="session"', 'session with spaces', ''])
                self.assertEqual(list((self.home / '.local/share/codex-work/sessions').iterdir()), [])
        shell = self.home / '.local/share/codex-code/code-shell.bash'
        result = subprocess.run(['bash', '--noprofile', '--norc', '-c',
                                 'source "$1"; cxr', 'test', str(shell)],
                                env=self.env, cwd=self.home, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.capture.read_text()), ['resume', '--all', '-c', 'tui.resume_cwd="session"'])
        result = self.shell('--code', '--resume')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.capture.read_text()), ['resume', '--all', '-c', 'tui.resume_cwd="session"'])

    def test_open_shell_reloads_updated_launcher_on_next_resume(self):
        self.assertEqual(self.setup_install('--apply').returncode, 0)
        shell = self.home / '.local/share/codex-code/code-shell.bash'
        updated = self.home / 'updated-shell.bash'
        updated.write_text(shell.read_text().replace(
            'command codex resume --all', 'command codex resume --all --no-alt-screen'))
        result = subprocess.run(['bash', '--noprofile', '--norc', '-c',
                                 'source "$1"; cp "$2" "$1"; codex -cr; codex --code --resume',
                                 'test', str(shell), str(updated)], env=self.env, cwd=self.home,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.capture.read_text()),
                         ['resume', '--all', '--no-alt-screen', '-c', 'tui.resume_cwd="session"'])

    def test_one_off_placement_still_works(self):
        self.assertEqual(self.setup_install('--apply').returncode, 0)
        result = self.shell('--code', '--one-off', 'Try a small script')
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(self.capture.read_text())
        folder = Path(args[args.index('--cd') + 1])
        state = json.loads((folder / 'state.json').read_text())
        self.assertEqual(state['kind'], 'one-off')
        self.assertEqual(Path(state['workdir']).parent, self.home / 'scratch')
        self.assertFalse((folder / 'draft').exists())
        self.assertFalse((Path(state['workdir']) / 'WORKBENCH.md').exists())
        self.assertFalse((Path(state['workdir']) / '.workbench/handoff/state.json').exists())
        self.assertTrue((folder / 'AGENTS.md').exists())
        receipt = json.loads((folder / 'workbench/policy.json').read_text())
        inventory = json.loads((folder / 'workbench/policy-revisions' / receipt['revision'] / 'inventory.json').read_text())
        self.assertEqual(inventory['project'], state['workdir'])

    def test_missing_external_storage_is_not_created(self):
        external = self.home.parent / ('missing-share-' + self.home.name)
        result = self.setup_install('--apply', '--project-root', str(external))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('External storage root is missing', result.stderr)
        self.assertFalse(external.exists())
        self.assertFalse((self.home / '.bashrc').exists())

    def test_linked_worktree_is_not_moved(self):
        self.assertEqual(self.setup_install('--apply').returncode, 0)
        folder = self.home / '.local/share/codex-work/sessions/test-linked'
        source = folder / 'draft'
        source.mkdir(parents=True)
        (source / '.git').write_text('gitdir: /some/other/repository/worktrees/test\n')
        (folder / 'state.json').write_text(json.dumps({'workdir': str(source), 'kind': 'draft', 'name': None}))
        helper = self.home / '.local/share/codex-code/code-workflow.py'
        result = subprocess.run([sys.executable, str(helper), 'place', '--session', str(folder), '--name', 'Linked'],
                                env=self.env, cwd=self.home, capture_output=True, text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(source.is_dir())
        self.assertFalse((self.home / 'code/Linked').exists())

    def test_direct_resume_helper_adds_no_workbench_options(self):
        self.assertEqual(self.setup_install('--apply').returncode, 0)
        helper = self.home / '.local/share/codex-code/code-workflow.py'
        result = subprocess.run([sys.executable, str(helper), 'resume', '--last'],
                                env=self.env, cwd=self.home, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.capture.read_text()), ['resume', '--last'])

    def new_draft(self):
        self.assertEqual(self.setup_install('--apply').returncode, 0)
        result = self.shell('--code', 'Build a useful tool')
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(self.capture.read_text())
        folder = Path(args[args.index('--cd') + 1])
        return folder, self.home / '.local/share/codex-code/code-workflow.py'

    def helper(self, helper, folder, action, *args):
        return subprocess.run([sys.executable, str(helper), action, '--session', str(folder), *args],
                              env=self.env, cwd=self.home, capture_output=True, text=True, timeout=20)

    def test_project_placement_queues_actual_folder_title_and_requires_acknowledgement(self):
        folder, helper = self.new_draft()
        result = self.helper(helper, folder, 'place', '--name', 'My Project')
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((folder / 'state.json').read_text())
        self.assertEqual(state['desired_title'], 'My-Project')
        project = Path(state['workdir'])
        self.assertTrue((project / 'WORKBENCH.md').exists())
        self.assertTrue((project / 'CLAUDE.md').exists())
        self.assertTrue((project / '.workbench/handoff/state.json').exists())
        self.assertEqual(state['title_sync'], 'pending')
        self.assertNotIn('display_title', state)
        wrong = self.helper(helper, folder, 'ack-title', '--title', 'Wrong')
        self.assertNotEqual(wrong.returncode, 0)
        self.assertEqual(json.loads((folder / 'state.json').read_text())['title_sync'], 'pending')
        ack = self.helper(helper, folder, 'ack-title', '--title', 'My-Project')
        self.assertEqual(ack.returncode, 0, ack.stderr)
        state = json.loads((folder / 'state.json').read_text())
        self.assertEqual(state['display_title'], 'My-Project')
        self.assertEqual(state['title_sync'], 'synced')

    def test_project_rename_queues_new_title_without_changing_session_root(self):
        folder, helper = self.new_draft()
        self.assertEqual(self.helper(helper, folder, 'place', '--name', 'Original').returncode, 0)
        self.assertEqual(self.helper(helper, folder, 'ack-title', '--title', 'Original').returncode, 0)
        result = self.helper(helper, folder, 'place', '--name', 'Renamed')
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((folder / 'state.json').read_text())
        self.assertEqual(Path(state['workdir']).name, 'Renamed')
        shared = json.loads((Path(state['workdir']) / '.workbench/handoff/state.json').read_text())
        self.assertEqual(shared['project'], state['workdir'])
        self.assertEqual(shared['events'][-1]['kind'], 'project_moved')
        self.assertEqual(state['desired_title'], 'Renamed')
        self.assertEqual(state['display_title'], 'Original')
        self.assertEqual(state['title_sync'], 'pending')
        self.assertTrue((folder / 'AGENTS.md').is_file())

    def test_custom_title_survives_folder_rename_until_explicitly_restored(self):
        folder, helper = self.new_draft()
        self.assertEqual(self.helper(helper, folder, 'place', '--name', 'Original').returncode, 0)
        self.assertEqual(self.helper(helper, folder, 'ack-title', '--title', 'Investigation', '--custom').returncode, 0)
        result = self.helper(helper, folder, 'place', '--name', 'Renamed')
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((folder / 'state.json').read_text())
        self.assertEqual(state['desired_title'], 'Investigation')
        self.assertEqual(state['display_title_mode'], 'custom')
        self.assertEqual(state['title_sync'], 'synced')
        result = self.helper(helper, folder, 'ack-title', '--title', 'Renamed', '--follow-folder')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((folder / 'state.json').read_text())['display_title_mode'], 'project')

    def test_renaming_adopted_existing_project_does_not_enroll_it(self):
        folder, helper = self.new_draft()
        existing = self.home / 'code/ExistingUnenrolled'
        existing.mkdir()
        (existing / 'AGENTS.md').write_text('Existing local rules.\n')
        self.assertEqual(self.helper(helper, folder, 'adopt', '--project', str(existing)).returncode, 0)
        result = self.helper(helper, folder, 'place', '--name', 'ExistingRenamed')
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.home / 'code/ExistingRenamed'
        self.assertEqual((target / 'AGENTS.md').read_text(), 'Existing local rules.\n')
        self.assertFalse((target / 'WORKBENCH.md').exists())
        self.assertFalse((target / '.workbench').exists())

    def test_adopting_existing_project_queues_title_without_moving_files(self):
        folder, helper = self.new_draft()
        existing = self.home / 'code/Established'
        existing.mkdir()
        (existing / 'keep.txt').write_text('existing data')
        (folder / 'draft/draft.txt').write_text('draft data')
        result = self.helper(helper, folder, 'adopt', '--project', str(existing))
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((folder / 'state.json').read_text())
        self.assertEqual(state['workdir'], str(existing))
        self.assertFalse((existing / 'WORKBENCH.md').exists())
        self.assertEqual(state['desired_title'], 'Established')
        self.assertEqual((existing / 'keep.txt').read_text(), 'existing data')
        self.assertEqual((folder / 'draft/draft.txt').read_text(), 'draft data')
        self.assertFalse((existing / 'draft.txt').exists())


if __name__ == '__main__':
    unittest.main()
