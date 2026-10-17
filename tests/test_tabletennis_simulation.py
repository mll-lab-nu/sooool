"""Causal empirical delivery and simulation/API command boundaries, without API calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from environments.tabletennis.simulation import DelayScheduler, load_profile
from scripts.tabletennis import main


class SimulationTests(unittest.TestCase):
    def test_finished_subscription_reply_is_not_eligible_before_sampled_frame(self):
        scheduler = DelayScheduler({"delays_s": [1.149]}, 7, 1, 5)
        metadata = scheduler.schedule(10)
        self.assertEqual(metadata["delivery_frame"], 125)
        self.assertFalse(scheduler.due(metadata, 120))
        self.assertTrue(scheduler.due(metadata, 125))
        slower = DelayScheduler({"delays_s": [1.149]}, 7, 3, 5)
        self.assertEqual(slower.schedule(10)["delivery_frame"], 50)

    def test_joint_action_and_terminal_clocks_stay_paired(self):
        scheduler = DelayScheduler({"delays_s": [1., 2.],
                                    "all_wire_completed_request_s": [1.2, 2.8]}, 7, 1, 5)
        for _ in range(20):
            row = scheduler.schedule(0)
            expected = 120 if row["sampled_api_seconds"] == 1. else 280
            self.assertEqual(row["terminal_frame"], expected)
            self.assertGreaterEqual(row["terminal_frame"], row["delivery_frame"])

    def test_seed_reproduces_private_delay_draws(self):
        a = DelayScheduler({"delays_s": [.1, .8, 2.]}, 91, 1, 5)
        b = DelayScheduler({"delays_s": [.1, .8, 2.]}, 91, 1, 5)
        self.assertEqual([a.schedule(i) for i in range(20)], [b.schedule(i) for i in range(20)])

    def test_rejects_missing_invalid_or_wrong_provider_timing(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"profile.json"
            for delays in ([], [0], [-1], [float("inf")], [True], ["1"]):
                path.write_text(json.dumps({"delays_s":delays,"model":"gpt-6.1-sol","service_tier":"ultrafast"}))
                with self.assertRaises(ValueError): load_profile(path)
            path.write_text(json.dumps({"delays_s":[1.],"model":"other","service_tier":"ultrafast"}))
            with self.assertRaises(ValueError): load_profile(path)

    def test_simulate_cannot_use_paid_api_or_rules(self):
        for source in ("api", "rules"):
            with patch.dict("os.environ", {}, clear=False), self.assertRaises(SystemExit) as exc:
                main(["simulate", "--source", source, "--output", "/tmp/never-run-pingpong"])
            self.assertEqual(exc.exception.code, 2)

    def test_eval_rejects_simulated_latency_options(self):
        with self.assertRaises(SystemExit) as exc:
            main(["eval", "--profile", "/tmp/profile.json", "--output", "/tmp/never-run-pingpong"])
        self.assertEqual(exc.exception.code, 2)
