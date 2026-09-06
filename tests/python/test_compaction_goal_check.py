"""Synthetic controls for evidence correlation; never production exam evidence."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import check_compaction_goal as gate
from cleanup_rulebook import build_applied_rulebook
from exam_evidence import _numbered_decoded
from rulebook import language_payload, render_language
from shadow_cleanup import compile_c_response
from state_store import snapshot_hash
from test_shadow_cleanup import c_response
import loop

class CompletionCheckTests(unittest.TestCase):
    def build(self,root, *, evolve=False, phase_repairs=False):
        files={};remote={};calls=[]
        def put(name,value,raw=False,remote_origin=False):
            content=value if raw else json.dumps(value)
            (root/name).write_text(content);files[name]=hashlib.sha256(content.encode()).hexdigest()
            if remote_origin:remote[name]='/root/alato-restart-20260906/fixture/'+name
        source={'version':'1','next_id':3,'rules':[{'id':f'rule-00{i}','status':'adopted','text_en':'Preserve deadlines. '*80,'history':[]} for i in [1,2]]}
        response=c_response();candidate,seeds=compile_c_response(source,response)
        applied=build_applied_rulebook(source,candidate);applied['kernel_tokens']=100
        language=language_payload(applied)['hash'];snapshot=loop.build_structured_cleanup_snapshot(candidate,checkpoint_turn=10,source_hash=snapshot_hash(source))
        def call(role,model,system,user,text,params=None):
            index=len(calls);codex=model.startswith('gpt-');identifier=('codex:' if codex else 'gen-')+str(index)
            request={'model':model,'system':system,'user':user};usage={'cost':0 if codex else .01,'response_receipt':{'id':identifier,'model':model,'finish_reason':'stop'}}
            item={'role':role,'model':model,'request':request,'text':text,'response_id':identifier,'usage':usage,'finish_reason':'stop','raw_request_file':f'request-{index}.json','raw_response_file':f'response-{index}.json'}
            if codex:
                item.update(billing='codex_subscription',reasoning='high',events_file=f'events-{index}.jsonl')
                put(item['raw_request_file'],dict(request,reasoning='high'),remote_origin=True)
                put(item['raw_response_file'],text,raw=True,remote_origin=True)
                put(item['events_file'],'\n'.join(json.dumps(e) for e in [{'type':'thread.started','thread_id':str(index)},{'type':'item.completed','item':{'type':'agent_message','text':text}},{'type':'turn.completed'}]),raw=True,remote_origin=True)
            else:
                put(item['raw_request_file'],{'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':user}],
                    **{k:v for k,v in (params or {}).items() if k in ('max_tokens','temperature')},'reasoning':{'enabled':False}},remote_origin=True)
                put(item['raw_response_file'],{'id':identifier,'model':model,'choices':[{'message':{'content':text},'finish_reason':'stop'}]},remote_origin=True)
            calls.append(item);return item
        initial={'source_hash':snapshot_hash(source)}
        broken=copy.deepcopy(response)
        broken['assignments']['rule-001']='excluded'
        broken['exclusions']=[{'source_id':'rule-001','reason':'operational'}]
        cycle_calls=[]
        if phase_repairs:
            cycle_calls.append(call('C','gpt-6-astra','draft',json.dumps(initial),json.dumps(broken)))
        draft=call('C','gpt-6-astra','draft',json.dumps(initial),json.dumps(response))
        cycle_calls.append(draft)
        advisory={'verdict':'pass','notes':['Preserve deadlines.']}
        b=call('B','moonshotai/kimi-k3','review',json.dumps(dict(initial,candidate=candidate)),json.dumps(advisory))
        cycle_calls.append(b)
        final_request=dict(initial,final_decision=True,b_advisory=advisory,previous_draft=response,previous_candidate=candidate)
        if phase_repairs:
            cycle_calls.append(call('C','gpt-6-astra','finalize',json.dumps(final_request),json.dumps(broken)))
            final_request['structural_correction']={'error':'exclusions must exactly match __exclude__ assignments','previous_draft':broken}
        final=call('C','gpt-6-astra','finalize',json.dumps(final_request),json.dumps(response))
        cycle_calls.append(final)
        cycle=[{'role':r['role'],'response_id':r['response_id'],'request':json.loads(r['request']['user']),'response':json.loads(r['text'])} for r in cycle_calls]
        suite=[];events=[]
        from exam_evidence import ExamResources,run_exam
        from turn_store import TurnState
        from contextlib import redirect_stdout
        import io
        for i in range(5):
            ident=f'E{i}';original=f'Send item {i} by 5 PM.';key=[{'id':ident+'.1','meaning':original,'critical':True,'literal_sets':[['5 PM']]}]
            judgment={'mode':'RELAY','items':[{'id':ident+'.1','verdict':'SURVIVED','evidence_lines':[1,1]}],'inventions':[]}
            benchmark={'id':ident,'name':'Synthetic deadline','source_turn':1,'original':original,'answer_key':key}
            suite.append(benchmark)
            def fixture_provider(model,system,user,**params):
                output=json.dumps(judgment) if model=='deepseek/deepseek-v3.2' else original
                role={'gpt-5.6-sol':'A','moonshotai/kimi-k2.6':'decoder','deepseek/deepseek-v3.2':'judge'}[model]
                item=call(role,model,system,user,output,params)
                return output,item['usage']
            trial=TurnState([],copy.deepcopy(applied),{'spend_usd':0}, {}, [])
            with redirect_stdout(io.StringIO()):
                run_exam(trial,i+1,resources=ExamResources(Path(gate.__file__).parent,{'version':'v2','benchmarks':[benchmark]},'gpt-5.6-sol','moonshotai/kimi-k2.6','deepseek/deepseek-v3.2'),provider=fixture_provider,count_tokens=lambda _:10)
            events.append(trial.conversation[-1])
        conversation=[{'turn':10,'type':'cleanup','status':'applied','candidate_hash':snapshot_hash(candidate),'source_hash':snapshot_hash(source),'exam_results':events,'applied_tokens':100,'post_state_receipt':{'adopted_language_hash':language,'rulebook_hash':snapshot_hash(applied)}}];scheduled=[]
        cleanup={'structured_snapshot':snapshot,'last_status':'applied','schema_version':2,'baseline_tokens':100}
        put('reload.json',{'rulebook':applied,'meta':{'automatic_cleanup':cleanup}},remote_origin=True)
        current=copy.deepcopy(applied)
        for i,role in enumerate(['A','B'],11):
            put(f'pre-turn-{i}.json',{'rulebook':current},remote_origin=True)
            context={'accepted_snapshot':snapshot,'post_checkpoint_changes':__import__('legislature').post_checkpoint_rule_changes(current,10),'current_machine_state':{'collaboration_input':{'cleanup_creative_seeds':{'seeds':seeds}}}}
            system='=== STRUCTURED WORKING CONTEXT ===\n'+json.dumps(context);user=f'It is turn {i}. You are Agent {role}.'
            r=call(role,{'A':'gpt-5.6-sol','B':'moonshotai/kimi-k3'}[role],system,user,'{}')
            put(f'start-state-{i}.json',{'conversation':conversation,'rulebook':current,'meta':{'automatic_cleanup':cleanup}},remote_origin=True)
            conversation.append({'turn':i,'type':'message','agent':role,'prompt_receipt':{'assembled_sha256':hashlib.sha256(f'SYSTEM\n{system}\nUSER\n{user}'.encode()).hexdigest()}})
            if evolve and role=='A':
                current['rules'].append({'id':'rule-evolved','status':'adopted','text_en':'A later general rule.','history':[{'turn':11,'verb':'adopt'}]})
                current['kernel_tokens']=105
                conversation.append({'turn':i,'type':'legislature','agent':'harness',
                    'post_state_receipt':{'adopted_language_hash':language_payload(current)['hash'],'rulebook_hash':snapshot_hash(current)}})
            put(f'terminal-state-{i}.json',{'conversation':conversation,'rulebook':current,'meta':{'automatic_cleanup':cleanup}},remote_origin=True)
            filename=f'scheduler-{i}.json'
            put(filename,{'unit':'language-loop.service','TriggeredBy':'language-loop.timer','ExecMainStartTimestampMonotonic':200,'LastTriggerUSecMonotonic':100,'InvocationID':str(i),'ExecMainStatus':'0','completed_turn':i},remote_origin=True)
            put(f'start-scheduler-{i}.json',json.loads((root/filename).read_text()),remote_origin=True)
            for name,origin in [(filename,f'scheduler-{i}-terminal.json'),
                                (f'start-scheduler-{i}.json',f'scheduler-{i}-start.json'),
                                (f'start-state-{i}.json',f'state-{i}-start.json'),
                                (f'terminal-state-{i}.json',f'state-{i}-terminal.json')]:
                remote[name]='/root/alato-restart-20260906/fixture/'+origin
            scheduled.append({'turn':i,'role':role,'pre_turn_snapshot_file':f'pre-turn-{i}.json','language_hash':language_payload(json.loads((root/f'pre-turn-{i}.json').read_text())['rulebook'])['hash'],'response_id':r['response_id'],'scheduler_snapshot_file':filename,'scheduler_start_file':f'start-scheduler-{i}.json','invocation_start_state_file':f'start-state-{i}.json','invocation_terminal_state_file':f'terminal-state-{i}.json'})
        models={'A':'gpt-5.6-sol','B':'moonshotai/kimi-k3','C':'gpt-6-astra'}
        report={'status':'PASS','stage':'complete','source_hash':snapshot_hash(source),'candidate_hash':snapshot_hash(candidate),'final_candidate_hash':snapshot_hash(candidate),'decision_authority':'C','c_cycle_completed':True,'applied_tokens':100,'source_tokens':1000,'applied_language_hash':language,'exam_results':events}
        production={'host':'claude-vps','path':'/root/alanguagealltheirown','revision':'a'*40,'adoption':{'turn':10,'candidate_hash':snapshot_hash(candidate),'language_hash':language},'reload_language_hash':language,'reload_snapshot_file':'reload.json','language_hash':language_payload(current)['hash'],'active_tokens':current['kernel_tokens'],'exams':events,'timer_active':True,'future_c_enabled':True,'models':models,'scheduled_turns':scheduled,'accepted_snapshot':snapshot,'conversation':conversation,'latest_turn':12}
        put('screenshot.png','synthetic screenshot bytes',raw=True)
        browser={'url':'https://alanguagealltheirown.com','language_hash':language_payload(current)['hash'],'active_tokens':current['kernel_tokens'],'latest_turn':12,'models':models,'exams':__import__('public_snapshot')._public_cleanup_event(conversation[0])['exam_results'],'screenshot_file':'screenshot.png','screenshot_sha256':files['screenshot.png'],'observed_text':'Synthetic control'}
        for name,value in {'source.json':source,'candidate.json':candidate,'creative-seeds.json':seeds,'report.json':report,'exam-events.json':events,'production.json':production,'provider-receipts.json':{'source_hash':snapshot_hash(source),'candidate_hash':snapshot_hash(candidate),'compaction_cycle':cycle,'calls':calls},'browser.json':browser}.items():put(name,value)
        put('manifest.json',{'sha256':dict(files),'remote_files':remote})
        live={'budget':{'expires_at':'2099-01-01T00:00:00+00:00','spent_usd':'0.2','limit_usd':'2','stopped':False},'revision':'a'*40,'timer':'active','state':{'rulebook.json':current,'meta.json':{'runtime_models':models,'automatic_cleanup':cleanup},'conversation.json':conversation},'remote_hashes':{k:files[k] for k in remote},'code':{name:hashlib.sha256((gate.Path(gate.__file__).parent/name).read_bytes()).hexdigest() for name in gate.RUNTIME_FILES}}
        return suite,live

    def test_positive_fixture_and_negative_semantic_controls(self):
        mutations={
            'failed_exam':('exam-events.json',lambda x:x[0].update(meaning_pass=False)),
            'live_size':('production.json',lambda x:x.update(active_tokens=99999)),
            'missing_exams':('production.json',lambda x:x.update(exams=[])),
            'local_only':('production.json',lambda x:x.update(host='local')),
            'no_continuation':('production.json',lambda x:x.update(scheduled_turns=[])),
            'wrong_candidate':('report.json',lambda x:x.update(candidate_hash='wrong')),
            'unrelated_c':('provider-receipts.json',lambda x:x['compaction_cycle'][-1].update(response_id='absent')),
            'unrelated_encoder':('provider-receipts.json',lambda x:x['calls'][3].update(text='not encoded text')),
            'unrelated_checkpoint':('production.json',lambda x:x['accepted_snapshot'].update(source_hash='unrelated')),
            'no_adoption':('production.json',lambda x:x['conversation'].pop(0)),
            'raw_length':('response-1.json',lambda x:x['choices'][0].update(finish_reason='length')),
            'wrong_changes':('pre-turn-11.json',lambda x:x['rulebook']['rules'].append({'id':'bad','status':'adopted','text_en':'different','history':[{'turn':11,'verb':'adopt'}]})),
            'manual_turn':('scheduler-11.json',lambda x:x.update(LastTriggerUSecMonotonic=99999999)),
        }
        for name,mutation in [('positive',None),*mutations.items()]:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
                root=Path(d);suite,live=self.build(root)
                if mutation:
                    filename,change=mutation;p=root/filename;value=json.loads(p.read_text());change(value);p.write_text(json.dumps(value))
                    m=json.loads((root/'manifest.json').read_text());m['sha256'][filename]=hashlib.sha256(p.read_bytes()).hexdigest();(root/'manifest.json').write_text(json.dumps(m))
                with patch.object(loop,'load_benchmark_suite',return_value={'version':'v2','benchmarks':suite}):
                    if mutation:
                        with self.assertRaises((ValueError,KeyError,StopIteration)):gate.check(root,live_reader=lambda _:live)
                    else:self.assertTrue(gate.check(root,live_reader=lambda _:live)['complete'])

    def test_accepts_normal_evolution_after_compact_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);suite,live=self.build(root,evolve=True)
            with patch.object(loop,'load_benchmark_suite',return_value={'version':'v2','benchmarks':suite}):
                self.assertTrue(gate.check(root,live_reader=lambda _:live)['complete'])

    def test_bounded_phase_repairs_and_exact_reviewed_draft(self):
        for mutation in (None, 'fifth_c', 'wrong_draft'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                root=Path(d);suite,live=self.build(root,phase_repairs=True)
                if mutation:
                    p=root/'provider-receipts.json';value=json.loads(p.read_text())
                    if mutation=='fifth_c':value['compaction_cycle'].append(copy.deepcopy(value['compaction_cycle'][-1]))
                    else:value['compaction_cycle'][-1]['request']['previous_draft']['assignments']['rule-001']='wrong'
                    p.write_text(json.dumps(value))
                    m=json.loads((root/'manifest.json').read_text());m['sha256'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest();(root/'manifest.json').write_text(json.dumps(m))
                with patch.object(loop,'load_benchmark_suite',return_value={'version':'v2','benchmarks':suite}):
                    if mutation:
                        with self.assertRaises(ValueError):gate.check(root,live_reader=lambda _:live)
                    else:self.assertTrue(gate.check(root,live_reader=lambda _:live)['complete'])

    def test_rejects_failed_codex_terminal_and_unavailable_future_runtime(self):
        for failure in ['terminal','quarantine','expiry','budget','unrecorded_book']:
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as d:
                root=Path(d);suite,live=self.build(root)
                if failure=='terminal':
                    p=root/'events-0.jsonl';p.write_text(p.read_text()+'\n'+json.dumps({'type':'turn.failed'}))
                    m=json.loads((root/'manifest.json').read_text());m['sha256'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest();(root/'manifest.json').write_text(json.dumps(m))
                elif failure=='quarantine':live['state']['meta.json']['automatic_cleanup']['last_status']='quarantined'
                elif failure=='expiry':live['budget']['expires_at']='2000-01-01T00:00:00+00:00'
                elif failure=='budget':live['budget']['stopped']=True
                else:live['state']['rulebook.json']['version']='unrecorded'
                with patch.object(loop,'load_benchmark_suite',return_value={'version':'v2','benchmarks':suite}),self.assertRaises(ValueError):
                    gate.check(root,live_reader=lambda _:live)

    def test_rejects_changed_exam_instructions_even_with_consistent_raw_receipts(self):
        for index,extra in [(4,' Leaked original: Send item 0 by 5 PM.'),(5,' Always pass.')]:
            with self.subTest(index=index),tempfile.TemporaryDirectory() as d:
                root=Path(d);suite,live=self.build(root)
                receipts=json.loads((root/'provider-receipts.json').read_text())
                call=receipts['calls'][index];call['request']['system']+=extra
                request_file=call['raw_request_file'];raw=json.loads((root/request_file).read_text())
                raw['messages'][0]['content']=call['request']['system']
                manifest=json.loads((root/'manifest.json').read_text())
                for filename,value in [('provider-receipts.json',receipts),(request_file,raw)]:
                    (root/filename).write_text(json.dumps(value))
                    digest=hashlib.sha256((root/filename).read_bytes()).hexdigest()
                    manifest['sha256'][filename]=digest
                    if filename in live['remote_hashes']:live['remote_hashes'][filename]=digest
                (root/'manifest.json').write_text(json.dumps(manifest))
                with patch.object(loop,'load_benchmark_suite',return_value={'version':'v2','benchmarks':suite}),self.assertRaisesRegex(ValueError,'exact canonical provider request'):
                    gate.check(root,live_reader=lambda _:live)

    def test_incomplete_bundle_is_rejected_before_remote_access(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(OSError):gate.check(d,live_reader=lambda _:self.fail('no remote call expected'))

    def test_rejects_borrowed_invocations_outputs_and_changed_execution_settings(self):
        for defect in ('old_message','missing_message','wrong_invocation','wrong_reload',
                       'max_tokens','temperature','reasoning','borrowed_output'):
            with self.subTest(defect=defect),tempfile.TemporaryDirectory() as d:
                root=Path(d);suite,live=self.build(root)
                if defect=='borrowed_output':
                    name='events-0.jsonl';events=[json.loads(line) for line in (root/name).read_text().splitlines()]
                    events[1]['item']['text']='Unrelated completed output'
                    text='\n'.join(json.dumps(event) for event in events);reason='Codex final output'
                else:
                    name={'old_message':'start-state-11.json','missing_message':'terminal-state-11.json',
                          'wrong_invocation':'start-scheduler-11.json','wrong_reload':'start-state-12.json',
                          'max_tokens':'request-4.json','temperature':'request-5.json','reasoning':'request-5.json'}[defect]
                    value=json.loads((root/name).read_text())
                    if defect=='old_message':
                        message=copy.deepcopy(live['state']['conversation.json'][1]);message['later_annotation']='enriched'
                        value['conversation'].append(message);reason='message not produced'
                    elif defect=='missing_message':value['conversation'].pop();reason='message not produced'
                    elif defect=='wrong_invocation':value['InvocationID']='unrelated';reason='scheduler invocation mismatch'
                    elif defect=='wrong_reload':value['rulebook']['version']='unrelated';reason='scheduled reload differs'
                    elif defect=='reasoning':value['reasoning']={'enabled':True};reason='reasoning settings mismatch'
                    else:value[defect]=3999 if defect=='max_tokens' else .9;reason='provider settings mismatch'
                    text=json.dumps(value)
                (root/name).write_text(text);digest=hashlib.sha256(text.encode()).hexdigest()
                manifest=json.loads((root/'manifest.json').read_text());manifest['sha256'][name]=digest
                live['remote_hashes'][name]=digest
                (root/'manifest.json').write_text(json.dumps(manifest))
                with patch.object(loop,'load_benchmark_suite',return_value={'version':'v2','benchmarks':suite}),self.assertRaisesRegex(ValueError,reason):
                    gate.check(root,live_reader=lambda _:live)

    def test_rejects_a_matching_scheduler_pair_from_an_unrelated_invocation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);suite,live=self.build(root)
            manifest=json.loads((root/'manifest.json').read_text())
            for name,phase in [('scheduler-11.json','terminal'),('start-scheduler-11.json','start')]:
                value=json.loads((root/name).read_text());value['InvocationID']='unrelated'
                text=json.dumps(value);(root/name).write_text(text);digest=hashlib.sha256(text.encode()).hexdigest()
                manifest['sha256'][name]=live['remote_hashes'][name]=digest
                manifest['remote_files'][name]=f'/root/alato-restart-20260906/fixture/scheduler-unrelated-{phase}.json'
            (root/'manifest.json').write_text(json.dumps(manifest))
            with patch.object(loop,'load_benchmark_suite',return_value={'version':'v2','benchmarks':suite}),self.assertRaisesRegex(ValueError,'invocation artifact origin mismatch'):
                gate.check(root,live_reader=lambda _:live)
