import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest

CHECK = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/security-check.py'))


class SecurityInventoryTests(unittest.TestCase):
    def fixture(self, root):
        (root / 'config').mkdir()
        (root / '.github/workflows').mkdir(parents=True)
        (root / 'requirements-claude.txt').write_text('example==1.0\n')
        (root / '.github/workflows/ci.yml').write_text('reviewed workflow\n')
        for target in ('310', '312'):
            (root / ('requirements-audit-' + target + '.txt')).write_text('example==1.0\n')
        provenance = {'source_sha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                      for name in ('requirements-claude.txt', '.github/workflows/ci.yml')},
                      'resolved_pins': {'3.10': {'example': '1.0'}, '3.12': {'example': '1.0'}}, 'python_targets': ['3.10', '3.12']}
        (root / 'config/dependency-audit.json').write_text(json.dumps(provenance))

    def test_stale_sources_rejected_before_egress(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            self.assertEqual(CHECK['inventory'](root)['3.10'], {'example': '1.0'})
            (root / 'requirements-claude.txt').write_text('example==2.0\n')
            with self.assertRaisesRegex(ValueError, 'sources changed'):
                CHECK['inventory'](root)

    def test_unreviewed_or_executable_requirements_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            for text in ('example==2.0\n', '-r private.txt\n', 'example @ https://invalid.test/code\n',
                         'example==1.0\nexample==1.0\n'):
                (root / 'requirements-audit-310.txt').write_text(text)
                with self.assertRaises(ValueError):
                    CHECK['inventory'](root)

    def test_missing_source_cannot_disable_stale_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            path = root / 'config/dependency-audit.json'
            provenance = json.loads(path.read_text())
            del provenance['source_sha256']['requirements-claude.txt']
            path.write_text(json.dumps(provenance))
            (root / 'requirements-claude.txt').write_text('example==2.0\n')
            with self.assertRaisesRegex(ValueError, 'source coverage'):
                CHECK['inventory'](root)

    def test_shallow_history_is_not_reported_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            clone = root / 'clone'
            subprocess.run(['git', 'init', str(source)], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty',
                            '-m', 'Synthetic shallow history fixture'], check=True, capture_output=True)
            subprocess.run(['git', 'clone', '--depth=1', source.as_uri(), str(clone)],
                           check=True, capture_output=True)
            check = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/security-check.py'))
            check['secrets'].__globals__['ROOT'] = clone
            with self.assertRaisesRegex(ValueError, 'unshallow'):
                check['secrets'](root / 'not-executed')


if __name__ == '__main__':
    unittest.main()
