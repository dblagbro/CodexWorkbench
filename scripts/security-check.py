#!/usr/bin/env python3
"""Approved security checks. Reports stay local and redacted; no automatic fixes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def inventory(root=ROOT):
    """Reject stale audit input before asking a vulnerability service about pins."""
    provenance = json.loads((root / 'config/dependency-audit.json').read_text())
    if set(provenance['source_sha256']) != {'requirements-claude.txt', '.github/workflows/ci.yml'}:
        raise ValueError('Incomplete dependency source coverage')
    for name, expected in provenance['source_sha256'].items():
        if name not in ('requirements-claude.txt', '.github/workflows/ci.yml'):
            raise ValueError('Unexpected dependency source')
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Dependency sources changed; regenerate and review the audit inventory')
    if provenance['python_targets'] != ['3.10', '3.12']:
        raise ValueError('Missing supported Python audit target')
    targets = {}
    for target in provenance['python_targets']:
        pins = {}
        path = root / ('requirements-audit-' + target.replace('.', '') + '.txt')
        for line in path.read_text().splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            if not re.fullmatch(r'[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+', line):
                raise ValueError('Audit inventory accepts exact reviewed pins only')
            name, version = line.split('==')
            name = re.sub(r'[-_.]+', '-', name).lower()
            if name in pins:
                raise ValueError('Duplicate audit pin')
            pins[name] = version
        if pins != provenance['resolved_pins'][target] or not pins:
            raise ValueError('Audit inventory differs from reviewed resolution')
        targets[target] = pins
    return targets


def dependencies():
    targets = inventory()
    # No package resolution, installation of audited code, fixes, or report upload.
    for target, pins in targets.items():
        with tempfile.TemporaryDirectory(prefix='workbench-audit-') as temp:
            report = Path(temp) / 'audit.json'
            requirements = ROOT / ('requirements-audit-' + target.replace('.', '') + '.txt')
            result = subprocess.run([sys.executable, '-m', 'pip_audit', '--disable-pip',
                                     '--no-deps', '--progress-spinner', 'off', '--format', 'json',
                                     '--output', str(report), '-r', str(requirements)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
            if result.returncode != 0:
                if report.exists():
                    data = json.loads(report.read_text())
                    for item in data.get('dependencies', []):
                        for vuln in item.get('vulns', []):
                            print(json.dumps({'package': item['name'], 'version': item['version'],
                                              'advisory': vuln['id'], 'fix_versions': vuln.get('fix_versions', [])}))
                raise ValueError('Dependency audit failed; inspect locally, never auto-fix or ignore')
            data = json.loads(report.read_text())
            observed = {re.sub(r'[-_.]+', '-', item['name']).lower(): item['version']
                        for item in data['dependencies'] if 'skip_reason' not in item}
            if observed != pins or any(item.get('vulns') or item.get('skip_reason') for item in data['dependencies']):
                raise ValueError('Dependency audit incomplete or vulnerable')
            print(json.dumps({'status': 'passed', 'python': target, 'audited_pins': len(pins), 'automatic_fixes': False}))


def secrets(tool):
    shallow = subprocess.check_output(['git', 'rev-parse', '--is-shallow-repository'], cwd=ROOT, text=True).strip()
    if shallow != 'false':
        raise ValueError('Full-history checking requires an unshallow Git repository')
    if any((ROOT / name).exists() for name in ('.gitleaks.toml', '.gitleaksignore')):
        raise ValueError('Repository scanner overrides require a separately reviewed security-policy change')
    tool = tool.resolve(strict=True)
    expected = json.loads((ROOT / 'config/security-tools.proposed.json').read_text())['gitleaks']['binary_sha256']
    if hashlib.sha256(tool.read_bytes()).hexdigest() != expected:
        raise ValueError('Gitleaks executable does not match approved checksum')
    with tempfile.TemporaryDirectory(prefix='workbench-secrets-') as temp:
        temp = Path(temp)
        env = {key: value for key, value in os.environ.items()
               if key in ('PATH', 'HOME', 'TMPDIR', 'SYSTEMROOT', 'SSL_CERT_FILE', 'SSL_CERT_DIR')}
        def scan(arguments, label, expected_code=0):
            report = temp / (label + '.json')
            result = subprocess.run([str(tool)] + arguments + ['--redact=100', '--no-banner',
                                    '--no-color', '--report-format=json', '--report-path', str(report)],
                                    cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
            if result.returncode != expected_code:
                raise ValueError('Secret check failed: ' + label + '; raw findings withheld')
            return report.read_text() if report.exists() else ''
        fixture = temp / 'fixture'
        fixture.mkdir()
        token = 'workbench_probe_' + '9a8b7c6d5e4f3210'
        (fixture / 'secret.txt').write_text(token)
        config = temp / 'fixture.toml'
        config.write_text('[[rules]]\nid="probe"\ndescription="Synthetic detector probe"\nregex="workbench_probe_[a-f0-9]{16}"\n')
        result = scan(['dir', str(fixture), '--config', str(config)], 'synthetic', 1)
        if token in result or 'REDACTED' not in result:
            raise ValueError('Secret detector redaction probe failed')
        scan(['git', '.', '--log-opts=--all --reflog --full-history', '--ignore-gitleaks-allow'], 'history')
        export = temp / 'export'
        export.mkdir()
        subprocess.run(['git', 'checkout-index', '--all', '--prefix=' + str(export) + '/'],
                       cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        scan(['dir', str(export), '--ignore-gitleaks-allow'], 'outgoing')
        archives = sorted((ROOT / 'artifacts').glob('*/*.tar.gz'))
        if not archives:
            raise ValueError('Build a distribution before scanning')
        for index, archive in enumerate(archives):
            scan(['dir', str(archive), '--max-archive-depth=2', '--ignore-gitleaks-allow'], 'archive-' + str(index))
        print(json.dumps({'status': 'passed', 'history': True, 'tracked_export': True,
                          'archives': len(archives), 'reports_uploaded': False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('check', choices=['inventory', 'dependencies', 'secrets'])
    parser.add_argument('--gitleaks', type=Path)
    args = parser.parse_args()
    try:
        if args.check == 'inventory':
            print(json.dumps({'status': 'passed', 'target_pin_counts': {target: len(pins) for target, pins in inventory().items()}}))
        elif args.check == 'dependencies':
            dependencies()
        else:
            if not args.gitleaks:
                parser.error('--gitleaks is required for secrets')
            secrets(args.gitleaks)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, 'Security check failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
