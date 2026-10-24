# Track the research, not just the best video

An evaluation record connects a hypothesis to a frozen configuration, model outputs, actual actions, and a decision. SOL generates prompt revisions and analyzes failures; humans supply preferences, inspect videos, and choose research constraints. The selected Asterix policy came from this human-guided autoresearch loop. Model weights are unchanged.

## Shared run records

New Asterix, Tetris, Touhou, Rhythm, Racing, Badminton, TableTennis and PCBA experiment
runs write `evaluation-record.json` with schema version 2. The shared fields are
`record_id`, `game`, `command`, `provider`, `clock`, `mode`, `status`, `summary` and
`evidence`. `provider` identifies actual subscription, API or rules decisions.
`clock` is `virtual`, `wall` or `none` (profiling without gameplay). The original
mode and game-specific results remain attached. PCBA stores aggregate metrics in
`summary.json` and links its full `report.json`, including raw calls and diagnostics,
through shared evidence. Historical files stay unchanged.

`completed` means the experiment finished, including a complete game loss.
`incomplete` means its result is partial or missing. `interrupted` identifies a
runner failure or interrupted execution. Game-owned acceptance gates still decide
whether an outcome qualifies as a verified result. Run initialization failures
are retained once an output directory exists.

`sol record RUN` appends the immutable record to `artifacts/GAME/evaluations.jsonl`.
`--registry PATH` selects another registry. Repeating the same registration is
idempotent. A changed record under the same ID is rejected. Supplying both
`--decision` and `--note` additionally appends a judgment to `assessments.jsonl`.

## Three different kinds of evidence

| Mode | What advances the game | What it proves |
|---|---|---|
| Profile simulation | A virtual clock with sampled historical response delays; computation may pause the environment | Closed-loop development under a specified delay model |
| Real-time subscription evaluation | A continuous wall clock, including actual model computation | Measured behavior with this subscription transport |
| Saved-action replay | Previously recorded actions; no model calls | Environment, screenshot and score integrity |

Fixed-screenshot preference tests measure agreement with annotated acceptable actions. They belong to development, and cannot establish game survival. Two observations from one event are correlated. A new response on an old screenshot is not an unseen-state test.

## Run and record

```bash
uv run sol simulate asterix --output runs/asterix-candidate-01
uv run sol record runs/asterix-candidate-01 --decision diagnostic \
  --note "Single development seed; inspect missed current-row pickups."

uv run sol eval asterix --output runs/asterix-realtime-01
uv run sol record runs/asterix-realtime-01 --decision retain \
  --note "Actual wall-clock trial completed; review score and lag before promotion."
```

Each directory contains `manifest.json` with the recipe and source hashes, `source_snapshot/`, the complete `task.txt`, issued requests and model public outputs, delivered actions, frame rewards/lives, `summary.json`, and `evaluation-record.json`. `assessments.jsonl` appends researcher decisions without replacing prior entries. Failures create `failure.json`; partial episodes stay interrupted and never become successful scores.

For each candidate, record:

1. **Hypothesis:** the concrete failure and expected behavior. Link a capture frame or video time.
2. **Change:** a prompt diff, output-format change, observation change, or scheduling change. Change one factor where practical.
3. **Conditions:** model/effort, prompt and system hashes, environment/source version, timing profile, seed, horizon, request capacity, and action-holding semantics.
4. **Evidence:** all attempted episodes, score, lives, elapsed game time, errors, observed latency and request drops. Compare at matching horizons; never extrapolate a short clip to a full game.
5. **Decision:** retain, reject, or diagnostic; explain the gate and remaining uncertainty. Freeze the candidate before confirmation and use fresh replies and additional seeds.

The agent may copy a recipe, edit its referenced prompt files, run the commands, inspect records, and append its conclusion. Do not change annotations to reward the candidate, pass evaluator truth or future delay draws to the actor, or delete losing runs to make a trend look better.

## Selected Asterix campaign

See [the research walkthrough](asterix-autoresearch.md), [machine-readable milestones](../research/asterix/evaluation-history.jsonl), and [selected raw records](../artifacts/asterix/serial-selected/). The walkthrough focuses on the route to the released configuration. Historical snapshots remain linked at a fixed source commit.

## Inspect a replay

With FFmpeg available, render the public English summaries next to verified game frames:

```bash
uv run python scripts/render_asterix_decisions.py \
  runs/asterix-development/seed-5 runs/asterix-development/replay.mp4 --music
uv run python scripts/audit_asterix_timing.py runs/asterix-development/seed-5
```

The video script verifies recorded rewards/lives and action identity, then optionally adds original quiet music and brightens only the game panel. It makes no model calls. Realtime renders say realtime replay; sampled-profile renders say profile simulation replay. The timing audit applies to simulation; realtime uses its actual delivery log.

## Touhou records and accounting


A result is useful when its input, condition, complete outcome and accounting can be checked. The selected Touhou case keeps historical records under `artifacts/touhou/` and writes a new `record.json` for every portable simulation or API episode.

