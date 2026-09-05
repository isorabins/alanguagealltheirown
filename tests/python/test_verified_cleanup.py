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
                 open_motion=False, oversized=False, source_tokens=1000, candidate_tokens=100, max_spend=1.1, probe_cost=0):
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
                if model=='c': return json.dumps(c_response()),usage
                if model=='b':
                    audits+=1;request=json.loads(user)
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
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(meta['tests_run'],prior['tests_run'])
            self.assertEqual(meta['benchmark_suite'],prior['benchmark_suite'])
            if not probe_cost:
                self.assertAlmostEqual(meta['spend_usd'],len(calls)*.01)
            exposed=(base/'out/candidate.json').exists()
            self.assertEqual(exposed,report['status']=='PASS')
            if exposed:
                self.assertEqual(len(json.loads((base/'out/creative-seeds.json').read_text())),3)
            return report,calls

    def test_all_real_exam_stages_and_exact_review_required_before_exposure(self):
        report,calls=self.run_case()
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(calls,['c','b','encoder','decoder','grader','encoder','decoder','grader'])
        self.assertEqual(len(report['exam_results']),2)
        self.assertEqual(report['reviewed_candidate_hash'],report['candidate_hash'])

    def test_c_revision_cannot_inherit_prior_review(self):
        report,calls=self.run_case(first_reject=True)
        self.assertEqual(calls[:4],['c','b','c','b'])
        self.assertEqual(report['status'],'PASS')

    def test_final_rejection_stops_before_exams(self):
        report,calls=self.run_case(first_reject=True,final_reject=True)
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(calls,['c','b','c','b'])

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
        self.assertEqual(calls,['c','b','c','b'])
        self.assertEqual(report['error_type'],'CleanupBudgetExceeded')
        report,calls=self.run_case(max_spend=.045)
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(calls,['c','b','encoder','decoder','grader'])
        self.assertEqual(report['error_type'],'CleanupBudgetExceeded')
        report,calls=self.run_case(max_spend=.005,probe_cost=.006)
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(calls,[])
        self.assertEqual(report['error_type'],'CleanupBudgetExceeded')
