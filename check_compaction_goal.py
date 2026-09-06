"""Fail closed unless one evidence bundle proves the requested live outcome.

Run with a directory containing admission artifacts plus remotely captured
production.json, provider-receipts.json and browser.json. Recompute meaning
judgments using the unchanged registered exam suite; prose gate labels do not count.
"""
import argparse
import hashlib
import json
from pathlib import Path
from cleanup_rulebook import build_applied_rulebook
from exam_evidence import _materialize_grader_evidence
from rulebook import language_payload, score_judgment_v2
from state_store import snapshot_hash


def check(directory):
    directory=Path(directory)
    def read(name):
        return json.loads((directory/name).read_text())
    def require(condition,message):
        if not condition:raise ValueError(message)
    manifest=read('manifest.json')
    required={'source.json','candidate.json','creative-seeds.json','report.json','exam-events.json',
              'production.json','provider-receipts.json','browser.json'}
    require(required <= set(manifest['sha256']),'missing evidence hashes')
    for name,digest in manifest['sha256'].items():
        require(Path(name).name==name,'artifact path must be a bundle file')
        require(hashlib.sha256((directory/name).read_bytes()).hexdigest()==digest,'artifact hash mismatch: '+name)
    source,candidate,report=read('source.json'),read('candidate.json'),read('report.json')
    require(report['status']=='PASS' and report['stage']=='complete','admission did not pass')
    require(report['source_hash']==snapshot_hash(source),'source hash mismatch')
    require(report['candidate_hash']==snapshot_hash(candidate)==report['final_candidate_hash'],'candidate hash mismatch')
    require(report['decision_authority']=='C' and report['c_cycle_completed'] is True,'C finalization absent')
    require(type(report['applied_tokens']) is int and 0<report['applied_tokens']<=4500,'book size gate failed')
    require(report['source_tokens']>report['applied_tokens'],'no book reduction')
    seeds=read('creative-seeds.json');require(len(seeds)==3,'exactly three ideas required')
    applied=build_applied_rulebook(source,candidate);language=language_payload(applied)['hash']
    require(language==report['applied_language_hash'],'applied identity mismatch')
    import loop
    suite=loop.load_benchmark_suite()['benchmarks']
    require(len(suite)==5,'registered suite changed')
    events=read('exam-events.json')
    require([e['benchmark_id'] for e in events]==[b['id'] for b in suite],'all five exams required exactly once')
    for benchmark,event in zip(suite,events):
        require(event['original']==benchmark['original'],'exam source changed')
        require(event['language_hash']==language,'exam candidate mismatch')
        require(event['judge_valid'] is True and event['meaning_pass'] is True,'failed exam '+benchmark['id'])
        require(bool(event['encoded'].strip()) and bool(event['decoded'].strip()),'missing real messages')
        judgment=event['judge_attempts'][-1]['judgment']
        materialized,error=_materialize_grader_evidence(judgment,event['decoded'])
        require(not error,'invalid judge evidence')
        score=score_judgment_v2(benchmark['answer_key'],materialized,event['decoded'],event['message_body_savings_pct'])
        require(score['valid'] and score['meaning_pass'],'recomputed meaning failure')
    production=read('production.json')
    require(production['host']=='claude-vps' and production['path']=='/root/alanguagealltheirown','local-only adoption')
    require(len(production['revision'])==40 and production['code_matches_local'] is True,'unverified release')
    require(production['adoption']['candidate_hash']==snapshot_hash(candidate),'live candidate mismatch')
    require(production['adoption']['language_hash']==language==production['reload_language_hash'],'adoption/reload mismatch')
    require(production['active_tokens']==report['applied_tokens'] and production['active_tokens']<=4500,'live measured size mismatch')
    require(production['exams']==report['exam_results'] and len(production['exams'])==5,'live compaction exams mismatch')
    require(production['timer_active'] is True and production['future_c_enabled'] is True,'autonomy disabled')
    require(production['models']=={'A':'gpt-5.6-sol','B':'moonshotai/kimi-k3','C':'gpt-6-astra'},'wrong live models')
    receipts=read('provider-receipts.json')
    require(receipts['source_hash']==snapshot_hash(source) and receipts['candidate_hash']==snapshot_hash(candidate),'provider receipt identity mismatch')
    from shadow_cleanup import compile_c_response
    cycle=receipts['compaction_cycle']
    require([r['role'] for r in cycle] in [['C','B','C'],['C','C','B','C'],['C','B','C','C']],'missing draft/advisory/final cycle')
    advisory=next(r for r in cycle if r['role']=='B')
    final=cycle[-1]
    require(final['request']['final_decision'] is True and final['request']['b_advisory']==advisory['response'],'C did not receive B comments')
    require(final['request']['source_hash']==snapshot_hash(source),'C finalized another source')
    final_candidate,final_seeds=compile_c_response(source,final['response'])
    require(final_candidate==candidate and final_seeds==seeds,'final C output mismatch')
    for item in cycle:
        require(any(r['response_id']==item['response_id'] and r['role']==item['role'] for r in receipts['calls']),'cycle lacks provider receipt')
    for role in ['C','A','B']:
        turns=[r for r in receipts['calls'] if r['role']==role]
        require(bool(turns),'missing real provider '+role)
        for r in turns:
            require(r['model']==production['models'][role] and bool(r['response_id']),'wrong provider route')
            require(r['finish_reason']=='stop','incomplete provider call')
            if role in ['A','C']:
                require(r['billing']=='codex_subscription' and r['reasoning']=='high','wrong Codex login or reasoning')
    for role in ['A','B']:
        scheduled=[r for r in production['scheduled_turns'] if r['role']==role and r['turn']>production['adoption']['turn']]
        require(bool(scheduled),'scheduled continuation missing for '+role)
        for r in scheduled:
            require(r['language_hash']==language and r['ideas']==seeds,'scheduled prompt book/ideas mismatch')
            require(r['scheduler_unit']=='language-loop.service' and bool(r['journal']),'manual-only continuation')
            require(any(c['response_id']==r['response_id'] for c in receipts['calls'] if c['role']==role),'scheduled provider receipt absent')
    browser=read('browser.json')
    require(browser['url']=='https://alanguagealltheirown.com','wrong public target')
    require(browser['language_hash']==language and browser['active_tokens']==production['active_tokens'],'public book mismatch')
    require(browser['latest_turn']==production['latest_turn'],'stale public activity')
    require(browser['models']==production['models'] and browser['exams']==production['exams'],'public model/test mismatch')
    require(bool(browser['screenshot_sha256']) and bool(browser['observed_text']),'missing browser evidence')
    return {'complete':True,'language_hash':language,'before_tokens':report['source_tokens'],
            'after_tokens':report['applied_tokens'],'meaning_passes':5,'production_revision':production['revision']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');args=parser.parse_args()
    try:print(json.dumps(check(args.directory),indent=2))
    except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
        print(json.dumps({'complete':False,'reason':str(exc)}));raise SystemExit(1)
