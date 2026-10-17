"""Coordinate independent physical, rendering, native-planning and model workers."""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
import functools
import json
import multiprocessing as mp
from pathlib import Path
from queue import Empty
import signal
import threading
import time

from PIL import Image

from environments.badminton.public import public_data
from runtime.subscription import SubscriptionClient
from .execution import physics_main, render_main, stats
from .tactics import POLICY_ROOT, SCHEMA, TacticalPlayer, decode_intent, format_prompt


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def run_episode(config, output):
    from .native import ROOT, load_plugin

    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "images").mkdir()
    write(output / "run.json", {key: value for key, value in config.items() if key != "api_key_file"})
    simulated = config.get("simulation", False)
    scheduler = None
    if simulated:
        from .simulation import DelayScheduler
        scheduler = DelayScheduler(config["latency_profile"], config["delay_seed"],
                                   config["slowdown"], config["capture_stride"])
    context = mp.get_context("spawn")
    commands, snapshots, observations, events = (context.Queue(), context.Queue(2), context.Queue(2), context.Queue())
    start, stop, render_stop = context.Event(), context.Event(), context.Event()
    advance = context.Queue() if simulated else None
    physics = context.Process(target=physics_main, args=(config, output, commands, snapshots, events, start, stop, advance),
                              name="tabletennis-physics")
    renderer = context.Process(target=render_main, args=(config, output, snapshots, observations, events, render_stop),
                               name="tabletennis-render")
    handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    for sig in handlers:
        signal.signal(sig, lambda *_: stop.set())
    workers = config.get("model_workers", 4) if config["source"] == "api" or simulated else 1
    native_workers = 1 if config["source"] == "sol" else workers
    pool = ThreadPoolExecutor(max_workers=native_workers, thread_name_prefix="tabletennis-model")
    client = budget = player = None
    pending = {}
    max_inflight = superseded = 0
    last_accepted_source = -1
    last_frame = 0
    calls = accepted = invalid = tactical = 0
    next_request = next_control = 0
    memory = ""
    history, control_costs, model_costs, served_tiers = [], [], [], []
    completion_times, observation_ages, used_workers = [], [], set()
    simulated_delays, model_waits = [], []
    installed_legs = set()
    return_origins = {}
    final = None
    started = time.monotonic()
    log_file = (output / "events.jsonl").open("w", buffering=1)

    def log(kind, **fields):
        log_file.write(json.dumps({"event": kind, "wall_mono": time.monotonic(), **fields},
                                  separators=(",", ":"), allow_nan=False) + "\n")

    def invoke(prompt, image, directory):
        if config["source"] == "api":
            result = client.complete(prompt, [image], directory,
                                     cancel_check=lambda: "game_stopped" if stop.is_set() else None)
            return {**result, "completed_mono": time.monotonic(), "worker": threading.current_thread().name}
        if stop.is_set():
            return {"cancelled_before_start": True}
        text, metadata = client.act(prompt, [image.read_bytes()], directory)
        return {"text": text, **metadata, "completed_mono": time.monotonic()}

    def receive(result, metadata):
        nonlocal invalid, accepted, memory, last_accepted_source, superseded
        if result.get("cancelled_before_start"):
            return
        model_costs.append(result["wall_seconds"])
        if result.get("worker"):
            used_workers.add(result["worker"])
        if not metadata["bootstrap"]:
            completion_times.append(result["completed_mono"])
            observation_ages.append((last_frame-metadata["source_frame"])/100)
        if result.get("service_tier"):
            served_tiers.append(result["service_tier"])
        log("reply_received", **metadata, receipt_frame=last_frame, worker=result.get("worker"),
            latency_wall_seconds=result["wall_seconds"], completed_mono=result.get("completed_mono"))
        try:
            intent = decode_intent(result["text"])
        except (ValueError, TypeError) as exc:
            invalid += 1
            log("intent_rejected", **metadata, error=str(exc))
            return
        if metadata["source_frame"] <= last_accepted_source:
            superseded += 1
            log("intent_superseded", **metadata, intent=intent)
            return
        last_accepted_source = metadata["source_frame"]
        player.accept(intent, metadata["request_id"])
        memory = intent["memory"]
        accepted += 1
        log("intent_accepted", **metadata, receipt_frame=last_frame, intent=intent,
            latency_wall_seconds=result["wall_seconds"], service_tier=result.get("service_tier"))

    def issue(packet, *, bootstrap=False):
        nonlocal calls, next_request, max_inflight
        frame = packet["frame"]
        recent = [{"frame": event["frame"], "selection": event["selection"],
                   "feedback": {key: value for key, value in event["feedback"].items()
                                if key in {"discarded", "rejected", "kept", "stage", "speed_scale",
                                           "normal_error_deg", "blade_error_m"}}} for event in history[-4:]]
        snapshot = {"state": public_data(packet["state"]), "policy": player.intent[0],
                    "tactics": player.context(packet["state"]), "memory": memory,
                    "history": recent, "slowdown": config["slowdown"],
                    "clock": "initialization" if bootstrap else config["clock"]}
        directory = output / "requests" / f"request-{calls:05d}"
        directory.mkdir(parents=True)
        write(directory / "snapshot.json", snapshot)
        # Latest two public views, not simulator truth or evaluator renderings.
        with Image.open(packet["image"]) as sheet:
            image = Image.new("RGB", (960, 360))
            image.paste(sheet.crop((1440, 0, 1920, 360)), (0, 0))
            image.paste(sheet.crop((1440, 360, 1920, 720)), (480, 0))
            image_path = directory / "observation.png"
            image.save(image_path)
        metadata = {"request_id": calls, "source_frame": frame, "bootstrap": bootstrap,
                    "issued_mono": time.monotonic()}
        if scheduler is not None:
            metadata.update(scheduler.schedule(frame))
            simulated_delays.append(metadata["sampled_api_seconds"])
        task = pool.submit(invoke, format_prompt(snapshot), image_path, directory)
        pending[task] = metadata
        max_inflight = max(max_inflight, len(pending))
        log("request_issued", **metadata)
        calls += 1
        next_request = frame + round(config.get("request_interval_s", .65)*100/config["slowdown"])
        return task

    def handle(event):
        nonlocal final, tactical
        kind = event["event"]
        if kind == "physics_finished":
            final = event["summary"]
            return
        if kind == "render_failed":
            raise RuntimeError(event["error"])
        if kind in {"planned_action", "immediate_action"}:
            request, feedback = event["request"], event["feedback"]
            selection = request["selection"]
            applied = "rejected" not in feedback and "discarded" not in feedback
            key = tuple(request["leg_key"])
            if applied and request["action"]["type"] == "act":
                installed_legs.add(key)
                if selection and key not in return_origins:
                    return_origins[key] = {"policy": selection["policy"], "intent_id": selection["intent_id"],
                                           "fallback": not selection["selected"]}
                    log("policy_activated", frame=event["frame"], leg_key=list(key), **return_origins[key])
            tactical += int(bool(applied and selection and selection["selected"] and not feedback.get("kept")))
            history.append({"frame": event["frame"], "type": request["action"]["type"],
                            "selection": selection, "feedback": feedback})
            if player is not None and player.reference.P.leg is not None:
                if tuple(player.reference.P.leg["key"]) == tuple(request["leg_key"]):
                    player.reference.P.on_act_reply(feedback if applied else None)
                    if not applied and key not in installed_legs:
                        player.reference.P.leg["acts"].clear()
            if not applied and request["action"]["type"] == "act":
                service = player.reference.srv
                if service and service["point"] == request["point"]:
                    service["acted"] = service["tossed"] = False
        log(kind, **{key: value for key, value in event.items() if key != "event"})

    try:
        physics.start()
        renderer.start()
        ready = set()
        while len(ready) < 2:
            event = events.get(timeout=60)
            if event["event"] in {"physics_ready", "render_ready"}:
                ready.add(event["event"])
                if event["event"] == "physics_ready":
                    sport = load_plugin(ROOT / "sports/tabletennis/plugin.py")
                    player = TacticalPlayer(event["spec"], sport.players()["reference"])
                    from .perception import fit_flight, rollout, solve_out, countershot
                    player.bp.fit_flight = functools.partial(fit_flight, gravity=player.bp.G, drag=player.bp.KD)
                    player.bp.rollout = functools.partial(rollout, gravity=player.bp.G, drag=player.bp.KD,
                        radius=player.bp.BALL_R, ez=player.bp.E_BOUNCE_Z, exy=player.bp.E_BOUNCE_XY,
                        table_x=player.bp.TABLE_X, table_y=player.bp.TABLE_Y)
                    player.bp.solve_out = functools.partial(solve_out, flight=player.bp.rollout,
                                                           radius=player.bp.BALL_R, net_z=player.bp.NET_Z)
                    # Deterministic repertoire computation is setup, not a freeze of live physics.
                    raw_serve_plan = player.bp.serve_plan
                    player.bp.serve_plan = functools.lru_cache(maxsize=16)(raw_serve_plan)
                    for name in player.bp.SERVE_ORDER:
                        player.bp.serve_plan(name, recipe=None)
                    import numpy as np
                    countershot(np.array([0.,-1.2,.3]),np.array([0.,-2.5,0.]),np.array([0.,.4]),player.bp.G,player.bp.KD)
                    player.service_plan = player.bp.serve_plan("mid_wide_fh_top", recipe=None)
                    if config["source"]=="rules":
                        player.accept({"policy": config.get("rules_policy","safe_center")}, None)
            else:
                handle(event)
                if final is not None:
                    raise RuntimeError(final["error"] or "Physics failed during startup")
        if config["source"] == "api":
            from runtime.api import ApiBudget, ApiClient
            budget = ApiBudget(Path(config["api_budget_file"]), config["api_limit_usd"])
            write(output / "budget-before.json", budget.snapshot())
            client = ApiClient({**config, "system_instructions_file": str(POLICY_ROOT / "system.txt")},
                               output / "api", budget, SCHEMA)
        elif config["source"] == "sol":
            client = SubscriptionClient(output=output / "worker", output_schema=SCHEMA,
                                        system=(POLICY_ROOT / "system.txt").read_text(),
                                        service_tier=config["subscription_service_tier"], auth_only_home=simulated)
        if config["source"] == "api":
            initial = observations.get(timeout=10)
            task = issue(initial, bootstrap=True)
            receive(task.result(), pending.pop(task))
            if player.intent[1] is None:
                raise RuntimeError("No valid model strategy before game start")
        start.set()
        while final is None:
            while True:
                try:
                    handle(events.get_nowait())
                except Empty:
                    break
            if final is not None:
                break
            if not physics.is_alive():
                handle(events.get(timeout=2))
                if final is None:
                    raise RuntimeError("Physics process exited without a final result")
            for task in list(pending):
                if not simulated and task.done():
                    receive(task.result(), pending.pop(task))
            try:
                packet = observations.get(timeout=.005)
            except Empty:
                continue
            frame = packet["frame"]
            last_frame = frame
            if simulated:
                for task in sorted(list(pending), key=lambda t: (pending[t]["delivery_frame"], pending[t]["request_id"])):
                    metadata = pending[task]
                    if scheduler.due(metadata, frame) and not metadata.get("delivered"):
                        before_wait = time.monotonic()
                        receive(task.result(), metadata)
                        metadata["delivered"] = True
                        model_waits.append(time.monotonic() - before_wait)
                    if metadata.get("delivered") and frame >= metadata["terminal_frame"]:
                        log("simulated_terminal", request_id=metadata["request_id"], frame=frame)
                        pending.pop(task)
            if frame < next_control:
                if simulated:
                    advance.put(frame + config["capture_stride"])
                continue
            image = Path(packet["image"])
            png = image.read_bytes()
            view = {"state": packet["state"], "observation": {
                **packet["metadata"], "image_png_b64": base64.b64encode(png).decode()}}
            before = time.perf_counter()
            action, selection = player.act(view)
            control_costs.append(time.perf_counter() - before)
            next_control = frame + config["observation_stride"]
            if action is not None:
                state = packet["state"]
                key = (state["point"], state.get("ball"), round(frame - state["t_since_played"] * 100))
                commands.put({"action": action, "source_frame": frame, "point": state["point"],
                              "contact_frame": frame + round(action.get("t", 0) * 100),
                              "leg_key": key, "selection": selection, "service": player.serve_request})
            if client is not None and len(pending)<workers and frame>=next_request and calls<config["max_calls"]:
                issue(packet)
            if simulated:
                advance.put(frame + config["capture_stride"])
        if final["error"] is not None:
            raise RuntimeError(final["error"])
    finally:
        stop.set()
        start.set()
        physics.join(timeout=10)
        renderer.join(timeout=3)
        render_stop.set()
        for process in (physics, renderer):
            if process.is_alive():
                process.terminate()
                process.join(timeout=3)
        pool.shutdown(wait=True, cancel_futures=True)
        late = []
        for task, metadata in pending.items():
            if task.cancelled():
                continue
            exception = task.exception()
            if exception is not None:
                late.append({**metadata, "status": "failed", "error_type": type(exception).__name__})
            else:
                result = task.result()
                late.append({**metadata, "status": "cancelled_before_start" if result.get("cancelled_before_start") else "completed"})
                if not result.get("cancelled_before_start") and not metadata.get("delivered"):
                    model_costs.append(result["wall_seconds"])
                    if result.get("service_tier"):
                        served_tiers.append(result["service_tier"])
        if client is not None:
            client.close()
        if final is None and (output / "physics-summary.json").exists():
            final = json.loads((output / "physics-summary.json").read_text())
        summary = {**(final or {"status": "failed"}), "source": config["source"], "calls": calls,
                   "accepted_intentions": accepted, "model_invalid": invalid,
                   "model_workers": native_workers, "virtual_capacity": workers if simulated else None,
                   "max_inflight_model_calls": max_inflight,
                   "model_worker_ids": sorted(used_workers),
                   "reply_intervals_seconds": stats([b-a for a,b in zip(sorted(completion_times), sorted(completion_times)[1:])]),
                   "observation_age_game_seconds": stats(observation_ages),
                   "superseded_intentions": superseded,
                   "tactical_action_submissions": tactical, "late_model_outcome": late,
                   "return_policy_origins": list(return_origins.values()),
                   "initialization_wall_seconds": final["started_mono"]-started if final and final.get("started_mono") else None,
                   "model_latency_seconds": stats(model_costs), "served_service_tiers": served_tiers,
                   "clock_mode": config["clock"], "real_time_api_acceptance": False if simulated else None,
                   "sampled_api_latency_seconds": stats(simulated_delays),
                   "subscription_wait_seconds": stats(model_waits),
                   "latency_profile_sha256": config.get("latency_profile", {}).get("sha256"),
                   "control_compute_seconds": stats(control_costs),
                   "total_wall_seconds": time.monotonic() - started}
        if budget is not None:
            summary["api_budget"] = budget.snapshot()
            write(output / "budget-after.json", summary["api_budget"])
        write(output / "summary.json", summary)
        log("summary", **summary)
        log_file.close()
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
    return summary
