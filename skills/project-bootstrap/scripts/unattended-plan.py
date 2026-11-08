#!/usr/bin/env python3
"""Validate/save a private unattended agreement. Never schedules work or sends mail."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import tempfile


def make_plan(scope, hours, check_minutes, report_minutes, budget, notification, stop_at,
              priority_source, owner_host, max_attempt_minutes, now=None):
    for name, value in [('hours', hours), ('check_minutes', check_minutes), ('report_minutes', report_minutes), ('max_attempt_minutes', max_attempt_minutes)]:
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            raise ValueError(name + ' must be a finite positive number')
    for name, value in [('scope', scope), ('budget', budget), ('notification', notification),
                        ('stop_at', stop_at), ('priority_source', priority_source), ('owner_host', owner_host)]:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(name + ' must record an explicit agreement')
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Timezone-aware start required')
    deadline = now + timedelta(hours=hours)
    if check_minutes * 60 > (deadline - now).total_seconds():
        raise ValueError('Check interval must fit within the agreed runtime')
    if max_attempt_minutes > hours * 60:
        raise ValueError('Per-attempt runtime must fit within the agreed runtime')
    return {'schema_version': 1, 'scope': scope.strip(), 'owner_host': owner_host.strip(),
            'max_attempt_minutes': max_attempt_minutes, 'priority_source': priority_source.strip(),
            'starts_at': now.astimezone(timezone.utc).isoformat(),
            'deadline': deadline.astimezone(timezone.utc).isoformat(),
            'check_minutes': check_minutes, 'report_minutes': report_minutes,
            'budget': budget.strip(), 'notification': notification.strip(),
            'stop_conditions': stop_at.strip(), 'status': 'agreed_needs_scheduler_setup',
            'scheduler_verified': False,
            'warning': 'Plan only. No timer, inference worker or notification has been created.'}


def save_plan(session, plan):
    session = session.expanduser().resolve(strict=True)
    state = session / 'state.json'
    if not state.is_file() or state.is_symlink():
        raise ValueError('Expected stable session state.json, not a project directory')
    metadata = json.loads(state.read_text())
    if not isinstance(metadata, dict) or not isinstance(metadata.get('workdir'), str):
        raise ValueError('Invalid session workdir')
    if not Path(metadata['workdir']).is_dir():
        raise ValueError('Saved workdir is unavailable')
    # Refuse redirected private state and preserve all prior agreements.
    for name in ('workbench', 'workbench/unattended', 'workbench/unattended/plan.json'):
        if (session / name).is_symlink():
            raise ValueError('Refusing redirected continuation state')
    folder = session / 'workbench/unattended'
    folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    plan = dict(plan, project=metadata['workdir'], engine=metadata.get('engine', 'codex'),
                native_id=metadata.get('native_id'), session=str(session))
    if not plan['native_id']:
        plan['native_id_status'] = 'resolve_exact_native_id_before_scheduling'
    destination = folder / 'plan.json'
    with tempfile.NamedTemporaryFile(dir=folder, prefix='.plan-', delete=False) as stream:
        temporary = Path(stream.name)
        os.fchmod(stream.fileno(), 0o600)
        stream.write((json.dumps(plan, indent=2) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    try:
        # Atomic no-clobber publication; never erase a running plan or its evidence.
        os.link(temporary, destination)
    finally:
        temporary.unlink()
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--scope', required=True)
    parser.add_argument('--hours', type=float, required=True)
    parser.add_argument('--check-minutes', type=float, required=True)
    parser.add_argument('--report-minutes', type=float, required=True)
    parser.add_argument('--budget', required=True)
    parser.add_argument('--owner-host', required=True)
    parser.add_argument('--max-attempt-minutes', type=float, required=True)
    parser.add_argument('--notification', required=True, help='Explicit channel/destination/subject agreement or in-chat only; no secrets.')
    parser.add_argument('--stop-at', required=True, help='Completion/approval/safety stop conditions, not a timestamp.')
    parser.add_argument('--priority-source', required=True)
    parser.add_argument('--apply', action='store_true', help='Save only after the owner has agreed these settings.')
    args = parser.parse_args()
    try:
        plan = make_plan(args.scope, args.hours, args.check_minutes, args.report_minutes,
                         args.budget, args.notification, args.stop_at, args.priority_source, args.owner_host, args.max_attempt_minutes)
        if args.apply:
            print(json.dumps({'saved': str(save_plan(args.session, plan)), 'scheduler_verified': False,
                              'next_action': 'Install and verify the agreed project scheduler; plan alone cannot continue work.'}, indent=2))
        else:
            plan['status'] = 'preview_not_authorized'
            print(json.dumps(plan, indent=2))
    except (ValueError, OSError, OverflowError) as exc:
        parser.exit(1, 'Unattended plan stopped: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
