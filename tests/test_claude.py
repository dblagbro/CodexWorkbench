import importlib.util
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('claude_adapter', ROOT / 'workflow/claude.py')
claude = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(claude)
ID = '019a5f00-1111-7111-8111-111111111111'


class ClaudeTests(unittest.TestCase):
    def test_official_sdk_metadata_excludes_prompt_fields(self):
        def metadata(**kwargs):
            self.assertEqual(kwargs['directory'], None)
            return [SimpleNamespace(session_id=ID, custom_title='Named task', summary='Title',
                                    first_prompt='PRIVATE BODY', cwd='/recorded/path', last_modified=7)]
        result = claude.list_sessions(sdk_list=metadata)
        self.assertTrue(result['complete'])
        self.assertNotIn('PRIVATE BODY', str(result))
        self.assertEqual(result['sessions'][0]['title'], 'Named task')

    def test_index_fallback_is_explicitly_incomplete_and_never_reads_jsonl(self):
        with tempfile.TemporaryDirectory() as folder:
            import json
            root = Path(folder)
            project = root / 'projects/encoded-with-hyphens'
            project.mkdir(parents=True)
            (project / 'sessions-index.json').write_text(json.dumps({'entries': [
                {'sessionId': ID, 'projectPath': '/exact/path-with-hyphens', 'summary': 'Title', 'firstPrompt': 'PRIVATE'}]}))
            (project / (ID + '.jsonl')).write_text('PRIVATE TRANSCRIPT MUST NOT BE READ')
            result = claude.metadata_indexes(root)
            self.assertFalse(result['complete'])
            self.assertEqual(result['sessions'][0]['project'], '/exact/path-with-hyphens')
            self.assertNotIn('PRIVATE', str(result))
            self.assertFalse((root / '.cache').exists())

    def test_resume_preserves_uuid_cwd_and_native_options(self):
        with tempfile.TemporaryDirectory() as folder:
            cwd, command = claude.resume_command({'id': ID, 'project': folder}, ['--model', 'sonnet', '--effort', 'high'])
            self.assertEqual(cwd, folder)
            self.assertEqual(command, ['claude', '--resume', ID, '--model', 'sonnet', '--effort', 'high'])

    def test_missing_or_relative_cwd_is_refused_without_guessing(self):
        for path in [None, 'relative/path', '/missing-workbench-test-path']:
            with self.subTest(path=path), self.assertRaises(claude.ClaudeError):
                claude.resume_command({'id': ID, 'project': path})

    def test_ambiguous_uuid_does_not_choose_arbitrary_project(self):
        rows = [{'id': ID, 'project': '/one'}, {'id': ID, 'project': '/two'}]
        with self.assertRaises(claude.ClaudeError):
            claude.select_session(rows, ID)
        self.assertEqual(claude.select_session(rows, ID, Path('/two'))['project'], '/two')

    def test_conflicting_identity_flags_are_not_forwarded(self):
        with tempfile.TemporaryDirectory() as folder:
            for flag in ['--fork-session', '--resume=other', '--session-id', '--continue']:
                with self.subTest(flag=flag), self.assertRaises(claude.ClaudeError):
                    claude.resume_command({'id': ID, 'project': folder}, [flag])

    def test_search_uses_metadata_and_invalid_selectors_are_refused(self):
        rows = [{'id': ID, 'title': 'Network repair', 'project': '/shared/project'}]
        self.assertEqual(claude.search_sessions(rows, 'NETWORK'), rows)
        for value in ['3', 'a task summary', '$(command)', '']:
            with self.subTest(value=value), self.assertRaises(claude.ClaudeError):
                claude.select_session(rows, value)

    def test_sdk_failure_does_not_fall_back_to_transcript_scan(self):
        def broken(**kwargs):
            raise RuntimeError('PRIVATE EXCEPTION DETAIL')
        with self.assertRaises(claude.ClaudeError) as caught:
            claude.list_sessions(sdk_list=broken)
        self.assertNotIn('PRIVATE', str(caught.exception))

    def test_dispatch_preserves_explicit_uuid_and_noninteractive_native_arguments(self):
        for original in [['--resume', ID, '--model', 'sonnet'], ['--resume', 'search words', '--model', 'sonnet']]:
            cwd, command = claude.dispatch_resume(original, interactive=False)
            self.assertIsNone(cwd)
            self.assertEqual(command, ['claude', *original])

    def test_dispatch_incomplete_metadata_falls_back_without_dropping_flags(self):
        original = ['--resume', 'topic', '--effort', 'high']
        cwd, command = claude.dispatch_resume(original, metadata={'complete': False, 'sessions': []}, interactive=True)
        self.assertIsNone(cwd)
        self.assertEqual(command, ['claude', *original])

    def test_dispatch_complete_metadata_picks_from_one_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            row = {'id': ID, 'project': folder, 'title': 'Network task'}
            seen = []
            def choose(rows):
                seen.append(rows)
                return rows[0]
            cwd, command = claude.dispatch_resume(['--resume', 'NETWORK', '--effort', 'high'],
                chooser=choose, metadata={'complete': True, 'sessions': [row]}, interactive=True)
            self.assertEqual(seen, [[row]])
            self.assertEqual(cwd, folder)
            self.assertEqual(command, ['claude', '--resume', ID, '--effort', 'high'])

    def test_explicit_native_fork_flag_uses_native_picker_unchanged(self):
        original = ['--resume', '--fork-session']
        cwd, command = claude.dispatch_resume(original, metadata={'complete': True, 'sessions': []}, interactive=True)
        self.assertIsNone(cwd)
        self.assertEqual(command, ['claude', *original])


if __name__ == '__main__':
    unittest.main()
