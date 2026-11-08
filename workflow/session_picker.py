#!/usr/bin/env python3
"""A metadata-only chooser shared by provider-specific session adapters."""
import json
import sys


def safe(value, width=100):
    text = json.dumps(str(value or ''), ensure_ascii=True)[1:-1]
    return text if len(text) <= width else text[:width - 3] + '...'


def choose(rows, reader=input, output=None):
    """Select from one stable metadata snapshot; numbers never trigger a rescan."""
    output = output or sys.stderr
    original = list(rows)
    visible = original
    while True:
        print('\nSession chooser: number or exact ID; /words filters; / resets; q cancels.', file=output)
        for index, row in enumerate(visible, 1):
            print(f"{index:>3}. {safe(row.get('title'), 60)} [{safe(row.get('status'), 30)}]", file=output)
            print(f"     {safe(row.get('project'), 100)} | {safe(row.get('id'), 100)}", file=output)
        if not visible:
            print('No matching sessions. Use / to reset the search.', file=output)
        try:
            answer = reader('Select: ').strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if not answer or answer.lower() in ('q', 'quit', 'cancel'):
            return None
        if answer.startswith('/'):
            query = answer[1:].casefold().strip()
            visible = [row for row in original if all(word in ' '.join(str(row.get(key, '')) for key in ('id', 'title', 'project', 'status')).casefold() for word in query.split())]
            continue
        if answer.isdigit():
            index = int(answer) - 1
            if 0 <= index < len(visible):
                return visible[index]
        else:
            matches = [row for row in original if row.get('id') == answer]
            if len(matches) == 1:
                return matches[0]
        print('Choose a displayed number, exact ID, or /search terms.', file=output)
