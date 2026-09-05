"""Opt-in old/new full-book comparison. Never applies candidate or writes canonical state.

Uses actual loop.call transport + experiment prompt text and model settings.
Scores literal preservation in corresponding lines, not complete semantics.
Reads OPENROUTER_API_KEY from process environment. No credential loading here.
"""
import argparse
from functools import partial
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import loop
from local_cleanup import ReservedTransport
from rulebook import render_language, language_payload
from state_store import atomic_write_json
from public_exam_progress import sanitize_completed_text
from check_candidate import ART, build

ENCODER = ('You are the encoder. Encode the message below into the project language '
           'using ONLY this rulebook. Where the rulebook is silent, fall back to plain '
           'English for that part. Output ONLY the encoded message, nothing else.\n\n')
DECODER = ('You are a fresh agent. You have never seen any prior conversation. Below is the '
           'complete rulebook of a constructed language. Decode the message you receive: '
           'reconstruct the original content as faithfully as you can. Do not invent anything '
           'the message does not encode. Output ONLY the reconstruction.\n\n')


def score(cases, decoded):
    lines = decoded.strip().splitlines()
    checks = []
    for i, case in enumerate(cases):
        line = lines[i] if i < len(lines) else ''
        for literal in case['literals']:
            checks.append({'case': case['id'], 'literal': literal, 'pass': literal in line})
        checks.append({'case': case['id'], 'directive': bool(case.get('directive')),
                       'pass': line.startswith('^') == bool(case.get('directive'))})
    source = '\n'.join(c['text'] for c in cases)
    syntax = [{'character': c, 'expected_count': source.count(c), 'actual_count': decoded.count(c),
               'pass': source.count(c) == decoded.count(c)} for c in ('<', '>', '`')]
    return {'added_syntax_checks': syntax, 'scope': 'case-sensitive substrings and directive markers at expected line positions',
            'line_count_pass': len(lines) == len(cases),
            'passed': sum(c['pass'] for c in checks), 'total': len(checks),
            'checks': checks}


