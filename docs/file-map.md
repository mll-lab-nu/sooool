# Read the core first

Use the root README, environment registry and recipes as the runnable interface.
`runtime/cli.py` dispatches commands through `runtime/envs.py`. Each game owns its runner.
`runtime/run_support.py` owns shared HTTP serving and source snapshots. Environment READMEs describe their manual/native setup; retained research snapshots keep historical commands and absolute paths for provenance. [Current results and conditions](results.md) identifies the active policy and evidence for all six games.

| Purpose | Files |
|---|---|
| Command dispatch and run snapshots | [`runtime/cli.py`](../runtime/cli.py), [`runtime/envs.py`](../runtime/envs.py), [`runtime/run_support.py`](../runtime/run_support.py) |
| Native SOL subscription transport | [`runtime/subscription.py`](../runtime/subscription.py) |
| Exact default conditions | [`recipes/`](../recipes/) and [`policies/`](../policies/) |
| Profile semantics and sample sources | [`profiles/README.md`](../profiles/README.md), [`timing.md`](timing.md) |
| Actor/evaluator separation | [`observation-contract.md`](observation-contract.md) |
| Large evidence retrieval and checksums | [`scripts/fetch_artifacts.py`](../scripts/fetch_artifacts.py), [`artifacts/index.jsonl`](../artifacts/index.jsonl) |

## Rhythm

Start with [`rhythm.md`](rhythm.md), `runtime/rhythm.py`, `recipes/rhythm.json`
and [the frozen policy and calibration](../policies/rhythm/v21/README.md). The simulator's causal event loop is
`environments/rhythm/experiments/rhythm/model_joint_training.py`; `model_native.py`
is the continuous API runner; `model_env.py` supplies public pixels/clocks.
`model_lean_policy.py` validates the selected action format and
`dist/model-executor.js` executes model literal times. `scheduler.py` now
contains accounting only. The trusted evaluator owns chart/audio diagnostics.
[The selected iteration record](rhythm-autoresearch.md) links raw evidence.
Inactive cropped/sparse timing controllers and machine-specific SSH workers
have been removed from the active tree.

## Touhou

Start with `environments/touhou/research/run_episode.py`, `scheduler.py`, `policies.py`, `control_delays.py`, and `environment.py`. `tracking_benchmark.py` and `tracking_summary.py` are the original delayed-branch scoring and selection pipeline. `dist/engine.mjs` is the deterministic game; `dist/app.mjs` owns browser presentation and the control bridge. `python/touhou_gym` is the structured Gym API, not the SOL actor input.

## Asterix

Start with `environments/asterix/runner.py` (one shared serial development/evaluation loop), `direct_action_transport.py` (unchanged model commands), `simulate_5x.py` (pixels, clock quantization and replay), and `policies/asterix/v28/` (exact strategy, timing preamble and public output format). `sol simulate asterix` uses virtual sampled delay; `sol eval asterix` uses actual wall time. `runtime/evaluation.py` writes run records and appended researcher assessments. `docs/asterix-autoresearch.md` and `research/asterix/evaluation-history.jsonl` explain the selected path; inactive source lives at a fixed historical commit.

## Tetris

Start with [`tetris.md`](tetris.md), `environments/tetris/runner.py` (one serial placement loop for simulation, real-time evaluation, rules baselines, recipe validation and zero-model replay), `engine.py` and `render.py` (the game and its public screen), `executor.py` (key scripts computed from the answer alone, public spawn detection, stale rule), `task.py` (exact actor text with the profile delay statement), `claude_cli.py` (stateless Claude Code CLI transport), `cli.py`/`scripts/tetris.py` (`sol simulate|eval|profile|replay tetris`), `policies/tetris/v11-short/` (selected) and `v12c-tradeoff/` (rejected), `recipes/tetris.json`/`tetris-1x.json` and `profiles/tetris/`. `baseline.py` is the evaluator-side rules comparison; `scripts/tetris_render.py` renders side-by-side replay GIFs. `artifacts/tetris/` holds the registry and the selected run's replayable decisions.

## Racing

Start with [`racing.md`](racing.md), [`scripts/racing.py`](../scripts/racing.py), [`recipes/racing.json`](../recipes/racing.json), and [`policies/racing/lane-commit-v14`](../policies/racing/lane-commit-v14/). `environments/racing/run.py` owns causal simulation and subscription/API transport; `live.py` owns continuous HTTP evaluation; `lane.py` is the coded visual tracker; `live_explained.py` adds the separately evaluated public-summary output. The iteration record is `research/racing/EVALUATION.md`. External roboolympics supplies the read-only game engine. Duplicate active Racing snapshots have been replaced by redirects.

## PingPong tactical control

The current PingPong entrypoint is [`scripts/tabletennis.py`](../scripts/tabletennis.py),
with physics/planning in `environments/tabletennis/execution.py`, camera-based
tactics in `environments/tabletennis/tactics.py`, four-worker scheduling in
`runner.py` and dual-view export in `replay.py`. Start with
[`tabletennis.md`](tabletennis.md) and [`artifacts/tabletennis`](../artifacts/tabletennis/README.md).

## PCBA test cell

Start with [`pcba.md`](pcba.md), [`pcba-loop.md`](pcba-loop.md) and the README section
[PCBA test cell](../README.md#pcba-test-cell-belt-to-magazine). [`scripts/pcba.py`](../scripts/pcba.py)
dispatches every command. In `environments/pcba/pcba_gym`: `scene.py`/`loop.py` build the
cell and belt, `environment.py` owns physics, devices and scoring, `runner.py` validates
literal actions, `pipeline.py` runs the guarded concurrent pipeline, `simulate.py` the
virtual-clock simulator, and `showcase.py`/`showcase_scene.py`/`showcase_art.py` the
render-only showcase video, and `showcase_figures.py` the README step close-ups,
model-input GIF and pipeline timeline. Prompts are in `policies/pcba`, the delay profile in
`profiles/pcba`, records in `artifacts/pcba`.

## Ignore on first pass

Full discussion tool traces, all historical profiles, old transport probes, legacy policy variants and offline case truth are not needed to run a frozen policy. Retained evidence documents the selected policies and subsequent development. PingPong snapshots under `research/in-progress` are historical source records with their own high-level/direct-action and slowdown conditions; the active release uses the tactical controller linked above. Racing uses the selected workflow linked above.
