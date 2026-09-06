#!/usr/bin/env python3
"""Run full local cleanup through Codex C, real final B and the registered judge.

Copies the actual saved experiment, settles any motion normally, invokes the
verified automatic-cleanup seam, commits/reloads, and delivers all three ideas
to both continuing roles on success. Never writes the source directory.
"""
from __future__ import annotations
import argparse
import copy
from functools import partial
import hashlib
import json
from pathlib import Path
import shutil

import loop
from collaboration import empty_state
from codex_compactor import CodexCompactor
from exam_evidence import ExamResources
from legislative_protocol import current_open_motion
from local_cleanup import ReservedTransport
from rulebook import language_payload, render_language
from state_store import atomic_write_json
from turn_store import TurnState, TurnStore
from verified_cleanup import CleanupPolicy, run_verified_cleanup


STATE_FILES = ('rulebook.json', 'conversation.json', 'meta.json',
               'collaboration.json', 'conversations.json', loop.COST_LEDGER_FILENAME)


def snapshot_source(source_dir: Path) -> dict[str, bytes]:
    """Copy one coherent committed snapshot without recovering/mutating source."""
    if not source_dir.is_dir():
        raise ValueError('source state directory is missing')
    with TurnStore(source_dir).writer() as store:
        if store.pending.exists() or store.pending_archive.exists():
            raise ValueError('source has pending recovery; refusing incoherent snapshot')
        return {name: (source_dir / name).read_bytes() for name in STATE_FILES
                if (source_dir / name).exists()}


