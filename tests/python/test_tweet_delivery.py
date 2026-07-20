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

    def test_async_receipt_polls_before_any_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"; delivery={"id":"stable","attempts":0,"status":"pending"}
            initial=Response(data={"success":True,"request_id":"stable","total_platforms":1})
            done=Response(data={"results":{"x":{"success":True,"url":"https://x.com/example/status/1"}}})
            with mock.patch("tweet.requests.post",return_value=initial) as post, mock.patch("tweet.requests.get",return_value=done) as get:
                first=attempt_post("hello",delivery,path); second=attempt_post("hello",delivery,path)
            self.assertEqual(first["status"],"posted"); self.assertTrue(second["confirmed"])
            self.assertEqual(post.call_count,1); self.assertEqual(get.call_count,1)

    def test_failure_and_ambiguous_timeout_stop_after_three(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"; delivery={"id":"stable","attempts":0,"status":"pending"}
            missing=Response(status=404,data={"status":"not_found"})
            with mock.patch("tweet.requests.post",side_effect=requests.Timeout("after send")) as post, \
                 mock.patch("tweet.requests.get",return_value=missing):
                for _ in range(4): attempt_post("hello",delivery,path)
            self.assertEqual(delivery["status"],"blocked"); self.assertEqual(delivery["attempts"],3); self.assertEqual(post.call_count,3)

    def test_dry_and_unconfirmed_do_not_claim_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json"; delivery={"id":"stable","attempts":0,"status":"pending"}
            with mock.patch("tweet.env",return_value=""):
                result=attempt_post("hello",delivery,path)
            self.assertEqual(result["status"],"dry"); self.assertEqual(delivery["attempts"],0)
            with mock.patch("tweet.requests.post",return_value=Response(data={"status":"ok"})):
                result=attempt_post("hello",delivery,path)
            self.assertFalse(result["confirmed"])

    def test_copy_length_and_stable_identity(self):
        rb={"rules":[{"id":"rule-1","status":"adopted","text_en":"x"*1000}]}; text=compose(rb,rb["rules"][0])
        self.assertLessEqual(len(text),MAX_LEN); self.assertEqual(stable_id("note","1",text),stable_id("note","1",text))


if __name__ == "__main__": unittest.main()
