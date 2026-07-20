import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from collaboration import RedisRest, deliver_one, empty_state, reconcile, stable_record


class FakeRedis(RedisRest):
    def __init__(self): self.namespace="test"; self.values={}; self.queues={}
    def command(self, *parts):
        command=str(parts[0]).upper()
        if command=="EVAL" and "RPUSH" in parts[1]:
            _,_,_,marker,queue,value=parts
            if marker in self.values: return 0
            self.values[marker]="1"; self.queues.setdefault(queue,[]).append(value); return 1
        if command=="EVAL" and "LINDEX" in parts[1]:
            _,_,_,queue,lease,ttl=parts
            if lease in self.values or not self.queues.get(queue): return None
            value=self.queues[queue][0]; self.values[lease]=value; return value
        if command=="EVAL" and "LREM" in parts[1]:
            _,_,_,queue,lease,done=parts; value=self.values.pop(lease,None)
            if value in self.queues.get(queue,[]): self.queues[queue].remove(value)
            self.values[done]="1"; return 1
        if command=="DEL": self.values.pop(parts[1],None); return 1
        if command=="SET": self.values[parts[1]]=parts[2]; return "OK"
        raise AssertionError(parts)


class CollaborationTests(unittest.TestCase):
    def test_enqueue_claim_lease_ack_and_idempotency(self):
        redis=FakeRedis(); record={"id":"s-1","kind":"SUGGESTION","text":"hello"}
        self.assertTrue(redis.enqueue("suggestion",record)); self.assertFalse(redis.enqueue("suggestion",record))
        claimed=redis.claim("suggestion","worker"); self.assertEqual(claimed["id"],"s-1")
        self.assertIsNone(redis.claim("suggestion","worker")); redis.ack("suggestion","worker","s-1")

    def test_restart_reconcile_and_exact_once_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"collaboration.json"; ask=stable_record("ASK","A","Which boundary?","ask-1")
            state=reconcile(path,[ask,ask]); self.assertEqual(len(state["asks"]),1)
            state["asks"][0].update({"status":"answered","answer":"Keep the boundary."})
            first=deliver_one(state,"ASK","A"); second=deliver_one(state,"ASK","A")
            self.assertEqual(first["kind"],"ASK"); self.assertEqual(first["question"],"Which boundary?"); self.assertEqual(first["answer"],"Keep the boundary.")
            self.assertIsNone(second)


if __name__ == "__main__": unittest.main()
