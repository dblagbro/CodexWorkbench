import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('distribution', ROOT / 'scripts/verify-distribution.py')
distribution = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(distribution)


class DistributionTests(unittest.TestCase):
    def test_local_links_reject_missing_or_escaping_destinations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'guide.md').write_text('# Guide\n')
            (root / 'README.md').write_text('[guide](guide.md#section)\n[external](https://example.invalid)\n[private](docs/status.md)\n[anchor](#heading)\n')
            self.assertEqual(distribution.check_links(root, [Path('README.md')]), 1)
            (root / 'README.md').write_text('[missing](missing.md)\n')
            with self.assertRaises(distribution.VerificationError):
                distribution.check_links(root, [Path('README.md')])
            (root / 'README.md').write_text('[escape](../outside.md)\n')
            with self.assertRaises(distribution.VerificationError):
                distribution.check_links(root, [Path('README.md')])

    def archive(self, path, files, manifest=None):
        hashes = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
        data = dict(files, **{'RELEASE.json': json.dumps(manifest or {'version': 'fixture', 'sha256': hashes}).encode()})
        with tarfile.open(path, 'w:gz') as archive:
            for name, content in data.items():
                entry = tarfile.TarInfo('codex-workbench/' + name)
                entry.size = len(content)
                archive.addfile(entry, io.BytesIO(content))

    def test_archive_requires_current_payload_and_matching_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'fixture.tar.gz'
            self.archive(archive, {'workflow/tool.py': b'current'})
            result = distribution.read_archive(archive, {'workflow/tool.py': b'current'}, 'fixture')
            self.assertEqual(result['workflow/tool.py'], b'current')
            with self.assertRaises(distribution.VerificationError):
                distribution.read_archive(archive, {'workflow/new.py': b'new'}, 'fixture')
            with self.assertRaises(distribution.VerificationError):
                distribution.read_archive(archive, {'workflow/tool.py': b'changed'}, 'fixture')
            self.archive(archive, {'workflow/tool.py': b'current'}, {'version': 'fixture', 'sha256': {}})
            with self.assertRaises(distribution.VerificationError):
                distribution.read_archive(archive, {}, 'fixture')

    def test_unsafe_and_private_archive_entries_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'fixture.tar.gz'
            for name in ('../escape', '.workbench/handoff/state.json', '.env.local', 'docs/status.md', 'backups/data.bin'):
                with self.subTest(name=name):
                    self.archive(archive, {name: b'private or unsafe'})
                    with self.assertRaises(distribution.VerificationError):
                        distribution.read_archive(archive, {}, 'fixture')
            with tarfile.open(archive, 'w:gz') as bundle:
                entry = tarfile.TarInfo('codex-workbench/link')
                entry.type = tarfile.SYMTYPE
                entry.linkname = '/outside'
                bundle.addfile(entry)
            with self.assertRaises(distribution.VerificationError):
                distribution.read_archive(archive, {}, 'fixture')
