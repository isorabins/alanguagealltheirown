"""Admit a compacted language only after exact-candidate semantic and real exam gates.

The source path and provider adapters are the inputs. This module owns drafting,
size limits, hash-bound review, all benchmark runs and a durable refusal/result.
It never applies language; the normal automatic-cleanup caller owns that commit.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
from typing import Any, Callable
from dataclasses import dataclass
import math
import hashlib

from cleanup_rulebook import build_applied_rulebook
from exam_evidence import ExamResources, run_exam
from legislative_protocol import current_open_motion
from rulebook import language_payload, render_language
from shadow_cleanup import (run_shadow_cleanup, _require_clean_completion, DEFAULT_MAX_SPEND_USD,
                            compile_c_response)
from state_store import atomic_write_json, load_json, snapshot_hash
from turn_store import TurnState


class CleanupBudgetExceeded(RuntimeError):
    """Recorded admission spending reached its stop threshold."""


@dataclass(frozen=True)
class CleanupPolicy:
    max_language_tokens: int = 4500


def run_verified_cleanup(source_path: Path, output_dir: Path, *,
                         exams: ExamResources, policy: CleanupPolicy = CleanupPolicy(),
                         call_model: Callable, token_counter: Callable,
                         meta: dict[str, Any], resume_draft_dir: Path | None = None, **kwargs: Any) -> dict[str, Any]:
    """Same cleanup-runner seam as shadow cleanup, with admission evidence.

    A PASS means C finalized the exact applied language and it passed every
    registered exam's meaning gate. Message savings are reported independently.
    Provider spending survives refusal; exam cursors/results do not enter active
    state. A failed/unavailable judge is a refusal, never implicit approval.
    """
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ValueError('verified cleanup output already exists')
    output_dir.mkdir(parents=True)
    source_bytes = Path(source_path).read_bytes()
    source = json.loads(source_bytes)
    start_spend = float(meta.get('spend_usd', 0))
    report = {'kind': 'verified_cleanup', 'status': 'FAIL', 'stage': 'preflight',
              'reason': 'not completed', 'source_hash': snapshot_hash(source),
              'applied': False, 'source_unchanged': True, 'exam_results': [],
              'max_language_tokens': policy.max_language_tokens}
    max_spend = float(kwargs.get('max_spend_usd', DEFAULT_MAX_SPEND_USD))
    raw_call, raw_tokens = call_model, token_counter
    def check_budget(*, before):
        spent = round(float(meta.get('spend_usd', 0)) - start_spend, 12)
        if spent > max_spend or (before and spent >= max_spend):
            raise CleanupBudgetExceeded('admission spending reached its stop threshold')
    def call_model(*args, **params):
        check_budget(before=True)
        result = raw_call(*args, **params)
        check_budget(before=False)
        return result
    def token_counter(*args, **params):
        check_budget(before=True)
        result = raw_tokens(*args, **params)
        check_budget(before=False)
        return result
    try:
        if not math.isfinite(max_spend) or max_spend <= 0:
            raise ValueError('a positive finite admission spend limit is required')
        if current_open_motion(source) is not None:
            report.update(stage='open_motion', reason='settle the open motion before cleanup')
            return report
        if not exams.suite.get('benchmarks'):
            raise ValueError('a nonempty registered exam suite is required')
        source_tokens = token_counter(render_language(source), meta)
        minimum = round(max(5.0, 100 * (1 - policy.max_language_tokens / source_tokens)), 2)
        options = dict(kwargs)
        options['min_reduction_pct'] = minimum
        if resume_draft_dir is not None:
            saved = Path(resume_draft_dir)
            shadow = load_json(saved / 'report.json', None)
            if (not isinstance(shadow, dict) or shadow.get('source_hash') != snapshot_hash(source)
                    or shadow.get('stage') != 'b_call' or shadow.get('status') != 'FAIL'
                    or shadow.get('b_advisory_error', {}).get('status') != 'unavailable'):
                raise ValueError('only an identical-source draft with unavailable B review can resume')
            candidate, seeds = compile_c_response(source, load_json(saved / 'c-response.json', None))
            if (snapshot_hash(candidate) != shadow.get('candidate_hash')
                    or candidate != load_json(saved / 'candidate.json', None)
                    or seeds != load_json(saved / 'creative-seeds.json', None)):
                raise ValueError('saved draft artifacts do not match their C response')
            saved_call = load_json(saved / 'c-call.json', None)
            if (not isinstance(saved_call, dict)
                    or saved_call.get('model') != options['model_c']
                    or json.loads(saved_call.get('content', 'null')) != load_json(saved / 'c-response.json', None)):
                raise ValueError('saved C response payload or model mismatch')
            _require_clean_completion(saved_call.get('usage', {}), 'Saved Agent C')
            # A repaired historical draft cannot impersonate a fresh initial call.
            # Bind the exact system and user input before reusing its response.
            rounds = shadow.get('round_count', 1)
            saved_round = saved / 'rounds' / f'{rounds:02d}'
            saved_request = load_json(saved_round / 'c-request.json', None)
            resume_call = call_model
            first = True
            def call_model(*args, **params):
                nonlocal first
                if first:
                    first = False
                    if (args[0] != saved_call['model']
                            or hashlib.sha256(args[1].encode()).hexdigest() != saved_call.get('prompt_sha256')
                            or json.loads(args[2]) != saved_request):
                        raise ValueError('saved C response belongs to a different request')
                    return saved_call['content'], saved_call['usage']
                return resume_call(*args, **params)
        shadow = run_shadow_cleanup(source_path, output_dir / 'shadow',
            call_model=call_model, token_counter=token_counter, meta=meta, **options)
        if resume_draft_dir is not None:
            shadow.update(resumed_draft_from=str(saved), prior_status='FAIL')
        report.update(copy.deepcopy(shadow))
        report.update(kind='verified_cleanup', status='FAIL', applied=False,
                      max_language_tokens=policy.max_language_tokens, exam_results=[])
        if shadow['status'] != 'PASS':
            return report
        candidate = load_json(output_dir / 'shadow/candidate.json', None)
        seeds = load_json(output_dir / 'shadow/creative-seeds.json', None)
        candidate_hash = snapshot_hash(candidate)
        if shadow.get('candidate_hash') != candidate_hash:
            raise ValueError('shadow candidate hash mismatch')
        # Check the representation that normal application will really install,
        # including assigned rule IDs, not only the pre-application draft.
        applied = build_applied_rulebook(source, candidate)
        applied_tokens = token_counter(render_language(applied), meta)
        if applied_tokens > policy.max_language_tokens:
            report.update(stage='size_gate', reason='applied language exceeds token ceiling')
            return report
        report['applied_language_hash'] = language_payload(applied)['hash']
        report['applied_tokens'] = applied_tokens
        # B is advisory. The shadow protocol already binds its comments to the
        # reviewed draft and gives C the final decision when B objects.
        audit = load_json(output_dir / 'shadow/b-audit.json', None)
        report['final_semantic_verdict'] = audit['verdict']
        report['reviewed_candidate_hash'] = audit['reviewed_candidate_hash']
        report['final_candidate_hash'] = candidate_hash
        report['c_cycle_completed'] = True
        report['decision_authority'] = 'C'
        report['b_review_mode'] = 'single_advisory'
        # Exams have isolated state; only real provider spending is charged back.
        trial = TurnState([], applied, copy.deepcopy(meta), {}, [])
        trial.meta.pop('benchmark_suite', None)
        trial.meta.pop('benchmark_results_v2', None)
        trial.meta['corpus_exams'] = []
        def provider(model, system, user, **params):
            params['meta'] = meta
            return call_model(model, system, user, **params)
        for index, benchmark in enumerate(exams.suite['benchmarks'], 1):
            report['stage'] = 'exam_' + benchmark['id']
            try:
                run_exam(trial, index, resources=exams, provider=provider,
                         count_tokens=lambda text: token_counter(text, meta))
            finally:
                atomic_write_json(output_dir / 'exam-events.json', trial.conversation)
            event = trial.conversation[-1]
            if event.get('benchmark_id') != benchmark['id'] or event.get('language_hash') != report['applied_language_hash']:
                raise ValueError('exam identity mismatch')
            report['exam_results'].append({k: copy.deepcopy(event.get(k)) for k in (
                'benchmark_id', 'language_hash', 'judge_valid', 'judge_status', 'judge_reason',
                'meaning_pass', 'compression_success', 'semantic_coverage_pct', 'survived', 'total',
                'orig_tokens', 'enc_tokens', 'message_body_savings_pct', 'critical_failures', 'inventions')})
            atomic_write_json(output_dir / 'report.json', report)
        failures = [e['benchmark_id'] for e in report['exam_results']
                    if e['judge_valid'] is not True or e['meaning_pass'] is not True]
        if failures:
            report.update(stage='exam_gate', reason='meaning/judge failure: ' + ', '.join(failures))
            return report
        # Caller reads these exact artifacts only after all admission gates pass.
        atomic_write_json(output_dir / 'candidate.json', candidate)
        atomic_write_json(output_dir / 'creative-seeds.json', seeds)
        report.update(status='PASS', stage='complete', decision_authority='C',
                      b_review_mode='single_advisory',
                      reason='C final book passed all registered meaning exams')
        return report
    except Exception as exc:
        report.update(status='FAIL', error_type=type(exc).__name__, reason=str(exc))
        return report
    finally:
        report['source_unchanged'] = Path(source_path).read_bytes() == source_bytes
        report['run_spend_usd'] = round(float(meta.get('spend_usd', 0))-start_spend, 12)
        if not report['source_unchanged']:
            report.update(status='FAIL', stage='source_integrity', reason='source changed during cleanup')
        atomic_write_json(output_dir / 'report.json', report)
