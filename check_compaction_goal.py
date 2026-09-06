"""Fail closed unless one evidence bundle proves the requested live outcome.

Run with a directory containing admission artifacts plus remotely captured
production.json, provider-receipts.json and browser.json. Recompute meaning
judgments using the unchanged registered exam suite; prose gate labels do not count.
"""
import argparse
import hashlib
import json
import re
import subprocess
import shlex
from datetime import datetime, timezone
from pathlib import Path
from cleanup_rulebook import build_applied_rulebook
from exam_evidence import _materialize_grader_evidence
from rulebook import language_payload, score_judgment_v2
from state_store import snapshot_hash


RUNTIME_FILES = tuple(sorted(
    ['loop.py', 'shadow_cleanup.py', 'verified_cleanup.py', 'runtime_session.py', 'local_cleanup.py',
     'codex_compactor.py', 'cleanup_replay.py', 'public_snapshot.py', 'viewer/index.html', 'viewer/public-state.js',
     'cleanup_rulebook.py', 'rulebook.py', 'exam_evidence.py', 'legislature.py',
     'legislative_protocol.py', 'turn_store.py', 'state_store.py', 'collaboration.py',
     'conversation_exam.py', 'public_exam_progress.py', 'project_lookup.py', 'run_turn.sh']
    + [str(p.relative_to(Path(__file__).parent)) for folder in ('prompts', 'benchmarks')
       for p in (Path(__file__).parent/folder).iterdir() if p.is_file()]))

def read_live(remote_files):
    # Fixed host/checkout; read-only verification never dispatches models.
    script = """import json,sys,hashlib,subprocess
from pathlib import Path
root=Path('/root/alanguagealltheirown')
request=json.load(sys.stdin)
config=json.loads(Path('/root/alato-restart-20260906/live-config-approved-2.json').read_text())
budget=json.loads(Path(config['ledger']).read_text())
for path in request['remote_files'].values():
 p=Path(path).resolve()
 if not (str(p).startswith('/root/alato-restart-20260906/') and p.suffix in {'.json','.jsonl','.txt'}):
  raise ValueError('remote evidence path outside approved receipt area')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
print(json.dumps({'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 'state':{name:json.loads((root/'state'/name).read_text()) for name in ['rulebook.json','conversation.json','meta.json']},
 'code':{name:sha(root/name) for name in request['code']},
 'budget':{'expires_at':config['expires_at'],'limit_usd':config['limit_usd'],'spent_usd':budget['charged_or_reserved_usd'],'stopped':budget['stopped']},
 'timer':subprocess.check_output(['systemctl','is-active','language-loop.timer'],text=True).strip(),
 'remote_hashes':{name:sha(path) for name,path in request['remote_files'].items()}}))"""
    result=subprocess.run(['ssh','-o','BatchMode=yes','claude-vps','python3 -c '+shlex.quote(script)],
        input=json.dumps({'remote_files':remote_files,'code':RUNTIME_FILES}),text=True,capture_output=True,check=True,timeout=30)
    return json.loads(result.stdout)


