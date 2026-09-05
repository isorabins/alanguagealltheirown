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

from cleanup_rulebook import build_applied_rulebook
from exam_evidence import ExamResources, run_exam
from legislative_protocol import current_open_motion
from rulebook import language_payload, render_language
from shadow_cleanup import (run_shadow_cleanup, cleanup_b_request_options,
                            validate_b_audit, _require_clean_completion, DEFAULT_MAX_SPEND_USD)
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
                         meta: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Same cleanup-runner seam as shadow cleanup, with admission evidence.

    A PASS means the exact applied language passed semantic review and every
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
        shadow = run_shadow_cleanup(source_path, output_dir / 'shadow',
            call_model=call_model, token_counter=token_counter, meta=meta, **options)
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
        report['stage'] = 'final_semantic_review'
        audit = load_json(output_dir / 'shadow/b-audit.json', None)
        if not (isinstance(audit, dict) and audit.get('verdict') == 'pass'
                and audit.get('reviewed_candidate_hash') == candidate_hash):
            request = {'source_hash': snapshot_hash(source), 'candidate_hash': candidate_hash,
                'original_adopted_language': [{'id': r['id'], 'text_en': r['text_en']}
                    for r in source['rules'] if r['status'] == 'adopted'],
                'complete_legislature': copy.deepcopy(source['rules']), 'candidate': candidate}
            from shadow_cleanup import DEFAULT_PROMPT_B_PATH
            prompt = Path(options.get('prompt_b_path') or DEFAULT_PROMPT_B_PATH).read_text()
            raw, usage = call_model(options['model_b'], prompt, json.dumps(request, ensure_ascii=False),
                max_tokens=6000, temperature=0, meta=meta,
                request_options=cleanup_b_request_options(source, candidate))
            atomic_write_json(output_dir / 'final-b-call.json', {'request': request, 'text': raw, 'usage': usage})
            _require_clean_completion(usage, 'Final Agent B')
            audit = json.loads(raw)
        validate_b_audit(source, candidate, audit)
        atomic_write_json(output_dir / 'final-b-audit.json', audit)
        report['final_semantic_verdict'] = audit['verdict']
        report['reviewed_candidate_hash'] = audit['reviewed_candidate_hash']
        if audit['verdict'] != 'pass':
            report.update(stage='final_semantic_review', reason='final candidate rejected by Agent B')
            return report
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
        report.update(status='PASS', stage='complete', decision_authority='validated_admission',
                      b_review_mode='final_candidate_required',
                      reason='full compact book passed final semantic review and all registered meaning exams')
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
