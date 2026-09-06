"""Offline candidate integrity; no model calls and no canonical writes."""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from cleanup_rulebook import compile_cleanup_draft
from state_store import snapshot_hash
from rulebook import render_language

ART = ROOT / 'docs/architecture/book-condensation-20260905'
EXPECTED_SOURCE = '53ffb801cbeec7f64ad3c6d16c8863aa2e97e692686f5f48e407ca843c15abc2'


def build():
    raw = (ROOT / 'state/rulebook.json').read_bytes()
    source = json.loads(raw)
    assert snapshot_hash(source) == EXPECTED_SOURCE, 'source changed; re-review required'
    text = (ART / 'BOOK.md').read_text()
    parts = re.split(r'^## (P\d\d) — ', text, flags=re.M)
    groups = {parts[i]: parts[i] + ' — ' + parts[i + 1].strip()
              for i in range(1, len(parts), 2)}
    assert set(groups) == {f'P{i:02}' for i in range(1, 15)}
    with (ART / 'coverage.tsv').open() as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    adopted = [r['id'] for r in source['rules'] if r['status'] == 'adopted']
    assert len(rows) == len(adopted) == 83
    assert len({r['source'] for r in rows}) == 83
    assert {f"rule-{r['source']}" for r in rows} == set(adopted)
    review = (ART / 'REVIEW.md').read_text()
    for row in rows:
        assert set(row['clauses'].split(',')) <= set(groups)
        assert row['obligations_and_resolution'].strip()
        assert row['disposition'].strip() in {'consolidated', 'superseded', 'conflict', 'operational'}
        for ref in re.findall(r'\bR\d\d\b', row['obligations_and_resolution']):
            assert f'| {ref} |' in review
    draft = {
        'groups': [{'id': k, 'text_en': v} for k, v in groups.items()],
        'assignments': {f"rule-{r['source']}": r['primary'] for r in rows},
        'exclusions': [{'source_id': f"rule-{r['source']}", 'reason': 'operational'}
                       for r in rows if r['primary'] == '__exclude__'],
    }
    candidate = compile_cleanup_draft(source, draft)
    assert len(candidate['rules']) == 14
    assert len(candidate['excluded_sources']) == 5
    assert (ROOT / 'state/rulebook.json').read_bytes() == raw
    report = {
        'status': 'PASS', 'scope': 'identity, mapping and compiler integrity only; not semantic equivalence',
        'source_snapshot_hash': snapshot_hash(source),
        'source_file_sha256': hashlib.sha256(raw).hexdigest(),
        'source_adopted_records': 83, 'mapped_records': 78, 'operational_exclusions': 5,
        'candidate_sections': 14, 'candidate_language_hash': snapshot_hash(candidate),
        'source_render_chars': len(render_language(source)),
        'candidate_render_chars': len(render_language(candidate)),
        'source_render_words': len(render_language(source).split()),
        'candidate_render_words': len(render_language(candidate).split()),
        'source_unchanged': True,
    }
    return draft, candidate, report


if __name__ == '__main__':
    draft, candidate, report = build()
    if '--write' in sys.argv:
        for name, content in [('draft.json', draft), ('candidate.json', candidate), ('integrity.json', report)]:
            (ART / name).write_text(json.dumps(content, indent=2, ensure_ascii=False) + '\n')
    else:
        assert json.loads((ART / 'candidate.json').read_text()) == candidate, 'candidate is stale'
        assert json.loads((ART / 'draft.json').read_text()) == draft, 'draft is stale'
    print(json.dumps(report, indent=2))
