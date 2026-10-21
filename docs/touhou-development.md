# Develop the Touhou policy

The task-policy training loop is: measure the API condition, practice with subscription calls under an explicit delay model, inspect failures, refine the strategy, freeze a candidate, then run actual realtime API evaluation. Repeated practice on a fixed encounter is intentional; track transfer to unseen conditions separately. Base-model weights remain frozen. See [latency-aware learning and control](latency-aware-learning.md). [The case study](touhou-research-record.md) follows the selected early v2 checkpoint through that loop.

## Install and inspect the environment

```bash
bash scripts/fetch-latency.sh
uv sync --locked --python 3.12
uv run playwright install --with-deps chromium
uv run sol doctor --game touhou
(cd environments/touhou && npm test)
```

Install Noto CJK fonts when the browser lacks Japanese/Chinese glyphs, e.g. `fonts-noto-cjk` on Ubuntu. A Chromium-compatible Linux system is required. Gym and browser physics share the same engine; changing the renderer or adding a public-summary panel does not change collision hitboxes. The panel is outside the actor's 640×480 observation.

## Profile with the API, strictly serially

Use retained task inputs from a real episode to preserve the complete game prompt, screenshots and JSON schema:

```bash
uv run sol profile touhou --episode runs/touhou-api-001/episode \
  --budget-usd 2 --max-calls 21 --output runs/touhou-profile-001
```

The command validates input hashes, deduplicates same-observation race inputs, waits for each response's terminal accounting before starting the next request, and executes no returned actions. It retains legal-JSON readiness, complete response timing, token/cache usage and cost. Small smoke runs do not estimate a tail. Vary observations and retain image-count strata; identical-image cache loops are not a substitute for changing-game profiling.

A serial readiness marginal is not a concurrent winner distribution. The default simulator selects `profile-control-tracking-safe-intercept-v2-transport-v1.json`, a **modeled** condition that transports selected-task serial timing into historical four-candidate readiness/terminal cohorts. The earlier fixed-case comparisons used `profile-control-early-study-v1.json`; their results retain that original condition. Preserve the joint vectors and occupancy tail. If experimenting with independent delays instead, label it as a stress assumption rather than fresh concurrent calibration. Do not feed a sampled future delay to the actor.

## Iterate with the subscription

```bash
codex login
uv run sol simulate touhou --seed 9 --output runs/touhou-dev-001
uv run sol record runs/touhou-dev-001
```

These are real subscription model decisions. The simulator schedules their application using the profile; if model computation is slower, virtual game time waits at the delivery event. A subscription episode may take several wall minutes for one game minute. No paid API fallback is permitted.

Start each candidate in an isolated Git worktree. Keep the selected baseline immutable, add a named strategy and recipe, and write the hypothesis before collecting answers. Use recorded failures to create cases for different skills: current-player recognition, small tracking, anticipating a turn, judging an approaching versus receding bullet, choosing a corridor, surviving the stopped interval, and preventive bomb timing. Human demonstration and review are inputs to research; keep them labeled.

The retained tracking benchmark source is under `environments/touhou/research/tracking_*`. Private replay prefixes and evaluator labels belong outside model input. The optional `development-cases.tar.gz` evidence archive retains the historical case corpus; original machine paths in these research helpers are not a second portable launcher. Use the canonical CLI for complete fresh episodes.

For case selection, score ordinary shot damage separately from bomb damage and check hits/deaths/resources first. Do not change the Gym reward, install a coded pursuit/dodge policy, pass future human controls, or call “move” inherently correct. Retain rejected candidates and fixed scoring boundaries. Whole episodes test a different failure mode than short windows.

## Freeze, evaluate, record

```bash
uv run sol eval touhou --seed 1 --budget-usd 5 --max-calls 100 \
  --output runs/touhou-api-001
uv run sol record runs/touhou-api-001
```

This path uses actual response delay, first-legal race arbitration, 1× browser clocks and no inference-time pause. Complete public `brief` and `plan` fields apply together. Losing requests still drain and bill. The v2 default is native English; this is a public decision summary, not a hidden chain-of-thought transcript.

Only a verified boss defeat is accepted. Surviving 60s, partial episodes, cached action replay, and wins under slower or modeled time are recorded separately. Keep development seed 1 labeled as seen; a single demo win is not a held-out success rate. See [evaluation records](evaluation-records.md) for evidence and accounting requirements.
