#!/usr/bin/env python3
"""List native thread metadata or resume the original ID locally or through SSH.

SSH attachment keeps execution and native state on the selected host. It does
not migrate the thread or copy transcripts between machines.
"""
import argparse
import json
import os
import re
import selectors
import shlex
import subprocess
import sys
import time
import uuid


class ResumeError(Exception):
    pass


def host_alias(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.@:-]{0,254}', value):
        raise argparse.ArgumentTypeError('Use a plain SSH alias or user@hostname, without shell syntax.')
    return value


def thread_id(value):
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError):
        raise argparse.ArgumentTypeError('Supply the native thread UUID, not a summary or invented ID.')
    return value


def ssh_command(host, command, interactive=False):
    # SSH joins its remote command arguments through the remote shell. Quote
    # each argument once and keep host data out of the command string.
    return ['ssh', '-t' if interactive else '-T', '-o', 'BatchMode=yes',
            '-o', 'ConnectTimeout=8', '--', host,
            'exec env PATH="$HOME/.local/bin:$PATH" ' + shlex.join(command)]


def transport_command(host=None, stdio=True):
    # The managed control proxy is not the public JSONL transport. A short-lived
    # stdio server provides metadata access without loading/resuming any thread.
    command = ['codex', 'app-server', '--stdio']
    return ssh_command(host, command) if host else command


class NativeClient:
    """Minimal bounded JSONL client; no prompts, turns, or history hydration."""
    def __init__(self, command, timeout=15):
        self.command = command
        self.timeout = timeout
        self.sequence = 0
        self.buffer = b''
        self.process = None
        self.selector = None

    def __enter__(self):
        try:
            self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except OSError:
            raise ResumeError('Cannot start native Codex transport. Check Codex/SSH installation and access.')
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        try:
            self.request('initialize', {
                'clientInfo': {'name': 'codex_workbench_resume', 'title': 'Workbench resume', 'version': '1'},
                'capabilities': {'experimentalApi': False, 'requestAttestation': False},
            })
            self.send({'method': 'initialized', 'params': {}})
        except BaseException:
            self.close()
            raise
        return self

    def send(self, message):
        try:
            self.process.stdin.write(json.dumps(message).encode() + b'\n')
            self.process.stdin.flush()
        except (OSError, BrokenPipeError):
            raise ResumeError('Native connection closed. Check daemon status, authentication, and SSH access.')

    def request(self, method, params):
        self.sequence += 1
        request_id = self.sequence
        self.send({'id': request_id, 'method': method, 'params': params})
        deadline = time.monotonic() + self.timeout
        while True:
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                if not line.strip():
                    continue
                try:
                    message = json.loads(line)
                except (ValueError, UnicodeError):
                    raise ResumeError('Native transport returned invalid JSON; no history was reconstructed.')
                if not isinstance(message, dict):
                    raise ResumeError('Native transport returned an unexpected protocol response.')
                if 'method' in message and 'id' in message:
                    # Do not answer approvals or other interactive server requests.
                    raise ResumeError('Native connection requires an interactive action; use the native CLI to handle it.')
                if message.get('id') != request_id:
                    continue
                if 'error' in message:
                    error = message.get('error')
                    code = error.get('code') if isinstance(error, dict) else None
                    raise ResumeError(f'Native {method} failed (code {code}); check installed CLI compatibility and daemon access.')
                return message.get('result')
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self.selector.select(remaining):
                raise ResumeError('Native metadata request timed out. No session was started.')
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise ResumeError('Native metadata connection ended. Check CLI compatibility and host access.')
            self.buffer += chunk
            if len(self.buffer) > 32 * 1024 * 1024:
                raise ResumeError('Native response exceeded the metadata client size limit.')

    def close(self):
        if self.selector:
            self.selector.close()
        if self.process:
            if self.process.stdin:
                try:
                    self.process.stdin.close()
                except OSError:
                    pass
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
            if self.process.stdout:
                self.process.stdout.close()

    def __exit__(self, *args):
        self.close()


FIELDS = ('id', 'sessionId', 'cwd', 'name', 'status', 'modelProvider', 'historyMode', 'updatedAt')


def list_threads(client, limit=100, max_pages=10):
    rows = []
    cursor = None
    cursors = set()
    for _ in range(max_pages):
        params = {'limit': limit, 'sortKey': 'updated_at', 'sortDirection': 'desc',
                  'useStateDbOnly': True, 'modelProviders': []}
        if cursor:
            params['cursor'] = cursor
        result = client.request('thread/list', params)
        if not isinstance(result, dict) or not isinstance(result.get('data'), list):
            raise ResumeError('Native thread list has an unsupported shape.')
        for row in result['data']:
            if not isinstance(row, dict):
                raise ResumeError('Native thread metadata has an unsupported shape.')
            rows.append({field: row.get(field) for field in FIELDS})
        cursor = result.get('nextCursor')
        if not cursor:
            return {'threads': rows, 'nextCursor': None, 'truncated': False}
        if not isinstance(cursor, str) or cursor in cursors:
            raise ResumeError('Native thread pagination repeated or returned an invalid cursor.')
        cursors.add(cursor)
    return {'threads': rows, 'nextCursor': cursor, 'truncated': True}


def resume_command(session=None, host=None):
    command = ['codex', 'resume', '--all']
    if session:
        thread_id(session)
        command.append(session)
    return ssh_command(host_alias(host), command, interactive=True) if host else command


def terminal_text(value):
    return json.dumps(str(value), ensure_ascii=True)[1:-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', type=host_alias, help='SSH host containing the original native state; execution stays there.')
    parser.add_argument('--json', action='store_true', help='Output thread metadata as JSON (list only).')
    parser.add_argument('--stdio', action='store_true', help='Compatibility alias; metadata listing always uses a short-lived stdio server.')
    parser.add_argument('--limit', type=int, default=100, help='Metadata page size, 1..100.')
    parser.add_argument('--max-pages', type=int, default=10, help='Maximum pages, 1..100.')
    parser.add_argument('--timeout', type=float, default=15, help='Per-request timeout in seconds, 1..60.')
    commands = parser.add_subparsers(dest='action', required=True)
    commands.add_parser('list', help='Read native thread metadata without reading turns or starting work.')
    resume = commands.add_parser('resume', help='Resume the original ID; without an ID, open the all-locations picker.')
    resume.add_argument('thread_id', nargs='?', type=thread_id)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100 or not 1 <= args.max_pages <= 100 or not 1 <= args.timeout <= 60:
        parser.error('Use limit/max-pages 1..100 and timeout 1..60.')
    if args.action == 'resume':
        if args.stdio or args.json:
            parser.error('--stdio and --json apply only to list.')
        command = resume_command(args.thread_id, args.host)
        if args.host:
            print(f'Resuming original native state on SSH host {args.host}; execution remains on that host.', file=sys.stderr)
        try:
            os.execvp(command[0], command)
        except OSError:
            parser.exit(1, 'Cannot launch native resume. Check Codex/SSH installation and access.\n')
    try:
        with NativeClient(transport_command(args.host), args.timeout) as client:
            result = list_threads(client, args.limit, args.max_pages)
    except ResumeError as error:
        parser.exit(1, f'{error}\n')
    result['executionHost'] = args.host or 'local'
    result['scope'] = 'Native stored threads; no turns, transcript bodies, or cloud memory copied.'
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for row in result['threads']:
            print(' | '.join(terminal_text(row.get(key) or '') for key in ('id', 'name', 'cwd')))
        if result['truncated']:
            print('Listing reached the page limit; increase --max-pages for more metadata.', file=sys.stderr)


if __name__ == '__main__':
    main()