## Run and register

```bash
# Real subscription answers; imposed API-like timing, not realtime acceptance.
uv run sol simulate touhou --seed 9 --output runs/touhou-dev-001

# Actual continuously advancing 1x game; explicit budget and process-only key.
uv run sol eval touhou --seed 1 --budget-usd 5 --max-calls 100 \
  --output runs/touhou-api-001

# Idempotent append. A changed record with the same ID is rejected.
uv run sol record runs/touhou-api-001 \
  --registry artifacts/touhou/evaluations.jsonl
```

The API command reads `OPENAI_API_KEY` from process memory or prompts without echo. There is no `--api-key` argument and no credential in snapshots. By default each API run has its own ledger and the stated budget applies to that ledger. `--ledger /path/to/shared-ledger.json --budget-usd N` explicitly makes N a **cumulative ledger cap**, not an additional allowance. Existing committed/inflight/unknown amounts count. Unknown usage stops admission until reconciled; do not erase the ledger or retry around it. Game failure does not cancel billing for losing or late responses.

Budget admission reserves conservative maximum fees for every in-flight request and settles actual usage afterward. The number of requests and the number of actions differ: a four-way race pays for all candidates but executes at most one response for that observation.

## Record contract

| Field | Meaning |
|---|---|
| `record_id` | Stable run identity; default is the unique output directory name |
| `provenance` | `historical_source_harness`, `previous_portable_release`, or fresh `package_cli` |
| `execution_mode` | Actual API, subscription/profile simulation, or saved-action replay |
| `seed`, `fanout`, summary language | Development/evaluation setup; include seen/held-out context in the note |
| `complete`, `integrity_verified`, `status` | A game loss differs from interrupted transport or incomplete accounting |
| `won`, `passed` | `won` describes boss defeat. `passed` additionally requires valid, continuous 1× API execution and completed accounting |
| `calls_issued`, `actions_applied` | All submitted decisions versus actually installed model plans |
| `latency` | Actual screenshot→action samples for realtime API only; not subscription wall time or simulated timing |
| `accounting` | Billed calls, settled costs, cumulative ledger commitment and unknown-usage state |
| `evidence` | Relative links to manifest, frozen requests, public responses, installed actions and original video |

`survived` with positive boss HP is not a defeat. A simulated win is not real-time acceptance. Replaying saved actions makes zero model calls and is labeled replay. An interrupted run is not silently scored as a game loss. Do not drop a complete failed run or replace old loss evidence with a successful video.

## Inspect a case

The Touhou runner rejects malformed or out-of-bounds actions and records them as invalid decisions; they are not applied to the game.

`episode/issued.jsonl` records each observation, image hashes and prompt hash. Each `decision_*` directory retains the exact PNGs, prompt and public JSON output. `episode/actions.jsonl` records the selected response, actual application clocks, keys, duration and same-response public summary. `episode/decisions.jsonl` includes stale/losing responses and their costs. `episode/final_state.json` is evaluator-only truth for offline replay; it is never given to the actor.

For the displayed summaries, verify that `brief` and `plan` match the same selected response. For timing, use `capture_to_apply_s` from actually applied actions; do not replace it with TTFT or average all race candidates. For acceptance, require 1× clock evidence, no pause/blur, terminal accounting, no unknown usage and `won=true`.

To publish a compact case, retain its audit and source hashes, put larger inputs/videos on the private evidence branch, and add a checksummed artifact entry. Keep original live capture separate from deterministic replay or a font-corrected re-render. Disclose postproduction such as adding BGM; the public summary is not an internal thought trace. The append operation preserves records; it does not audit arbitrary imported claims for you.

## Rhythm records

See [the workflow](rhythm.md) and [selected evaluation history](../research/rhythm/evaluation-history.jsonl). `sol simulate rhythm` makes fresh subscription decisions with imposed delay; `sol eval rhythm` uses actual advancing1x audio/API; `sol profile rhythm` is strictly serial and executes no actions. Every run has a source manifest and evaluation record. Native runs additionally retain immutable literal actions, sampled model inputs, continuous display frames, audio diagnostics and terminal accounting.

Register with `sol record RUN --registry artifacts/rhythm/evaluations.jsonl`. Append a research judgment separately with `--decision retain|reject|diagnostic --note TEXT`. Hypothesis, parent condition, changed factor, source/policy/chart hashes, observation cadence, request capacity, preview length, clock/calibration, all judgments, empty presses, latency and cost belong in the record. Registry IDs are immutable; assessments append. Near-perfect accuracy is distinct from full combo, and a historical source-harness run is distinct from a new portable-CLI run.

For a new Rhythm hypothesis,copy the recipe and set its`hypothesis` and`parent_record` fields before running. They are embedded in the manifest and evaluation record. Preserve the complete actual result even when its clock-integrity gate fails; mark that run diagnostic rather than overwriting it with a good source-harness clip. The selected walkthrough is intentionally a curated adopted lineage; it does not claim every historical trial was a matched comparison.
