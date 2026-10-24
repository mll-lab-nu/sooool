"""Offline Tetris contracts: engine determinism, key-only executor, public task text, rules runs and zero-model replay."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "environments/tetris")]

import baseline  # noqa: E402
import cli  # noqa: E402
import engine  # noqa: E402
import executor  # noqa: E402
import render  # noqa: E402
import runner  # noqa: E402
import task  # noqa: E402

RECIPE = json.loads((ROOT / "recipes/tetris.json").read_text())


def play(env, keys):
    for key in keys:
        env.step(key)
        env.step(engine.NOOP)


class Engine(unittest.TestCase):
    def test_same_seed_same_game(self):
        a, b = engine.Tetris(seed=7), engine.Tetris(seed=7)
        for _ in range(600):
            action = (a.tick // 7) % 8
            a.step(action)
            b.step(action)
        self.assertTrue((a.board == b.board).all())
        self.assertEqual((a.kind, a.lines, a.score, a.pieces), (b.kind, b.lines, b.score, b.pieces))

    def test_seven_bag(self):
        env = engine.Tetris(seed=3)
        kinds = [env.kind] + env.upcoming(13)
        self.assertEqual(sorted(kinds[:7]), sorted("IJLOSTZ"))
        self.assertEqual(sorted(kinds[7:14]), sorted("IJLOSTZ"))

    def test_gravity_speeds_up_with_level(self):
        self.assertGreater(engine.Tetris(start_level=1).frames_per_row(), engine.Tetris(start_level=5).frames_per_row())


class Executor(unittest.TestCase):
    def test_key_script_lands_every_legal_placement(self):
        """Keys computed from the answer alone reach the placement the answer names, on an empty board."""
        checked = 0
        for kind in "IJLOSTZ":
            for rot in range(1 if kind == "O" else 4):
                for col in range(10):
                    env = engine.Tetris(seed=0)
                    env.kind, env.rot, env.x, env.y = kind, 0, executor.SPAWN_X[kind], 0
                    expected = baseline.landing(env.board, kind, rot, col)
                    if expected is None:
                        continue
                    before = env.pieces
                    play(env, executor.key_script({"piece": kind, "rot": rot, "col": col}))
                    self.assertEqual(env.pieces, before + 1)
                    self.assertEqual(sorted(zip(*[list(x) for x in env.board.nonzero()])), sorted(expected), (kind, rot, col))
                    checked += 1
        self.assertGreater(checked, 150)

    def test_public_spawn_detection_matches_engine(self):
        env, ex = engine.Tetris(seed=5, start_level=9), executor.KeyExecutor()
        ex.observe(render.render(env))
        for frame in range(1500):  # mix of executor drops and natural locks under fast gravity
            if frame % 90 == 0 and not ex.script:
                self.assertEqual(ex.kind, env.kind)  # the piece letter is read from the public screen
                ex.apply({"rot": frame % 4, "col": (frame // 90) % 8}, ex.piece_index, frame)
            env.step(ex.action())
            ex.observe(render.render(env))
            if env.over:
                break  # the terminal spawn overlaps the stack; nothing is controlled after it
            self.assertEqual(ex.piece_index, env.pieces, frame)
        self.assertGreater(env.pieces, 10)

    def test_own_rotation_back_into_the_spawn_rows_is_not_a_spawn(self):
        """An I piece one row down, rotated upright by the executor's own key, re-enters the spawn rows."""
        env, ex = engine.Tetris(seed=3, start_level=1), executor.KeyExecutor()  # seed 3 spawns an I first
        self.assertEqual(env.kind, "I")
        ex.observe(render.render(env))
        for frame in range(200):
            if frame == 70:
                self.assertEqual(env.y, 1)
                self.assertEqual(ex.apply({"rot": 1, "col": 0}, ex.piece_index, frame), "applied")
            env.step(ex.action())
            ex.observe(render.render(env))
        self.assertEqual((env.pieces, ex.piece_index), (1, 1))
        self.assertEqual(sorted(set(int(c) for c in env.board.nonzero()[1])), [0])  # landed upright in column 0

    def test_random_placements_never_desync_the_public_piece_counter(self):
        import random
        for seed in range(6):
            for level in (1, 8, 15):
                env, ex, rng = engine.Tetris(seed=seed, start_level=level), executor.KeyExecutor(), random.Random(seed * 100 + level)
                ex.observe(render.render(env))
                for frame in range(1800):  # answers at random moments; unanswered pieces lock under gravity
                    if not ex.script and ex.kind and rng.random() < 0.05:
                        ex.apply({"rot": rng.randrange(4), "col": rng.randrange(10)}, ex.piece_index, frame)
                    env.step(ex.action())
                    ex.observe(render.render(env))
                    if env.over:
                        break
                    self.assertEqual(ex.piece_index, env.pieces, (seed, level, frame))

    def test_stale_and_invalid_answers(self):
        ex = executor.KeyExecutor()
        self.assertEqual(ex.apply({"rot": 0, "col": 3}, target=1, frame=0), "stale")
        for text in ("no json", '{"rot":4,"col":1}', '{"rot":0,"col":10}', '{"col":1}'):
            with self.assertRaises((ValueError, KeyError)):
                executor.parse_answer(text)
        parsed = executor.parse_answer('text {"rot":1,"col":2,"reason":"ok"} more')
        self.assertEqual((parsed["rot"], parsed["col"]), (1, 2))


