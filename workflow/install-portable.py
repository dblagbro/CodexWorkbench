#!/usr/bin/env python3
"""Preview or install the per-user code-mode workflow; ordinary Codex stays native."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import shutil
import sys
import os
import subprocess

FILES = ['code-workflow.py', 'code-workflow-instructions.txt', 'code-shell.bash',
         'install-portable.py', 'code-baseline.txt', 'lifecycle.md', 'remote-control.py', 'resume.py', 'coordinator.py', 'policy.py', 'session_picker.py', 'claude.py', 'claude-shell.bash', 'handoff.py', 'project-entry.md']


def payload(source):
    files = {Path(name): (source / name).read_bytes() for name in FILES}
    skill = source / 'skills/project-bootstrap'
    if not skill.is_dir():
        skill = source.parent / 'skills/project-bootstrap'
    if not (skill / 'SKILL.md').is_file():
        raise ValueError('Missing bundled project-bootstrap skill')
    for path in sorted(skill.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            files[Path('skills/project-bootstrap') / path.relative_to(skill)] = path.read_bytes()
    return files


def install(args):
    home = (args.home or Path.home()).expanduser().resolve()
    source = Path(__file__).resolve().parent
    target = home / '.local/share/codex-code'
    settings_file = home / '.config/codex-code/settings.json'
    settings = json.loads(settings_file.read_text()) if settings_file.exists() else {}
    if not isinstance(settings, dict):
        raise ValueError('Existing settings must be a JSON object')
    for key, supplied, default in [
        ('project_root', args.project_root, home / 'code'),
        ('scratch_root', args.scratch_root, home / 'scratch'),
        ('session_root', args.session_root, home / '.local/share/codex-work/sessions'),
    ]:
        value = supplied if supplied is not None else settings.get(key, str(default))
        # Expand ~/ relative to the chosen home, also for isolated installation tests.
        if str(value).startswith('~/'):
            value = home / str(value)[2:]
        path = Path(value)
        if not path.is_absolute():
            raise ValueError(f'{key} must be absolute or start with ~/')
        settings[key] = str(path)
    if args.chrome is not None:
        settings['chrome'] = args.chrome == 'on'
    settings.setdefault('chrome', False)
    settings.setdefault('remote_control', True)
    settings.setdefault('claude_enabled', False)
    settings.setdefault('project_bootstrap', True)
    if args.project_bootstrap is not None:
        settings['project_bootstrap'] = args.project_bootstrap == 'on'
    if args.with_claude:
        if not shutil.which('claude') and not (home / '.local/bin/claude').is_file():
            raise ValueError('Install Claude Code separately before enabling its Workbench wrapper.')
        settings['claude_enabled'] = True
    directories = []
    for key in ('project_root', 'scratch_root', 'session_root'):
        path = Path(settings[key])
        if not path.is_dir():
            if path.exists() or path.is_symlink():
                raise ValueError(f'{key} is not a usable directory: {path}')
            if not path.is_relative_to(home):
                raise ValueError(f'External storage root is missing: {path}. Verify its mount and prepare it explicitly before setup.')
            directories.append(path)
    changes = {target / relative: data for relative, data in payload(source).items()}
    changes[settings_file] = (json.dumps(settings, indent=2) + '\n').encode()
    if settings['claude_enabled']:
        changes[target / 'claude-enabled'] = b'Opt-in Claude Workbench wrapper enabled.\n'
    if settings['remote_control']:
        unit_dir = home / '.config/systemd/user'
        service = '''[Unit]
Description=Re-establish Codex Workbench remote control
After=network-online.target

[Service]
Type=oneshot
Environment="PATH=%h/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 "%h/.local/share/codex-code/remote-control.py" ensure
TimeoutStartSec=180
'''
        codex_home = os.environ.get('CODEX_HOME')
        if codex_home:
            # systemd uses percent expansion and quoted environment values.
            escaped = codex_home.replace('%', '%%').replace('\\', '\\\\').replace('"', '\\"')
            if '\n' in escaped or '\r' in escaped:
                raise ValueError('CODEX_HOME contains a newline')
            service = service.replace('[Service]\n', '[Service]\nEnvironment="CODEX_HOME=' + escaped + '"\n')
        changes[unit_dir / 'codex-code-remote-control.service'] = service.encode()
        changes[unit_dir / 'codex-code-remote-control.timer'] = b'''[Unit]
Description=Keep Codex Workbench remote control available

[Timer]
OnStartupSec=20s
OnUnitInactiveSec=60s
AccuracySec=10s
Unit=codex-code-remote-control.service

[Install]
WantedBy=timers.target
'''
    bashrc = home / '.bashrc'
    text = bashrc.read_text() if bashrc.exists() else ''
    marker = '# Codex portable project workflow'
    activation = 'source ' + shlex.quote(str(target / 'code-shell.bash'))
    if marker not in text:
        # The standalone Codex installer uses ~/.local/bin, including on SSH hosts.
        text += '\n' + marker + '\nexport PATH="$HOME/.local/bin:$PATH"\n' + activation + '\n'
    elif activation not in text.splitlines():
        raise ValueError('Existing shell workflow marker has a different activation path; review .bashrc')
    changes[bashrc] = text.encode()
    pending = {}
    for path, data in changes.items():
        if path.is_symlink():
            raise ValueError(f'Refusing to replace symlink: {path}')
        if not path.exists() or path.read_bytes() != data:
            pending[path] = data
    print('Apply' if args.apply else 'Preview only; use --apply to install')
    for path in directories:
        print('Create directory: ' + str(path))
    for path in pending:
        print(('Update: ' if path.exists() else 'Create: ') + str(path))
    if not pending and not directories:
        print('Already up to date')
    if not args.apply:
        return
    for path in directories:
        path.mkdir(parents=True, exist_ok=True)
    # Back up every existing changed file before writing any replacement.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup = home / '.local/state/codex-code/backups' / stamp
    existing = [path for path in pending if path.exists()]
    if existing:
        backup.mkdir(parents=True)
        for path in existing:
            copy = backup / path.relative_to(home)
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, copy)
        print('Original files backed up at: ' + str(backup))
    for path, data in pending.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if args.with_claude and args.home is None:
        environment = target / 'claude-sdk'
        try:
            if not (environment / 'bin/python').is_file():
                created = subprocess.run([sys.executable, '-m', 'venv', str(environment)], capture_output=True, text=True, timeout=60)
                if created.returncode:
                    raise ValueError('Could not create the isolated Claude SDK environment; install Python venv support. Native Claude remains available.')
            installed = subprocess.run([str(environment / 'bin/python'), '-m', 'pip', 'install', '--disable-pip-version-check', 'claude-agent-sdk==0.2.179'],
                                       capture_output=True, text=True, timeout=300)
            if installed.returncode:
                raise ValueError('Isolated Claude SDK installation failed. Check package access; the wrapper will use the native picker fallback.')
            print('Optional Claude metadata SDK installed in an isolated local environment.')
        except subprocess.TimeoutExpired:
            raise ValueError('Claude SDK setup timed out; no system Python or native Claude upgrade was attempted.') from None
    if settings['remote_control'] and args.home is None:
        try:
            for command in (['systemctl', '--user', 'daemon-reload'],
                            ['systemctl', '--user', 'enable', '--now', 'codex-code-remote-control.timer'],
                            ['systemctl', '--user', 'start', '--no-block', 'codex-code-remote-control.service']):
                completed = subprocess.run(command, capture_output=True, text=True, timeout=20)
                if completed.returncode:
                    print('Remote-control units installed but service activation failed; check systemctl --user status.')
                    break
            else:
                print('Remote-control recovery timer enabled; device attachment still requires verification.')
        except (OSError, subprocess.TimeoutExpired):
            print('Remote-control units installed; user service manager unavailable. Code-mode startup also checks remote control.')
    print('Activate in a new shell, or: ' + activation)
    print('No global Codex instructions, config, credentials, or session history changed.')
    print('Requires Codex CLI and Python 3.10+. Python 3.10 uses tomli when available for config inventory.')
    print('Browser mode reuses configured integrations; remote-control recovery defaults on.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--home', type=Path, help='Install for this home directory (isolated testing)')
    parser.add_argument('--project-root')
    parser.add_argument('--scratch-root')
    parser.add_argument('--session-root')
    parser.add_argument('--chrome', choices=['on', 'off'])
    parser.add_argument('--project-bootstrap', choices=['on', 'off'], help='Automatically enroll new named code projects with the shared entry/role resources (default on); existing projects are unchanged.')
    parser.add_argument('--with-claude', action='store_true', help='Enable the opt-in Claude wrapper and install its optional metadata SDK in an isolated environment.')
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error('Python 3.10+ is required')
    try:
        install(args)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Installation stopped: {exc}\n')


if __name__ == '__main__':
    main()
