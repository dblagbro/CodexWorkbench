#!/usr/bin/env python3
"""Report local bootstrap capabilities without installing or configuring tools."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

TOOLS = ('codex', 'claude', 'git', 'rg', 'jq', 'curl', 'ssh', 'rsync', 'docker',
         'aws', 'dig', 'openssl', 'nc', 'python3', 'node', 'npm', 'npx',
         'ansible', 'shellcheck', 'playwright', 'uv')


def probe(args):
    """Bound local diagnostic commands; retain stdout only, never config dumps."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=10)
        if result.returncode:
            return {'status': 'failed', 'exit_code': result.returncode,
                    'note': 'May be sandbox or host related; usability is unverified.'}
        return {'status': 'ok', 'output': result.stdout.strip()[:24000]}
    except subprocess.TimeoutExpired:
        return {'status': 'timeout'}
    except OSError:
        return {'status': 'unavailable'}


def read_config(codex_home):
    config = codex_home / 'config.toml'
    if not config.exists():
        return {'status': 'absent'}
    if tomllib is None:
        return {'status': 'parser_unavailable',
                'note': 'Python 3.10 needs optional tomli for configuration inventory; other discovery still works.'}
    try:
        data = tomllib.loads(config.read_text())
        invalid = [key for key in ('mcp_servers', 'profiles', 'agents', 'features')
                   if key in data and not isinstance(data[key], dict)]
        if invalid:
            return {'status': 'invalid_section_types', 'sections': invalid}
        return {'status': 'parsed', 'scope': 'base user config only',
                'sections': sorted(data),
                'mcp_server_names': sorted(data.get('mcp_servers', {})),
                'legacy_profile_names': sorted(data.get('profiles', {})),
                'profile_files': sorted(p.name for p in codex_home.glob('*.config.toml')),
                'agent_keys': sorted(data.get('agents', {})),
                'feature_names': sorted(data.get('features', {}))}
    except (OSError, ValueError):
        return {'status': 'unreadable_or_invalid'}


def skill_names(root):
    """Inspect bounded skill locations, never recursively traverse the home directory."""
    if not root.is_dir():
        return []
    try:
        paths = list(root.glob('*/SKILL.md')) + list(root.glob('.system/*/SKILL.md'))
        return sorted(str(p.relative_to(root)) for p in paths)
    except OSError:
        return []


def inventory(project, codex_home, run_probes=False):
    tools = {name: {'status': 'detected' if shutil.which(name) else 'not_on_path',
                    'path': shutil.which(name)} for name in TOOLS}
    report = {
        'schema_version': 1,
        'captured_at': datetime.now(timezone.utc).isoformat(),
        'project': str(project.resolve()),
        'limits': ['PATH detection is not a functionality or authentication check.',
                   'Configuration names are not effective session capabilities.',
                   'No credentials, environment values, browser data, or session history collected.',
                   'No package installation, service changes, network scans, or feature toggles.',
                   'Explicit probes may trigger normal tool startup behavior.'],
        'tools': tools,
        'python_venv_module': importlib.util.find_spec('venv') is not None,
        'user_config': read_config(codex_home),
        'skills': {
            'codex_home': skill_names(codex_home / 'skills'),
            'user_agents': skill_names(Path.home() / '.agents/skills'),
            'project_agents': skill_names(project / '.agents/skills'),
            'project_codex': skill_names(project / '.codex/skills'),
            'project_source': skill_names(project / 'skills'),
            'limits': 'Plugin-provided and ancestor skills may also exist; session catalog is authoritative for this session.'},
        'project_conventions': [name for name in (
            'AGENTS.md', 'README.md', 'pyproject.toml', 'package.json', 'Makefile',
            'compose.yaml', 'Dockerfile', '.git') if (project / name).exists()],
        'probes': {},
    }
    if run_probes:
        commands = {'codex_version': ['codex', '--version'],
                    'codex_help': ['codex', '--help'],
                    'codex_features': ['codex', 'features', 'list'],
                    'compose_version': ['docker', 'compose', 'version'],
                    'aws_version': ['aws', '--version'],
                    'playwright_version': ['playwright', '--version']}
        report['probes'] = {key: probe(args) for key, args in commands.items()
                            if tools[args[0]]['path']}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--probe', action='store_true',
                        help='Run bounded version/help commands; no installs or remote checks.')
    parser.add_argument('--output', type=Path, help='Create a new JSON file; refuse overwrite.')
    args = parser.parse_args()
    if not args.project.is_dir():
        parser.error('--project must be an existing directory')
    codex_home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))).expanduser()
    payload = json.dumps(inventory(args.project, codex_home, args.probe), indent=2) + '\n'
    if args.output:
        try:
            with args.output.open('x') as handle:
                handle.write(payload)
        except OSError as exc:
            parser.exit(1, f'Cannot create output: {exc.strerror}\n')
    else:
        sys.stdout.write(payload)


if __name__ == '__main__':
    main()
