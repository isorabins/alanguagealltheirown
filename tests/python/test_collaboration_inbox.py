import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import collab_sync
from collaboration import (RedisRest, append_inbox_spool, deliver_one, empty_state,
                           import_inbox_spool, reconcile, stable_record, write_outbox)
from state_store import load_json
from tests.support.stub_server import server


class FakeRedis(RedisRest):
    def __init__(self): self.namespace="test"; self.values={}; self.queues={}
    def command(self, *parts):
        command=str(parts[0]).upper()
        if command=="EVAL" and "RPUSH" in parts[1]:
            _,_,_,marker,queue,value=parts
            if marker in self.values: return 0
            self.values[marker]="1"; self.queues.setdefault(queue,[]).append(value); return 1
        if command=="EVAL" and "LINDEX" in parts[1]:
            _,_,_,queue,lease,ttl,owner=parts
            if lease in self.values or not self.queues.get(queue): return None
            value=self.queues[queue][0]; self.values[lease]=owner+"\n"+value; return value
        if command=="EVAL" and "LREM" in parts[1]:
            _,_,_,queue,lease,done,owner=parts; leased=self.values.get(lease)
            if not leased or not leased.startswith(owner+"\n"): return 0
            value=leased.split("\n",1)[1]; self.values.pop(lease,None)
            if value in self.queues.get(queue,[]): self.queues[queue].remove(value)
            self.values[done]="1"; return 1
        if command=="DEL": self.values.pop(parts[1],None); return 1
        if command=="SET": self.values[parts[1]]=parts[2]; return "OK"
        if command=="GET": return self.values.get(parts[1])
        raise AssertionError(parts)


