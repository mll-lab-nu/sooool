# Rhythm: develop in simulation, evaluate against the real clock

The default is the selected v21 literal-time policy, 25 notes over the complete
17-second **preview excerpt**, not the complete commercial song. Music runs at
1x. Notes have 2.5s of visual approach. The policy sees 390x844 pixels; default
API observations are 200ms apart with at most 16 requests in flight.

## Run

```bash
bash scripts/fetch-latency.sh
uv sync --locked --python 3.12
uv run playwright install --with-deps chromium
codex login
uv run sol doctor --game rhythm --auth
uv run sol simulate rhythm --seed 20261016 --output runs/rhythm-dev-001
```

Simulation makes new subscription-model decisions. `--seed` selects the delay
sampling sequence; the recipe retains a fixed chart, so changing this seed
does not create a new chart. It imposes the retained
joint distribution of API action-readiness, image age, transport and terminal
request occupancy. A 50ms content/timestamp displacement is explicitly injected
to represent the diagnosed screenshot delay; its future draws stay private.
Model computation may pause virtual time. It is development evidence, not a
real-time result. No paid API fallback exists.

```bash
# Original public fixtures, sequential requests; no keys are executed.
uv run sol profile rhythm --episode artifacts/rhythm/selected \
  --budget-usd 1 --max-calls 20 --output runs/rhythm-profile-001

# Continuously advancing browser and original audio; real streamed API calls.
uv run sol eval rhythm --budget-usd 5 --max-calls 90 \
  --output runs/rhythm-api-001
```

The API key is read from `OPENAI_API_KEY` or prompted without echo. The bundled
preview and chart are the exact selected experiment inputs; `--audio` accepts
an explicitly supplied local replacement. A replacement soundtrack does not
imply the chart matches it. `--browser-executable` selects an installed browser.
A duration override must match the recipe/chart; use a separate recipe and
chart for different horizons. A low max-calls budget can cause missed notes;
the environment continues while admission stops.

The default budget belongs to that output. `--ledger /absolute/shared.json`
uses a cumulative shared budget with an exactly matching cap; reservations,
unknown usage and previous charges count. All symlinks resolve to one canonical
ledger lock. The selected experiment's enforced ceiling is USD 80. No key,
account notification or credential file is committed with a run.

## State and action

The actor receives screenshots and public capture timestamps, an external
monotonic clock, pending literal plans, the last 2 raw receipts, recent observed
RTTs, request version and the frozen model-authored memory. Public calibration
states receptor y=717 and speed 0.2404px/ms. The memory says image timestamps
are approximately 50ms later than their content; GPT must account for this in
its output. The formula in the frozen memory is guidance for GPT, not a program
that the executor evaluates. It never receives chart notes, audio-clock truth
or future delays. See [the frozen policy notes](../policies/rhythm/v21/README.md).

```json
{"v":2,"a":[["k18","k",4804,4954]]}
{"comment":"A visible K note is scheduled from its position and capture time."}
```

This illustrates the actual wire schema; the comment is a public short
explanation, not private reasoning. Keys, IDs, times and expiries come from GPT.
The validated first JSON object dispatches immediately; commentary and stream
accounting continue afterward. The executor preserves the numbers, validates
syntax and handles immutable IDs. It does not detect notes, choose keys,
compute arrival, snap to beats, repair times or merge different IDs by proximity.
Internal reasoning remains allowed at low effort. The adapter is not a policy.

## Freeze, inspect, record

Each run freezes engine/policy/recipe/profile sources in `manifest.json` and
`source_snapshot/`; native runs also verify `native-freeze.json` before and
after play. Native details are in `model-timing/episode/result.json` and
`requests.jsonl`. Original continuous compositor PNGs are retained independently
of the model observation rate. `summary.json`, `accounting.json` and
`evaluation-record.json` connect conditions, judgments and terminal charges.

```bash
uv run sol record runs/rhythm-api-001 --registry artifacts/rhythm/evaluations.jsonl
uv run sol record runs/rhythm-api-001 --decision diagnostic \
  --note "Inspect startup GO frame and upper slanted-lane identity."
```

Registry append is idempotent and rejects changed evidence under the same ID.
Assessments append separately; keep unsuccessful runs. Compare all 25 judgments,
weighted accuracy, misses, empty presses, max combo, readiness distribution and
cost. `complete` means the full chart was evaluated. Strict full-combo `passed`
is stronger: the selected historical run has 98.8% accuracy and zero misses,
but two empty presses, so it **does not pass full combo**. It also does not
establish three consecutive full-length successes.

Render with the retained game observations and original same-response comments:

```bash
cd environments/rhythm
python -m experiments.rhythm.render_decision_replay \
  --run-dir /absolute/runs/rhythm-api-001/model-timing/episode \
  --audio dist/assets/preview-17s.m4a --language en \
  --frame-content-lag-ms 50 --tail-seconds 2 --output /absolute/rhythm-video
```

The renderer uses stable audio diagnostics and records its presentation-only
content-time offset. Audio is remuxed from the source file; the result is not a
microphone recording. Actions and judgments remain unchanged.

[Selected research path](rhythm-autoresearch.md) · [Evaluation history](../research/rhythm/evaluation-history.jsonl)

## Portability limits

The packaged subscription simulation has a fresh 25/25 Perfect result. The new local API migration check completed and settled its calls, but its 0.69s clock drift failed the real-time integrity gate and did not reproduce the selected Ubuntu score. See [validation](validation.md) for the full failed outcome. Use a suitable browser/host and inspect clock diagnostics; a successful HTTP call or simulation score alone does not establish timing performance.
