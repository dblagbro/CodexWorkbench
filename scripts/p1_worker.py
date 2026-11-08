#!/usr/bin/env python3
"""Isolated SSH fixture worker. No provider API, auth change or production operation."""
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = runpy.run_path(str(ROOT / 'workflow/message_contract.py'))
RECOVERY = runpy.run_path(str(ROOT / 'workflow/recovery.py'))
HANDOFF = runpy.run_path(str(ROOT / 'workflow/handoff.py'))
IMPLEMENTATION = hashlib.sha256(b''.join((ROOT/name).read_bytes() for name in ('workflow/message_contract.py','workflow/recovery.py','workflow/handoff.py','scripts/p1_worker.py'))).hexdigest()


def fixture_project(value):
    path = Path(value).resolve(strict=True)
    if not path.is_relative_to(ROOT / '.workbench/p1-tests'):
        raise ValueError('Only the isolated P1 fixture tree may be used.')
    return path


def probe(project):
    project = fixture_project(project)
    data = json.loads(subprocess.check_output(['findmnt','-J','-o','TARGET,FSTYPE,SOURCE','-T',str(project)],text=True))['filesystems'][0]
    state = json.loads((project / '.workbench/handoff/state.json').read_text())
    return {'mounted': True, 'mount_target': data['target'], 'filesystem': data['fstype'],
            'source_sha256': hashlib.sha256(data['source'].encode()).hexdigest(),
            'project_path': str(project), 'project_id': state['project_id']}


def crash_child(request):
    path = Path(request['directory']).resolve()
    if path.parent != Path('/tmp') or not path.name.startswith('workbench-p1-fixture-'):
        raise ValueError('Crash worker must use its own temporary fixture.')
    journal = RECOVERY['Journal'](path/'journal', 'boot-a', allow_ephemeral=True)
    if request['phase'] == 'before-intent':
        os._exit(17)
    operation = journal.begin(request['project_id'], 1, 'fixture-owner', 'mutation', 'fixture-intent')
    print(json.dumps({'operation': operation['id']}),flush=True)
    if request['phase'] == 'after-intent':
        os._exit(17)
    if request['phase'] == 'during-local-lock':
        with journal._locked():
            os._exit(17)
    journal.mark(operation['id'], 'dispatched_outcome_unknown')
    RECOVERY['durable_write'](path/'effect.json', {'operation':operation['id'],'count':1})
    os._exit(17)