def verify_continuation(requests, expected_snapshot, expected_seeds, role):
    """Check actual structured payload, not incidental words in a prompt."""
    marker = '=== STRUCTURED WORKING CONTEXT ===\n'
    for request in requests:
        if marker not in request['system']:
            continue
        context = json.JSONDecoder().raw_decode(request['system'].split(marker, 1)[1])[0]
        machine = context['current_machine_state']
        delivery = (machine.get('collaboration_input') or {}).get('cleanup_creative_seeds')
        if (context['accepted_snapshot'] == expected_snapshot and delivery == expected_seeds
                and len(delivery['seeds']) == 3 and f'You are Agent {role}.' in request['user']):
            return
    raise AssertionError('continuation did not receive exact accepted book and three ideas')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-state', type=Path, default=loop.ROOT / 'state')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--budget', type=Path, required=True,
                        help='Existing shared $1 ledger; cannot start a new allowance')
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--resume-draft', type=Path, help='Resume validated C draft after unavailable B review')
    parser.add_argument('--reconcile-context-request', type=Path, help='Recorded request for a proven pre-generation context rejection')
    parser.add_argument('--replay-first-c', type=Path, help='Reuse one complete C receipt only for an identical request')
    parser.add_argument('--motion-review-note', help='Optional, attributed local operator suggestion to B')
    args = parser.parse_args()
    if not args.budget.exists():
        raise ValueError('existing shared budget ledger is required')
    args.output.mkdir(parents=True, exist_ok=False)
    originals = snapshot_source(args.source_state)
    state_dir = args.output / 'state'
    state_dir.mkdir()
    for name, data in originals.items():
        (state_dir / name).write_bytes(data)
    atomic_write_json(args.output / 'source-provenance.json', {
        'source_state': str(args.source_state.resolve()),
        'file_sha256': {k: hashlib.sha256(v).hexdigest() for k,v in originals.items()},
        'selection': 'all saved state records; no adopted-rule subset or manufactured motion result',
    })
    catalog = loop.requests.get('https://openrouter.ai/api/v1/models', timeout=30)
    catalog.raise_for_status()
    models = {m['id']: m for m in catalog.json()['data']
              if m['id'] in {loop.MODEL_A, loop.MODEL_B, loop.MODEL_DECODER, loop.MODEL_GRADER}}
    atomic_write_json(args.output / 'model-preflight.json', models)
    transport = ReservedTransport('1.00', models, args.budget, max_output_tokens=6000)
    if args.reconcile_context_request:
        transport.reconcile_context_rejection(args.reconcile_context_request)
    api = partial(loop.call, transport=transport)
    codex = CodexCompactor(args.output / 'codex', executable=args.codex, replay_first=args.replay_first_c)
    loop.MODEL_C = 'gpt-6-astra'
    call_index = 0
    def dispatch(model, system, user, **kwargs):
        nonlocal call_index
        call_index += 1
        call_path = args.output / 'calls' / f'{call_index:03}'
        call_path.mkdir(parents=True)
        atomic_write_json(call_path / 'request.json', {
            'model': model, 'system': system, 'user': user,
            **{k: v for k,v in kwargs.items() if k != 'meta'},
        })
        print(f'Provider call {call_index}: {model}', flush=True)
        provider = codex if model == loop.MODEL_C else api
        text, usage = provider(model, system, user, **kwargs)
        atomic_write_json(call_path / 'response.json', {'text': text, 'usage': usage})
        return text, usage
    loop.call = dispatch
    loop.token_count = partial(loop.token_count, call_model=dispatch)
    loop.STATE = state_dir
    loop.AUTOMATIC_CLEANUP_EDITION = 'local-verified-codex-v2-history-projection'
    resources = ExamResources(loop.ROOT, loop.load_benchmark_suite(),
        loop.MODEL_A, loop.MODEL_DECODER, loop.MODEL_GRADER)
    result = {'status': 'FAILED', 'scope': 'full saved experiment, local copy only',
              'cleanup_applied': False, 'continued_roles': [],
              'open_motion_turns': [], 'api_budget_before_usd': str(transport.used)}
    def verified(source, ephemeral_output, **kwargs):
        # The real normal caller owns loading/applying the validated outputs.
        # Retain its temporary evidence before the caller cleans it up.
        try:
            return run_verified_cleanup(source, ephemeral_output, exams=resources,
                policy=CleanupPolicy(), resume_draft_dir=args.resume_draft, **kwargs)
        finally:
            if Path(ephemeral_output).exists():
                shutil.copytree(ephemeral_output, args.output / 'cleanup')
    try:
        with TurnStore(state_dir).writer() as store:
            state = store.load(TurnState([], {}, {}, empty_state(), []))
            loop.ensure_structured_protocol_cutover(state.conversation, state.rulebook,
                state.meta, activation_turn=state.next_turn-1)
            loop.configure_cost_receipt_ledger(state_dir / loop.COST_LEDGER_FILENAME, state.meta)
            if args.motion_review_note:
                state.collaboration.setdefault('suggestions', []).insert(0, {
                    'id': 'local-cleanup-review-' + args.output.name, 'kind': 'SUGGESTION',
                    'status': 'approved', 'requester': 'B', 'text': args.motion_review_note,
                    'source': 'Codex local operator review under user-approved cleanup task'})
                result['motion_review_note'] = args.motion_review_note
            store.commit(state)
            # Normal B/A decisions only; a maximum is a stop, never authority to
            # discard a motion or silently force an adoption/rejection.
            for _ in range(8):
                if current_open_motion(state.rulebook) is None:
                    break
                turn = state.next_turn
                if turn % loop.TEST_EVERY == 0:
                    role = 'exam'
                    state.public_exam_progress = loop.test_turn(state.conversation,
                        state.rulebook, state.meta, turn,
                        progress_path=state_dir / 'public-exam-progress.local.json')
                    outcome = 'completed'
                else:
                    role = loop.next_legislative_actor(state.meta)
                    outcome = loop.agent_turn(state.conversation, state.rulebook, state.meta,
                                              state.collaboration, turn)
                store.commit(state)
                result['open_motion_turns'].append({'turn': turn, 'role': role, 'outcome': outcome})
            if current_open_motion(state.rulebook) is not None:
                result.update(status='WAITING_FOR_MOTION', reason='normal actors have not settled the open motion')
                return
            cstate = state.meta.get('automatic_cleanup', {})
            if cstate.get('last_status') == 'quarantined':
                loop.reset_automatic_cleanup_quarantine(cstate,
                    reviewed_edition=loop.AUTOMATIC_CLEANUP_EDITION,
                    operator='user-approved full local verified cleanup')
            state.rulebook['kernel_tokens'] = loop.token_count(render_language(state.rulebook), state.meta)
            # Explicit local request to compact now. Only scheduling metadata
            # changes; the source language and legislative decisions remain real.
            cstate.update(schema_version=loop.AUTOMATIC_CLEANUP_STATE_SCHEMA_VERSION,
                baseline_tokens=max(1,int(state.rulebook['kernel_tokens']/1.11)),
                baseline_language_hash=language_payload(state.rulebook)['hash'],
                baseline_turn=state.next_turn-1, last_attempt_language_hash=None, last_status='armed')
            state.meta['automatic_cleanup'] = cstate
            result['trigger'] = 'explicit local operator request; growth baseline re-armed in copy only'
            atomic_write_json(args.output / 'settled-source.json', state.rulebook)
            before_hash = language_payload(state.rulebook)['hash']
            store.commit(state)
            applied = loop.maybe_run_automatic_cleanup(state.conversation, state.rulebook,
                state.meta, state.next_turn, cleanup_runner=verified)
            store.commit(state)
            result['cleanup_applied'] = applied
            if not applied:
                assert language_payload(state.rulebook)['hash'] == before_hash
                result.update(status='REJECTED_OLD_BOOK_RETAINED',
                    reason=state.meta['automatic_cleanup'].get('last_reason'))
                return
            accepted_hash = language_payload(state.rulebook)['hash']
            state = store.load(TurnState([], {}, {}, {}, []))
            assert language_payload(state.rulebook)['hash'] == accepted_hash
            result['reload_preserved_language'] = True
            expected_snapshot = copy.deepcopy(state.meta['automatic_cleanup']['structured_snapshot'])
            pending = state.meta['automatic_cleanup']['pending_creative_seeds']
            expected_seeds = {k: copy.deepcopy(pending[k]) for k in ('cleanup_turn', 'seeds')}
            # Deliver the structured book and three non-operative seeds through
            # the actual continuation request to each role, after durable reload.
            for _ in range(8):
                if state.next_turn % loop.TEST_EVERY == 0:
                    state.public_exam_progress = loop.test_turn(state.conversation,
                        state.rulebook, state.meta, state.next_turn,
                        progress_path=state_dir / 'public-exam-progress.local.json')
                    store.commit(state)
                    state = store.load(TurnState([], {}, {}, {}, []))
                    continue
                role = loop.next_legislative_actor(state.meta)
                prior_calls = call_index
                outcome = loop.agent_turn(state.conversation, state.rulebook, state.meta,
                    state.collaboration, state.next_turn)
                store.commit(state)
                if outcome == 'structural_failure':
                    continue
                requests = [json.loads((args.output/'calls'/f'{i:03}'/'request.json').read_text())
                            for i in range(prior_calls+1,call_index+1)]
                verify_continuation(requests, expected_snapshot, expected_seeds, role)
                result['continued_roles'].append(role)
                state = store.load(TurnState([], {}, {}, {}, []))
                if set(result['continued_roles']) == {'A','B'}:
                    break
            assert set(result['continued_roles']) == {'A','B'}
            assert 'pending_creative_seeds' not in state.meta['automatic_cleanup']
            result.update(status='APPLIED_AND_CONTINUED', accepted_language_hash=accepted_hash)
    except Exception as exc:
        result.update(status='FAILED', failure_type=type(exc).__name__, reason=str(exc))
        raise
    finally:
        result['api_budget_after_usd'] = str(transport.used)
        result['codex_billing'] = 'existing ChatGPT subscription allowance, separate from API dollars'
        result['original_state_unchanged'] = all((args.source_state/name).read_bytes()==raw
                                               for name,raw in originals.items())
        atomic_write_json(args.output / 'acceptance.json', result)
        print(json.dumps(result,indent=2),flush=True)
        assert result['original_state_unchanged']


if __name__ == '__main__':
    main()
