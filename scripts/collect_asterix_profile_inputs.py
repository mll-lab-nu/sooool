"""Collect native Atari observations with seeded scripted actions, no inference.

Offline state collection is not gameplay evaluation. No scripted policy is used
when measuring DeepSeek, and collected actions never become model outputs.
"""
from collections import deque
import argparse
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "environments/asterix"))
from runner import build_task
from simulate_5x import make_env, png, select_images


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    recipe = json.loads((ROOT / "recipes/asterix.json").read_text())
    task, _ = build_task(ROOT, recipe, "realtime")
    records = []
    for seed in (5, 9, 17):
        env, obs, _, noops = make_env(seed)
        rng = random.Random(seed)
        window, history = deque(maxlen=9), []
        action = 0
        try:
            for frame in range(513):
                if frame % 48 == 0:
                    action = rng.randrange(9)
                    history.append((frame, action))
                if frame % 4 == 0:
                    window.append((frame, png(obs)))
                if frame in range(32, 513, 48):
                    images = select_images(window)
                    prompt = task + f"Current observation frame: {frame}. Image frames: {[f for f,_ in images]}. Current held action: {action}.\n"
                    prompt += "Applied commands, oldest first, age_in_raw_frames:action: " + ",".join(
                        f"{frame-f}:{v}" for f, v in history[-8:]) + ".\n"
                    files = []
                    for i, (_, raw) in enumerate(images):
                        name = f"seed{seed}-frame{frame}-{i}.png"
                        (a.output / name).write_bytes(raw)
                        files.append(name)
                    records.append({"game": "asterix", "prompt": prompt,
                        "system": (ROOT / recipe["system"]).read_text(), "image_paths": files,
                        "output_format": "action_reason", "max_tokens": 512,
                        "provenance": {"collection": "new offline native Atari seeded scripted trajectory",
                                       "seed": seed, "frame": frame, "reset_noops": noops,
                                       "policy_recipe": "recipes/asterix.json", "model_calls": 0,
                                       "gameplay_evaluation": False}})
                obs, _, done, truncated, _ = env.step(action)
                if done or truncated:
                    break
        finally:
            env.close()
    (a.output / "records.json").write_text(json.dumps(records, indent=2))
    print(json.dumps({"cases": len(records), "seeds": [5, 9, 17]}))


if __name__ == "__main__":
    main()
