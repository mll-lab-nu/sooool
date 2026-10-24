# Real-time evaluation

## Badminton: actual realtime API at S3

`sol eval badminton --budget-usd 15 --ledger outputs/badminton-budget.json --output outputs/badminton-api101`
runs one L1, seed-101 native match. It uses one serial `gpt-6.1-sol / low / ultrafast`
request and a continuously advancing S3 clock. S3 means 3× slowdown: one game second takes three wall seconds. Camera control and native stroke
planning run off the physics process. Limits, preparation timing, public English
summaries and verified replay video are described in [Badminton](badminton.md).
Run `sol preflight badminton` with an explicit output directory before paid use. The latest retained goal-v2 API match completed 8:11 with 90/97 legal returns and matching native replay. It predates the latest public-input acknowledgement filter correction; [the evidence record](../artifacts/badminton/realtime-rerun-005.json) identifies the exact run conditions.

## Asterix

```bash
uv run sol eval asterix --seed 5 --duration 20 --output runs/asterix-realtime
```

This uses actual ChatGPT subscription inference and a continuously advancing 12-raw-FPS clock (5× slowdown). One request is in flight; complete model actions are held unchanged until replaced. Game time continues while the model computes. There is no automatic hop release, neutral landing or row-based filtering. A completed response is applied on the next game tick; the next observation is captured at the next four-frame observation tick.

`sol simulate asterix` uses the same policy/action semantics but samples a historical API delay profile and pauses native computation outside virtual game time. The historical 500-point demonstration is profile development evidence. The realtime command measures subscription latency and game performance; it is not a paid ultrafast API calibration or native-speed result.

Each trial retains the exact task, model public output, capture frame, delivery frame, actual capture-to-apply duration, frame lag, applied action, rewards/lives, source snapshot and evaluation record. Interrupted calls preserve partial artifacts; authentication failures cannot fall back to paid API. The default quota stop is 80%. Record retain/reject decisions with `sol record`; see [the recording protocol](evaluation-records.md).

### Explicit paid API trial at 12 FPS

```bash
# Example only: obtain authorization for the new USD cap before running.
# Key comes from OPENAI_API_KEY or hidden terminal input, never arguments.
uv run sol eval asterix --provider api --seed 5 --wall-seconds 60 \
  --budget-usd 5 --max-calls 100 --output runs/asterix-api-60s
uv run python scripts/render_asterix_decisions.py \
  runs/asterix-api-60s/seed-5 runs/asterix-api-60s/replay.mp4 --music
```

This explicit transport uses `gpt-6.1-sol / low / ultrafast`, three past screenshots,
V28 and the same unchanged held actions. It has one in-flight request. A complete,
schema-valid action and public English summary apply at the next 12-FPS tick;
stream termination and billing settlement finish before another request is admitted.
The game keeps advancing during both phases. The API path uses the task directly,
without the Codex coding wrapper. `--wall-seconds 60` means 720 raw frames / 12
game seconds; `--duration 60` instead means 3,600 frames / 300 actual seconds.

Each run has a persistent capped ledger unless `--ledger` explicitly selects a
shared cumulative ledger. The shared Responses client reserves conservative
costs before sending, settles terminal usage, verifies model/tier, and blocks
admission on unknown accounting. Interrupted runs retain all evidence and cannot
be promoted to successful API evaluations. Reused API/accounting source files
are included in the frozen manifest. Fresh paid validation completed twice with seed 5 at 12 raw FPS: **50 points/one life**
and **300 points/two lives**, each over 720 frames / 60 wall seconds (12 game seconds).
The two games made 25 and 31 API calls, all settled, costing US$0.8909508 and
US$1.1090868 from reported usage. Legal-action latency medians were 1.598s and
1.487s, with maxima of 8.590s and 2.747s. These are two trials, not a win-rate estimate.
[Inputs, outputs, frozen source, accounting and run records](../artifacts/asterix/api-validation/20261017/README.md)
include both outcomes; the README now shows the repeat run.

