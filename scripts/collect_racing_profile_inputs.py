"""Offline native camera trajectories for profile inputs; never model gameplay."""
from collections import deque
import argparse
import base64
import json
import os
from pathlib import Path
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT_REVISION = "da1f787f775ea6524d698c0b063157ded4c0fef9"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    revision = subprocess.check_output(
        ["git", "-C", str(a.environment), "rev-parse", "HEAD"], text=True).strip()
    if revision != ENVIRONMENT_REVISION:
        raise ValueError("Expected the pinned read-only native environment revision")
    os.environ["RACING_ENV_ROOT"] = str(a.environment.resolve())
    os.environ.setdefault("MUJOCO_GL", "egl")
    os.environ.setdefault("LP_NUM_THREADS", "1")
    sys.path.insert(0, str(ROOT / "environments/racing"))
    from run import make_world, observe, camera_metrics, controller_prompt
    from core.sport import FINISHED, UNIT_OVER
    sys.path.insert(0, str(a.environment / "sports/racing"))
    from builtin_players import Reference
    a.output.mkdir(parents=True, exist_ok=False)
    recipe = json.loads((ROOT / "recipes/racing.json").read_text())
    profile = json.loads((ROOT / recipe["profile"]).read_text())
    delays = {k: profile[k] for k in ("p50", "p95", "mean")}
    records = []
    for seed in (101, 304, 305):
        _, _, m, views, spec = make_world(seed, 1, 1)
        ref = Reference(spec, "A", seed)
        history = deque(maxlen=2)
        count = 0
        while m.k <= 1200 and m.phase().state != FINISHED:
            if m.phase().state == UNIT_OVER:
                m.resume()
                history.clear()
            if m.k % 20 == 0:
                state, image = observe(m, views)
                command = ref.act({"state": state, "observation": {
                    "image_png_b64": base64.b64encode(image).decode()}})
                m.apply("A", command)
                if m.k % 60 == 0:
                    state["camera_measurements"] = camera_metrics(image, spec)
                    history.append((state, image))
                    if m.k >= 120 and m.k % 120 == 0:
                        prompt = controller_prompt([x[0] for x in history], "metric", 1,
                                                   delays, 1, "lane", "arrival")
                        paths = []
                        for i, (_, raw) in enumerate(history):
                            name = f"seed{seed}-step{m.k}-{i}.png"
                            (a.output / name).write_bytes(raw)
                            paths.append(name)
                        records.append({"game": "racing", "prompt": prompt,
                            "system": (ROOT / recipe["system"]).read_text(),
                            "image_paths": paths, "max_tokens": 512,
                            "provenance": {"collection": "new offline native reference-controller trajectory",
                                "seed": seed, "step": m.k, "policy_recipe": "recipes/racing.json",
                                "environment_revision": revision,
                                "model_calls": 0, "gameplay_evaluation": False}})
                        count += 1
            m.step()
        print(json.dumps({"seed": seed, "cases": count}), flush=True)
    (a.output / "records.json").write_text(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