class CollaborationTests(unittest.TestCase):
    def test_real_rest_client_uses_json_command_envelope(self):
        httpd=server({"/":(200,{"result":1})}); thread=threading.Thread(target=httpd.serve_forever,daemon=True); thread.start()
        try:
            redis=RedisRest(f"http://127.0.0.1:{httpd.server_port}","fixture-token","test")
            self.assertEqual(redis.command("SET","key","value"),1)
            request=httpd.RequestHandlerClass.requests[-1]
            self.assertEqual(request["path"],"/"); self.assertEqual(request["body"],b'["SET", "key", "value"]')
        finally:
            httpd.shutdown(); thread.join(); httpd.server_close()

    def test_enqueue_claim_lease_ack_and_idempotency(self):
        redis=FakeRedis(); record={"id":"s-1","kind":"SUGGESTION","text":"hello"}
        self.assertTrue(redis.enqueue("suggestion",record)); self.assertFalse(redis.enqueue("suggestion",record))
        claimed=redis.claim("suggestion","worker"); self.assertEqual(claimed["id"],"s-1")
        self.assertIsNone(redis.claim("suggestion","worker"))
        redis.ack("suggestion","stale-worker","s-1"); self.assertEqual(len(redis.queues["test:queue:suggestion"]),1)
        redis.ack("suggestion","worker","s-1"); self.assertEqual(redis.queues["test:queue:suggestion"],[])

    def test_restart_reconcile_and_exact_once_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"collaboration.json"; ask=stable_record("ASK","A","Which boundary?","ask-1")
            state=reconcile(path,[ask,ask]); self.assertEqual(len(state["asks"]),1)
            state["asks"][0].update({"status":"answered","answer":"Keep the boundary."})
            first=deliver_one(state,"ASK","A"); second=deliver_one(state,"ASK","A")
            self.assertEqual(first["kind"],"ASK"); self.assertEqual(first["question"],"Which boundary?"); self.assertEqual(first["answer"],"Keep the boundary.")
            self.assertIsNone(second)

    def test_local_spool_is_fsynced_before_transport_ack(self):
        with tempfile.TemporaryDirectory() as directory:
            spool=Path(directory)/"collaboration-inbox.json"; redis=FakeRedis()
            record={"id":"suggestion-2","kind":"SUGGESTION","text":"hello","status":"pending_review"}
            redis.enqueue("suggestion",record); original_ack=redis.ack
            def guarded_ack(queue,owner,record_id):
                saved=load_json(spool,{})
                self.assertIn(record_id,[r.get("id") for r in saved.get("records",[])])
                original_ack(queue,owner,record_id)
            redis.ack=guarded_ack
            self.assertEqual(collab_sync.pull(redis,spool,owner="worker"),0)
            canonical=Path(directory)/"collaboration.json"
            state=import_inbox_spool(empty_state(),spool,turn=4)
            self.assertFalse(canonical.exists())
            self.assertEqual(state["suggestions"][0]["id"],"suggestion-2")
            self.assertEqual(redis.queues["test:queue:suggestion"],[])

    def test_moderation_contract_applies_approved_decision_once(self):
        with tempfile.TemporaryDirectory() as directory:
            spool=Path(directory)/"collaboration-inbox.json"; redis=FakeRedis(); state=empty_state()
            state["suggestions"].append({"id":"suggestion-3","kind":"SUGGESTION","text":"idea",
                                         "status":"pending_review"})
            command={"id":"command-3","kind":"MODERATION","target_id":"suggestion-3","action":"moderate_suggestion",
                     "decision":"approved","created_at":1}
            redis.enqueue("moderation",command)
            collab_sync.pull(redis,spool,owner="worker")
            state=import_inbox_spool(state,spool,turn=5)
            self.assertEqual(state["suggestions"][0]["status"],"approved")

    def test_private_redis_recovers_canonical_state_after_local_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            spool=Path(directory)/"collaboration-inbox.json"; redis=FakeRedis(); remote=empty_state()
            remote["asks"].append(stable_record("ASK","A","Recovered question?","ask-recover"))
            redis.publish_private(remote)
            collab_sync.pull(redis,spool,owner="worker")
            recovered=import_inbox_spool(empty_state(),spool)
            self.assertEqual(recovered["asks"][0]["id"],"ask-recover")
            self.assertEqual(load_json(spool,{})["recovery_state"]["asks"][0]["question"],"Recovered question?")

    def test_courier_exception_never_writes_canonical_or_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory); spool=directory/"collaboration-inbox.json"
            canonical=directory/"collaboration.json"
            class BrokenRedis:
                def load_private(self): raise TimeoutError("offline")
            self.assertEqual(collab_sync.pull(BrokenRedis(),spool),0)
            self.assertFalse(spool.exists()); self.assertFalse(canonical.exists())

    def test_spool_replay_imports_each_command_once(self):
        with tempfile.TemporaryDirectory() as directory:
            spool=Path(directory)/"collaboration-inbox.json"
            record={"id":"suggestion-replay","kind":"SUGGESTION","text":"idea","status":"pending_review"}
            append_inbox_spool(spool,[record,record])
            state=import_inbox_spool(empty_state(),spool)
            state=import_inbox_spool(state,spool)
            self.assertEqual([r["id"] for r in state["suggestions"]],["suggestion-replay"])
            self.assertEqual(state["processed_inbox_ids"],["suggestion-replay"])

    def test_outbox_publication_reads_loop_authored_snapshot_only(self):
        with tempfile.TemporaryDirectory() as directory:
            outbox=Path(directory)/"collaboration-outbox.json"; redis=FakeRedis(); state=empty_state()
            state["asks"].append(stable_record("ASK","A","Published question?","ask-publish"))
            write_outbox(outbox,state)
            self.assertEqual(collab_sync.push(redis,outbox),0)
            published=json.loads(redis.values["test:private-state"])
            self.assertEqual(published["asks"][0]["id"],"ask-publish")

    def test_run_turn_bounds_courier_and_continues_on_failure(self):
        script=(Path(__file__).parents[2]/"run_turn.sh").read_text()
        self.assertIn("timeout 8s python3 collab_sync.py pull",script)
        self.assertIn("timeout 8s python3 collab_sync.py push",script)
        self.assertRegex(script,r"collab_sync\.py pull.*\|\| true[\s\S]*python3 loop\.py")

    def test_research_returns_question_and_result_only_to_requester_once(self):
        state=empty_state(); research=stable_record("RESEARCH","B","What evidence?","research-1")
        research.update({"status":"answered","findings":"A cited result.","limitations":"One source.",
                         "citations":[{"title":"Primary","url":"https://example.test"}]})
        state["research"].append(research)
        self.assertIsNone(deliver_one(state,"RESEARCH","A",10))
        delivered=deliver_one(state,"RESEARCH","B",11)
        self.assertEqual(delivered["question"],"What evidence?")
        self.assertEqual(delivered["findings"],"A cited result.")
        self.assertIsNone(deliver_one(state,"RESEARCH","B",12))


if __name__ == "__main__": unittest.main()
