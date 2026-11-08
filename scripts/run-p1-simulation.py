#!/usr/bin/env python3
"""Run synthetic protocol/recovery cases over existing SSH; no production faults."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import shlex
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
IMPLEMENTATION=hashlib.sha256(b''.join((ROOT/name).read_bytes() for name in ('workflow/message_contract.py','workflow/recovery.py','workflow/handoff.py','scripts/p1_worker.py'))).hexdigest()


def ssh_call(host, request, relay=None):
    command='cd '+shlex.quote(str(ROOT))+' && exec python3 scripts/p1_worker.py'
    target=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-T',host,command]
    if relay:
        target=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-T',relay,shlex.join(target)]
    result=subprocess.run(target,input=json.dumps(request),capture_output=True,text=True,timeout=90)
    try:data=json.loads(result.stdout)
    except ValueError:raise RuntimeError('SSH/worker transport failed for '+host+': '+result.stderr[:200]) from None
    if data.get('implementation_sha256')!=IMPLEMENTATION:
        raise RuntimeError('Worker/source implementation changed during the test; restart with a frozen candidate.')
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hosts',nargs=3,required=True)
    parser.add_argument('--first-host-via',help='Use an existing trusted relay for the first host, without adding keys.')
    args=parser.parse_args()
    if any(not h or h.startswith('-') or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._@-' for c in h) for h in args.hosts+[args.first_host_via or 'none']):
        parser.error('Use simple existing SSH aliases only.')
    run_id=str(uuid.uuid4());folder=ROOT/'.workbench/p1-tests'/run_id;project=folder/'project'
    project.mkdir(parents=True,mode=0o700)
    handoff=runpy.run_path(str(ROOT/'workflow/handoff.py'));handoff['initialize'](project,True)
    state=handoff['read_state'](handoff['root'](project));report={'run_id':run_id,'status':'running','evidence_kind':'deterministic_fixtures_not_real_model_language_learning',
                                                           'implementation_sha256':IMPLEMENTATION,'handoffs':[],'host_recovery':[],'limitations':['No real LLM API/account switch','No real reboot/unmount/firewall fault','No OS-user ACL or partition fencing claim']}
    def call(index,request,allow_error=False):
        response=ssh_call(args.hosts[index],request,args.first_host_via if index==0 else None)
        if not response['ok'] and not allow_error:raise RuntimeError(response['error'])
        return response['result'] if response['ok'] else response
    try:
        for sender in range(3):
            for receiver in range(3):
                for engine_a,engine_b in (('codex','claude'),('claude','codex')):
                    offer=call(sender,{'action':'offer','project_id':state['project_id'],'revision':state['revision'],
                                       'policy_hash':state['policy_revision'],'checkpoint_hash':hashlib.sha256(b'fixture-checkpoint').hexdigest(),
                                       'sender':f'fixture-{sender}-{engine_a}','receiver':f'fixture-{receiver}-{engine_b}',
                                       'intent':{'objective':'Test a synthetic isolated fixture','allowed_operations':['inspect','test','report'],
                                                 'constraints':{'production_changes':False,'max_cost':0,'fixture_only':True},
                                                 'acceptance':['Record evidence','Preserve restrictions'],'next_action':'Report; never deploy'}})
                    bad=call(receiver,{'action':'interpret','message':offer,'inject_fault':'omit_constraint' if engine_a=='codex' else 'operation_drift'})
                    rejected=call(sender,{'action':'review','message':offer,'receipt':bad});assert rejected['accepted'] is False
                    pattern=call(sender,{'action':'pattern','message':offer,'receipt':bad,'review_result':rejected,
                                         'sender_provider':engine_a,'receiver_provider':engine_b,'adapter_version':'fixture-v1','evidence_kind':'synthetic_fixture'})
                    corrected=call(sender,{'action':'correct','message':offer})
                    understood=call(receiver,{'action':'interpret','message':corrected})
                    accepted=call(sender,{'action':'review','message':corrected,'receipt':understood});assert accepted['accepted'] is True
                    ack=call(receiver,{'action':'ack','message':corrected,'receipt':understood,'review':accepted});assert not ack['execution_authorized']
                    old_ack=call(receiver,{'action':'ack','message':offer,'receipt':understood,'review':accepted},True);assert not old_ack['ok']
                    for field in ('current_policy','current_checkpoint'):
                        stale_evidence=call(sender,{'action':'review','message':corrected,'receipt':understood,field:'changed-evidence'},True)
                        assert not stale_evidence['ok']
                    stale=call(sender,{'action':'review','message':corrected,'receipt':understood,'current_revision':state['revision']+1},True);assert not stale['ok']
                    report['handoffs'].append({'sender_node':sender+1,'receiver_node':receiver+1,'direction':engine_a+'->'+engine_b,'status':'passed',
                                                'correction':pattern,'old_approval_invalidated':True,'stale_revision_rejected':True})
                    print('Handoff case',len(report['handoffs']),'passed',flush=True)
        for index in range(3):
            result=call(index,{'action':'recovery-cases','project':str(project)})
            report['host_recovery'].append({'node':index+1,**result})
            print('Recovery node',index+1,':',result['count'],'cases passed',flush=True)
        # Actual shared NFS metadata ownership race, across distinct SSH nodes.
        actors=[]
        for index in (1,2):
            response=ssh_call(args.hosts[index],{'action':'shared','project':str(project),'handoff_action':'join','label':f'fixture-node-{index+1}','provider':'fixture','host':f'node-{index+1}','native_id':f'fixture-{index+1}'})
            # Handler uses an explicit handoff_action to keep transport action separate.
            if not response['ok']:raise RuntimeError(response['error'])
            actors.append(response['result']['participant'])
        for index,actor in zip((1,2),actors):
            call(index,{'action':'shared','project':str(project),'handoff_action':'sync','participant':actor,'expected':state['revision'],
                        'policy':state['policy_revision'],'note':'Reviewed synthetic fixture only'})
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda pair:ssh_call(args.hosts[pair[0]],{'action':'shared','project':str(project),'handoff_action':'claim',
                                       'participant':pair[1],'expected':state['revision'],'note':'Competing fixture claim'}),zip((1,2),actors)))
        assert sum(r['ok'] for r in responses)==1
        winner=next(i for i,response in enumerate(responses) if response['ok']);loser=1-winner
        win_index,lose_index=(1,2)[winner],(1,2)[loser]
        owned=responses[winner]['result']
        blocked=call(lose_index,{'action':'shared','project':str(project),'handoff_action':'claim','participant':actors[loser],
                                 'expected':owned['revision'],'note':'No timeout takeover'},True);assert not blocked['ok']
        released=call(win_index,{'action':'shared','project':str(project),'handoff_action':'release','participant':actors[winner],
                                'expected':owned['revision'],'note':'First fixture writer complete'})
        call(lose_index,{'action':'shared','project':str(project),'handoff_action':'sync','participant':actors[loser],
                        'expected':released['revision'],'policy':state['policy_revision'],'note':'Read other writer result'})
        claimed=call(lose_index,{'action':'shared','project':str(project),'handoff_action':'claim','participant':actors[loser],
                                'expected':released['revision'],'note':'Reviewed transfer to second fixture writer'})
        stale_owner=call(win_index,{'action':'shared','project':str(project),'handoff_action':'release','participant':actors[winner],
                                    'expected':owned['revision'],'note':'Stale original writer'},True);assert not stale_owner['ok']
        call(lose_index,{'action':'shared','project':str(project),'handoff_action':'release','participant':actors[loser],
                        'expected':claimed['revision'],'note':'Second fixture writer complete'})
        report['shared_owner_race']={'status':'passed','successful_claims':1,'nodes':2,'reviewed_transfer':True,'stale_owner_rejected':True}
        report['status']='passed'
    except Exception as exc:
        report['status']='failed';report['error_type']=type(exc).__name__
        raise
    finally:
        (folder/'evidence.json').write_text(json.dumps(report,indent=2));(folder/'evidence.json').chmod(0o600)
        print('Private evidence:',folder/'evidence.json',flush=True)
    print(json.dumps({'status':report['status'],'handoffs':len(report['handoffs']),'recovery_cases':sum(x['count'] for x in report['host_recovery']),
                      'shared_owner_race':report.get('shared_owner_race')}))


if __name__=='__main__':main()
