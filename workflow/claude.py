#!/usr/bin/env python3
"""Metadata-only Claude session adapter with exact-ID, exact-workdir resume.

The optional official Agent SDK supplies all-project metadata. Without it, only
native sessions-index.json files are read and incomplete coverage is explicit.
This adapter does not directly scan transcripts or hydrate messages; the SDK
may inspect native storage internally. No prompt cache or model call is made.
"""
import argparse
import json
import os
from pathlib import Path
import runpy
import sys
import uuid


class ClaudeError(Exception):
    pass


def session_id(value):
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError):
        raise ClaudeError('Supply a complete native Claude session UUID.') from None


def normalize(record, source):
    def value(*names):
        for name in names:
            found = record.get(name) if isinstance(record, dict) else getattr(record, name, None)
            if found is not None:
                return found
        return None
    identity = session_id(value('session_id', 'sessionId'))
    project = value('cwd', 'projectPath')
    # Never fall back to first_prompt/firstPrompt, or a lossy directory decode.
    title = value('custom_title', 'customTitle') or value('summary') or '(untitled)'
    modified = value('last_modified', 'modified', 'fileMtime')
    return {'id': identity, 'title': str(title), 'project': project if isinstance(project, str) else None,
            'status': 'stored', 'updated_at': modified, 'engine': 'claude', 'metadata_source': source}


def metadata_indexes(config_dir):
    root = config_dir / 'projects'
    directories = sorted(path for path in root.iterdir() if path.is_dir()) if root.is_dir() else []
    sessions = []
    indexes = 0
    unreadable = 0
    for directory in directories:
        path = directory / 'sessions-index.json'
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError('Oversized index')
            data = json.loads(path.read_text())
            if not isinstance(data, dict) or not isinstance(data.get('entries'), list):
                raise ValueError('Unsupported index')
            indexes += 1
            for entry in data['entries']:
                if isinstance(entry, dict) and not entry.get('isSidechain'):
                    try:
                        sessions.append(normalize(entry, 'native_index'))
                    except ClaudeError:
                        unreadable += 1
        except (OSError, ValueError):
            unreadable += 1
    return {'sessions': sessions, 'source': 'native_index', 'complete': False,
            'warnings': ['Index-only coverage is partial. Install the optional official claude-agent-sdk for all-project metadata, or use native claude --resume then Ctrl+A.'],
            'indexed_project_count': indexes, 'project_directory_count': len(directories),
            'unreadable_metadata_count': unreadable}


def list_sessions(config_dir=None, sdk_list=None):
    config_dir = config_dir or Path(os.environ.get('CLAUDE_CONFIG_DIR', str(Path.home() / '.claude'))).expanduser()
    if sdk_list is None:
        try:
            from claude_agent_sdk import list_sessions as sdk_list
        except ImportError:
            return metadata_indexes(config_dir)
    try:
        # Public metadata API; deliberately never call get_session_messages/query.
        values = sdk_list(directory=None, limit=10000, offset=0)
        sessions = []
        invalid = 0
        for value in values:
            try:
                sessions.append(normalize(value, 'official_sdk'))
            except ClaudeError:
                invalid += 1
        truncated = len(values) >= 10000
        return {'sessions': sessions, 'source': 'official_sdk', 'complete': not truncated and not invalid,
                'warnings': ['Metadata was truncated or some records were invalid.'] if truncated or invalid else [],
                'unreadable_metadata_count': invalid}
    except Exception:
        # Do not echo SDK exceptions that could contain local data or credentials.
        raise ClaudeError('Official Claude metadata discovery failed; check the SDK/configuration version. No transcript fallback was attempted.') from None


def search_sessions(rows, query):
    needle = query.casefold()
    return [row for row in rows if needle in '\n'.join(str(row.get(key) or '') for key in ('id', 'title', 'project')).casefold()]


def select_session(rows, identity, project=None):
    identity = session_id(identity)
    matches = [row for row in rows if row['id'] == identity]
    if project is not None:
        matches = [row for row in matches if row.get('project') == str(project)]
    paths = {row.get('project') for row in matches}
    if not matches:
        raise ClaudeError('Session UUID was not found in available metadata; use the native picker or configure the official SDK.')
    if len(paths) != 1:
        raise ClaudeError('This UUID has multiple project paths; select an exact project path rather than guessing.')
    return matches[0]


