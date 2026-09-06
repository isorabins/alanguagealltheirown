import copy
import json
from pathlib import Path
import tempfile
import unittest

from run_full_cleanup import snapshot_source, verify_continuation
from turn_store import TurnStore, TurnRecoveryError


class FullCleanupTests(unittest.TestCase):
    def test_copy_requires_coherent_source_and_never_recovers_it(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            original = b'{"rules": []}'
            (source/'rulebook.json').write_bytes(original)
            self.assertEqual(snapshot_source(source), {'rulebook.json': original})
            ledger=b'{"receipts":{}}'
            (source/'cost-receipts.local.json').write_bytes(ledger)
            self.assertEqual(snapshot_source(source)['cost-receipts.local.json'],ledger)
            for journal in ('turn-commit.local.json', 'turn-archive.local.json'):
                pending = source/journal
                pending.write_text('{}')
                with self.assertRaisesRegex(ValueError, 'pending recovery'):
                    snapshot_source(source)
                self.assertTrue(pending.exists())
                self.assertEqual((source/'rulebook.json').read_bytes(), original)
                pending.unlink()
            with TurnStore(source).writer():
                with self.assertRaises(TurnRecoveryError):
                    snapshot_source(source)

    def test_delivery_requires_exact_book_ideas_and_role_in_actual_context(self):
        snapshot = {'source_hash':'source', 'candidate_hash':'candidate', 'checkpoint_turn':7,
                    'rulebook':{'rules':[]}}
        seeds = {'cleanup_turn':7, 'seeds':[
            {'idea':str(i), 'experiment':'Try it.', 'risk':'May fail.'} for i in range(3)]}
        context = {'accepted_snapshot':snapshot,
                   'current_machine_state':{'collaboration_input':{'cleanup_creative_seeds':seeds}}}
        def request(c, role='A'):
            return {'system':'=== STRUCTURED WORKING CONTEXT ===\n'+json.dumps(c),
                    'user':f'It is turn 8. You are Agent {role}.'}
        verify_continuation([request(context)], snapshot, seeds, 'A')
        for altered in ('source', 'idea', 'missing', 'role', 'incidental'):
            c = copy.deepcopy(context); role='A'
            if altered=='source': c['accepted_snapshot']['source_hash']='different'
            if altered=='idea': c['current_machine_state']['collaboration_input']['cleanup_creative_seeds']['seeds'][0]['idea']='different'
            if altered=='missing': c['current_machine_state']['collaboration_input']['cleanup_creative_seeds']['seeds'].pop()
            if altered=='role': role='B'
            r=request(c, role)
            if altered=='incidental': r={'system':'unstructured', 'user':'accepted_snapshot cleanup_creative_seeds'}
            with self.subTest(altered=altered), self.assertRaises(AssertionError):
                verify_continuation([r],snapshot,seeds,'A')

    def test_default_admission_commit_reload_and_exact_delivery(self):
        from unittest.mock import patch
        import loop
        from collaboration import empty_state
        from turn_store import TurnState
        from rulebook import language_payload
        from test_shadow_cleanup import c_response
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as directory, ExitStack() as patches:
            root = Path(directory)
            book = {'version':'1', 'next_id':3,'changes':0,'kernel_tokens':1000,
                'rules':[{'id':f'rule-00{i}','status':'adopted','text_en':'Preserve deadlines. '*80,
                          'history':[]} for i in (1,2)]}
            meta={'spend_usd':0,'last_agent':'B','tests_run':0,'automatic_cleanup':{
                'schema_version':2,'baseline_tokens':800,'baseline_language_hash':'old',
                'baseline_turn':0,'last_status':'armed','last_attempt_language_hash':None}}
            state=TurnState([],book,meta,empty_state(),[])
            suite={'version':'test','benchmarks':[{'id':'E1','name':'Deadline','source_turn':1,
                'original':'Send by 5 PM.','answer_key':[{'id':'E1.1','meaning':'Send by 5 PM.',
                'critical':True,'literal_sets':[['5 PM']]}]}]}
            requests=[]
            def provider(model,system,user,**kwargs):
                requests.append({'model':model,'system':system,'user':user})
                kwargs['meta']['spend_usd']+=.01
                usage={'cost':.01,'response_receipt':{'finish_reason':'stop'}}
                if 'STRUCTURED WORKING CONTEXT' in system:
                    role='A' if model=='encoder' else 'B'
                    return json.dumps({'deliberation':('Public proposal:' if role=='A' else 'Public audit:')+
                        ' The accepted language should be tested before another change is proposed.',
                        'motion':None,'fault_response':None,'measurements':[],'requests':[]}),usage
                if model=='c': return json.dumps(c_response()),usage
                if model=='b':
                    request=json.loads(user)
                    return json.dumps({'verdict':'pass','reviewed_source_hash':request['source_hash'],
                        'reviewed_candidate_hash':request['candidate_hash'],
                        'covered_source_ids':['rule-001','rule-002'],'omissions':[],
                        'meaning_changes':[],'operational_text':[],'notes':[]}),usage
                if model in ('encoder','decoder'): return 'Send by 5 PM.',usage
                return json.dumps({'mode':'RELAY','items':[{'id':'E1.1','verdict':'SURVIVED',
                    'evidence_lines':[1,1]}],'inventions':[]}),usage
            def tokens(text,meta):
                return (100 if 'CONTRACT' in text else 1000) if text.startswith('LANGUAGE') else 10
            for key,value in {'STATE':root,'MODEL_C':'c','MODEL_B':'b','MODEL_A':'encoder',
                'MODEL_DECODER':'decoder','MODEL_GRADER':'grader','call':provider,
                'token_count':tokens,'load_benchmark_suite':lambda:suite}.items():
                patches.enter_context(patch.object(loop,key,value))
            with TurnStore(root).writer() as store:
                loop.ensure_structured_protocol_cutover(state.conversation,state.rulebook,state.meta,activation_turn=0)
                store.commit(state)
                self.assertTrue(loop.maybe_run_automatic_cleanup(state.conversation,state.rulebook,state.meta,1))
                self.assertEqual([r['model'] for r in requests],['c','b','c','encoder','decoder','grader'])
                self.assertEqual(state.meta['tests_run'],0)
                accepted_hash=language_payload(state.rulebook)['hash']
                store.commit(state)
                state=store.load(TurnState([],{}, {},{},[]))
                self.assertEqual(language_payload(state.rulebook)['hash'],accepted_hash)
                expected_snapshot=copy.deepcopy(state.meta['automatic_cleanup']['structured_snapshot'])
                pending=state.meta['automatic_cleanup']['pending_creative_seeds']
                expected_seeds={k:copy.deepcopy(pending[k]) for k in ('cleanup_turn','seeds')}
                for role in ('A','B'):
                    before=len(requests)
                    outcome=loop.agent_turn(state.conversation,state.rulebook,state.meta,state.collaboration,state.next_turn)
                    self.assertEqual(outcome,'accepted')
                    verify_continuation(requests[before:],expected_snapshot,expected_seeds,role)
                    store.commit(state)
                    state=store.load(TurnState([],{}, {},{},[]))
                    if role=='A':
                        self.assertEqual(state.meta['automatic_cleanup']['pending_creative_seeds']['delivered_roles'],['A'])
                self.assertNotIn('pending_creative_seeds',state.meta['automatic_cleanup'])
                self.assertEqual(language_payload(state.rulebook)['hash'],accepted_hash)
