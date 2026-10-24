"""Build the exact text an actor receives, in Asterix's form: prefix with measured delay statistics and the
request protocol, the policy, and the public output instructions. Per-request lines (observation frame, image
frames, applied placements with ages) are appended by the runner."""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

FPS = 60


def profile_delays(root: Path, recipe: dict) -> list[float]:
    delays = json.loads((root / recipe["profile"]).read_text())["capture_to_complete_seconds"]
    if not delays or any((not isinstance(d, (int, float))) or not math.isfinite(d) or d <= 0 for d in delays):
        raise ValueError("Profile must list positive finite capture-to-complete seconds")
    return [float(d) for d in delays]


def quantile(values: list[float], q: float) -> float:
    values = sorted(values)
    position = (len(values) - 1) * q
    lo, hi = math.floor(position), math.ceil(position)
    return values[lo] + (values[hi] - values[lo]) * (position - lo)


def read(root: Path, recipe: dict, key: str) -> str:
    return (root / recipe[key]).read_text()


def build_task(root: Path, recipe: dict, mode: str) -> tuple[str, str]:
    """Return (system, task). ``task`` is the fixed text of every request; the runner appends the observation lines."""
    if mode not in ("simulation", "realtime"):
        raise ValueError(mode)
    args = recipe["args"]
    slowdown = float(args.get("slowdown", 1))
    stride, window = int(args["observation_stride_frames"]), int(args["observation_window"])
    delays = [d / slowdown for d in profile_delays(root, recipe)]  # game seconds
    prefix = read(root, recipe, "task_prefix").format(
        slowdown_clause="" if slowdown == 1 else f", {slowdown:g} times slower than normal speed",
        window_frames=stride * (window - 1), mid_age=stride * 2, stride=stride,
        mean_ms=statistics.mean(delays) * 1000, median_ms=statistics.median(delays) * 1000, p95_ms=quantile(delays, 0.95) * 1000)
    if mode == "realtime":
        prefix = prefix.replace("The virtual game advances", "The real-time game advances continuously")
        prefix = prefix.replace("available only after a sampled complete response delay.",
                                "available when your actual response completes; the game keeps advancing while you compute.")
        prefix = prefix.replace("Native computation wall time does not advance this simulation.",
                                "Actual computation wall time DOES advance this real-time game.")
        prefix = prefix.replace("Measured previous complete-response delay:",
                                "Historical context only; live latency is measured in this run. Previous delay:")
    task = prefix + read(root, recipe, "prompt").strip() + "\n"
    memory = read(root, recipe, "memory").strip()
    if memory and not memory.startswith("("):
        task += "\n## Policy memory (notes kept from earlier practice)\n" + memory + "\n"
    task += "\n" + read(root, recipe, "output_instructions")
    return read(root, recipe, "system").strip(), task


def request_text(task: str, frame: int, image_frames: list[int], applied: list[dict]) -> str:
    """Asterix's per-request lines: current frame, image frames, applied commands with ages in frames."""
    history = ",".join(f"{frame - row['frame']}:{row['piece']}/rot{row['rot']}/col{row['col']}"
                       for row in applied[-8:] if row.get("status") == "applied")
    return (task + f"Current observation frame: {frame}. Image frames: {image_frames}.\n"
            f"Applied placements, oldest first, age_in_frames:piece/rot/col: {history or 'none yet'}.\n")
