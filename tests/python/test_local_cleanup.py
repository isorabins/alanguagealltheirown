import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import loop
from local_cleanup import LocalBudgetError, ReservedTransport


class LocalCleanupBudgetTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.receipt = Path(self.directory.name) / "budget.json"
        self.models = {"test/model": {"context_length": 100,
                                     "pricing": {"prompt": ".01", "completion": ".02"}}}

    def test_refuses_dispatch_when_maximum_request_cost_does_not_fit(self):
        post = Mock()
        transport = ReservedTransport("1.19", self.models, self.receipt, post=post)
        with self.assertRaises(LocalBudgetError):
            transport("unused", json={"model": "test/model", "max_tokens": 10})
        post.assert_not_called()

    def test_exact_charge_releases_reservation_and_repeated_calls_share_budget(self):
        def post(*args, **kwargs):
            pending = json.loads(self.receipt.read_text())
            self.assertTrue(pending["stopped"])
            self.assertEqual(pending["attempts"][-1]["status"], "uncertain")
            return Mock(status_code=200, json=lambda: {"id": "receipt", "usage": {"cost": .3}})
        transport = ReservedTransport("1.5", self.models, self.receipt, post=post)
        for _ in range(2):
            transport("unused", json={"model": "test/model", "max_tokens": 10})
        with self.assertRaises(LocalBudgetError):
            transport("unused", json={"model": "test/model", "max_tokens": 10})
        self.assertEqual(str(transport.used), "0.60")

    def test_uncertain_charge_stops_real_call_retry_loop_and_retains_reservation(self):
        post = Mock(side_effect=loop.requests.Timeout())
        transport = ReservedTransport("10", self.models, self.receipt, post=post)
        with patch.object(loop, "api_key", return_value="test-key"), self.assertRaises(LocalBudgetError):
            loop.call("test/model", "system", "user", max_tokens=10, transport=transport)
        post.assert_called_once()
        saved = json.loads(self.receipt.read_text())
        self.assertTrue(saved["stopped"])
        self.assertEqual(saved["charged_or_reserved_usd"], "1.20")
        self.assertNotIn("test-key", self.receipt.read_text())

    def test_missing_or_invalid_cost_never_frees_reservation(self):
        for cost in [None, -1, float("nan"), True]:
            with self.subTest(cost=cost):
                self.receipt.unlink(missing_ok=True)
                post = Mock(return_value=Mock(status_code=200, json=lambda: {"usage": {"cost": cost}}))
                transport = ReservedTransport("10", self.models, self.receipt, post=post)
                with self.assertRaises(LocalBudgetError):
                    transport("unused", json={"model": "test/model", "max_tokens": 10})
                self.assertTrue(transport.stopped)
                self.assertEqual(str(transport.used), "1.20")

    def test_text_rehearsal_fits_one_dollar_without_reserving_empty_context(self):
        models = {"moonshotai/kimi-k3": {"context_length": 1048576,
                  "pricing": {"prompt": ".000003", "completion": ".000015"}}}
        post = Mock(return_value=Mock(status_code=200, json=lambda: {"usage": {"cost": .01}}))
        transport = ReservedTransport("1", models, self.receipt, post=post)
        transport("unused", json={"model": "moonshotai/kimi-k3", "max_tokens": 22000,
                                   "messages": [{"role": "user", "content": "A small text fixture."}]})
        self.assertLess(float(transport.attempts[0]["reserved_usd"]), 1)
        self.assertEqual(post.call_args.kwargs["json"]["provider"]["max_price"],
                         {"prompt": 3, "completion": 15})

    def test_restart_keeps_spend_and_uncertain_reservations(self):
        post = Mock(return_value=Mock(status_code=200, json=lambda: {"usage": {"cost": .3}}))
        transport = ReservedTransport("1.5", self.models, self.receipt, post=post)
        transport("unused", json={"model": "test/model", "max_tokens": 10})
        resumed = ReservedTransport("1.5", self.models, self.receipt, post=post)
        self.assertEqual(resumed.used, transport.used)
        resumed("unused", json={"model": "test/model", "max_tokens": 10})
        with self.assertRaises(LocalBudgetError):
            resumed("unused", json={"model": "test/model", "max_tokens": 10})
        with self.assertRaises(LocalBudgetError):
            ReservedTransport("2", self.models, self.receipt, post=post)

    def test_explicit_fixture_output_ceiling_is_sent_and_reserved(self):
        post = Mock(return_value=Mock(status_code=200, json=lambda: {"usage": {"cost": .01}}))
        transport = ReservedTransport("1.1", self.models, self.receipt, post=post, max_output_tokens=5)
        transport("unused", json={"model": "test/model", "max_tokens": 10})
        self.assertEqual(post.call_args.kwargs["json"]["max_tokens"], 5)
        self.assertEqual(transport.attempts[0]["reserved_usd"], "1.10")
        self.assertEqual(transport.attempts[0]["output_token_limit"], 5)


if __name__ == "__main__":
    unittest.main()