def recovery_cases(project):
    results = []
    observed = probe(project)
    expected = {k:v for k,v in observed.items() if k!='mounted'}
    for name, actual, ready in (
        ('real_share_identity', observed, True),
        ('missing_share', dict(observed,mounted=False),False),
        ('wrong_mount_identity',dict(observed,source_sha256='wrong'),False),
        ('wrong_project_sentinel',dict(observed,project_id=str(uuid.uuid4())),False)):
        assert RECOVERY['verify_location'](expected, actual)['ready'] is ready
        results.append(name)
    for phase in ('before-intent','after-intent','during-local-lock','after-effect-before-response'):
        with tempfile.TemporaryDirectory(prefix='workbench-p1-fixture-') as directory:
            request={'action':'crash-child','phase':phase,'directory':directory,'project_id':expected['project_id']}
            child=subprocess.run([sys.executable,str(Path(__file__).resolve())],input=json.dumps(request),capture_output=True,text=True,timeout=15)
            assert child.returncode==17,child.stderr
            journal=RECOVERY['Journal'](Path(directory)/'journal','boot-b',allow_ephemeral=True)
            if phase=='before-intent':
                assert not list(journal.directory.glob('*.json'))
            else:
                operation=json.loads(child.stdout)['operation'];saved=journal.recovery(operation)
                assert saved['reboot_detected'] and saved['automatic_replay'] is False
                if phase=='after-effect-before-response':
                    assert saved['action']=='read_only_reconcile'
                    effect=json.loads((Path(directory)/'effect.json').read_text());assert effect['count']==1
                    journal.mark(operation,'observed_applied','Read-only fixture counter verified1')
                    journal.mark(operation,'reconciled','No duplicate mutation')
                    assert json.loads((Path(directory)/'effect.json').read_text())['count']==1
                else:
                    # The local controller lock must be released even after process death.
                    journal.mark(operation,'dispatched_outcome_unknown')
            results.append('process_loss_'+phase)
    for status in (None,408,429,500,502,503,504):
        decision=RECOVERY['retry_decision']('read',True,0,3,status,0,60,5 if status==429 else 0)
        assert decision['retry'];results.append('read_retry_'+str(status))
    for status in (401,403,404):
        assert not RECOVERY['retry_decision']('read',True,0,3,status,0,60)['retry']
        results.append('no_retry_'+str(status))
    assert not RECOVERY['retry_decision']('mutation',True,0,3,None,0,60)['retry']
    results.append('unknown_mutation_never_replayed')
    with tempfile.TemporaryDirectory(prefix='workbench-p1-fixture-') as directory:
        journal=RECOVERY['Journal'](directory,'boot-a',allow_ephemeral=True)
        base={'provider':'codex','host':'fixture-node','account_alias':'fixture-account',
              'project_id':expected['project_id'],'project_path':str(project),'boot_id':'boot-a','desired_open':True}
        records=[dict(base,id=str(uuid.uuid4()),native_id='fixture-open'),
                 dict(base,id=str(uuid.uuid4()),native_id='fixture-closed',desired_open=False),
                 dict(base,id=str(uuid.uuid4()),native_id='fixture-loaded'),
                 dict(base,id=str(uuid.uuid4()),native_id='fixture-uncertain')]
        journal.save_sessions(records)
        restarted=RECOVERY['Journal'](directory,'boot-b',allow_ephemeral=True)
        good={'location_verified':True,'native_identity_verified':True,'account_verified':True,'native_loaded':False,'pending_or_uncertain_work':False,'native_state':'not_loaded','idle_resume_verified_safe':True}
        observations={r['id']:dict(good) for r in records}
        observations[records[2]['id']]['native_loaded']=True
        observations[records[3]['id']]['pending_or_uncertain_work']=True
        plan=RECOVERY['restore_plan'](restarted.sessions(),'boot-b',observations,'fixture-node')
        assert [r['restore_candidate'] for r in plan]==[True,False,False,False]
        assert all(not r['replay_commands'] and not r['resume_unattended_work'] for r in plan)
        assert not RECOVERY['restore_plan'](records[:1],'boot-a',observations,'fixture-node')[0]['restore_candidate']
        assert not RECOVERY['restore_plan'](records[:1],'boot-b',observations,'other-node')[0]['restore_candidate']
        unsupported=dict(observations);unsupported[records[0]['id']]=dict(good,idle_resume_verified_safe=False)
        assert not RECOVERY['restore_plan'](records[:1],'boot-b',unsupported,'fixture-node')[0]['restore_candidate']
        results.append('unknown_native_resume_effects_blocked')
        results.extend(['registry_survives_restart','only_desired_open','loaded_skip','uncertain_skip','same_boot_no_duplicate','host_identity_not_migrated','no_unattended_replay'])
    return {'status':'passed','cases':results,'count':len(results),'storage':observed,
            'evidence_kind':'real_SSH_filesystem_process_loss_with_simulated_boot_and_API_faults'}


def handle(request):
    action=request.pop('action')
    if action=='offer':return CONTRACT['offer'](**request)
    if action=='interpret':
        msg=request['message'];intent=copy.deepcopy(msg['intent'])
        if request.get('inject_fault')=='omit_constraint':intent['constraints'].pop('production_changes')
        elif request.get('inject_fault')=='operation_drift':intent['allowed_operations']=['publish']
        return CONTRACT['interpretation'](msg,msg['receiver'],intent)
    if action=='review':
        msg=request['message']
        return CONTRACT['review'](msg,request['receipt'],msg['sender'],request.get('current_revision',msg['revision']),
                                  request.get('current_policy',msg['policy_hash']),request.get('current_checkpoint',msg['checkpoint_hash']),'Fixture sender reviewed exact fields',True)
    if action=='correct':return CONTRACT['correct'](request['message'],'Fixture mismatch: repeat exact allowed operations and constraints.')
    if action=='ack':
        msg=request['message'];return CONTRACT['acknowledge'](msg,request['receipt'],request['review'],msg['receiver'])
    if action=='pattern':return CONTRACT['correction_observation'](**request)
    if action=='probe':return probe(request['project'])
    if action=='recovery-cases':return recovery_cases(request['project'])
    if action=='shared':
        project=fixture_project(request.pop('project'));operation=request.pop('handoff_action')
        return HANDOFF['brief'](project,**request) if operation=='brief' else HANDOFF['change'](project,operation,**request)
    if action=='crash-child':return crash_child(request)
    raise ValueError('Unknown fixture action')


def main():
    try:
        result=handle(json.load(sys.stdin));print(json.dumps({'ok':True,'implementation_sha256':IMPLEMENTATION,'python':sys.version.split()[0],'result':result},sort_keys=True))
    except (ValueError,KeyError,AssertionError,OSError,HANDOFF['HandoffError']) as exc:
        print(json.dumps({'ok':False,'implementation_sha256':IMPLEMENTATION,'error_type':type(exc).__name__,'error':str(exc)}));raise SystemExit(2)


if __name__=='__main__':main()
