"""Render recorded Tetris episodes to a GIF by zero-model replay (deterministic replay rendering, not a screen capture).

    uv run python scripts/tetris_render.py out.gif RUN/episode-00-s0-l1-p20 [RUN2/episode-00-s0-l1-p20 ...] [--fps 8]

Several episodes of the same case (for example the selected policy, a rejected candidate and the rules baseline)
are drawn side by side. Each panel's header shows the run's title, the elapsed game time, lines cleared and new
holes since the clip started, and whether a request is in flight.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "environments/tetris")]

from PIL import Image, ImageDraw  # noqa: E402

from baseline import features  # noqa: E402
from engine import NOOP  # noqa: E402
from executor import KeyExecutor, parse_answer  # noqa: E402
from render import render  # noqa: E402
from runner import FPS, make_env  # noqa: E402

BAR = 44


def panel(episode: Path, title: str | None, fps: int) -> list[Image.Image]:
    summary = json.loads((episode / "summary.json").read_text())
    case = summary["case"]
    rows = [json.loads(line) for line in (episode / "decisions.jsonl").read_text().splitlines()]
    deliveries = {r["delivery_frame"]: r for r in rows if r.get("delivery_frame") is not None}
    captures = {r["obs_frame"] for r in rows}
    title = title or f"{summary['provider']} {summary['mode']} {summary['slowdown']:g}x"
    env, executor = make_env(case["seed"], case["level"], case.get("prefix", 0)), KeyExecutor()
    lines0, holes0, frames, step, waiting = env.lines, features(env.board)[2], [], max(1, FPS // fps), False
    for frame in range(summary["frames"]):
        screen = render(env)
        executor.observe(screen)
        if frame in captures:
            waiting = True
        if frame in deliveries:
            row = deliveries[frame]
            if row["status"] != "invalid":
                executor.apply(parse_answer(row["answer"]), row["target"], frame)
            waiting = False
        if frame % step == 0:
            image = Image.fromarray(screen)
            bar = Image.new("RGB", (image.width, BAR), (24, 24, 34))
            d = ImageDraw.Draw(bar)
            d.text((6, 4), f"{title}  t={frame / FPS:5.1f}s  lines +{env.lines - lines0}  holes {features(env.board)[2] - holes0:+d}", fill=(230, 230, 240))
            d.text((6, 22), "waiting for answer (piece keeps falling)" if waiting else "keys pressed / next observation tick",
                   fill=(255, 200, 120) if waiting else (140, 255, 160))
            canvas = Image.new("RGB", (image.width, image.height + BAR))
            canvas.paste(bar, (0, 0))
            canvas.paste(image, (0, BAR))
            frames.append(canvas)
        env.step(executor.action() if not env.over else NOOP)
    if env.over:
        ImageDraw.Draw(frames[-1]).text((60, 250), "GAME OVER", fill=(255, 80, 80))
    return frames


def main():
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    p.add_argument("episodes", type=Path, nargs="+")
    p.add_argument("--title", action="append", default=[], help="one per episode, in order")
    p.add_argument("--fps", type=int, default=8)
    a = p.parse_args()
    panels = [panel(episode, a.title[i] if i < len(a.title) else None, a.fps) for i, episode in enumerate(a.episodes)]
    length = max(len(x) for x in panels)
    panels = [x + [x[-1]] * (length - len(x)) for x in panels]
    frames = []
    for row in zip(*panels):
        width = sum(f.width for f in row) + 8 * (len(row) - 1)
        canvas, x = Image.new("RGB", (width, row[0].height)), 0
        for f in row:
            canvas.paste(f, (x, 0))
            x += f.width + 8
        frames.append(canvas)
    frames[0].save(a.output, save_all=True, append_images=frames[1:], duration=int(1000 / a.fps), loop=0, optimize=True)
    print(f"{len(frames)} frames -> {a.output} ({a.output.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
