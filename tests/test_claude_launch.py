"""Exercise provider launch boundaries with a fake native CLI, without model calls."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]


class ClaudeLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.install = self.home / 'installed'
        shutil.copytree(ROOT / 'workflow', self.install, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(ROOT / 'skills/project-bootstrap', self.install / 'skills/project-bootstrap')
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        self.capture = self.home / 'capture.json'
        fake = self.bin / 'claude'
        fake.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
if sys.argv[1:] == ['--help']:
    print(os.environ.get('FAKE_HELP', '--session-id --append-system-prompt --add-dir'))
elif sys.argv[1:] == ['--version']:
    print('2.1.test')
else:
    Path(os.environ['CAPTURE']).write_text(json.dumps({'args':sys.argv[1:], 'cwd':os.getcwd()}))
''')
        fake.chmod(0o755)
        self.sessions = self.home / 'sessions'
        self.projects = self.home / 'projects'
        self.projects.mkdir()
        self.scratch = self.home / 'scratch'
        settings = self.home / 'settings.json'
        settings.write_text(json.dumps({'session_root':str(self.sessions), 'project_root':str(self.projects),
                                        'scratch_root':str(self.scratch), 'remote_control':True}))
        self.env = dict(os.environ, HOME=str(self.home), CODEX_CODE_SETTINGS=str(settings),
                        CLAUDE_CONFIG_DIR=str(self.home / '.claude'), CAPTURE=str(self.capture),
                        PATH=str(self.bin) + os.pathsep + os.environ['PATH'])

    def shell(self, *args):
        return subprocess.run(['bash','--noprofile','--norc','-c',
                               'source "$1"; shift; claude "$@"','test',
                               str(self.install / 'claude-shell.bash'),*args],
                              cwd=self.home, env=self.env, capture_output=True, text=True, timeout=30)

    def test_plain_and_explicit_uuid_resume_are_native(self):
        for args in [('hello world','--model','sonnet'),
                     ('--resume','01234567-89ab-4cde-8fab-0123456789ab','--model','opus')]:
            result = self.shell(*args)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(self.capture.read_text()), {'args':list(args),'cwd':str(self.home)})
        self.assertFalse(self.sessions.exists())

    def test_noninteractive_bare_resume_preserves_native_flags(self):
        args = ['--resume','--model','sonnet']
        result = self.shell(*args)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.capture.read_text())['args'],args)
        self.assertFalse(self.sessions.exists())

    def test_opt_in_launch_creates_scoped_claude_policy_and_native_identity(self):
        result = self.shell('--code','build a tool')
        self.assertEqual(result.returncode,0,result.stderr)
        folders = list(self.sessions.iterdir())
        self.assertEqual(len(folders),1)
        folder = folders[0]
        state = json.loads((folder / 'state.json').read_text())
        self.assertEqual(state['engine'],'claude')
        self.assertEqual(str(uuid.UUID(state['native_id'])), state['native_id'])
        captured = json.loads(self.capture.read_text())
        args = captured['args']
        self.assertEqual(captured['cwd'],str(folder))
        self.assertEqual(args[args.index('--session-id')+1],state['native_id'])
        self.assertTrue((folder / 'CLAUDE.md').is_file())
        self.assertFalse((folder / 'AGENTS.md').exists())
        instructions = next((folder / 'workbench/policy-revisions').glob('*/instructions.md')).read_text()
        self.assertIn('claude --code',instructions)
        self.assertNotIn('{{LAUNCH_COMMAND}}',instructions)
        self.assertIn('build a tool',args[-1])
        self.assertEqual(args[-2],'--')
        self.assertIn(str(self.projects),args)
        self.assertIn(str(self.scratch),args)
        for forbidden in ('--sandbox','--ask-for-approval','--dangerously-skip-permissions','--remote-control'):
            self.assertNotIn(forbidden,args)

    def test_unsupported_cli_fails_before_creating_session(self):
        self.env['FAKE_HELP'] = '--session-id --add-dir'
        result = self.shell('--code','test')
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(self.sessions.exists())
        self.assertFalse(self.capture.exists())

    def test_upgrade_selects_claude_policy_without_launching(self):
        (self.install / 'policy.py').write_text("import json,os,sys\nfrom pathlib import Path\nPath(os.environ['CAPTURE']).write_text(json.dumps(sys.argv[1:]))\n")
        result = self.shell('--code','--upgrade','--list')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.capture.read_text()),['--engine','claude','--list'])
        self.assertFalse(self.sessions.exists())


if __name__ == '__main__':
    unittest.main()
