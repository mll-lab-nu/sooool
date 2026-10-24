"""One serial visual placement loop shared by profile simulation, real-time evaluation, rules baselines and replay.

The loop is Asterix's: the screen is captured at fixed observation ticks into a rolling window; one request is in
flight; a new request is captured at the first tick after the previous reply arrived and its keys were pressed, with
the window's oldest, middle and newest images and their frame numbers; the reply is applied when it arrives
(sampled delay in simulation, actual arrival in real time); ticks while a request is in flight are counted as drops.
The actor sees only those images, the frame numbers and its own applied placements.
"""
from __future__ import annotations

from collections import deque
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import math
from pathlib import Path
import random
import statistics
import time

import numpy as np

from baseline import RulesActor, features
from engine import NOOP, Tetris
from executor import KeyExecutor, key_script, parse_answer
from render import render
from task import build_task, profile_delays, request_text

FPS = 60
SCALE = 2  # default upscale (nearest) of sent screenshots; recipes may set args.image_scale; hashes are of the PNG bytes


def png(screen, scale: int = SCALE) -> bytes:
    from PIL import Image
    image = Image.fromarray(screen)
    if scale != 1:
        image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def delay_frames(seconds: float, slowdown: float = 1.0) -> int:
    """Wall-clock seconds become game frames; a slowed game makes the same delay cover fewer frames."""
    if not math.isfinite(seconds) or seconds <= 0 or not math.isfinite(slowdown) or slowdown < 1:
        raise ValueError("Positive latency and finite slowdown >= 1 required")
    return max(1, math.ceil(seconds / slowdown * FPS))


def select_images(window):
    """Asterix's selection: oldest, third-newest and newest frames of the window."""
    n = len(window)
    return [window[i] for i in sorted({0, max(0, n - 3), n - 1})]


def make_env(seed: int, level: int, prefix: int) -> Tetris:
    """A deterministic start state: ``prefix`` pieces placed by the rules baseline at zero delay."""
    env = Tetris(seed=seed, start_level=level)
    rules = RulesActor()
    for _ in range(prefix):
        if env.over:
            break
        answer = {**json.loads(rules.act_on_truth(env)[0]), "piece": env.kind}
        for key in key_script(answer):  # press, release
            env.step(key)
            env.step(NOOP)
    return env


def board_state(env: Tetris) -> dict:
    height, _, holes, bump = features(env.board)
    return {"lines": env.lines, "pieces": env.pieces, "score": env.score, "level": env.level,
            "holes": holes, "height_sum": height, "bumpiness": bump}


