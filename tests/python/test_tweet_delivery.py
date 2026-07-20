import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests
from state_store import load_json
from tweet import MAX_LEN, attempt_post, compose, deliver, stable_id


class Response:
    def __init__(self,status=200,data=None): self.status_code=status; self._data=data or {}; self.ok=200<=status<300
    def json(self): return self._data


class TweetTests(unittest.TestCase):
    def setUp(self):
        self.env=mock.patch("tweet.env",side_effect=lambda name:{"TWEET_ENABLE":"1","UPLOAD_POST_API_KEY":"k","UPLOAD_POST_USER":"u"}.get(name,"")); self.env.start()
    def tearDown(self): self.env.stop()

    def test_confirmed_x_receipt_only_and_request_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"; delivery={"id":"stable","attempts":0,"status":"pending"}
            response=Response(data={"results":[{"platform":"x","status":"posted","post_id":"123"}]})
            with mock.patch("tweet.requests.post",return_value=response) as post:
                result=attempt_post("hello",delivery,path)
            self.assertTrue(result["confirmed"]); kwargs=post.call_args.kwargs
            self.assertEqual(kwargs["headers"]["Idempotency-Key"],"stable")
            self.assertEqual(kwargs["data"],{"user":"u","platform[]":["x"],"title":"hello","x_title":"hello",
                                              "request_id":"stable","async_upload":"false"})

    def test_official_synchronous_x_result_shape_confirms(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"; delivery={"id":"stable","attempts":0,"status":"pending"}
            response=Response(data={"success":True,"results":{"x":{"success":True,"url":"https://x.com/example/status/1"}}})
            with mock.patch("tweet.requests.post",return_value=response): result=attempt_post("hello",delivery,path)
            self.assertTrue(result["confirmed"]); self.assertEqual(result["receipt"]["platform"],"x")

    def test_async_receipt_polls_before_any_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"; delivery={"id":"stable","attempts":0,"status":"pending"}
            initial=Response(data={"success":True,"request_id":"stable","total_platforms":1})
            done=Response(data={"results":{"x":{"success":True,"url":"https://x.com/example/status/1"}}})
            with mock.patch("tweet.requests.post",return_value=initial) as post, mock.patch("tweet.requests.get",return_value=done) as get:
                first=attempt_post("hello",delivery,path); first_status=first["status"]
                second=attempt_post("hello",delivery,path)
            self.assertEqual(first_status,"pending_confirmation"); self.assertTrue(second["confirmed"])
            self.assertEqual(post.call_count,1); self.assertEqual(get.call_count,1)

    def test_pending_async_poll_never_reposts(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"
            delivery={"id":"stable","attempts":1,"status":"pending_confirmation","request_id":"job-1"}
            pending=Response(data={"status":"processing"})
            with mock.patch("tweet.requests.post") as post, mock.patch("tweet.requests.get",return_value=pending):
                result=attempt_post("hello",delivery,path)
            self.assertEqual(result["status"],"pending_confirmation"); post.assert_not_called()

    def test_x_queued_result_is_pending_not_posted(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"; delivery={"id":"stable","attempts":0,"status":"pending"}
            queued=Response(data={"success":True,"results":{"x":{"success":True,"status":"queued","id":"job-2"}}})
            with mock.patch("tweet.requests.post",return_value=queued): result=attempt_post("hello",delivery,path)
            self.assertEqual(result["status"],"pending_confirmation"); self.assertFalse(result["confirmed"])
            self.assertEqual(result["request_id"],"job-2")

    def test_failure_and_ambiguous_timeout_stop_after_three(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"; delivery={"id":"stable","attempts":0,"status":"pending"}
            missing=Response(status=404,data={"status":"not_found"})
            with mock.patch("tweet.requests.post",side_effect=requests.Timeout("after send")) as post, \
                 mock.patch("tweet.requests.get",return_value=missing):
                for _ in range(4): attempt_post("hello",delivery,path)
            self.assertEqual(delivery["status"],"blocked"); self.assertEqual(delivery["attempts"],3); self.assertEqual(post.call_count,3)

    def test_non_2xx_and_connection_failure_never_confirm(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"
            for effect in (Response(status=503,data={"error":"down"}), requests.ConnectionError("before send")):
                delivery={"id":"stable","attempts":0,"status":"pending"}
                with mock.patch("tweet.requests.post",return_value=effect) if isinstance(effect,Response) else \
                     mock.patch("tweet.requests.post",side_effect=effect):
                    result=attempt_post("hello",delivery,path)
                self.assertFalse(result["confirmed"])

    def test_dry_and_unconfirmed_do_not_claim_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"; delivery={"id":"stable","attempts":0,"status":"pending"}
            with mock.patch("tweet.env",return_value=""):
                result=attempt_post("hello",delivery,path)
            self.assertEqual(result["status"],"dry"); self.assertEqual(result["text"],"hello"); self.assertEqual(delivery["attempts"],0)
            with mock.patch("tweet.requests.post",return_value=Response(data={"status":"ok"})):
                result=attempt_post("hello",delivery,path)
            self.assertFalse(result["confirmed"])
            partial=Response(data={"success":True,"results":{"x":{"success":False,"error":"denied"},
                                                                 "linkedin":{"success":True,"id":"wrong"}}})
            with mock.patch("tweet.requests.post",return_value=partial):
                result=attempt_post("hello",{"id":"partial","attempts":0,"status":"pending"},path)
            self.assertFalse(result["confirmed"])

    def test_copy_length_and_stable_identity(self):
        rb={"rules":[{"id":"rule-1","status":"adopted","text_en":"x"*1000}]}; text=compose(rb,rb["rules"][0])
        self.assertLessEqual(len(text),MAX_LEN); self.assertEqual(stable_id("note","1",text),stable_id("note","1",text))

    def test_request_identity_is_on_disk_before_network_call(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"; delivery={"id":"stable","attempts":0,"status":"pending"}
            def inspect_then_fail(*args,**kwargs):
                saved=load_json(path,{})["deliveries"]["stable"]
                self.assertEqual(saved["request_id"],"stable"); self.assertEqual(saved["status"],"attempting")
                raise requests.ConnectionError("before send")
            with mock.patch("tweet.requests.post",side_effect=inspect_then_fail): attempt_post("hello",delivery,path)

    def test_blocked_item_does_not_prevent_later_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"; state={"deliveries":{}}
            blocked={"id":"blocked","attempts":3,"status":"blocked","confirmed":False}
            state["deliveries"]["blocked"]=blocked
            receipt=Response(data={"success":True,"results":{"x":{"success":True,"url":"https://x.com/example/status/2"}}})
            with mock.patch("tweet.requests.post",return_value=receipt):
                later=deliver("note","later","later note",state,path)
            self.assertTrue(later["confirmed"]); self.assertEqual(blocked["status"],"blocked")


if __name__ == "__main__": unittest.main()