The earlier interrupted attempt and its blocked ledger remain unchanged, with
unknown actual cost conservatively reserved at US$0.27747. After explicit retry
authorization, the new shared ledger was capped at US$9.72253, deducting that old
reservation from the original US$10 total. The probe, 10-input serial profile and
both games have 67 settled requests, totaling US$2.1357948; including the old
reservation, cumulative commitment is US$2.4132648. No unknown charge was released.
[Earlier failure evidence](../artifacts/asterix/api-validation/20261016/) remains retained.
A rendered replay reconstructs saved actions and checks every reward/life; it is
not an original screen recording. Its added music and game-panel color adjustment
are recorded in [video provenance](../assets/asterix/v28-api-60s.provenance.json).

## Tetris

```bash
uv run sol eval tetris --provider claude --output runs/tetris-realtime
```

Stateless Claude Code CLI decisions on a continuously advancing clock at the recipe's 2× slowdown; one request in
flight; a late answer is discarded. [Run and record](tetris.md).

## Touhou: actual realtime API evaluation

The selected Touhou path is implemented in the portable CLI. Offline/browser contracts are checked; a fresh paid full-game run of this entrypoint is pending at the user’s request. Historical source-harness API wins are retained separately.

```bash
uv run sol eval touhou --seed 1 --budget-usd 5 --max-calls 100 \
  --output runs/touhou-api-001
```

The default recipe uses `gpt-6.1-sol / low`, actual API streaming, a four-way first-complete-legal race, four in-flight slots, three past screenshots, native English public summaries and the original 1× game engine. The race gives each observation multiple chances to produce a legal plan before its deadline; it is one of the [latency-aware control mechanisms](latency-aware-learning.md), distinct from staggered observation pipelines. Every selected key and duration comes from GPT. The game advances throughout inference. `--budget-usd` is required; an existing shared ledger must be explicitly selected with `--ledger` and counts toward that cumulative cap.

`sol simulate touhou` uses a ChatGPT subscription and modeled profile timing. It rejects API recipes rather than falling back to a paid provider. `sol profile touhou --episode RUN/episode ...` makes strictly serial API requests on deduplicated frozen inputs; returned actions are not executed. These commands measure different conditions.

Real-time acceptance requires boss defeat, completed terminal accounting, actual 1× clock evidence and no pause/blur. `record.json`, the manifest, immutable inputs, responses, applied-action log, evaluator-only final state and original live video form the evidence chain. [Record requirements](evaluation-records.md) describe how to append outcomes without erasing failures. [The case study](touhou-research-record.md) distinguishes historical source-harness runs from new portable CLI validation.

An early legal JSON response can be applied while its terminal event is pending. This does not free its concurrency slot or fee reservation. All losing/stale responses must drain, validate and settle. Missing usage or unknown cost blocks new admission until reconciliation. Readiness/terminal/transport times are distinct; TTFT is not action latency.

The current policy accepts only short public summaries, not internal reasoning traces. A summary and action are displayed atomically from the same selected response. The display panel is outside the actor's observation. Postprocessed videos must retain their original timing and label added audio or rendering changes.

## Rhythm: model-owned absolute tap times

`sol eval rhythm --budget-usd 5 --max-calls 90 --output runs/rhythm-api-001`
uses the selected v21 policy and a continuously advancing browser/audio clock.
GPT chooses each key and absolute tap timestamp in the executor’s monotonic
clock domain. The executor preserves those timestamps and handles timed key
delivery; it does not calculate tap times from note coordinates.

The selected native API episode achieved 24 Perfect, 1 Great and zero Miss over
a 17-second preview at 1× audio speed, with 2.5s visual approach. Two empty
presses broke the combo. See [the current workflow](rhythm.md) for commands,
calibration, budgets and portability limits, and [the case study](rhythm-autoresearch.md)
for the selected experiment. Historical and fresh runs retain separate records.

## Racing

Racing retains its selected-policy path: `sol eval racing` uses real API decisions while original-speed physics advances. It requires an existing capped ledger and a process-only credential. See [Racing setup, profiling and evaluation](racing.md). The selected historical seed304 result remains separate from this Asterix release and its subscription checks.

Protocol reference: [OpenAI Docs — Codex app-server](https://learn.chatgpt.com/docs/app-server).