def resume_command(row, extra_args=()):
    identity = session_id(row.get('id'))
    project = row.get('project')
    if not isinstance(project, str) or not Path(project).is_absolute() or not Path(project).is_dir():
        raise ClaudeError('The exact recorded working directory is missing or unavailable; no home/path fallback was used.')
    forbidden = {'--resume', '-r', '--continue', '-c', '--fork-session', '--session-id', '--teleport'}
    if any(arg.split('=', 1)[0] in forbidden for arg in extra_args):
        raise ClaudeError('Extra native flags must not replace, fork, or redirect the selected session identity.')
    return project, ['claude', '--resume', identity, *extra_args]


def dispatch_resume(original, chooser=None, metadata=None, interactive=None):
    """Return (cwd-or-None, command) for a native resume wrapper invocation."""
    if not original or original[0] not in ('--resume', '-r'):
        raise ClaudeError('Dispatch requires an original native -r/--resume invocation.')
    original = list(original)
    candidate = original[1] if len(original) > 1 else ''
    if candidate and not candidate.startswith('-'):
        try:
            session_id(candidate)
        except ClaudeError:
            query = candidate
            extras = original[2:]
        else:
            return None, ['claude', *original]
    else:
        query = ''
        extras = original[1:]
    if interactive is None:
        interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if not interactive:
        return None, ['claude', *original]
    identity_flags = {'--fork-session', '--session-id', '--continue', '-c', '--resume', '-r', '--teleport'}
    if any(arg.split('=', 1)[0] in identity_flags for arg in extras):
        return None, ['claude', *original]
    try:
        result = metadata if metadata is not None else list_sessions()
    except ClaudeError:
        print('Optional metadata discovery failed; using native Claude resume. Press Ctrl+A for all projects.', file=sys.stderr)
        return None, ['claude', *original]
    if not result['complete']:
        print('Full metadata discovery is unavailable; using native Claude resume. Press Ctrl+A for all projects, then type to search.', file=sys.stderr)
        return None, ['claude', *original]
    rows = search_sessions(result['sessions'], query)
    if chooser is None:
        chooser = runpy.run_path(str(Path(__file__).resolve().with_name('session_picker.py')))['choose']
    selected = chooser(rows)
    if selected is None:
        return None, None
    return resume_command(selected, extras)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    actions = parser.add_subparsers(dest='action', required=True)
    listing = actions.add_parser('list')
    listing.add_argument('--query', default='')
    picking = actions.add_parser('pick')
    picking.add_argument('query', nargs='?', default='')
    resuming = actions.add_parser('resume')
    resuming.add_argument('identity')
    resuming.add_argument('--project', type=Path)
    actions.add_parser('dispatch', help='Wrapper-only native resume dispatch with complete-metadata or native fallback.')
    # Native flags belong after -- and are handed to the native executable intact.
    raw = sys.argv[1:]
    native = []
    if '--' in raw:
        boundary = raw.index('--')
        native = raw[boundary + 1:]
        raw = raw[:boundary]
    args = parser.parse_args(raw)
    if args.action == 'dispatch':
        try:
            project, command = dispatch_resume(native)
            if command is None:
                return 0
            if project is not None:
                os.chdir(project)
            os.execvp(command[0], command)
        except (ClaudeError, OSError) as error:
            message = str(error) if isinstance(error, ClaudeError) else 'Could not launch native Claude.'
            parser.exit(1, message + '\n')
    if args.action == 'list' and native:
        parser.error('Native launch flags apply only to resume/pick.')
    try:
        result = list_sessions()
        if args.action in ('list', 'pick'):
            result['sessions'] = search_sessions(result['sessions'], args.query)
        if args.action == 'list':
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                for row in result['sessions']:
                    print(' | '.join(json.dumps(str(row.get(key) or ''))[1:-1] for key in ('id', 'title', 'project')))
                for warning in result['warnings']:
                    print(warning, file=sys.stderr)
            return 0
        if args.action == 'pick':
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise ClaudeError('Interactive selection requires a terminal; use list or resume UUID explicitly.')
            for warning in result['warnings']:
                print(warning, file=sys.stderr)
            chooser = runpy.run_path(str(Path(__file__).resolve().with_name('session_picker.py')))
            row = chooser['choose'](result['sessions'])
            if row is None:
                return 0
        else:
            row = select_session(result['sessions'], args.identity, args.project)
        project, command = resume_command(row, native)
        os.chdir(project)
        os.execvp(command[0], command)
    except (ClaudeError, OSError) as error:
        message = str(error) if isinstance(error, ClaudeError) else 'Could not launch native Claude; check installation and filesystem access.'
        parser.exit(1, message + '\n')


if __name__ == '__main__':
    main()