def check(directory, *, live_reader=read_live):
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
    require(len(report['exam_results'])==5,'report lacks five results')
    for reported,event in zip(report['exam_results'],events):
        require(all(reported.get(key)==event.get(key) for key in ('benchmark_id','judge_valid','meaning_pass','semantic_coverage_pct','orig_tokens','enc_tokens','message_body_savings_pct')),'report/exam result mismatch')
    production=read('production.json')
    require(production['host']=='claude-vps' and production['path']=='/root/alanguagealltheirown','local-only adoption')
    require(re.fullmatch(r'[0-9a-f]{40}',production['revision']) is not None,'unverified release')
    require(production['adoption']['candidate_hash']==snapshot_hash(candidate),'live candidate mismatch')
    adoption=next((e for e in production['conversation'] if e.get('type')=='cleanup' and e.get('status')=='applied' and e.get('candidate_hash')==snapshot_hash(candidate)),None)
    require(adoption is not None and adoption['turn']==production['adoption']['turn'],'canonical adoption absent')
    require(adoption['source_hash']==snapshot_hash(source) and adoption['exam_results']==report['exam_results'],'canonical admission correlation failed')
    require(production['adoption']['language_hash']==language==production['reload_language_hash'],'adoption/reload mismatch')
    require(adoption['post_state_receipt']['adopted_language_hash']==language and adoption['applied_tokens']==report['applied_tokens'],'canonical compact checkpoint mismatch')
    expected_snapshot=loop.build_structured_cleanup_snapshot(candidate,checkpoint_turn=adoption['turn'],source_hash=snapshot_hash(source))
    require(production['accepted_snapshot']==expected_snapshot,'unrelated structured checkpoint')
    require(production['reload_snapshot_file'] in manifest['remote_files'],'reload lacks remote provenance')
    reload_state=read(production['reload_snapshot_file'])
    require(language_payload(reload_state['rulebook'])['hash']==language and reload_state['rulebook']['kernel_tokens']==report['applied_tokens'],'persisted compact checkpoint mismatch')
    require(reload_state['meta']['automatic_cleanup']['structured_snapshot']==expected_snapshot,'persisted structured checkpoint mismatch')
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
        matched=next((r for r in receipts['calls'] if r['response_id']==item['response_id'] and r['role']==item['role']),None)
        require(matched is not None,'cycle lacks provider receipt')
        require(json.loads(matched['text'])==item['response'] and json.loads(matched['request']['user'])==item['request'],'cycle request/output mismatch')
    calls=receipts['calls']
    for r in calls:
        usage=r['usage']; request=r['request']; receipt=usage['response_receipt']
        require(receipt['id']==r['response_id'] and receipt['model']==r['model'],'provider receipt correlation failed')
        require(receipt['finish_reason']=='stop' and request['model']==r['model'],'provider request/response route mismatch')
        if r.get('billing')=='codex_subscription':
            raw_request=read(r['raw_request_file']);raw_text=(directory/r['raw_response_file']).read_text()
            require(raw_request['model']==request['model'] and raw_request['system']==request['system'] and raw_request['user']==request['user'],'Codex request mismatch')
            require(raw_request['reasoning']=='high' and raw_text==r['text'],'Codex output/reasoning mismatch')
            terminal=[json.loads(line) for line in (directory/r['events_file']).read_text().splitlines()]
            require(any(e.get('type')=='turn.completed' for e in terminal) and not any(e.get('type')=='turn.failed' for e in terminal),'Codex terminal receipt absent or failed')
            require(any('codex:'+str(e.get('thread_id'))==r['response_id'] for e in terminal if e.get('type')=='thread.started'),'Codex response identity mismatch')
        else:
            raw_request=read(r['raw_request_file']);raw_response=read(r['raw_response_file'])
            messages=([{'role':'system','content':request['system']}] if request['system'] else [])+[{'role':'user','content':request['user']}]
            require(raw_request['messages']==messages and raw_request['model']==r['model'],'paid request mismatch')
            require(raw_response['id']==r['response_id'] and raw_response['model']==r['model'],'paid response mismatch')
            require(raw_response['choices'][0]['message']['content']==r['text'] and raw_response['choices'][0]['finish_reason']=='stop','paid output mismatch or incomplete')
        for key in ['raw_request_file','raw_response_file']+(['events_file'] if r.get('billing')=='codex_subscription' else []):
            require(r[key] in manifest['remote_files'],'provider artifact lacks remote provenance')
    # Re-execute the unchanged exam orchestration against retained responses only.
    # Exact request equality rejects answer leakage and altered grading prompts.
    import copy
    from contextlib import redirect_stdout
    import io
    from exam_evidence import ExamResources, run_exam
    from turn_store import TurnState
    trial=TurnState([],copy.deepcopy(applied),{'spend_usd':0}, {}, [])
    resources=ExamResources(Path(__file__).parent,loop.load_benchmark_suite(),
                            'gpt-5.6-sol','moonshotai/kimi-k2.6','deepseek/deepseek-v3.2')
    def replay_provider(model,system,user,**params):
        matching=[r for r in calls if r['request']=={'model':model,'system':system,'user':user}]
        require(len(matching)==1,'exam lacks an exact canonical provider request')
        return matching[0]['text'],matching[0]['usage']
    for index,event in enumerate(events,1):
        def count_tokens(value):
            if value==event['original']:return event['orig_tokens']
            require(value==event['encoded'],'unknown exam token measurement')
            return event['enc_tokens']
        with redirect_stdout(io.StringIO()):
            run_exam(trial,index,resources=resources,provider=replay_provider,count_tokens=count_tokens)
        actual=trial.conversation[-1]
        require(all(actual[key]==event[key] for key in ('benchmark_id','language_hash','encoded','decoded','judge_attempts','judge_valid','meaning_pass','semantic_coverage_pct','message_body_savings_pct')),'canonical exam replay mismatch')
    for role in ['C','A','B']:
        turns=[r for r in receipts['calls'] if r['role']==role]
        require(bool(turns),'missing real provider '+role)
        for r in turns:
            require(r['model']==production['models'][role] and bool(r['response_id']),'wrong provider route')
            require(r['finish_reason']=='stop','incomplete provider call')
            if role in ['A','C']:
                require(r['billing']=='codex_subscription' and r['reasoning']=='high','wrong Codex login or reasoning')
    for role in ['A','B']:
        scheduled=[r for r in production['scheduled_turns'] if r['role']==role and r['turn']>=production['adoption']['turn']]
        require(bool(scheduled),'scheduled continuation missing for '+role)
        for r in scheduled:
            require(r['pre_turn_snapshot_file'] in manifest['remote_files'],'pre-turn state lacks remote provenance')
            pre_turn=read(r['pre_turn_snapshot_file'])
            require(r['language_hash']==language_payload(pre_turn['rulebook'])['hash'],'scheduled prompt book mismatch')
            call=next(c for c in receipts['calls'] if c['response_id']==r['response_id'])
            prompt=call['request']; marker='=== STRUCTURED WORKING CONTEXT ===\n'
            require(marker in prompt['system'] and f'It is turn {r["turn"]}. You are Agent {role}.' in prompt['user'],'scheduled request identity mismatch')
            context=json.JSONDecoder().raw_decode(prompt['system'].split(marker,1)[1])[0]
            require(context['accepted_snapshot']==expected_snapshot,'scheduled accepted book mismatch')
            from legislature import post_checkpoint_rule_changes
            require(context['post_checkpoint_changes']==post_checkpoint_rule_changes(pre_turn['rulebook'],adoption['turn']),'scheduled rule changes mismatch')
            delivery=context['current_machine_state']['collaboration_input'].get('cleanup_creative_seeds')
            require(delivery and delivery['seeds']==seeds,'three-idea delivery absent')
            canonical=next(e for e in production['conversation'] if e.get('turn')==r['turn'] and e.get('agent')==role and e.get('type')=='message')
            from legislature import latest_post_state_receipt
            prior=latest_post_state_receipt(production['conversation'][:production['conversation'].index(canonical)])
            require(prior and prior['rulebook_hash']==snapshot_hash(pre_turn['rulebook']) and prior['adopted_language_hash']==r['language_hash'],'pre-turn book lacks canonical lineage')
            assembled=hashlib.sha256(f'SYSTEM\n{prompt["system"]}\nUSER\n{prompt["user"]}'.encode()).hexdigest()
            require(canonical['prompt_receipt']['assembled_sha256']==assembled,'canonical prompt receipt mismatch')
            require(r['scheduler_snapshot_file'] in manifest['remote_files'],'scheduler evidence lacks remote capture')
            scheduler=read(r['scheduler_snapshot_file'])
            require(scheduler['unit']=='language-loop.service' and scheduler['TriggeredBy']=='language-loop.timer','manual-only continuation')
            delay=int(scheduler['ExecMainStartTimestampMonotonic'])-int(scheduler['LastTriggerUSecMonotonic'])
            require(0<=delay<=5000000 and bool(scheduler['InvocationID']),'service start not bound to timer trigger')
            require(scheduler['ExecMainStatus']=='0' and scheduler['completed_turn']>=r['turn'],'scheduled service did not complete')
            require(any(c['response_id']==r['response_id'] for c in receipts['calls'] if c['role']==role),'scheduled provider receipt absent')
    browser=read('browser.json')
    require(browser['url']=='https://alanguagealltheirown.com','wrong public target')
    require(browser['language_hash']==production['language_hash'] and browser['active_tokens']==production['active_tokens'],'public book mismatch')
    require(browser['latest_turn']==production['latest_turn'],'stale public activity')
    from public_snapshot import _public_cleanup_event
    require(browser['models']==production['models'] and browser['exams']==_public_cleanup_event(adoption)['exam_results'],'public model/test mismatch')
    require(browser['screenshot_file'] in manifest['sha256'],'screenshot bytes missing')
    require(manifest['sha256'][browser['screenshot_file']]==browser['screenshot_sha256'] and bool(browser['observed_text']),'missing browser evidence')
    live=live_reader(manifest['remote_files'])
    require(datetime.fromisoformat(live['budget']['expires_at'])>datetime.now(timezone.utc),'operating window expired')
    require(live['budget']['stopped'] is False and float(live['budget']['spent_usd'])<float(live['budget']['limit_usd']),'budget exhausted or uncertain')
    require(live['revision']==production['revision'] and live['timer']=='active','production changed or timer stopped')
    require(language_payload(live['state']['rulebook.json'])['hash']==production['language_hash'],'actual live book mismatch')
    require(live['state']['rulebook.json']['kernel_tokens']==production['active_tokens'],'actual live size mismatch')
    cleanup=live['state']['meta.json']['automatic_cleanup']
    require(cleanup['structured_snapshot']==expected_snapshot,'actual structured checkpoint mismatch')
    require(cleanup['schema_version']==loop.AUTOMATIC_CLEANUP_STATE_SCHEMA_VERSION and type(cleanup['baseline_tokens']) is int and cleanup['baseline_tokens']>0 and cleanup['last_status'] in {'applied','armed'} and not cleanup.get('quarantine'),'future cleanup unavailable')
    require(live['state']['meta.json']['runtime_models']==production['models'],'actual live routing mismatch')
    require(live['state']['conversation.json']==production['conversation'],'canonical history mismatch')
    from legislature import latest_post_state_receipt
    latest=latest_post_state_receipt(live['state']['conversation.json'])
    require(latest and latest['rulebook_hash']==snapshot_hash(live['state']['rulebook.json']) and latest['adopted_language_hash']==production['language_hash'],'live book lacks canonical lineage')
    for name,digest in live['remote_hashes'].items():
        require(name in manifest['sha256'] and manifest['sha256'][name]==digest,'remote receipt mismatch')
    for name in RUNTIME_FILES:
        require(live['code'][name]==hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest(),'deployed code mismatch: '+name)

    return {'complete':True,'language_hash':language,'before_tokens':report['source_tokens'],
            'after_tokens':report['applied_tokens'],'meaning_passes':5,'production_revision':production['revision']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');args=parser.parse_args()
    try:print(json.dumps(check(args.directory),indent=2))
    except (OSError,ValueError,KeyError,TypeError,IndexError,StopIteration,subprocess.SubprocessError) as exc:
        print(json.dumps({'complete':False,'reason':str(exc)}));raise SystemExit(1)