def run_episode(root, recipe, out: Path, case: dict, task: str, delays: list[float], client, mode: str, provider: str,
                duration: float, slowdown: float):
    out.mkdir(parents=True, exist_ok=False)
    args = recipe["args"]
    stride, window = int(args["observation_stride_frames"]), deque(maxlen=int(args["observation_window"]))
    scale = int(args.get("image_scale", SCALE))
    env = make_env(case["seed"], case["level"], case.get("prefix", 0))
    start = board_state(env)
    rng = random.Random(int(args.get("latency_seed_offset", 0)) + case.get("delay_seed", case["seed"]))
    executor, requests, deliveries, pending = KeyExecutor(), [], [], None
    horizon = round(duration * FPS)
    frame, drops, lag_max, started = 0, 0, 0.0, time.monotonic()
    pool = ThreadPoolExecutor(1)
    status, error = "horizon", None

    def request(text, images, directory):
        answer, meta = client.act(text, images, directory)
        return {"answer": answer, "meta": meta}

    try:
        with (out / "steps.jsonl").open("w") as steps, (out / "issued.jsonl").open("w") as issued:
            while frame < horizon and not env.over:
                if mode == "realtime":
                    remaining = started + frame * slowdown / FPS - time.monotonic()
                    if remaining > 0:
                        time.sleep(remaining)
                    lag_max = max(lag_max, time.monotonic() - started - frame * slowdown / FPS)
                screen = render(env)
                executor.observe(screen)
                if pending is not None:
                    row, future = pending
                    available = frame >= row["action_ready_frame"] if mode == "simulation" else future.done()
                    if available:
                        try:
                            result = future.result()
                        except Exception as exc:  # the transport failed: the row says so, then the episode is interrupted
                            row.update(status="error", error_type=type(exc).__name__, error=str(exc)[:500])
                            raise
                        row["delivery_frame"] = frame
                        row.update(answer=result["answer"], call_wall_seconds=result["meta"].get("wall_seconds"),
                                   output_tokens=result["meta"].get("output_tokens"))
                        try:
                            answer = parse_answer(result["answer"])
                            row["status"] = executor.apply(answer, row["target"], frame)
                        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                            row.update(status="invalid", error=str(exc)[:200])
                        deliveries.append({"frame": frame, "seq": row["seq"], "mode": mode, "status": row["status"],
                                           "capture_to_apply_s": (frame - row["obs_frame"]) / FPS,
                                           "actual_capture_to_apply_s": time.monotonic() - started - row["capture_wall_seconds"]})
                        pending = None
                if frame % stride == 0:
                    window.append((frame, png(screen, scale)))
                    if pending is not None or executor.busy:
                        drops += 1  # a tick while a request is in flight or its keys are still being pressed
                    else:
                        images = select_images(window)
                        text = request_text(task, frame, [f for f, _ in images], executor.applied) if provider != "rules" else None
                        sampled = rng.choice(delays) if mode == "simulation" else None
                        row = {"seq": len(requests), "obs_frame": frame, "target": executor.piece_index,
                               "image_frames": [f for f, _ in images], "image_sha256": [hashlib.sha256(im).hexdigest() for _, im in images],
                               "sampled_capture_to_complete_s": sampled, "capture_wall_seconds": time.monotonic() - started,
                               "action_ready_frame": frame + delay_frames(sampled, slowdown) if sampled is not None else None,
                               "delivery_frame": None}
                        issued.write(json.dumps(row) + "\n"); issued.flush()
                        requests.append(row)
                        call_dir = out / "calls" / f"call-{row['seq']:05d}"
                        if provider == "rules":
                            answer_text, meta = client.act_on_truth(env)
                            call_dir.mkdir(parents=True)
                            (call_dir / "result.json").write_text(json.dumps({"answer": answer_text, "meta": meta}))
                            future = pool.submit(lambda a=answer_text, m=meta: {"answer": a, "meta": m})
                        elif mode == "simulation":
                            try:
                                result = request(text, [im for _, im in images], call_dir)  # virtual clock waits for computation
                            except Exception as exc:
                                row.update(status="error", error_type=type(exc).__name__, error=str(exc)[:500])
                                raise
                            future = pool.submit(lambda r=result: r)
                        else:
                            future = pool.submit(request, text, [im for _, im in images], call_dir)
                        pending = (row, future)
                action = executor.action()
                env.step(action)
                steps.write(json.dumps({"frame": frame, "action": action, "lines": env.lines, "pieces": env.pieces}) + "\n")
                frame += 1
                if frame % 60 == 0:
                    steps.flush()
                    (out / "progress.json").write_text(json.dumps({"frames": frame, "game_seconds": frame / FPS, "lines": env.lines - start["lines"],
                                                                   "pieces": env.pieces - start["pieces"], "calls": len(requests), "drops": drops, "mode": mode}) + "\n")
                if env.over:
                    status = "natural_end"
    except BaseException as exc:
        error, status = {"type": type(exc).__name__, "message": str(exc)[:500]}, "interrupted"
        raise
    finally:
        pool.shutdown(wait=True)
        with (out / "decisions.jsonl").open("w") as log:
            for row in requests:
                if row["delivery_frame"] is None:
                    row["status"] = row.get("status") or ("interrupted" if status == "interrupted" else "unapplied_after_horizon")
                log.write(json.dumps(row) + "\n")
        (out / "actions.json").write_text(json.dumps(executor.applied, indent=1) + "\n")
        (out / "deliveries.json").write_text(json.dumps(deliveries, indent=1) + "\n")
        end = board_state(env)
        ages = sorted(d["capture_to_apply_s"] for d in deliveries)
        elapsed = time.monotonic() - started
        summary = {"case": case, "mode": mode, "provider": provider, "slowdown": slowdown,
                   "frames": frame, "game_seconds": frame / FPS, "environment_wall_seconds": elapsed, "virtual_wall_seconds": frame * slowdown / FPS,
                   "start": start, "end": end, "lines": end["lines"] - start["lines"], "pieces": end["pieces"] - start["pieces"],
                   "new_holes": end["holes"] - start["holes"], "height_delta": end["height_sum"] - start["height_sum"],
                   "survived": not env.over, "calls": len(requests), "drops": drops, "peak_inflight": int(bool(requests)),
                   "applied": sum(r.get("status") == "applied" for r in requests),
                   "stale": sum(r.get("status") == "stale" for r in requests), "invalid": sum(r.get("status") == "invalid" for r in requests),
                   "capture_to_apply_game_s_median": statistics.median(ages) if ages else None,
                   "capture_to_apply_game_s_max": max(ages) if ages else None,
                   "max_frame_lag_seconds": lag_max if mode == "realtime" else None, "status": status, "error": error,
                   "limitation": ("Sampled measured delays; actor computation pauses the virtual clock." if mode == "simulation"
                                  else "Actual response latency on a continuously advancing clock.")}
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def provenance(root) -> dict:
    """Versions the retained evidence depends on: image hashes change with the renderer's Pillow build."""
    import platform
    import subprocess
    import PIL
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=10).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        commit = None
    return {"python": platform.python_version(), "pillow": PIL.__version__, "numpy": np.__version__, "source_commit": commit}