class Task(unittest.TestCase):
    def test_selected_recipe_and_policy_hashes(self):
        meta = json.loads((ROOT / "policies/tetris" / RECIPE["policy"] / "policy.json").read_text())
        self.assertEqual(RECIPE["policy"], "v11-short")
        for key, name in (("prompt", "prompt_sha256"), ("system", "system_sha256"), ("task_prefix", "task_prefix_sha256")):
            self.assertEqual(hashlib.sha256((ROOT / RECIPE[key]).read_bytes()).hexdigest(), meta[name])
        self.assertEqual(hashlib.sha256((ROOT / RECIPE["profile"]).read_bytes()).hexdigest(), meta["profile_sha256"])
        self.assertEqual((RECIPE["args"]["requests_in_flight"], RECIPE["args"]["controller"], meta["max_inflight"]), (1, "key_script", 1))
        self.assertEqual((RECIPE["args"]["observation_stride_frames"], RECIPE["args"]["observation_window"]), (60, 9))
        self.assertEqual(json.loads((ROOT / "recipes/tetris-1x.json").read_text())["args"]["slowdown"], 1)

    def test_task_text_states_mode_and_measured_delay(self):
        import statistics
        system, sim = task.build_task(ROOT, RECIPE, "simulation")
        _, live = task.build_task(ROOT, RECIPE, "realtime")
        self.assertIn("does not advance this simulation", sim)
        self.assertIn("DOES advance this real-time game", live)
        self.assertIn("2 times slower than normal speed", sim)
        self.assertIn("next 60-frame observation tick", sim)
        self.assertIn("The actual delay of your request is unknown", sim)
        for placeholder in ("{mean_ms", "{median_ms", "{p95_ms", "{stride}", "{window_frames}", "{mid_age}", "{slowdown_clause}"):
            self.assertNotIn(placeholder, sim + live)
        self.assertEqual(system, (ROOT / "policies/asterix/v28/system.txt").read_text().strip())  # same system text as Asterix
        median_ms = statistics.median(task.profile_delays(ROOT, RECIPE)) / 2 * 1000
        self.assertIn(f"median {median_ms:.0f} ms", sim)
        text = task.request_text(sim, 300, [140, 260, 300], [{"frame": 100, "status": "applied", "piece": "T", "rot": 1, "col": 4}])
        self.assertIn("Current observation frame: 300. Image frames: [140, 260, 300].", text)
        self.assertIn("200:T/rot1/col4", text)

    def test_profile_rejects_bad_delays(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "p.json"
            path.write_text(json.dumps({"capture_to_complete_seconds": [1.0, 0.0]}))
            with self.assertRaises(ValueError):
                task.profile_delays(Path(directory), {"profile": "p.json"})
        with self.assertRaises(ValueError):
            runner.delay_frames(1.0, 0.5)


class RulesRunAndReplay(unittest.TestCase):
    def run_rules(self, directory, duration="8"):
        out = Path(directory) / "run"
        cli.main(["simulate", "--provider", "rules", "--seed", "4", "--level", "3", "--prefix", "15",
                  "--duration", duration, "--output", str(out)])
        return out, json.loads((out / "manifest.json").read_text())

    def test_rules_simulation_records_and_replays(self):
        with tempfile.TemporaryDirectory() as directory:
            out, manifest = self.run_rules(directory)
            record = json.loads((out / "evaluation-record.json").read_text())
            self.assertEqual((record["game"], record["provider"], record["clock"], record["status"]), ("tetris", "rules", "virtual", "completed"))
            # CLI overrides are folded into the frozen recipe, so manifest, record, task text and run agree.
            self.assertEqual((manifest["recipe"]["args"]["duration"], manifest["recipe"]["args"]["episodes"]), (8.0, [{"seed": 4, "level": 3, "prefix": 15}]))
            self.assertEqual(record["recipe"]["args"]["duration"], 8.0)
            summary = json.loads((out / "summary.json").read_text())
            episode = summary["episodes"][0]
            self.assertEqual(episode["case"], {"seed": 4, "level": 3, "prefix": 15})
            self.assertGreater(episode["calls"], 0)
            self.assertTrue((out / "source_snapshot/environments/tetris/runner.py").exists())
            (episode_dir,) = sorted(out.glob("episode-*"))
            rows = [json.loads(line) for line in (episode_dir / "decisions.jsonl").read_text().splitlines()]
            self.assertTrue(all(len(r["image_sha256"]) == len(r["image_frames"]) for r in rows))
            self.assertTrue(all(len(r["image_frames"]) == 3 for r in rows[2:]))
            self.assertGreater(episode["drops"], 0)
            result = runner.verify_replay(ROOT, manifest["recipe"], episode_dir)
            self.assertEqual((result["model_calls"], result["verified_requests"], result["verified_key_scripts"]), (0, len(rows), True))

    def test_replay_catches_every_kind_of_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            out, manifest = self.run_rules(directory)
            (episode_dir,) = sorted(out.glob("episode-*"))
            decisions, summary_text = (episode_dir / "decisions.jsonl").read_text(), (episode_dir / "summary.json").read_text()
            rows = [json.loads(line) for line in decisions.splitlines()]
            applied = next(i for i, r in enumerate(rows) if r["status"] == "applied")

            def tamper(label, rows_edit=None, summary_edit=None):
                edited = [dict(r) for r in rows]
                if rows_edit:
                    rows_edit(edited)
                (episode_dir / "decisions.jsonl").write_text("\n".join(json.dumps(r) for r in edited) + "\n")
                summary = json.loads(summary_text)
                if summary_edit:
                    summary_edit(summary)
                (episode_dir / "summary.json").write_text(json.dumps(summary))
                with self.assertRaises(AssertionError, msg=label):
                    runner.verify_replay(ROOT, manifest["recipe"], episode_dir)

            def set_answer(e):
                e[applied]["answer"] = json.dumps({"rot": (json.loads(e[applied]["answer"])["rot"] + 1) % 4, "col": 0})
            tamper("answer", set_answer)
            tamper("image hash", lambda e: e[0]["image_sha256"].__setitem__(0, "0" * 64))
            tamper("image frames", lambda e: e[1]["image_frames"].__setitem__(0, e[1]["image_frames"][0] - 60))
            tamper("delivery one frame late", lambda e: e[applied].update(delivery_frame=e[applied]["delivery_frame"] + 1))
            tamper("delivery one frame early", lambda e: e[applied].update(delivery_frame=e[applied]["delivery_frame"] - 1))
            tamper("status relabelled", lambda e: e[applied].update(status="stale"))
            tamper("invalid relabelled", lambda e: e[applied].update(status="invalid"))
            tamper("target", lambda e: e[applied].update(target=e[applied]["target"] + 1))
            tamper("dropped request", lambda e: e.pop())
            tamper("summary lines", summary_edit=lambda s: s.update(lines=s["lines"] + 1))
            tamper("summary holes", summary_edit=lambda s: s.update(new_holes=s["new_holes"] + 1))
            tamper("summary frames", summary_edit=lambda s: s.update(frames=s["frames"] - 10))
            tamper("summary drops", summary_edit=lambda s: s.update(drops=s["drops"] + 1))
            tamper("summary calls", summary_edit=lambda s: s.update(calls=s["calls"] + 1))
            tamper("summary survived", summary_edit=lambda s: s.update(survived=not s["survived"]))
            (episode_dir / "decisions.jsonl").write_text(decisions)
            (episode_dir / "summary.json").write_text(summary_text)
            (episode_dir / "actions.json").write_text("[]\n")
            with self.assertRaises(AssertionError):
                runner.verify_replay(ROOT, manifest["recipe"], episode_dir)

    def test_bad_arguments_fail_before_any_run_directory_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "run"
            for argv in (["--slowdown", "0.5"], ["--level", "3"], ["--seed", "1", "--level", "0"], ["--seed", "1", "--prefix", "-1"]):
                with self.assertRaises(SystemExit):
                    cli.main(["simulate", "--provider", "rules", *argv, "--duration", "2", "--output", str(out)])
                self.assertFalse(out.exists(), argv)
            for key, value in (("observation_window", 2), ("observation_stride_frames", 0), ("requests_in_flight", 2),
                               ("controller", "hover"), ("episodes", []), ("slowdown", 0)):
                with self.assertRaises(ValueError, msg=key):
                    runner.validate_recipe({**RECIPE, "args": {**RECIPE["args"], key: value}})

    def test_transport_failure_is_recorded_in_the_decision_row(self):
        class Flaky:
            calls = 0

            def __init__(self, output, system):
                pass

            def act(self, text, images, directory):
                Flaky.calls += 1
                if Flaky.calls == 2:
                    raise RuntimeError("transport down")
                return json.dumps({"rot": 0, "col": 3}), {"wall_seconds": 0.1}

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "run"
            recipe = {**RECIPE, "args": {**RECIPE["args"], "duration": 20, "episodes": [{"seed": 1, "level": 1, "prefix": 0}]}}
            out.mkdir()
            with self.assertRaises(RuntimeError):
                runner.run_recipe(ROOT, recipe, out, Flaky, "simulation", "claude")
            (episode_dir,) = sorted(out.glob("episode-*"))
            rows = [json.loads(line) for line in (episode_dir / "decisions.jsonl").read_text().splitlines()]
            self.assertEqual([r["status"] for r in rows], ["applied", "error"])
            self.assertEqual(rows[1]["error_type"], "RuntimeError")
            episode = json.loads((episode_dir / "summary.json").read_text())
            self.assertEqual((episode["status"], episode["error"]["type"]), ("interrupted", "RuntimeError"))
            self.assertEqual(json.loads((out / "summary.json").read_text())["status"], "interrupted")

    def test_retained_selected_run_replays_without_model_calls(self):
        run = ROOT / "artifacts/tetris/records/claude-eval-2x"
        manifest = json.loads((run / "manifest.json").read_text())
        self.assertEqual(manifest["recipe"]["policy"], RECIPE["policy"])
        self.assertEqual((manifest["provider"], manifest["clock"]), ("claude", "wall"))
        for episode in sorted(run.glob("episode-*")):
            result = runner.verify_replay(ROOT, manifest["recipe"], episode)
            summary = json.loads((episode / "summary.json").read_text())
            self.assertEqual((result["model_calls"], result["lines"], result["survived"]), (0, summary["lines"], True))
            self.assertEqual(result["verified_requests"], summary["calls"])
        records = [json.loads(line) for line in (ROOT / "artifacts/tetris/evaluations.jsonl").read_text().splitlines()]
        self.assertIn("claude-eval-2x", {r["record_id"] for r in records})

    def test_rules_baseline_never_sees_pixels_but_actors_never_see_truth(self):
        env = engine.Tetris(seed=1)
        answer, meta = baseline.RulesActor().act_on_truth(env)
        self.assertEqual(meta["auth"], "rules")
        self.assertIn("rot", executor.parse_answer(answer))
        source = (ROOT / "environments/tetris/runner.py").read_text()
        self.assertNotIn("env.board", source.split("def run_episode")[1].split("def episodes_from")[0].replace("board_state(env)", ""))


if __name__ == "__main__":
    unittest.main()
