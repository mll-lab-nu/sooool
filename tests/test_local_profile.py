"""Timing and evidence integrity tests; synthetic streams are never experiment data."""
import json
from pathlib import Path
import tempfile
import unittest

from runtime.local_profile import MODEL, consume, digest, read_corpus, summarize, validate


def stream(parts, *, finish="stop", done=True, model=MODEL):
    for part in parts:
        yield b"data: " + json.dumps({"model": model, "choices": [
            {"delta": {"content": part}, "finish_reason": None}]}).encode() + b"\n"
    yield b"data: " + json.dumps({"model": model, "choices": [
        {"delta": {}, "finish_reason": finish}], "usage": {
        "prompt_tokens": 100, "completion_tokens": 10}}).encode() + b"\n"
    if done:
        yield b"data: [DONE]\n"


class ProfileTests(unittest.TestCase):
    case = {"game": "racing"}

    def measured(self, lines, case=None):
        ticks = iter(i / 10 for i in range(1, 100))
        return consume(lines, case or self.case, 0, lambda: next(ticks))

    def test_only_complete_legal_action_is_ready(self):
        row = self.measured(stream(["[[3", ",0,1.5", "]]", " "]))
        self.assertTrue(row["valid"])
        self.assertLess(row["ttft_s"], row["action_ready_s"])
        self.assertLess(row["action_ready_s"], row["stream_done_s"])

    def test_invalid_bounds_do_not_publish(self):
        row = self.measured(stream(["[[99,0,1.5]]"]))
        self.assertFalse(row["valid"])
        self.assertIsNone(row["action_ready_s"])

    def test_trailing_mutation_invalidates_provisional_action(self):
        row = self.measured(stream(["[[3,0,1.5]]", " junk"]))
        self.assertFalse(row["valid"])
        self.assertIsNotNone(row["action_ready_s"])

    def test_missing_done_length_and_wrong_model_fail(self):
        for kw in ({"done": False}, {"finish": "length"}, {"model": "other"}):
            with self.subTest(kw=kw):
                self.assertFalse(self.measured(stream(["[[3,0,1.5]]"], **kw))["valid"])

    def test_rhythm_action_precedes_commentary(self):
        case = {"game": "rhythm", "commentary": True}
        row = self.measured(stream(['{"v":1,"a":[]}', '\n{"comment":"No visible notes."}']), case)
        self.assertTrue(row["valid"])
        self.assertLess(row["action_ready_s"], row["finish_s"])
        row = self.measured(stream(['{"v":1,"a":[]}', '\n{"comment":5}']), case)
        self.assertFalse(row["valid"])

    def test_failures_retained_but_not_valid_latency(self):
        report = summarize([{"valid": True, "ttft_s": 1},
                            {"valid": False, "ttft_s": 100}])
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["ttft_s"]["max"], 1)

    def test_corrupt_input_refused_before_network(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "image.png").write_bytes(b"image")
            row = {"id": "one", "prompt": "hello", "prompt_sha256": digest(b"hello"),
                   "images": [{"path": "image.png", "sha256": digest(b"image")}]}
            (p / "corpus.json").write_text(json.dumps([row]))
            self.assertEqual(len(read_corpus(p / "corpus.json")), 1)
            (p / "image.png").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                read_corpus(p / "corpus.json")


if __name__ == "__main__":
    unittest.main()
