import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
POLICY_HASH='1'*64
CHECKPOINT_HASH='2'*64


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'workflow' / (name + '.py'))
    item = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item)
    return item


policy, contract, recovery = (module(name) for name in ('repo_policy', 'message_contract', 'recovery'))


class GovernanceTests(unittest.TestCase):
    def facts(self, **changes):
        return dict(dict(hosting='external', authority='owner', visibility='public',
                         sensitivity='publishable', criticality='development', team='solo'), **changes)

    def test_independent_axes_and_solo_review_do_not_grant_authority(self):
        result = policy.propose(self.facts())
        self.assertEqual(result['profile'], 'public_owned')
        self.assertEqual(result['branch']['independent_approvals'], 0)
        self.assertEqual(result['status'], 'proposal_requires_owner_review')
        self.assertFalse(result['plaintext_credential_commit'])
        self.assertEqual(policy.propose(self.facts(visibility='private', sensitivity='confidential'))['profile'], 'external_restricted')
        self.assertEqual(policy.propose(self.facts(hosting='internal_controlled', visibility='internal', sensitivity='internal', team='team'))['profile'], 'internal_restricted')

    def test_unknown_conflict_and_upstream_cannot_configure_remote(self):
        for facts in (self.facts(authority='unknown'), self.facts(sensitivity='confidential')):
            self.assertEqual(policy.propose(facts)['profile'], 'unknown_read_only')
            self.assertFalse(policy.propose(facts)['branch']['configure_remote'])
        self.assertFalse(policy.propose(self.facts(authority='client_or_upstream'))['branch']['configure_remote'])
        with self.assertRaises(ValueError):
            policy.propose(dict(self.facts(), surprise=True))


class MessageContractTests(unittest.TestCase):
    def message(self):
        return contract.offer(str(uuid.uuid4()), 3, POLICY_HASH, CHECKPOINT_HASH, 'sender', 'receiver',
                              {'objective': 'Run a fixture test', 'allowed_operations': ['inspect','test'],
                               'constraints': {'production_changes': False, 'max_cost': 0},
                               'acceptance': ['Evidence recorded'], 'next_action': 'Report results'})

    def test_misinterpretation_requires_correction_and_both_acknowledgements(self):
        msg = self.message()
        wrong = copy.deepcopy(msg['intent']);wrong['constraints'].pop('production_changes')
        receipt = contract.interpretation(msg, 'receiver', wrong)
        rejected = contract.review(msg, receipt, 'sender', 3, POLICY_HASH, CHECKPOINT_HASH, 'Omitted constraint', True)
        self.assertFalse(rejected['accepted'])
        with self.assertRaises(ValueError):
            contract.acknowledge(msg, receipt, rejected, 'receiver')
        corrected = contract.correct(msg, 'Repeat exact constraints; no production changes')
        receipt = contract.interpretation(corrected, 'receiver', copy.deepcopy(corrected['intent']))
        accepted = contract.review(corrected, receipt, 'sender', 3, POLICY_HASH, CHECKPOINT_HASH, 'Reviewed corrected interpretation', True)
        self.assertFalse(contract.acknowledge(corrected, receipt, accepted, 'receiver')['execution_authorized'])
        with self.assertRaises(ValueError):
            contract.acknowledge(msg, receipt, accepted, 'receiver')

    def test_observation_cannot_reuse_old_review_after_content_changes(self):
        message=self.message();receipt=contract.interpretation(message,'receiver',message['intent'])
        reviewed=contract.review(message,receipt,'sender',3,POLICY_HASH,CHECKPOINT_HASH,'Reviewed',True)
        message['intent']['objective']='Changed after review'
        with self.assertRaises(ValueError):
            contract.correction_observation(message,receipt,reviewed,'codex','claude','fixture-v1','synthetic_fixture')

    def test_malformed_ingress_and_fake_sender_acceptance_rejected(self):
        message=self.message()
        for field,value in (('allowed_operations','test'),('acceptance',True),('objective',{'not':'text'})):
            bad=copy.deepcopy(message);bad['intent'][field]=value
            with self.assertRaises(ValueError):
                contract.interpretation(bad,'receiver',bad['intent'])
        receipt=contract.interpretation(message,'receiver',message['intent'])
        with self.assertRaises(ValueError):
            contract.review(message,receipt,'sender',3,POLICY_HASH,CHECKPOINT_HASH,'Wrong type','false')

    def test_stale_evidence_ambiguity_and_type_drift_fail_closed(self):
        msg = self.message()
        receipt = contract.interpretation(msg, 'receiver', msg['intent'])
        with self.assertRaises(ValueError):
            contract.review(msg, receipt, 'sender', 4, POLICY_HASH, CHECKPOINT_HASH, 'State changed', True)
        wrong = copy.deepcopy(msg['intent']);wrong['constraints']['production_changes'] = 0
        result = contract.review(msg, contract.interpretation(msg, 'receiver', wrong), 'sender', 3, POLICY_HASH, CHECKPOINT_HASH, 'Type mismatch', True)
        self.assertFalse(result['accepted'])
        with self.assertRaises(ValueError):
            contract.correct(contract.correct(contract.correct(msg, 'one'), 'two'), 'three')