def sensitivity(cases):
    """Each literal/marker assertion must notice its own targeted damage."""
    source = '\n'.join(c['text'] for c in cases)
    baseline = score(cases, source)
    assert baseline['line_count_pass'] and baseline['passed'] == baseline['total']
    for case_index, case in enumerate(cases):
        for literal in case['literals']:
            lines = source.splitlines()
            lines[case_index] = lines[case_index].replace(literal, '[REMOVED]')
            mutated = score(cases, '\n'.join(lines))
            assert any(c['case'] == case['id'] and c.get('literal') == literal and not c['pass']
                       for c in mutated['checks'])
        lines = source.splitlines()
        lines[case_index] = lines[case_index][1:] if case.get('directive') else '^' + lines[case_index]
        mutated = score(cases, '\n'.join(lines))
        assert any(c['case'] == case['id'] and 'directive' in c and not c['pass'] for c in mutated['checks'])
    for character in ('<', '>', '`'):
        mutated = score(cases, source + character)
        assert any(c['character'] == character and not c['pass'] for c in mutated['added_syntax_checks'])
    return {'status': 'PASS', 'targeted_assertions': baseline['total'] + 3,
            'scope': 'assertion sensitivity only, not model or language proof'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path)
    p.add_argument('--budget', type=Path)
    p.add_argument('--offline', action='store_true')
    args = p.parse_args()
    fixture_path = Path(__file__).with_name('cases.json')
    fixture = json.loads(fixture_path.read_text())
    _, candidate, integrity = build()
    sensitive = sensitivity(fixture['cases'])
    if args.offline:
        print(json.dumps(sensitive, indent=2))
        return
    assert args.output and args.budget
    args.output.mkdir(parents=True, exist_ok=False)
    original_bytes = (ROOT / 'state/rulebook.json').read_bytes()
    old = json.loads(original_bytes)
    before = json.loads(args.budget.read_text())
    assert before['limit_usd'] == '1.00' and not before['stopped']
    response = loop.requests.get('https://openrouter.ai/api/v1/models', timeout=30)
    response.raise_for_status()
    models = {m['id']: m for m in response.json()['data']
              if m['id'] in {loop.MODEL_A, loop.MODEL_DECODER, loop.MODEL_GRADER}}
    atomic_write_json(args.output / 'model-preflight.json', models)
    transport = ReservedTransport('1.00', models, args.budget, max_output_tokens=4000)
    provider = partial(loop.call, transport=transport)
    payload = '\n'.join(c['text'] for c in fixture['cases'])
    result = {'status': 'IN_PROGRESS', 'integrity': integrity, 'sensitivity': sensitive,
              'fixture_sha256': hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
              'cost_before_usd': before['charged_or_reserved_usd'],
              'encoder': loop.MODEL_A, 'decoder': loop.MODEL_DECODER, 'versions': {}}
    atomic_write_json(args.output / 'fixture.json', fixture)
    atomic_write_json(args.output / 'candidate.json', candidate)
    (args.output / 'input.txt').write_text(payload)

    probe_number = 0

    def invoke(label, model, system, user, **kwargs):
        nonlocal probe_number
        if label == "token-probe":
            probe_number += 1
            label += f"-{probe_number:02}"
        atomic_write_json(args.output / (label + '-request.json'),
                          {'model': model, 'system': system, 'user': user, **kwargs})
        text, usage = provider(model, system, user, **kwargs)
        atomic_write_json(args.output / (label + '-response.json'), {'text': text, 'usage': usage})
        if kwargs.get('max_tokens') != 1:
            receipt = usage.get('response_receipt', {})
            assert receipt.get('finish_reason') == 'stop', f'{label}: incomplete provider response'
            text = sanitize_completed_text(text, stage=label)
        print(label + ' received', flush=True)
        return text, usage

    try:
        for version, rb in [('old', old), ('candidate', candidate)]:
            book = render_language(rb)
            (args.output / (version + '-book.txt')).write_text(book)
            encoded, enc_usage = invoke(version + '-encode', loop.MODEL_A, ENCODER + book,
                                        payload, max_tokens=4000, temperature=0.3)
            # New call: no history, source, expected output or answer key goes to decoder.
            decoded, dec_usage = invoke(version + '-decode', loop.MODEL_DECODER, DECODER + book,
                                        encoded.strip(), max_tokens=4000, temperature=0.1)
            diagnostic, diag_usage = invoke(version + '-diagnostic', loop.MODEL_DECODER,
                DECODER + book, fixture['diagnostic']['encoded'], max_tokens=4000, temperature=0.1)
            expected = fixture['diagnostic']['expected_lines']
            actual = diagnostic.strip().splitlines()
            result['versions'][version] = {
                'language_hash': language_payload(rb)['hash'],
                'encoded': encoded, 'decoded': decoded, 'factual_checks': score(fixture['cases'], decoded),
                'diagnostic': {'text': diagnostic, 'exact_lines_pass': actual == expected,
                               'matching_lines': sum(a == e for a, e in zip(actual, expected)),
                               'expected_lines': len(expected), 'actual_lines': len(actual)},
                'usage': {'encoder': enc_usage, 'decoder': dec_usage, 'diagnostic': diag_usage},
            }
            atomic_write_json(args.output / 'result.json', result)
        # Provider-token probes use same existing calibration seam; 1-token outputs are not content proof.
        counter = partial(loop.token_count, call_model=partial(invoke, 'token-probe'))
        result['tokens'] = {'old_book': counter(render_language(old), None),
                            'candidate_book': counter(render_language(candidate), None),
                            'input': counter(payload, None)}
        for version in result['versions']:
            result['tokens'][version + '_encoded'] = counter(result['versions'][version]['encoded'].strip(), None)
        result['status'] = 'COMPLETED_COMPARISON'
    finally:
        result['source_unchanged'] = (ROOT / 'state/rulebook.json').read_bytes() == original_bytes
        result['cost_after_usd'] = str(transport.used)
        atomic_write_json(args.output / 'result.json', result)
        assert result['source_unchanged']
        print(json.dumps({k: v for k, v in result.items() if k != 'versions'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
