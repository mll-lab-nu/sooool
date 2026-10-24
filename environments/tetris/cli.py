"""Command entrypoint: sol simulate|eval|replay tetris."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from runtime import experiment
from runtime.options import positive_float
from runtime.run_support import ROOT

PROVIDERS = ("claude", "subscription", "rules")


def parser():
    p = argparse.ArgumentParser(prog="sol <command> tetris")
    commands = p.add_subparsers(dest="command", required=True)
    for command in ("simulate", "eval"):
        child = commands.add_parser(command, prog=f"sol {command} tetris")
        child.add_argument("--output", type=Path)
        child.add_argument("--recipe", type=Path)
        child.add_argument("--seed", type=int, help="One episode from this seed instead of the recipe's episode list")
        child.add_argument("--level", type=int, default=None, help="Start level for --seed (default 1)")
        child.add_argument("--prefix", type=int, default=None, help="Pieces pre-placed by the rules baseline for --seed (default 0)")
        child.add_argument("--duration", type=positive_float, help="Episode length in game seconds")
        child.add_argument("--slowdown", type=positive_float, help="Game slowdown factor (>= 1; 1 = normal speed)")
        choices = PROVIDERS if command == "simulate" else PROVIDERS[:2]
        child.add_argument("--provider", choices=choices, default="claude",
                           help="Decision source (default claude): claude (stateless Claude Code CLI), subscription (ChatGPT via Codex)"
                                + (", rules (true-board baseline, simulate only)" if command == "simulate" else ""))
    replay = commands.add_parser("replay", prog="sol replay tetris", help="Zero-model replay check of a recorded run")
    replay.add_argument("run", type=Path)
    return p


def load_recipe(a):
    return json.loads((a.recipe or ROOT / "recipes/tetris.json").read_text())


def client_factory(recipe, provider, mode):
    if provider == "rules":
        from baseline import RulesActor
        return RulesActor
    if provider == "claude":
        from claude_cli import ClaudeCliClient
        settings = recipe.get("claude", {})
        return lambda output, system: ClaudeCliClient(output=output, system=system, model=settings.get("model", "opus"),
                                                      effort=settings.get("effort", "low"))
    from runtime.subscription import SubscriptionClient
    settings = recipe.get("subscription", {})
    os.environ["SOL_QUOTA_STOP_PERCENT"] = str(min(int(os.environ.get("SOL_QUOTA_STOP_PERCENT", "80")),
                                                 int(recipe["args"].get("quota_stop_percent", 80))))
    return lambda output, system: SubscriptionClient(output=output, system=system, effort=settings.get("effort", "low"),
                                                     service_tier=settings.get("service_tier"), prestart=bool(settings.get("prestart", False)))


def tetris(recipe, out, a):
    from runner import run_recipe
    mode = "realtime" if a.command == "eval" else "simulation"
    return run_recipe(ROOT, recipe, out, client_factory(recipe, a.provider, mode), mode, a.provider)


def run_replay(a):
    from runner import verify_replay
    manifest = json.loads((a.run / "manifest.json").read_text())
    results = [verify_replay(ROOT, manifest["recipe"], episode) for episode in sorted(a.run.glob("episode-*"))]
    print(json.dumps(results, indent=2))


def main(argv=None):
    p = parser()
    a = p.parse_args(argv)
    a.game = "tetris"
    if a.command == "replay":
        return run_replay(a)
    if (a.level is not None or a.prefix is not None) and a.seed is None:
        p.error("--level and --prefix require --seed")
    from runner import apply_overrides
    try:
        recipe = apply_overrides(load_recipe(a), a)
    except (ValueError, KeyError, TypeError) as exc:
        p.error(f"recipe: {exc}")
    mode = {"simulate": {"claude": "claude_with_simulated_profile", "subscription": "subscription_with_simulated_profile",
                         "rules": "rules_baseline_with_simulated_profile"},
            "eval": {"claude": "real_time_claude", "subscription": "real_time_subscription"}}[a.command][a.provider]
    out, result = experiment.execute(a, recipe, mode, tetris)
    print(json.dumps({"output": str(out), "aggregate": json.loads((out / "summary.json").read_text())["aggregate"]}, indent=2))


if __name__ == "__main__":
    main()