def validate_recipe(recipe: dict) -> dict:
    """Reject a recipe this runner cannot honour before any run directory exists (Asterix checks its selected values)."""
    args = recipe["args"]
    checks = ((float(args.get("slowdown", 1)) >= 1, "slowdown must be >= 1 (1 = normal speed)"),
              (int(args["observation_window"]) >= 3, "observation_window must hold at least the three images sent"),
              (int(args["observation_stride_frames"]) >= 1, "observation_stride_frames must be >= 1"),
              (int(args.get("image_scale", SCALE)) >= 1, "image_scale must be >= 1"),
              (float(args["duration"]) > 0, "duration must be positive"),
              (int(args.get("requests_in_flight", 1)) == 1, "this runner keeps exactly one request in flight"),
              (args.get("controller", "key_script") == "key_script", "this runner executes answers as key scripts"),
              (bool(args["episodes"]), "episodes must not be empty"))
    for ok, message in checks:
        if not ok:
            raise ValueError(message)
    for case in args["episodes"]:
        if not {"seed", "level"} <= set(case) or case["level"] < 1 or case.get("prefix", 0) < 0:
            raise ValueError(f"malformed episode {case}")
    return recipe


def apply_overrides(recipe: dict, args) -> dict:
    """Return the recipe actually run: CLI overrides for duration, slowdown and a single episode are written into
    ``args`` so the frozen manifest, the task text and the evaluation record all describe the same condition."""
    overrides = {key: getattr(args, key) for key in ("duration", "slowdown") if getattr(args, key, None) is not None}
    if getattr(args, "seed", None) is not None:
        overrides["episodes"] = [{"seed": args.seed, "level": args.level if args.level is not None else 1, "prefix": args.prefix if args.prefix is not None else 0}]
    if overrides:
        recipe = {**recipe, "args": {**recipe["args"], **overrides}}
    return validate_recipe(recipe)


def run_recipe(root, recipe, out: Path, client_factory, mode: str, provider: str):
    duration, slowdown = float(recipe["args"]["duration"]), float(recipe["args"].get("slowdown", 1))
    system, task = build_task(root, recipe, mode)
    delays = profile_delays(root, recipe)
    (out / "task.txt").write_text(task)
    (out / "provenance.json").write_text(json.dumps(provenance(root), indent=2) + "\n")
    client = client_factory(output=out / "transport-worker", system=system)
    summaries = []
    try:
        for i, case in enumerate(recipe["args"]["episodes"]):
            name = f"episode-{i:02d}-s{case['seed']}-l{case['level']}-p{case.get('prefix', 0)}"
            try:
                summaries.append(run_episode(root, recipe, out / name, case, task, delays, client, mode, provider, duration, slowdown))
            except BaseException:
                partial = out / name / "summary.json"
                if partial.exists():
                    summaries.append(json.loads(partial.read_text()))
                raise
    finally:
        client.close()
        n = len(summaries)
        mean = lambda key: (sum(s[key] for s in summaries) / n) if n else None  # noqa: E731
        ages = sorted(a for s in summaries for a in [s.get("capture_to_apply_game_s_median")] if a is not None)
        aggregate = {"episodes": n, "lines_mean": mean("lines"), "new_holes_mean": mean("new_holes"),
                     "height_delta_mean": mean("height_delta"), "pieces_mean": mean("pieces"),
                     "survived": sum(s["survived"] for s in summaries), "calls": sum(s["calls"] for s in summaries),
                     "drops": sum(s["drops"] for s in summaries), "stale": sum(s["stale"] for s in summaries),
                     "invalid": sum(s["invalid"] for s in summaries),
                     "capture_to_apply_game_s_median_of_medians": statistics.median(ages) if ages else None}
        (out / "summary.json").write_text(json.dumps({
            "mode": mode, "provider": provider, "clock": "virtual" if mode == "simulation" else "wall",
            "duration_game_seconds": duration, "slowdown": slowdown, "observation_stride_frames": recipe["args"]["observation_stride_frames"],
            "aggregate": aggregate, "episodes": summaries,
            "status": "interrupted" if any(s.get("status") == "interrupted" for s in summaries) else "completed",
            "limitation": ("Sampled measured delays; actor computation pauses the virtual clock." if mode == "simulation"
                           else "Actual response latency on a continuously advancing clock."),
        }, indent=2) + "\n")
    return summaries


