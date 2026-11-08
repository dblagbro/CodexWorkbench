#!/usr/bin/env python3
"""Offline distribution checks. Not a comprehensive secret scanner or live-provider QA."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import runpy
import shlex
import subprocess
import sys
import tarfile
import tempfile
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_NAMES = {
    'status.md', 'initial-assessment.md', 'bootstrap-inventory.json',
    'policy-upgrade-evidence.json', 'release-evidence.json', 'email-update.html',
    'plan.json', 'state.json', 'auth.json', 'settings.json',
}
PRIVATE_PARTS = {'.workbench', '.codex', '.claude', '.git', '.venv', '__pycache__', 'backups'}
CLI_FILES = (
    'workflow/code-workflow.py', 'workflow/install-portable.py',
    'workflow/remote-control.py', 'workflow/resume.py', 'workflow/coordinator.py',
    'workflow/policy.py', 'workflow/claude.py', 'workflow/handoff.py',
    'skills/project-bootstrap/scripts/inventory.py',
    'skills/project-bootstrap/scripts/unattended-plan.py',
)


class VerificationError(Exception):
    pass


def execute(command, cwd, env=None):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise VerificationError('Command failed: ' + shlex.join(map(str, command)) + '\n' + result.stderr)
    return result


def markdown_targets(text):
    # Validate destinations, not prose examples or fenced code. Anchors are separate.
    text = re.sub(r'(?ms)^\s*(`{3,}|~{3,}).*?^\s*\1\s*$', '', text)
    inline = re.findall(r'!?\[[^\]\n]*\]\(\s*(<[^>\n]+>|[^\s)]+)', text)
    references = re.findall(r'(?m)^\s*\[[^\]\n]+\]:\s*(<[^>\n]+>|\S+)', text)
    return [value[1:-1] if value.startswith('<') else value for value in inline + references]


def check_links(root, markdown_paths):
    checked = 0
    failures = []
    root = root.resolve()
    for relative in markdown_paths:
        source = root / relative
        if source.name in PRIVATE_NAMES:
            continue
        for target in markdown_targets(source.read_text()):
            if target.startswith('#') or urlsplit(target).scheme or target.startswith('//'):
                continue
            path = unquote(urlsplit(target).path)
            if not path:
                continue
            destination = (root / path.lstrip('/') if path.startswith('/') else source.parent / path).resolve()
            if not destination.is_relative_to(root):
                failures.append(str(relative) + ': destination leaves repository: ' + target)
            elif destination.name in PRIVATE_NAMES:
                # Local operational evidence is intentionally absent from public clones.
                continue
            elif not destination.exists():
                failures.append(str(relative) + ': missing local destination: ' + target)
            else:
                checked += 1
    if failures:
        raise VerificationError('\n'.join(failures))
    return checked


def read_archive(path, required, version):
    files = {}
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if not member.isfile() or name.is_absolute() or '..' in name.parts or len(name.parts) < 2 or name.parts[0] != 'codex-workbench':
                raise VerificationError('Unsafe archive entry: ' + member.name)
            relative = str(PurePosixPath(*name.parts[1:]))
            if relative in files:
                raise VerificationError('Repeated archive entry: ' + relative)
            if name.name in PRIVATE_NAMES or set(name.parts) & PRIVATE_PARTS or name.name.startswith('.env') or name.suffix in ('.sqlite', '.db', '.log', '.jsonl', '.pyc'):
                raise VerificationError('Private/runtime archive entry: ' + relative)
            stream = archive.extractfile(member)
            files[relative] = stream.read()
    missing = set(required) - set(files)
    if missing:
        raise VerificationError('Archive missing required files: ' + ', '.join(sorted(missing)))
    if 'RELEASE.json' not in files:
        raise VerificationError('Archive has no release manifest')
    manifest = json.loads(files['RELEASE.json'])
    if manifest.get('version') != version:
        raise VerificationError('Archive release version differs from source')
    actual = {name: hashlib.sha256(content).hexdigest() for name, content in files.items() if name != 'RELEASE.json'}
    if manifest.get('sha256') != actual:
        raise VerificationError('Release manifest does not match archive contents')
    for name, content in required.items():
        if content is not None and files[name] != content:
            raise VerificationError('Archive payload differs from current source: ' + name)
    return files


def private_environment(folder):
    home = folder / 'home'
    home.mkdir()
    bin_dir = folder / 'bin'
    bin_dir.mkdir()
    called = folder / 'unexpected-native-command'
    for name in ('codex', 'claude', 'ssh', 'systemctl', 'curl', 'docker', 'npm', 'pip'):
        executable = bin_dir / name
        executable.write_text('#!/bin/sh\nprintf "%s\\n" "$0" >> ' + shlex.quote(str(called)) + '\nexit 99\n')
        executable.chmod(0o700)
    # Do not inherit provider credentials, real homes, proxies, or native CLI paths.
    env = {
        'HOME': str(home), 'PATH': str(bin_dir), 'CODEX_HOME': str(home / '.codex'),
        'CODEX_CODE_SETTINGS': str(home / '.config/codex-code/settings.json'),
        'XDG_CONFIG_HOME': str(home / '.config'), 'XDG_STATE_HOME': str(home / '.local/state'),
        'XDG_CACHE_HOME': str(home / '.cache'), 'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C.UTF-8',
    }
    return home, env, called


def smoke_install(files):
    with tempfile.TemporaryDirectory(prefix='workbench-distribution-') as temporary:
        folder = Path(temporary)
        source = folder / 'source'
        source.mkdir()
        for name, content in files.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        home, env, native_called = private_environment(folder)
        installer = source / 'workflow/install-portable.py'
        common = [sys.executable, str(installer), '--home', str(home), '--project-root', str(home / 'code'), '--chrome', 'off']
        execute(common, source, env)
        if (home / '.bashrc').exists() or (home / '.local/share/codex-code').exists():
            raise VerificationError('Installer preview unexpectedly wrote installed state')
        execute(common + ['--apply'], source, env)
        installed = home / '.local/share/codex-code'
        for name in CLI_FILES:
            relative = name.removeprefix('workflow/') if name.startswith('workflow/') else name
            script = installed / relative
            result = execute([sys.executable, str(script), '--help'], home, env)
            if 'usage:' not in result.stdout.lower():
                raise VerificationError('CLI help is missing usage: ' + relative)
        if native_called.exists():
            raise VerificationError('Offline help/install smoke attempted a native command')
        for name in ('code-shell.bash', 'claude-shell.bash', 'handoff.py'):
            if not (installed / name).is_file():
                raise VerificationError('Installed payload missing: ' + name)
        return len(CLI_FILES)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Default: archive for the current source release version')
    args = parser.parse_args()
    try:
        release = runpy.run_path(str(ROOT / 'scripts/build-release.py'))
        version = release['VERSION']
        installer = runpy.run_path(str(ROOT / 'workflow/install-portable.py'))
        payload = installer['payload'](ROOT / 'workflow')
        required = {str(path if path.parts[0] == 'skills' else Path('workflow') / path): content for path, content in payload.items()}
        required.update({name: None for name in ('README.md', 'LICENSE', 'requirements-claude.txt', 'docs/commands-and-installation.md', 'docs/Codex-Workbench-One-Page.pdf')})
        tracked = execute(['git', 'ls-files', '-z', '--', '*.md'], ROOT).stdout.split('\0')
        links = check_links(ROOT, [Path(name) for name in tracked if name])
        archive = args.archive or ROOT / 'artifacts' / version / ('codex-workbench-' + version + '.tar.gz')
        files = read_archive(archive, required, version)
        helps = smoke_install(files)
        print(json.dumps({'status': 'passed', 'version': version, 'local_links_checked': links,
                          'archive_files_checked': len(files), 'installed_cli_help_checks': helps,
                          'limits': 'Offline fixtures only; filename exclusions are not comprehensive secret scanning. No live provider/UI/deployment validation.'}))
    except (VerificationError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        parser.exit(1, 'Distribution verification failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