class RecoveryTests(unittest.TestCase):
    def test_mutation_lost_response_survives_restart_without_replay(self):
        with tempfile.TemporaryDirectory() as d:
            journal = recovery.Journal(d, 'boot-a', allow_ephemeral=True)
            record = journal.begin(str(uuid.uuid4()), 4, 'owner-a', 'mutation', 'intent-digest')
            journal.mark(record['id'], 'dispatched_outcome_unknown')
            restarted = recovery.Journal(d, 'boot-b', allow_ephemeral=True)
            pending = restarted.recovery(record['id'])
            self.assertTrue(pending['reboot_detected'])
            self.assertEqual(pending['action'], 'read_only_reconcile')
            self.assertFalse(pending['automatic_replay'])
            with self.assertRaises(ValueError):
                restarted.mark(record['id'], 'reconciled')
            restarted.mark(record['id'], 'observed_applied', 'Fixture effect verified once')
            restarted.mark(record['id'], 'reconciled', 'No replay')
            with self.assertRaises(ValueError):
                restarted.mark(record['id'], 'dispatched_outcome_unknown')
            self.assertEqual((Path(d)/(record['id']+'.json')).stat().st_mode & 0o777, 0o600)

    def test_share_identity_and_no_fallback_journal(self):
        expected = dict(mount_target='/fixture/share', filesystem='nfs4', source_sha256='source', project_id='fixture-id', project_path='/fixture/share/project')
        self.assertFalse(recovery.verify_location(expected, dict(expected, mounted=False))['ready'])
        self.assertFalse(recovery.verify_location(expected, dict(expected, mounted=True, project_id='wrong'))['ready'])
        self.assertTrue(recovery.verify_location(expected, dict(expected, mounted=True))['ready'])
        with tempfile.TemporaryDirectory() as d:
            absent = Path(d)/'absent-share'
            with self.assertRaises(ValueError):
                recovery.Journal(absent/'journal', 'boot', shared_roots=(absent,), allow_ephemeral=True)
            self.assertFalse(absent.exists())

    def test_production_journal_refuses_temporary_storage(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                recovery.Journal(d, 'boot-a')

    def test_nonboolean_mount_and_restore_flags_never_count_as_verified(self):
        expected=dict(mount_target='/fixture/share',filesystem='nfs4',source_sha256='source',project_id='fixture-id',project_path='/fixture/share/project')
        self.assertFalse(recovery.verify_location(expected, dict(expected,mounted='false'))['ready'])
        row=dict(id='one',provider='codex',host='node-a',account_alias='profile-a',native_id='same-id',boot_id='old',desired_open=True)
        for flag in ('location_verified','native_identity_verified','account_verified'):
            observed=dict(location_verified=True,native_identity_verified=True,account_verified=True,native_loaded=False,pending_or_uncertain_work=False,native_state='not_loaded',idle_resume_verified_safe=True)
            observed[flag]='false'
            self.assertFalse(recovery.restore_plan([row],'new',{'one':observed},'node-a')[0]['restore_candidate'])

    def test_account_namespace_preserved_and_path_dotdot_cannot_bypass_storage_guard(self):
        row=dict(provider='codex',host='node-a',native_id='same-id',boot_id='old',desired_open=True)
        rows=[dict(row,id='a',account_alias='profile-a'),dict(row,id='b',account_alias='profile-b')]
        good=dict(location_verified=True,native_identity_verified=True,account_verified=True,native_loaded=False,pending_or_uncertain_work=False,native_state='not_loaded',idle_resume_verified_safe=True)
        self.assertEqual(len(recovery.restore_plan(rows,'new',{'a':good,'b':good},'node-a')),2)
        with tempfile.TemporaryDirectory() as d:
            escaped=Path('/var/../')/Path(d).relative_to('/')/'must-not-create'
            with self.assertRaises(ValueError):
                recovery.Journal(escaped,'boot-a')
            self.assertFalse((Path(d)/'must-not-create').exists())

    def test_missing_or_unknown_native_activity_is_not_idle(self):
        row=dict(id='one',provider='codex',host='node-a',account_alias='account-a',native_id='native-id',boot_id='old',desired_open=True)
        good=dict(location_verified=True,native_identity_verified=True,account_verified=True,native_loaded=False,pending_or_uncertain_work=False,native_state='not_loaded',idle_resume_verified_safe=True)
        for key in ('native_loaded','pending_or_uncertain_work','native_state','idle_resume_verified_safe'):
            missing=dict(good);missing.pop(key)
            self.assertFalse(recovery.restore_plan([row],'new',{'one':missing},'node-a')[0]['restore_candidate'])

    def test_failed_parent_directory_sync_does_not_claim_ready(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            with patch.object(recovery.os,'fsync',side_effect=OSError('Simulated fsync failure')):
                with self.assertRaises(OSError):
                    recovery.Journal(Path(d)/'new'/'journal','boot',allow_ephemeral=True)

    def test_api_retry_auth_rate_limit_and_uncertainty(self):
        self.assertTrue(recovery.retry_decision('read', True, 0, 3, 503, 0, 30)['retry'])
        self.assertEqual(recovery.retry_decision('read', True, 0, 3, 429, 0, 30, 8)['delay_seconds'], 8)
        self.assertFalse(recovery.retry_decision('mutation', True, 0, 3, None, 0, 30)['retry'])
        self.assertFalse(recovery.retry_decision('read', False, 0, 3, 403, 0, 30)['retry'])
        self.assertFalse(recovery.retry_decision('read', False, 3, 3, 503, 0, 30)['retry'])
        self.assertFalse(recovery.retry_decision('read', False, 0, 3, 429, 0, 30, 60)['retry'])

    def test_boot_plan_keeps_closed_loaded_wrong_host_and_uncertain_sessions_idle(self):
        base=dict(provider='codex',host='node-a',account_alias='fixture-account',native_id='native-a',boot_id='boot-a',desired_open=True)
        records=[dict(base,id='open'),dict(base,id='closed',native_id='native-b',desired_open=False),dict(base,id='uncertain',native_id='native-c')]
        good={'location_verified':True,'native_identity_verified':True,'account_verified':True,'native_loaded':False,'pending_or_uncertain_work':False,'native_state':'not_loaded','idle_resume_verified_safe':True}
        result=recovery.restore_plan(records, 'boot-b', {'open':good,'closed':good,'uncertain':dict(good,pending_or_uncertain_work=True)}, 'node-a')
        self.assertEqual([r['restore_candidate'] for r in result],[True,False,False])
        self.assertTrue(all(not r['replay_commands'] and not r['resume_unattended_work'] for r in result))
        self.assertFalse(recovery.restore_plan(records[:1], 'boot-a', {'open':good}, 'node-a')[0]['restore_candidate'])
        self.assertFalse(recovery.restore_plan(records[:1], 'boot-b', {'open':good}, 'node-b')[0]['restore_candidate'])
