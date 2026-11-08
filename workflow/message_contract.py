#!/usr/bin/env python3
"""Typed data-only review protocol. Understanding receipts never grant authority."""
import hashlib
import json
import re
import uuid

AUTHORITY = 'none; check actual project owner and current user grants separately'
OPERATIONS = {'inspect', 'edit_fixture', 'test', 'review', 'report', 'reconcile'}


def text(value, label, maximum=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(label + ' must be a nonempty bounded string.')


def sha(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('An exact SHA256 evidence digest is required.')


def encoded(value):
    try:
        result = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (TypeError,ValueError):
        raise ValueError('Contract data must be finite JSON values.') from None
    if len(result.encode()) > 256000:
        raise ValueError('Message exceeds the bounded contract size.')
    return result


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def validate_intent(intent):
    if not isinstance(intent, dict) or set(intent) != {'objective','allowed_operations','constraints','acceptance','next_action'}:
        raise ValueError('Intent must explicitly contain all contract fields.')
    text(intent['objective'], 'Objective');text(intent['next_action'], 'Next action')
    ops = intent['allowed_operations']
    if not isinstance(ops, list) or not ops or any(not isinstance(op,str) or op not in OPERATIONS for op in ops) or len(set(ops)) != len(ops):
        raise ValueError('Only explicit unique fixture/read/review operations are supported; no execution grant.')
    if not isinstance(intent['constraints'],dict) or not 1 <= len(intent['constraints']) <= 64 or any(not isinstance(k,str) or not re.fullmatch('[a-z][a-z0-9_]{0,63}',k) for k in intent['constraints']):
        raise ValueError('Explicit bounded named constraints required.')
    acceptance=intent['acceptance']
    if not isinstance(acceptance,list) or not 1 <= len(acceptance) <= 64:
        raise ValueError('Acceptance criteria must be a bounded list of strings.')
    for value in acceptance:text(value,'Acceptance criterion')
    encoded(intent)


def validate_message(message):
    base={'schema','id','project_id','revision','policy_hash','checkpoint_hash','sender','receiver','intent','round','previous_offer','authority'}
    if not isinstance(message,dict) or set(message) not in (base,base|{'correction_note'}):
        raise ValueError('Unsupported envelope fields.')
    if type(message['schema']) is not int or message['schema'] != 1 or type(message['revision']) is not int or message['revision'] < 0:
        raise ValueError('Exact supported schema and nonnegative project revision required.')
    for key in ('id','project_id'):
        text(message[key],key,200);uuid.UUID(message[key])
    sha(message['policy_hash']);sha(message['checkpoint_hash'])
    text(message['sender'],'Sender',200);text(message['receiver'],'Receiver',200)
    if message['sender']==message['receiver'] or message['authority']!=AUTHORITY:
        raise ValueError('Distinct participants and no-authority contract required.')
    if type(message['round']) is not int or not 0 <= message['round'] <= 2:
        raise ValueError('Correction round is outside the bounded protocol.')
    if message['round']:
        text(message.get('correction_note'),'Correction note');text(message['previous_offer'],'Previous offer',200);uuid.UUID(message['previous_offer'])
    elif message['previous_offer'] is not None or 'correction_note' in message:
        raise ValueError('Initial offer cannot masquerade as a correction.')
    validate_intent(message['intent'])


def validate_receipt(message, receipt):
    if not isinstance(receipt,dict) or set(receipt) != {'offer_id','offer_digest','receiver','understood_intent','needs_clarification'}:
        raise ValueError('Unsupported interpretation fields.')
    if receipt['offer_id'] != message['id'] or receipt['offer_digest'] != digest(message) or receipt['receiver'] != message['receiver']:
        raise ValueError('Interpretation is not bound to the exact offer and recipient.')
    if type(receipt['needs_clarification']) is not bool or not isinstance(receipt['understood_intent'],dict):
        raise ValueError('Interpretation requires a structured account and explicit clarification state.')
    encoded(receipt)


def offer(project_id, revision, policy_hash, checkpoint_hash, sender, receiver, intent):
    message={'schema':1,'id':str(uuid.uuid4()),'project_id':project_id,'revision':revision,
             'policy_hash':policy_hash,'checkpoint_hash':checkpoint_hash,'sender':sender,'receiver':receiver,
             'intent':intent,'round':0,'previous_offer':None,'authority':AUTHORITY}
    validate_message(message)
    return json.loads(encoded(message))


def interpretation(message, receiver, understood_intent, clarification=False):
    validate_message(message)
    result={'offer_id':message['id'],'offer_digest':digest(message),'receiver':receiver,
            'understood_intent':understood_intent,'needs_clarification':clarification}
    validate_receipt(message,result)
    return json.loads(encoded(result))


def review(message, receipt, sender, current_revision, current_policy, current_checkpoint, semantic_note, sender_accepts=False):
    validate_message(message);validate_receipt(message,receipt)
    if type(sender_accepts) is not bool or type(current_revision) is not int:
        raise ValueError('Acceptance and revision must have exact types.')
    text(semantic_note,'Sender review')
    if sender != message['sender']:
        raise ValueError('Original sender must review interpretation.')
    if (message['revision'],message['policy_hash'],message['checkpoint_hash']) != (current_revision,current_policy,current_checkpoint):
        raise ValueError('Project evidence changed; create a new offer.')
    accepted=sender_accepts and receipt['needs_clarification'] is False and digest(receipt['understood_intent'])==digest(message['intent'])
    return {'offer_id':message['id'],'offer_digest':digest(message),'receipt_digest':digest(receipt),
            'sender':sender,'accepted':accepted,'note':semantic_note,
            'status':'accepted_for_receiver_ack' if accepted else 'correction_or_clarification_required','execution_authorized':False}


def correct(message, note, maximum_rounds=2):
    validate_message(message);text(note,'Correction note')
    if type(maximum_rounds) is not int or not 1 <= maximum_rounds <= 2 or message['round'] >= maximum_rounds:
        raise ValueError('Correction budget exhausted; escalate unresolved ambiguity.')
    result=json.loads(encoded(message))
    result.update(id=str(uuid.uuid4()),previous_offer=message['id'],round=message['round']+1,correction_note=note)
    validate_message(result)
    return result


def acknowledge(message, receipt, sender_review, receiver):
    validate_message(message);validate_receipt(message,receipt)
    if receiver != message['receiver'] or sender_review.get('accepted') is not True or sender_review.get('execution_authorized') is not False:
        raise ValueError('Explicit sender acceptance of understanding, not execution authority, is required.')
    if sender_review.get('sender') != message['sender'] or sender_review.get('offer_digest') != digest(message) or sender_review.get('receipt_digest') != digest(receipt):
        raise ValueError('Correction/interpretation changed; old review is invalid.')
    if receipt['needs_clarification'] is not False or digest(receipt['understood_intent']) != digest(message['intent']):
        raise ValueError('A mismatched or ambiguous interpretation cannot be acknowledged.')
    return {'offer_id':message['id'],'accepted_digest':digest(message),'receiver':receiver,
            'status':'understanding_acknowledged','execution_authorized':False,
            'notice':'Participant/fixture assertions are not authenticated identity or proof of model comprehension.'}


def correction_observation(message, receipt, review_result, sender_provider, receiver_provider, adapter_version, evidence_kind):
    validate_message(message);validate_receipt(message,receipt)
    if review_result.get('offer_id') != message['id'] or review_result.get('offer_digest') != digest(message) or review_result.get('receipt_digest') != digest(receipt):
        raise ValueError('Observation must bind the exact reviewed message and interpretation.')
    if evidence_kind not in ('synthetic_fixture','observed_model_exchange_requires_review'):
        raise ValueError('Explicit provenance required; fixtures must not teach live provider assumptions.')
    for value in (sender_provider,receiver_provider,adapter_version):text(value,'Adapter identifier',200)
    understood=receipt['understood_intent']
    mismatches=[key for key in message['intent'] if digest(message['intent'][key]) != digest(understood.get(key))]
    return {'schema':1,'sender_provider':sender_provider,'receiver_provider':receiver_provider,'adapter_version':adapter_version,
            'field_mismatches':mismatches,'needs_clarification':receipt['needs_clarification'],
            'instruction':'Restate/review these fields without widening scope.',
            'automatic_permission_changes':False,'model_training':False,'evidence_kind':evidence_kind,
            'usable_for_automatic_live_adaptation':False}
