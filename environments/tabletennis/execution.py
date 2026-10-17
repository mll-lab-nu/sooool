"""Physics ownership, asynchronous native IK, and independent public-camera rendering."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import json
import math
import os
import multiprocessing as mp
from pathlib import Path
from queue import Empty, Full
from types import SimpleNamespace
import statistics
import time

import numpy as np


def stats(values):
    ordered = sorted(values)
    return {"count": len(values), "min": min(values) if values else None,
            "mean": statistics.fmean(values) if values else None,
            "p95": ordered[math.ceil(.95 * len(values)) - 1] if values else None,
            "max": max(values) if values else None}


def put_latest(channel, value):
    """Drop old observations when a consumer is busy; never block physics."""
    while True:
        try:
            channel.get_nowait()
        except Empty:
            break
    try:
        channel.put_nowait(value)
    except Full:
        pass


def wait_tick(previous_started, period):
    """Schedule from the previous actual start, so a stall never causes a burst."""
    delay = previous_started + period - time.monotonic()
    if delay > 0:
        time.sleep(delay)
    return time.monotonic()


def install_prepared(env, request, prepared):
    """Install at the exact prepared boundary; never trim an outdated trajectory."""
    core = env.match.R
    if request["point"] != env.state()["point"]:
        return {"discarded": "previous_point"}
    if env.frame != prepared["install_frame"]:
        return {"discarded": "missed_install_deadline"}
    if not np.allclose(core.s._target, prepared["anchor"], atol=1e-8, rtol=0):
        return {"discarded": "command_anchor_changed"}
    recovery = core.rest_command()
    recovery["speed"] = .6
    recovery["q"][2:] = prepared["recovery_arm"]
    result = core.submit({"type": "traj", "k0": core.k, "q": prepared["rows"], "then": recovery})
    info = prepared["info"]
    if "rejected" not in result:
        core.contact_k = request["contact_frame"]
        core._last_act = info
    core.shots.append({"k": core.k, "leg": core.n_our_legs, **info})
    return {**info, **result}


_PLANNER = None
_PLAN_UPDATES = None
_RECOVERY_ARM = None


def planner_init(seed, updates=None):
    global _PLANNER, _PLAN_UPDATES, _RECOVERY_ARM
    from .native import ROOT, load_plugin
    load_plugin(ROOT / "sports/tabletennis/plugin.py")
    os.environ["DUEL_SEED"] = str(seed)
    from duel import Planner
    from workers import _check_session
    _PLANNER = Planner("A")
    import match
    import rally
    match.WRIST_POW = 0.
    rally.RETURN_TOL = (1e-3, 5e-3)
    _PLAN_UPDATES = updates
    _check_session()
    _RECOVERY_ARM, error = _PLANNER._ik(np.array([0., -1.30, .30]), np.array([0., .8660254, .5]),
                                       _PLANNER.s.inst["q0"], np.array([0., -1.75]))
    if error > 1e-3:
        raise ValueError("Receiving recovery pose is not reachable")


def planner_ready():
    return True


def rehearse_robot(pl, targets, count):
    """Native robot/servo rehearsal on the same time base as its reflex state."""
    import mujoco as mj
    twin = pl._twin_session()
    mj.mj_resetData(twin.m, twin.d)
    twin.d.qpos[twin._qadr] = pl.s.d.qpos[pl.s._qadr]
    twin.d.qvel[twin._vadr] = pl.s.d.qvel[pl.s._vadr]
    twin.d.qpos[:3], twin.d.qpos[3:7] = [3., 3., 5.], [1, 0, 0, 0]
    twin.d.time = pl.s.d.time
    mj.mj_forward(twin.m, twin.d)
    twin._target, twin._k, twin._actions = pl.s._target.copy(), 0, []
    twin._events, twin._last_touch = [], {}
    twin.servo.copy_from(pl.s.servo)
    twin.substep_hook = None
    twin._robot_table = twin._robot_net = 0
    for target in targets[:count]:
        twin.d.qpos[:3], twin.d.qvel[:6] = [3., 3., 5.], 0
        twin.step(target)
    state = twin.state()
    pl._rehearsal_table = bool(twin._robot_table or twin._robot_net)
    return state["paddle_pos"], state["paddle_normal"], state["paddle_vel"]


def contact_trajectory(target, previous, prepared, seconds, low, high, serve=False, acc=None):
    """Native arm plan plus a bounded rail stroke through the contact, not a stop."""
    import rally
    import rcb_tt
    from workers import trajectory
    rows, info = trajectory(target, previous, prepared, seconds, low, high, serve=serve, acc=acc)
    drive = prepared.get("rail_velocity")
    if drive is not None:
        n = info["contact_steps"]
        start_speed = (np.asarray(target)-np.asarray(previous))/.01
        goal = np.array(prepared["base_goal"])
        base = rally.hermite(np.asarray(target)[:2], start_speed[:2], goal, drive, n*.01, n)
        follow = rally.hermite(goal, drive, goal+drive*.05, np.zeros(2), .1, 10)
        base = np.vstack((base, follow, np.tile(follow[-1], (max(0,len(rows)-n-10),1))))
        rows = [np.r_[base[i], np.asarray(row)[2:]] for i,row in enumerate(rows)]
        rows = rcb_tt.limit_rows(rows, target, start_speed, lo=low+1e-4, hi=high-1e-4)
        info["rail_velocity_requested"] = drive.tolist()
    return rows,info


def plan_contact(job):
    """Native IK and full trajectory generation, using only own-robot command state."""
    from arm_commands import Core
    from workers import prepare, keep_better, _check_session
    trajectory = contact_trajectory
    import mujoco as mj
    import rally
    started = time.perf_counter()
    pl = _PLANNER
    rally.PLANNER = "limits"
    # Rehearse only the robot and its servo; the ball is parked out of reach.
    mj.mj_resetData(pl.s.m, pl.s.d)
    pl.s.d.qpos[pl.s._qadr] = job["q"]
    pl.s.d.qvel[pl.s._vadr] = job["qd"]
    pl.s.d.qpos[:3] = [3, 3, 5]
    pl.s.d.qpos[3:7] = [1, 0, 0, 0]
    pl.s.d.time = job["sim_time"]
    mj.mj_forward(pl.s.m, pl.s.d)
    pl.s._k = 0
    pl.s._target = np.array(job["target"])
    pl.s._actions = [np.array(job[key]) for key in ("prev2", "prev", "target")]
    pl.s._events, pl.s._last_touch = [], {}
    pl.s.servo.copy_from(job["servo"])
    actions = [np.asarray(job[key], float) for key in ("prev2", "prev", "target")]
    state = SimpleNamespace(_target=actions[-1], JOINT_LOW=pl.s.JOINT_LOW, JOINT_HIGH=pl.s.JOINT_HIGH)
    command = SimpleNamespace(cmd=job["command_in_force"], s=state, k=job["source_frame"])
    command._target_vel = lambda: (actions[-1] - actions[-2]) / .01
    command._target_acc = lambda: (actions[-1] - 2 * actions[-2] + actions[-3]) / .0001
    for frame in range(job["source_frame"], job["install_frame"]):
        command.k = frame
        state._target = np.asarray(Core._arm_target(command), float)
        actions.append(state._target.copy())
        actions = actions[-3:]
        pl.s.step(state._target)
    remaining = job["contact_frame"] - job["install_frame"]
    effective = dict(job, q=pl.s.d.qpos[pl.s._qadr].tolist(),
                     target=state._target.tolist(), prev=actions[-2].tolist(), prev2=actions[-3].tolist(),
                     decision=dict(job["decision"], t=remaining / 100))
    rail_velocity = None
    if not job["serving"]:
        total = np.array(effective["decision"]["vel"])
        rail_velocity = np.array([0.,np.clip(total[1]*.65,0.,.85)])
        effective["decision"] = dict(effective["decision"], vel=(total-np.r_[rail_velocity,0.]).tolist())
    via_heights = rally.VIA_DZ
    rally.VIA_DZ = ()
    try:
        prepared = prepare(pl, effective)
    finally:
        rally.VIA_DZ = via_heights
    if rail_velocity is not None:
        prepared["rail_velocity"] = rail_velocity
    prepared_at = time.perf_counter()
    install_frame = job["install_frame"]
    old_rows = None
    if not job["serving"]:
        # Deliver a usable trajectory as soon as IK finishes. Robot-only
        # calibration continues while this first stroke is already moving.
        coarse, coarse_info = trajectory(state._target, actions[-2], prepared, remaining / 100,
            pl.s.JOINT_LOW, pl.s.JOINT_HIGH, acc=command._target_acc())
        import rcb_tt
        coarse = rcb_tt.limit_rows(coarse, state._target, command._target_vel(),
                                   lo=pl.s.JOINT_LOW+1e-4, hi=pl.s.JOINT_HIGH-1e-4)
        if rally.touches_table(_check_session(), coarse[:remaining]):
            q = np.r_[prepared["base_goal"], prepared["q"]]
            position, rotation = pl.s.fk(q)
            velocity = pl.s.jacobian(q)[:3, 2:] @ prepared["qd"]
            for dz in via_heights:
                before, error = pl._ik(rally.via_pose(position, velocity, rotation[:, 0], dz),
                                       rotation[:, 0], prepared["q"], prepared["base_goal"])
                if error <= 1e-3:
                    prepared["vias"].append((dz, before))
            coarse, coarse_info = trajectory(state._target, actions[-2], prepared, remaining / 100,
                pl.s.JOINT_LOW, pl.s.JOINT_HIGH, acc=command._target_acc())
        old = command.cmd
        previous_rows = list(old["q"][max(0, install_frame-old["k0"]):]) if old and old["type"] == "traj" else []
        coarse, coarse_info = keep_better(coarse, coarse_info, previous_rows, job["decision"])
        coarse = coarse[:remaining+8]
        coarse_info.update(stage="initial", speed_scale=prepared["speed_scale"] / max(.05, coarse_info.get("plan_scale", 1)),
                           paddle_pos=job["decision"]["pos"], paddle_normal=job["decision"]["normal"],
                           paddle_vel=job["decision"]["vel"])
        _PLAN_UPDATES.put((job["request"], {"rows": [np.asarray(row).tolist() for row in coarse],
            "info": coarse_info, "anchor": state._target.tolist(), "install_frame": install_frame,
            "recovery_arm": _RECOVERY_ARM.tolist(),
            "worker_s": time.perf_counter()-started}))
        refine_frame = min(job["contact_frame"]-6, job["source_frame"]+50)
        for frame in range(install_frame, refine_frame):
            pl.s.step(coarse[frame-install_frame])
        old_rows = coarse[refine_frame-install_frame:]
        install_frame = refine_frame
        state._target = pl.s._target.copy()
        actions = pl.s._actions[-3:]
        remaining = job["contact_frame"]-install_frame
    # Preserve native execution scatter: calibrate to the perturbed contact
    # configuration, never cancel the environment's position/normal scatter.
    contact_q = np.r_[prepared["base_goal"], prepared["q"]]
    desired_pos, rotation = pl.s.fk(contact_q)
    desired_normal = rotation[:, 0]
    desired_vel = pl.s.jacobian(contact_q)[:3, 2:] @ prepared["qd"]
    if rail_velocity is not None:
        desired_vel += np.r_[rail_velocity,0.]
    best = None
    for iteration in range(2):
        rows, info = trajectory(state._target, actions[-2], prepared, remaining / 100,
                                pl.s.JOINT_LOW, pl.s.JOINT_HIGH, serve=job["serving"], acc=command._target_acc())
        if not job["serving"]:
            rows = rcb_tt.limit_rows(rows, state._target, command._target_vel(),
                                    lo=pl.s.JOINT_LOW+1e-4, hi=pl.s.JOINT_HIGH-1e-4)
        pos, normal, velocity = rehearse_robot(pl, rows, remaining)
        angle = float(np.arccos(np.clip(normal @ desired_normal, -1, 1)))
        loss = np.linalg.norm(pos-desired_pos) + .1*angle + .15*np.linalg.norm(velocity-desired_vel)
        if pl._rehearsal_table:
            loss += 1
        if best is None or loss < best[0]:
            best = (loss, rows, info, pos, normal, velocity, pl._rehearsal_table)
        if iteration == 0:
            q = np.r_[prepared["base_goal"], prepared["q"]]
            jac = pl.s.jacobian(q)[:, 2:]
            error = np.r_[desired_pos-pos, np.cross(normal, desired_normal)]
            prepared["q"] = np.clip(prepared["q"] + jac.T @ np.linalg.solve(jac @ jac.T + 1e-4*np.eye(6), error),
                                    pl.s.JOINT_LOW[2:]+1e-4, pl.s.JOINT_HIGH[2:]-1e-4)
            linear = jac[:3]
            weight = np.diag(rally.ARM_VEL**2)
            prepared["qd"] += .7 * weight @ linear.T @ np.linalg.solve(
                linear @ weight @ linear.T + 1e-6*np.eye(3), desired_vel-velocity)
    _, rows, info, pos, normal, velocity, table = best
    rows = rows[:remaining+8]
    old = command.cmd
    if old_rows is None:
        old_rows = list(old["q"][max(0, install_frame-old["k0"]):]) if old and old["type"] == "traj" else []
    # A calibrated pose intentionally offsets ideal FK to cancel servo lag.
    # Rank both candidates under the same physical servo, not ideal FK.
    if len(old_rows) >= remaining:
        old_pos, old_normal, old_velocity = rehearse_robot(pl, old_rows, remaining)
        angle = float(np.arccos(np.clip(old_normal @ desired_normal, -1, 1)))
        loss = np.linalg.norm(old_pos-desired_pos) + .1*angle + .15*np.linalg.norm(old_velocity-desired_vel)
        loss += int(pl._rehearsal_table)
        if loss + .002 < best[0]:
            rows, pos, normal, velocity, table = old_rows, old_pos, old_normal, old_velocity, pl._rehearsal_table
            info = dict(info, kept="the trajectory in force (better physical rehearsal)")
    info.update(blade_error_m=float(np.linalg.norm(pos-desired_pos)),
                normal_error_deg=float(np.degrees(np.arccos(np.clip(normal @ desired_normal, -1, 1)))),
                paddle_vel_delivered=velocity.tolist(), table_contact_in_rehearsal=table)
    scale = prepared["speed_scale"]
    if info.get("plan_scale") is not None and info["plan_scale"] < .97:
        scale /= max(.05, info["plan_scale"])
    dec = job["decision"]
    info.update(ik_residual=prepared["ik_residual"], speed_scale=scale,
                stage="calibrated",
                ik_seconds=prepared_at-started, trajectory_seconds=time.perf_counter()-prepared_at,
                n_swing_steps_available=remaining, T_from_now=remaining / 100,
                paddle_pos=dec["pos"], paddle_normal=dec["normal"], paddle_vel=dec["vel"],
                stroke="asynchronous native preparation and trajectory")
    return {"rows": [np.asarray(row).tolist() for row in rows], "info": info,
            "anchor": state._target.tolist(), "install_frame": install_frame,
            "recovery_arm": _RECOVERY_ARM.tolist(),
            "worker_s": time.perf_counter() - started}


def physics_main(config, output, commands, snapshots, events, start, stop, advance=None):
    from .native import TableTennisEnvironment
    from core.sport import Refused, parse_action

    output = Path(output)
    env = None
    updates = mp.get_context("spawn").Queue()
    pool = ProcessPoolExecutor(max_workers=2, mp_context=mp.get_context("spawn"),
                               initializer=planner_init, initargs=(config["seed"], updates))
    request = queued = scheduled_toss = None
    planning = {}
    latest_sources = {}
    ready_plans = []
    tick_intervals, step_costs, install_costs, planning_costs = [], [], [], []
    initial_costs = []
    invalid = installed = discarded = 0
    recorded_contacts = set()
    status, error = "stopped", None
    started = ended = None
    allowed_frame = 0
    gate_wait_seconds = 0.
    log = (output / "physics.jsonl").open("w", buffering=1)
    presentation = (output / "presentation.jsonl").open("w", buffering=256 * 1024)

    def emit(kind, **fields):
        row = {"event": kind, "frame": env.frame, "wall_mono": time.monotonic(), **fields}
        log.write(json.dumps(row, separators=(",", ":")) + "\n")
        events.put(row)

    def snapshot(terminal=False):
        job, metadata = env.match.camera_job("A")
        return {"frame": env.frame, "state": env.state(), "job": job, "metadata": metadata,
                "captured_mono": time.monotonic(), "started_mono": started,
                "terminal": terminal}

    try:
        env = TableTennisEnvironment(config["level"], config["seed"])
        import serve
        import builtin_players
        for recipe in builtin_players.SERVES.values():
            serve.vz_for_height(recipe["height"])
        pool.submit(planner_ready).result(timeout=30)
        events.put({"event": "physics_ready", "spec": env.spec})
        put_latest(snapshots, snapshot())
        while not start.wait(.05):
            if stop.is_set():
                return
        started = time.monotonic()
        previous_tick = started
        emit("clock_started", started_mono=started)
        while env.frame < round(config["duration"] * 100) and not stop.is_set():
            if (output / "STOP").exists():
                break
            if advance is not None and env.frame >= allowed_frame:
                before_gate = time.monotonic()
                while not stop.is_set():
                    try:
                        allowed_frame = advance.get(timeout=.1)
                        break
                    except Empty:
                        continue
                gate_wait_seconds += time.monotonic() - before_gate
                if stop.is_set():
                    break
                previous_tick = time.monotonic()
            tick = wait_tick(previous_tick, .01 * config["slowdown"])
            if env.frame:
                tick_intervals.append(tick - previous_tick)
            previous_tick = tick
            while True:
                try:
                    initial_request, initial_plan = updates.get_nowait()
                except Empty:
                    break
                ready_plans.append((initial_request, initial_plan))
                initial_costs.append(initial_plan["worker_s"])
            for task in list(planning):
                if task.done():
                    final_plan = task.result()
                    ready_plans.append((planning.pop(task), final_plan))
                    planning_costs.append(final_plan["worker_s"])
            if advance is not None:
                for ready_request, prepared_ready in ready_plans:
                    ready_frame = ready_request.get("planning_frame", ready_request["source_frame"]) + math.ceil(prepared_ready["worker_s"] / (.01 * config["slowdown"]))
                    prepared_ready["virtual_ready_frame"] = ready_frame
            ready_plans.sort(key=lambda item: max(item[1]["install_frame"], item[1].get("virtual_ready_frame", 0)))
            while ready_plans and env.frame >= max(ready_plans[0][1]["install_frame"], ready_plans[0][1].get("virtual_ready_frame", 0)):
                ready_request, prepared_ready = ready_plans.pop(0)
                before = time.perf_counter()
                key = tuple(ready_request["leg_key"])
                if prepared_ready["info"].get("stage")=="calibrated" and ready_request["source_frame"]<latest_sources.get(key,0):
                    feedback = {"discarded": "newer_observation_is_being_planned"}
                else:
                    feedback = install_prepared(env, ready_request, prepared_ready)
                install_costs.append(time.perf_counter() - before)
                invalid += int("rejected" in feedback)
                discarded += int("discarded" in feedback)
                installed += int("rejected" not in feedback and "discarded" not in feedback)
                if ready_request.get("service") and "rejected" not in feedback and "discarded" not in feedback:
                    scheduled_toss = ready_request
                emit("planned_action", request=ready_request, feedback=feedback,
                     installation_seconds=install_costs[-1], preparation_seconds=prepared_ready["worker_s"])
            if scheduled_toss is not None and env.frame >= scheduled_toss["service"]["toss_frame"]:
                if scheduled_toss["point"] == env.state()["point"]:
                    action = scheduled_toss["service"]["toss"]
                    cmd = parse_action(env.layer, "A", action, env.match, {})
                    low, info = env.layer.lower("A", cmd, None, env.match)
                    feedback = {**info, **env.match.apply("A", low)}
                    emit("immediate_action", request={**scheduled_toss, "action": action}, feedback=feedback)
                scheduled_toss = None
            try:
                message = commands.get_nowait()
            except Empty:
                message = None
            if message is not None:
                if message["point"] != env.state()["point"]:
                    emit("action_discarded", reason="previous_point", source_frame=message["source_frame"])
                    discarded += 1
                elif message["action"]["type"] == "act":
                    queued = message
                    latest_sources[tuple(message["leg_key"])] = message["source_frame"]
                else:
                    try:
                        cmd = parse_action(env.layer, "A", message["action"], env.match, {})
                        low, info = env.layer.lower("A", cmd, None, env.match)
                        feedback = {**info, **env.match.apply("A", low)}
                    except Refused as exc:
                        feedback = {"rejected": str(exc)}
                    invalid += int("rejected" in feedback)
                    emit("immediate_action", request=message, feedback=feedback)
            if len(planning)<2 and queued is not None:
                request, queued = queued, None
                remaining = request["contact_frame"] - env.frame
                # Reserve compute time, rather than spending a third of every
                # flight idling. Short post-bounce corrections are cheap.
                serving = env.match.R.leg["kind"] == "our_serve"
                initial_budget = math.ceil(max(initial_costs[-8:], default=.10) / (.01*config["slowdown"])) + 2
                lead = min(50, max(6, remaining//2)) if serving else min(25, max(12, initial_budget))
                if request["point"] != env.state()["point"] or remaining <= lead + 2:
                    emit("planned_action", request=request, feedback={"discarded": "stale_before_preparation"})
                    discarded += 1
                else:
                    decision = {**request["action"], "t": remaining / 100}
                    cmd = parse_action(env.layer, "A", decision, env.match, {})
                    core = env.match.R
                    actions = core.s._actions
                    job = {"decision": cmd, "point": request["point"], "ball": request["leg_key"],
                           "ordinal": core.n_our_legs, "serving": serving, "request": request,
                           "q": core.s.d.qpos[core.s._qadr].tolist(), "target": core.s._target.tolist(),
                           "qd": core.s.d.qvel[core.s._vadr].tolist(), "sim_time": core.s.d.time,
                           "servo": copy.deepcopy(core.s.servo),
                           "prev": (actions[-2] if len(actions) >= 2 else core.s._target).tolist(),
                           "prev2": (actions[-3] if len(actions) >= 3 else core.s._target).tolist(),
                           "source_frame": env.frame, "install_frame": env.frame + lead,
                           "contact_frame": request["contact_frame"], "command_in_force": copy.deepcopy(core.cmd)}
                    request["planning_frame"] = env.frame
                    planning[pool.submit(plan_contact, job)] = request
                    emit("planning_started", source_frame=request["source_frame"], contact_frame=request["contact_frame"])
            before = time.perf_counter()
            info = env.step()
            step_costs.append(time.perf_counter() - before)
            log.write(json.dumps({"event": "tick", "frame": env.frame, "wall_mono": tick,
                                  "step_seconds": step_costs[-1]}, separators=(",", ":")) + "\n")
            for event in info["events"]:
                emit("native_event", native_event=event)
            # Offline presentation only: never put these simulator poses on the
            # observations channel. Preserve every physical frame for a replay
            # without 20 Hz aliasing or history-tile jumps.
            core = env.match.R
            for contact in core.s._events:
                if contact["kind"] == "paddle" and contact["t"] not in recorded_contacts:
                    recorded_contacts.add(contact["t"])
                    # Offline diagnostics only, deliberately excluded from the
                    # events/observations channels read by the tactical actor.
                    log.write(json.dumps({"event": "contact_diagnostic", "frame": env.frame,
                        "wall_mono": time.monotonic(), "contact": contact,
                        "point": len(core.points)+1, "leg": core.leg["kind"],
                        "requested": core._last_act, "servo_reflexes": core.s.servo.n_reflex},
                        separators=(",", ":")) + "\n")
            presentation.write(json.dumps({"frame": env.frame, "wall_mono": time.monotonic(),
                "qpos": core.s.d.qpos.tolist(), "opp_x": core.opp_x(), "state": env.state()},
                separators=(",", ":")) + "\n")
            if env.frame % config.get("capture_stride", 5) == 0:
                put_latest(snapshots, snapshot())
            if env.frame % 100 == 0:
                progress = {"status": "running", "frame": env.frame, "score": env.match.scores(),
                            "wall_seconds": time.monotonic() - started, "invalid": invalid,
                            "plans_installed": installed}
                (output / "physics-progress.json").write_text(json.dumps(progress, indent=2))
            if info["done"]:
                status = "completed"
                break
        else:
            if not stop.is_set():
                status = "window_completed"
        ended = time.monotonic()
        put_latest(snapshots, snapshot(terminal=True))
    except BaseException as exc:
        ended = time.monotonic()
        status, error = "failed", f"{type(exc).__name__}: {exc}"
    finally:
        wall = ended - started if started is not None and ended is not None else 0
        summary = {"status": status, "error": error, "frames": env.frame if env else 0,
                   "native_planning_workers": 2,
                   "game_seconds": env.frame / 100 if env else 0, "gameplay_wall_seconds": wall,
                   "started_mono": started, "ended_mono": ended, "invalid": invalid,
                   "plans_installed": installed, "plans_discarded": discarded,
                   "clock": {"requested_slowdown": config["slowdown"],
                             "catch_up_steps": sum(dt < .0095 * config["slowdown"] for dt in tick_intervals),
                             "mode": "subscription_with_simulated_api_profile" if advance is not None else "actual_wall",
                             "physics_waits_for_model": advance is not None, "physics_waits_for_preparation": False,
                             "simulation_gate_wall_seconds": gate_wait_seconds,
                             "tick_intervals_seconds": stats(tick_intervals), "step_seconds": stats(step_costs),
                             "installation_seconds": stats(install_costs), "preparation_seconds": stats(planning_costs),
                             "initial_preparation_seconds": stats(initial_costs),
                             "effective_slowdown": wall / (env.frame / 100) if env and env.frame else None},
                   **(env.outcome() if env else {})}
        (output / "physics-summary.json").write_text(json.dumps(summary, indent=2))
        events.put({"event": "physics_finished", "summary": summary})
        log.close()
        presentation.close()
        if advance is not None:
            # Python 3.11 has no terminate_workers(). Bound cleanup of robot-only
            # jobs whose contact deadlines or episode have already ended.
            processes = list((pool._processes or {}).values())
            pool.shutdown(wait=False, cancel_futures=True)
            for process in processes:
                process.join(timeout=.5)
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=2)
        else:
            pool.shutdown(wait=True, cancel_futures=True)
        if env is not None:
            env.close()


def render_main(config, output, snapshots, observations, events, stop):
    """Own the EGL context and record every rendered public observation independently."""
    from .native import ROOT, load_plugin, MatchConfig

    output = Path(output)
    sport = load_plugin(ROOT / "sports/tabletennis/plugin.py")
    cfg = MatchConfig(sport="tabletennis", format="match-wallclock", seats=("A",),
                      seed=config["seed"], level=config["level"], action_level="high", play="program")
    renderer = sport.worker_init("render", "A", cfg)
    events.put({"event": "render_ready"})
    log = (output / "captures.jsonl").open("w", buffering=1)
    try:
        while not stop.is_set():
            try:
                snapshot = snapshots.get(timeout=.1)
            except Empty:
                continue
            before = time.perf_counter()
            png = sport.worker_call(renderer, "render", snapshot["job"])["png"]
            image = output / "images" / f'frame-{snapshot["frame"]:07d}.png'
            image.write_bytes(png)
            packet = {key: snapshot[key] for key in ("frame", "state", "metadata", "captured_mono", "started_mono", "terminal")}
            packet.update(image=str(image), available_mono=time.monotonic(), render_seconds=time.perf_counter() - before)
            log.write(json.dumps(packet, separators=(",", ":")) + "\n")
            put_latest(observations, packet)
            if snapshot["terminal"]:
                break
    except BaseException as exc:
        events.put({"event": "render_failed", "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        renderer.r.close()
        log.close()
