import tempfile
import unittest
from pathlib import Path
from cleanup_replay import CleanupReplay

class CleanupReplayTests(unittest.TestCase):
    def test_identical_occurrences_resume_in_order_without_redispatch(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]; accounted=set()
            def provider(*args,**kwargs):
                receipt=str(len(calls));calls.append(receipt)
                accounted.add(receipt)
                return receipt,{'cost':.01,'response_receipt':{'id':receipt,'finish_reason':'stop'}}
            def account(meta,usage):accounted.add(usage['response_receipt']['id'])
            first=CleanupReplay(Path(d),account=account).call(provider)
            self.assertEqual([first('c','s','u',meta={})[0] for _ in range(2)],['0','1'])
            resumed=CleanupReplay(Path(d),account=account).call(provider)
            results=[resumed('c','s','u',meta={}) for _ in range(2)]
            self.assertEqual([r[0] for r in results],['0','1'])
            self.assertTrue(all(r[1]['replayed'] for r in results))
            self.assertEqual(calls,['0','1']);self.assertEqual(accounted,{'0','1'})
            changed=CleanupReplay(Path(d),account=account).call(provider)
            self.assertEqual(changed('c','new system','u',meta={})[0],'2')

    def test_incomplete_response_and_interruption_do_not_become_completed_replay(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            def provider(*args,**kwargs):
                calls.append(1)
                return 'partial',{'cost':.01,'response_receipt':{'finish_reason':'length'}}
            for _ in range(2):CleanupReplay(d,account=lambda *a:None).call(provider)('c')
            self.assertEqual(len(calls),2)
            def interrupted(*a,**kw):raise RuntimeError('interrupted')
            with self.assertRaises(RuntimeError):CleanupReplay(d,account=lambda *a:None).call(interrupted)('c')
            self.assertFalse(list(Path(d).glob('*.json')))