def verify_replay(root, recipe, episode_dir: Path) -> dict:
    """Zero-model replay: rebuild the episode from its recorded answers and delivery frames and re-derive everything
    else. Checked against the record: every issued image (frames and SHA-256s), the request target, the executor
    status of every delivery, the sampled delay arithmetic of a simulation, the key scripts in ``actions.json``
    when retained, the drop count, the horizon, and every number in the episode summary. No model is called."""
    summary = json.loads((episode_dir / "summary.json").read_text())
    case, args = summary["case"], recipe["args"]
    stride, window = int(args["observation_stride_frames"]), deque(maxlen=int(args["observation_window"]))
    scale, slowdown = int(args.get("image_scale", SCALE)), float(summary["slowdown"])
    horizon = round(float(args["duration"]) * FPS)
    requests = [json.loads(line) for line in (episode_dir / "decisions.jsonl").read_text().splitlines()]
    if [r["seq"] for r in requests] != list(range(len(requests))):
        raise AssertionError("request sequence numbers are not contiguous")
    env, executor = make_env(case["seed"], case["level"], case.get("prefix", 0)), KeyExecutor()
    start = board_state(env)
    by_obs = {r["obs_frame"]: r for r in requests}
    by_delivery = {r["delivery_frame"]: r for r in requests if r.get("delivery_frame") is not None}
    if len(by_obs) != len(requests) or len(by_delivery) != sum(r.get("delivery_frame") is not None for r in requests):
        raise AssertionError("duplicate observation or delivery frames")
    for row in requests:
        delivered = row.get("delivery_frame")
        if delivered is not None and delivered < row["obs_frame"]:
            raise AssertionError(f"request {row['seq']} delivered before it was captured")
        if summary["mode"] == "simulation":
            ready = row["obs_frame"] + delay_frames(row["sampled_capture_to_complete_s"], slowdown)
            if row["action_ready_frame"] != ready or (delivered is not None and delivered != ready):
                raise AssertionError(f"request {row['seq']}: delivery does not match its sampled delay")
    checked, drops, pending, statuses = 0, 0, None, {"applied": 0, "stale": 0, "invalid": 0}
    if summary["frames"] > horizon:
        raise AssertionError("episode ran past the recipe horizon")
    for frame in range(summary["frames"]):
        if env.over:
            raise AssertionError(f"game was over before the recorded end at frame {frame}")
        screen = render(env)
        executor.observe(screen)
        if frame in by_delivery:
            row = by_delivery[frame]
            if row["status"] == "invalid":
                try:
                    parse_answer(row["answer"])
                except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                    pass
                else:
                    raise AssertionError(f"answer recorded as invalid parses at frame {frame}")
            else:
                status = executor.apply(parse_answer(row["answer"]), row["target"], frame)
                if status != row["status"]:
                    raise AssertionError(f"executor status mismatch at frame {frame}: {status} vs {row['status']}")
            statuses[row["status"]] += 1
            pending = None
        if frame % stride == 0:
            window.append((frame, png(screen, scale)))
            if pending is not None or executor.busy:
                drops += 1
                if frame in by_obs:
                    raise AssertionError(f"request captured at frame {frame} while another was in flight")
            elif frame in by_obs:
                row = by_obs[frame]
                images = select_images(window)
                if [f for f, _ in images] != row["image_frames"]:
                    raise AssertionError(f"image frames mismatch at frame {frame}")
                if [hashlib.sha256(im).hexdigest() for _, im in images] != row["image_sha256"]:
                    raise AssertionError(f"image mismatch at frame {frame}")
                if row["target"] != executor.piece_index:
                    raise AssertionError(f"request target mismatch at frame {frame}")
                checked, pending = checked + 1, row
        env.step(executor.action())
    if checked != len(requests):
        raise AssertionError("not every issued request was checked")
    end = board_state(env)
    derived = {"start": start, "end": end, "lines": end["lines"] - start["lines"], "pieces": end["pieces"] - start["pieces"],
               "new_holes": end["holes"] - start["holes"], "height_delta": end["height_sum"] - start["height_sum"],
               "survived": not env.over, "calls": len(requests), "drops": drops, **statuses,
               "status": "natural_end" if env.over else "horizon"}
    for key, value in derived.items():
        if summary.get(key) != value:
            raise AssertionError(f"summary {key!r} does not match the replay: {summary.get(key)!r} vs {value!r}")
    if not env.over and summary["frames"] != horizon:
        raise AssertionError("episode stopped before the horizon without a game over")
    actions_file = episode_dir / "actions.json"
    if actions_file.exists() and json.loads(actions_file.read_text()) != executor.applied:
        raise AssertionError("retained key scripts do not match the replayed executor")
    return {"episode": episode_dir.name, "verified_frames": summary["frames"], "verified_requests": checked,
            "verified_key_scripts": actions_file.exists(), "lines": summary["lines"], "survived": summary["survived"],
            "model_calls": 0}
