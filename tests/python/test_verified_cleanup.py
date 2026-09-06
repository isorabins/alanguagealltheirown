import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from exam_evidence import ExamResources
from verified_cleanup import run_verified_cleanup, CleanupPolicy
from test_shadow_cleanup import c_response

ROOT = Path(__file__).resolve().parents[2]


class VerifiedCleanupTests(unittest.TestCase):
    def run_case(self, *, first_reject=False, final_reject=False, invalid_judge=False,
                 meaning_fail=False, provider_fail=False, stale_audit=False,
                 open_motion=False, oversized=False, source_tokens=1000, candidate_tokens=100, max_spend=1.1, probe_cost=0, resume=False, changed_resume=False, tamper_resume=None):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = {'version':'1', 'next_id':3, 'changes':0, 'kernel_tokens':source_tokens,
                'rules':[{'id':f'rule-00{i}', 'status':'adopted', 'text_en':'Preserve deadlines. '*80,
                          'history':[]} for i in (1,2)]}
            if open_motion:
                source['rules'].append({'id':'rule-003','status':'proposed','text_en':'Pending.'})
            path=base/'source.json'; path.write_text(json.dumps(source))
            before=path.read_bytes()
            suite={'version':'test', 'benchmarks':[{'id':f'E{i}', 'name':'Deadline',
                'source_turn':i, 'original':'Send by 5 PM.', 'answer_key':[
                    {'id':f'E{i}.1','meaning':'Send by 5 PM.','critical':True,'literal_sets':[['5 PM']]}]}
                    for i in (1,2)]}
            meta={'spend_usd':0,'tests_run':9,'benchmark_suite':{'version':'live','next_index':4,'cycle':3}}
            prior=copy.deepcopy(meta)
            calls=[]; audits=0
            def call(model,system,user,**kwargs):
                nonlocal audits
                calls.append(model);kwargs['meta']['spend_usd']+=.01
                usage={'cost':.01,'response_receipt':{'finish_reason':'stop'}}
                if model=='c':
                    request=json.loads(user)
                    if 'b_advisory' in request:
                        self.assertEqual(request['b_review_scope']['kind'],'operative_dependency_and_cited_history_v1')
                        self.assertEqual(request['b_review_scope']['retained_text_ids'],['rule-001','rule-002'])
                    return json.dumps(c_response()),usage
                if model=='b':
                    audits+=1;request=json.loads(user)
                    if resume and audits==1: raise RuntimeError('review unavailable')
                    rejected=(first_reject and audits==1) or (final_reject and audits>1)
                    return json.dumps({'verdict':'REJECT' if rejected else 'pass',
                        'reviewed_source_hash':request['source_hash'],
                        'reviewed_candidate_hash':'stale' if stale_audit else request['candidate_hash'],
                        'covered_source_ids':['rule-001','rule-002'],
                        'omissions':[{'source_id':'rule-001','issue':'Missing deadline.'}] if rejected else [],
                        'meaning_changes':[],'operational_text':[],'notes':[]}),usage
                if provider_fail: raise RuntimeError('provider unavailable')
                if model=='encoder': return 'Send by 5 PM.',usage
                if model=='decoder':
                    self.assertEqual(user,'Send by 5 PM.')
                    self.assertNotIn('ATOMIC ANSWER KEY',system)
                    return 'Send by 5 PM.',usage
                key=json.loads(user.split('ATOMIC ANSWER KEY:\n')[1].split('\n\nNUMBERED DECODED:')[0])
                grade={'mode':'RELAY','items':[{'id':key[0]['id'],
                    'verdict':'CORRUPTED' if meaning_fail else 'SURVIVED',
                    'evidence_lines':[99,99] if invalid_judge else [1,1]}], 'inventions':[]}
                return json.dumps(grade),usage
            def tokens(text,_meta):
                _meta['spend_usd'] += probe_cost
                if text.startswith('LANGUAGE'):
                    return (5000 if oversized else candidate_tokens) if 'CONTRACT' in text else source_tokens
                return 10
            report=run_verified_cleanup(path,base/'out',exams=ExamResources(ROOT,suite,'encoder','decoder','grader'),
                policy=CleanupPolicy(), model_c='c',model_b='b',call_model=call,
                token_counter=tokens,meta=meta,max_spend_usd=max_spend)
            if resume:
                self.assertEqual(report['status'],'FAIL')
                if changed_resume:
                    source['rules'][0]['text_en']='Changed language.'
                    path.write_text(json.dumps(source));before=path.read_bytes()
                if tamper_resume:
                    saved_path=base/'out/shadow/c-call.json'
                    saved=json.loads(saved_path.read_text())
                    if tamper_resume=='content':saved['content']='{}'
                    elif tamper_resume=='model':saved['model']='different-c'
                    elif tamper_resume=='prompt':saved['prompt_sha256']='stale'
                    saved_path.write_text(json.dumps(saved))
                report=run_verified_cleanup(path,base/'resumed',exams=ExamResources(ROOT,suite,'encoder','decoder','grader'),
                    policy=CleanupPolicy(),model_c='c',model_b='b',call_model=call,
                    token_counter=tokens,meta=meta,max_spend_usd=max_spend,resume_draft_dir=base/'out/shadow')
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(meta['tests_run'],prior['tests_run'])
            self.assertEqual(meta['benchmark_suite'],prior['benchmark_suite'])
            if not probe_cost:
                self.assertAlmostEqual(meta['spend_usd'],len(calls)*.01)
            result_dir=base/('resumed' if resume else 'out')
            exposed=(result_dir/'candidate.json').exists()
            self.assertEqual(exposed,report['status']=='PASS')
            if exposed:
                self.assertEqual(len(json.loads((result_dir/'creative-seeds.json').read_text())),3)
            return report,calls

    def test_all_real_exam_stages_and_exact_review_required_before_exposure(self):
        report,calls=self.run_case()
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(calls,['c','b','c','encoder','decoder','grader','encoder','decoder','grader'])
        self.assertEqual(len(report['exam_results']),2)
        self.assertEqual(report['reviewed_candidate_hash'],report['candidate_hash'])

    def test_c_revision_cannot_inherit_prior_review(self):
        report,calls=self.run_case(first_reject=True)
        self.assertEqual(calls[:4],['c','b','c','encoder'])
        self.assertEqual(report['status'],'PASS')

    def test_c_overrules_b_and_all_exams_decide_adoption(self):
        report,calls=self.run_case(first_reject=True,final_reject=True)
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(calls.count('b'),1)
        self.assertEqual(report['decision_authority'],'C')

    def test_bad_judge_or_meaning_stops_admission_but_runs_whole_suite(self):
        for flag in ('invalid_judge','meaning_fail'):
            with self.subTest(flag=flag):
                report,calls=self.run_case(**{flag:True})
                self.assertEqual(report['status'],'FAIL')
                self.assertEqual(len(report['exam_results']),2)
                self.assertEqual(report['stage'],'exam_gate')

    def test_provider_failure_retains_old_book_and_spend(self):
        report,_=self.run_case(provider_fail=True)
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(report['error_type'],'RuntimeError')

    def test_stale_review_is_not_admission(self):
        report,calls=self.run_case(stale_audit=True)
        self.assertEqual(report['status'],'FAIL')
        self.assertNotIn('encoder',calls)

    def test_open_motion_must_not_be_discarded(self):
        report,calls=self.run_case(open_motion=True)
        self.assertEqual(report['stage'],'open_motion')
        self.assertEqual(calls,[])

    def test_oversized_book_cannot_proceed(self):
        report,calls=self.run_case(oversized=True)
        self.assertEqual(report['status'],'FAIL')
        self.assertNotIn('encoder',calls)

    def test_exact_size_ceiling_despite_percentage_rounding(self):
        report,_=self.run_case(source_tokens=21491,candidate_tokens=4500)
        self.assertEqual(report['status'],'PASS')
        report,calls=self.run_case(source_tokens=21491,candidate_tokens=4501)
        self.assertEqual(report['status'],'FAIL')
        self.assertNotIn('encoder',calls)

    def test_admission_budget_covers_revision_exams_and_token_probes(self):
        report,calls=self.run_case(first_reject=True,max_spend=.035)
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(calls,['c','b','c','encoder'])
        self.assertEqual(report['error_type'],'CleanupBudgetExceeded')
        report,calls=self.run_case(max_spend=.045)
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(calls,['c','b','c','encoder','decoder'])
        self.assertEqual(report['error_type'],'CleanupBudgetExceeded')
        report,calls=self.run_case(max_spend=.005,probe_cost=.006)
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(calls,[])
        self.assertEqual(report['error_type'],'CleanupBudgetExceeded')

    def test_resume_unavailable_review_revalidates_draft_without_redrafting(self):
        report,calls=self.run_case(resume=True)
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(calls,['c','b','b','c','encoder','decoder','grader','encoder','decoder','grader'])
        self.assertEqual(report['prior_status'],'FAIL')

    def test_resume_refuses_changed_source_before_review(self):
        report,calls=self.run_case(resume=True,changed_resume=True)
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(calls,['c','b'])

    def test_review_projection_keeps_operative_dependencies_and_cited_history(self):
        from shadow_cleanup import semantic_review_request
        from state_store import snapshot_hash
        import hashlib
        source={'rules':[
            {'id':'rule-001','status':'adopted','text_en':'Keep exceptions in rules 003–004.', 'history':[{'why':'Relevant memory evidence.'}]},
            {'id':'rule-002','status':'rejected','text_en':'Uncited retired text.', 'history':[{'why':'Uncited revision chatter.'}]},
            {'id':'rule-003','status':'repealed','text_en':'Preserve the example from rule-005.','history':[]},
            {'id':'rule-004','status':'rejected','text_en':'A scope exception.','history':[{'why':'Cited retired evidence with rule‑006.'}]},
            {'id':'rule-005','status':'repealed','text_en':'A transitive example.','history':[]},
            {'id':'rule-006','status':'rejected','text_en':'Unicode history dependency.', 'supersedes':'rule–007','history':[]},
            {'id':'rule-007','status':'repealed','text_en':'Metadata dependency.','history':[]}]}
        before=copy.deepcopy(source)
        candidate={'legislative_memory':{'failure_modes':[{'source_ids':['rule-001','rule-004']}]}}
        request=semantic_review_request(source,candidate);rows=request['complete_legislature']
        self.assertEqual(request['original_adopted_language'],[{'id':'rule-001','text_en':source['rules'][0]['text_en']}])
        self.assertEqual(rows[0]['history'],source['rules'][0]['history'])
        self.assertEqual(rows[0]['text_location'],'original_adopted_language')
        self.assertEqual(rows[3]['history'],source['rules'][3]['history'])
        self.assertEqual([row['text_en'] for row in rows[2:]],[row['text_en'] for row in source['rules'][2:]])
        self.assertNotIn('history',rows[1]);self.assertNotIn('text_en',rows[1])
        self.assertEqual(rows[1]['record_hash'],snapshot_hash(source['rules'][1]))
        self.assertEqual(rows[1]['text_sha256'],hashlib.sha256(source['rules'][1]['text_en'].encode()).hexdigest())
        projection=request['history_projection']
        self.assertEqual(projection['indexed_only_ids'],['rule-002'])
        self.assertEqual(projection['projection_hash'],snapshot_hash(rows))
        self.assertEqual(request['source_hash'],snapshot_hash(source));self.assertEqual(source,before)

    def test_resume_rejects_mismatched_payload_model_and_prompt(self):
        for tamper in ('content','model','prompt'):
            with self.subTest(tamper=tamper):
                report,calls=self.run_case(resume=True,tamper_resume=tamper)
                self.assertEqual(report['status'],'FAIL')
                self.assertEqual(calls,['c','b'])
