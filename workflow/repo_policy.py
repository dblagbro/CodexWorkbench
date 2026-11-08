#!/usr/bin/env python3
"""Propose repository governance from explicit facts. Never changes remote settings."""
import argparse
import hashlib
import json
from pathlib import Path

AXES = {
    'hosting': {'internal_controlled', 'external', 'unknown'},
    'authority': {'owner', 'organization', 'client_or_upstream', 'unknown'},
    'visibility': {'public', 'private', 'internal', 'unknown'},
    'sensitivity': {'publishable', 'internal', 'confidential', 'operational_secrets', 'unknown'},
    'criticality': {'development', 'production', 'safety_critical', 'unknown'},
    'team': {'solo', 'team', 'unknown'},
}


def propose(facts):
    if not isinstance(facts,dict) or set(facts) != set(AXES) or any(not isinstance(facts[k],str) or facts[k] not in choices for k, choices in AXES.items()):
        raise ValueError('Supply exactly the documented classification axes and values.')
    known = all(value != 'unknown' for value in facts.values())
    profile = 'unknown_read_only'
    if known:
        if facts['authority'] == 'client_or_upstream':
            profile = 'contribution_only'
        elif facts['hosting'] == 'internal_controlled' and facts['visibility'] != 'public':
            profile = 'internal_restricted'
        elif facts['visibility'] == 'public' and facts['sensitivity'] == 'publishable':
            profile = 'public_owned'
        elif facts['hosting'] == 'external' and facts['visibility'] in ('private', 'internal'):
            profile = 'external_restricted'
    conflict = facts['visibility'] == 'public' and facts['sensitivity'] != 'publishable'
    if conflict:
        profile = 'unknown_read_only'
    high_risk = facts['criticality'] in ('production', 'safety_critical')
    independent = 2 if facts['criticality'] == 'safety_critical' else 1 if facts['team'] == 'team' else 0
    rules = {
        'profile': profile, 'facts': facts, 'status': 'proposal_requires_owner_review',
        'read_and_isolated_tests': 'reviewed_self_authored_fixtures_without_credentials_or_untrusted_repo_code',
        'execute_untrusted_repo_code': False,
        'source_edits_within_existing_authority': profile != 'unknown_read_only',
        'publish': 'explicit_publication_and_data_clearance_required',
        'change_remote_settings': 'separate_approved_repository_specific_plan_required',
        'release_or_deploy': 'explicit_owner_or_authorized_release_approval_required',
        'force_push_or_history_rewrite': 'forbidden_without_specific_separate_authorization',
        'plaintext_credential_commit': False,
        'local_secret_files': 'site_policy_only_outside_git_build_and_publication_inputs',
        'public_attribution': 'owner_approved_names_and_emails_allowed; no_blanket_third_party_PII_grant',
        'scan_uploads': False,
        'dependency_metadata_egress': 'owner_review_required' if profile != 'public_owned' else 'public_package_metadata_only',
        'secret_scanner': 'pinned_Gitleaks_CLI_local_redacted_reports',
        'dependency_scanner': 'pip-audit_resolved_pins_no_resolution' if profile == 'public_owned' else 'reviewed_offline_database_or_approved_metadata_egress',
        'branch': {'pull_request': True, 'required_checks': ['test (3.10)', 'test (3.12)'],
                   'proposed_security_checks': ['security-secrets', 'security-dependencies'],
                   'conversation_resolution': True, 'force_push': False, 'delete': False,
                   'independent_approvals': independent,
                   'approval_prerequisite': 'real_reviewers_and_break_glass_policy_must_exist; agent_self_review_is_not_independent',
                   'administrator_bypass': 'owner_decision_required; never_automatic'},
        'deployment_review': 'independent_review_plus_explicit_approval' if high_risk else 'risk_proportionate_owner_release_review',
        'open_decisions': ['Confirm classification and attribution scope.',
                           'Confirm exact green check names before enabling protection.',
                           'Choose enforce-admin/break-glass and release approval policy.',
                           'Verify hosting-plan feature availability and existing overlapping rules.',
                           'Approve any scanner/dependency metadata egress.'],
    }
    if profile in ('unknown_read_only', 'contribution_only'):
        rules['branch']['configure_remote'] = False
        rules['publish'] = 'not_authorized_by_this_classification'
    else:
        rules['branch']['configure_remote'] = 'requires_separate_owner_approval'
    if conflict:
        rules['conflict'] = 'Public visibility conflicts with nonpublishable sensitivity.'
    digest = hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest()
    return dict(rules, proposal_sha256=digest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facts', type=Path, required=True, help='JSON classification facts, without secrets.')
    args = parser.parse_args()
    try:
        print(json.dumps(propose(json.loads(args.facts.read_text())), indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(1, 'Repository proposal stopped: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
