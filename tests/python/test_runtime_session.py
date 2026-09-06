import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from runtime_session import RuntimeSession
from local_cleanup import LocalBudgetError
import loop

class RuntimeTests(unittest.TestCase):
    def config(self, root):
        p=root/'config.json'
        p.write_text(json.dumps({'expires_at':'2099-01-01T00:00:00+00:00','limit_usd':'.15',
            'ledger':str(root/'budget.json'),'codex_evidence':str(root/'codex'),
            'codex':'codex','models':{'m':{'context_length':10,
                'pricing':{'prompt':'0.01','completion':'0.01','request':'0'}}}}))
        return p

    def test_expiry_and_auxiliary_fees_stop_before_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            post=Mock(); c=Mock(); p=self.config(Path(d))
            session=RuntimeSession(p,post=post,compactor=c)
            with self.assertRaises(LocalBudgetError):
                session.post('url',json={'tools':[]})
            session.now=lambda:datetime(2100,1,1,tzinfo=timezone.utc)
            with self.assertRaises(LocalBudgetError):session.compact('gpt-6-astra')
            with self.assertRaises(LocalBudgetError):session.post('url',json={})
            post.assert_not_called(); c.assert_not_called()

    def test_cap_survives_restart_and_astra_uses_subscription_adapter(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=self.config(root)
            response=Mock(status_code=200)
            response.json.return_value={'id':'paid','usage':{'cost':'.10'}}
            c=Mock(return_value=('{}',{'cost':0,'billing':'codex_subscription'}))
            session=RuntimeSession(p,post=Mock(return_value=response),compactor=c)
            with patch.object(loop,'_runtime_session',session),patch.object(loop,'api_key',side_effect=AssertionError):
                _,usage=loop.call('gpt-6-astra','system','data',request_options={'schema':'test'})
            self.assertEqual(usage['billing'],'codex_subscription');c.assert_called_once()
            session.post('url',json={'model':'m','max_tokens':1,'messages':[{'role':'user','content':'x'}]})
            post=Mock(); resumed=RuntimeSession(p,post=post,compactor=c)
            with self.assertRaises(LocalBudgetError):
                resumed.post('url',json={'model':'m','max_tokens':1,'messages':[{'role':'user','content':'x'}]})
            post.assert_not_called()

    def test_cleanup_record_survives_temporary_output_removal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); session=RuntimeSession(self.config(root),compactor=Mock())
            with tempfile.TemporaryDirectory() as output:
                p=Path(output); (p/'report.json').write_text('{"status":"FAIL","candidate_hash":"abc"}')
                (p/'exam-events.json').write_text('[{"judge_attempts":[{},{}]}]')
                retained=Path(session.retain_cleanup(p))
            self.assertEqual(json.loads((retained/'report.json').read_text())['candidate_hash'],'abc')
            self.assertEqual(len(json.loads((retained/'exam-events.json').read_text())[0]['judge_attempts']),2)

    def test_sol_and_astra_route_before_api_key_with_high_reasoning(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch('runtime_session.CodexCompactor') as factory:
                session=RuntimeSession(self.config(root))
                self.assertEqual(factory.call_args.kwargs['reasoning'],'high')
            c=Mock(return_value=('text',{'cost':0}))
            session.compactor=c
            with patch.object(loop,'_runtime_session',session),patch.object(loop,'api_key',side_effect=AssertionError):
                for model in ('gpt-5.6-sol','gpt-6-astra'):
                    loop.call(model,'system','data')
            self.assertEqual([c.args[0] for c in c.call_args_list],['gpt-5.6-sol','gpt-6-astra'])
