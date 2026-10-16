# Racing: develop in simulation, evaluate in real time

SOL iterates a driving policy against a moving environment, using serial API latency measurements to make subscription development reflect delayed decisions. The selected checkpoint is **lane-commit-v14**, an early hybrid policy with a verified Level 1 real-time API match win. It is the policy behind the featured video, not the latest development checkpoint or a claim that every Racing configuration is solved.

Read the [iteration and evaluation record](../research/racing/EVALUATION.md), [exact task prompt](../policies/racing/lane-commit-v14/prompt.txt), and [actual API input/output example](../policies/racing/lane-commit-v14/example/). The model remains in the loop throughout each race.

## Policy and control boundary

Every 0.6 seconds the runner attempts a new request, with two recent legal front-camera observations, own telemetry, referee feedback, and pixel-derived road/obstacle measurements. Up to eight requests may be pending; responses arrive after model latency. GPT returns `[[target_speed, lane_offset_left_m, lookahead_m]]`. Positive offset is left of the yellow stripe, not left of the car. Goals expire three game seconds after their observation; obsolete responses cannot overwrite newer goals.

A **coded visual controller** reads fresh frames at 5 Hz, fits the yellow stripe, follows GPT's selected offset using pure pursuit, and reduces speed on high curvature. GPT chooses lane, target speed, lookahead, obstacle maneuvers and recovery. Code supplies continuous steering, including on frames GPT never sees. This is substantial hybrid control, not direct GPT steering or just action holding. Fixed-goal baselines can also win some matches; GPT necessity is not established.

The optional video variant adds a short public English `decision_summary` before the same goal in the same API response. This is an output-format change and is evaluated separately. The right panel is the model's actual returned explanation, not hidden reasoning or post-hoc commentary.

## Setup

Use a separate Python 3.12 environment for Racing and a read-only checkout of the original environment. Do not modify or submit our policy to the environment repository.

```bash
git clone https://github.com/CHIGUI0/roboolympics /tmp/racing-environment
git -C /tmp/racing-environment checkout da1f787f775ea6524d698c0b063157ded4c0fef9
python3.12 -m venv /tmp/sol-racing-venv
/tmp/sol-racing-venv/bin/pip install -r environments/racing/requirements.txt
export RACING_ENV_ROOT=/tmp/racing-environment
export MUJOCO_GL=egl LP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
```

`RACING_ENV_ROOT` must contain `core/episode.py` and the Racing plugin. MuJoCo needs a working EGL driver. The original paid run used Python 3.13/MuJoCo 3.3.7; local replay used Python 3.12/MuJoCo 3.3.7 and matched the exact trajectory hash. Dependency relocation is a new execution condition, not a new paid success claim.

## Develop without paid API calls

Sign in to Codex with a ChatGPT subscription. `RACING_CODEX_BINARY` selects the native executable and `CODEX_HOME` an existing login directory. Authentication is copied only into a private temporary runtime directory and removed when the client closes; nothing enters the repository. Requested settings are SOL/low/ultrafast with the minimal outer prompt; actual subscription tier is unverified. The current adapter sends `localImage detail=auto`.

```bash
/tmp/sol-racing-venv/bin/python scripts/racing.py simulate \
  --output runs/racing-lane-commit-dev101 --seed 101 \
  --hypothesis 'Replicate lane commitment with measured API response delays'
```

The virtual simulator samples the retained serial API delay distribution. A computed response stays unavailable until its scheduled virtual delivery. If subscription computation is slower, the simulator waits at that event rather than advancing the world using a future answer. Real subscription computation time and virtual game time are recorded separately. Three worker threads are the selected development setting; this is not the API profile's concurrency and does not prove the same latency at higher load.

The retained 32-call distribution measured a **one-frame direct-steering workload**. Using it for lane goals/history-two is an explicit proxy timing condition. Preserve it for historical comparisons; profile the exact new workload before claiming calibrated transfer. Image inputs were omitted by the historical subscription adapter, although numeric camera measurements were present. Historical 3/3 groups are therefore numeric-feature hybrid evidence, not valid visual-subscription replication. Current image transport is corrected; a new successful subscription group has not been established by this packaging change.

For the free HTTP/controller check, use `scripts/racing.py preflight --output runs/racing-free --seed 304`. This uses fixed grid-based goals with artificial delays, **zero GPT calls** and canonical player mode `oracle` to bypass model metering. It is plumbing/baseline validation, never model acceptance.

## Profile serially, then evaluate with real API decisions

Paid commands require an explicitly initialized cumulative ledger and stage ceiling. They prompt for a process-only key. Never reset an existing ledger to manufacture fresh budget. The copied accounting uses historical conservative price caps; recheck pricing before a new paid campaign. No paid calls are needed to inspect this release.

```bash
# Creates a NEW ledger exclusively; refuses to replace any existing file.
/tmp/sol-racing-venv/bin/python scripts/racing.py budget \
  --budget-ledger runs/racing-budget.json --total-cap-usd 30

# Actual paid profiling; concurrency ONE, including stream drain/accounting.
# --samples-dir may select recorded development inputs for a representative workload.
/tmp/sol-racing-venv/bin/python scripts/racing.py profile \
  --output runs/racing-serial-profile --calls 16 \
  --budget-ledger runs/racing-budget.json --stage-cap-usd 2

# Actual paid 1x evaluation; no imposed latency and no pause during decisions.
/tmp/sol-racing-venv/bin/python scripts/racing.py eval \
  --output runs/racing-api304 --seed 304 \
  --budget-ledger runs/racing-budget.json --stage-cap-usd 10

# Same-response public English summary, as used by the featured video.
# Add --summaries to the eval command for this separately evaluated variant.
```

The profile default repeats the packaged real API example; use representative samples rather than claiming broad latency coverage from this one state. A new profile is saved separately; changing the simulation profile requires an explicit recipe edit and new source hashes.

API evaluation uses the environment's original HTTP service and metering proxy pointed at `api.openai.com`, at 1x wall-clock physics. The streaming client publishes a complete validated goal once the returned model/tier are verified, then drains and accounts for the full response. Partial numbers are never actions. A changed final response or later error invalidates the evaluation. API profiling itself remains serial. The shared ledger reserves all outstanding requests and conservatively charges uncertain failures.

`python -m runtime.cli simulate racing ...` and `python -m runtime.cli eval racing ...` delegate to the same entrypoint. Use the Racing virtual environment for these commands. Racing is an external-environment integration, not an engine bundled by `uv sync`.

## Evaluation records and video

Each new run preserves `manifest.json` (hypothesis, recipe, policy/profile/environment source hashes), exact inputs/outputs, issued requests, installed controls, episode log, summary and `evaluation_record.json`. Only completed runs with successful independent replay enter a win/loss comparison. Missing/error/interrupted records remain unverified with `won: null`; losses are retained. Use `record --output <run> --record-mode eval` to rebuild a compact record from existing results; this is an index operation, not a new evaluation.

The [record-writing guide](../research/racing/RECORDS.md) defines comparison and promotion gates. Historical compact records live in [research/racing/evidence](../research/racing/evidence/); original run IDs and hashes remain intact.

[Watch/download the featured seed304 video](../artifacts/videos/racing-seed304-win-loss-win.mp4). It is a verified trajectory replay of real API gameplay, 1920×1080/20 fps, at original game speed. Review waits are omitted. The original heat order was loss/win/win; the presentation is edited to **win/loss/win (original heats 2/1/3)** and labeled on every frame. Original clock, score and response text are retained. A quiet original electronic instrumental was composed procedurally and added in post-production; encoded video packets are unchanged (see the music audit). Video ordering and soundtrack are never evaluation results.

![Selected Racing run](../policies/racing/lane-commit-v14/preview.png)

Level 2–4, duel, multi-car race, strict direct-actuator control, and official Harbor isolation are outside these acceptance claims.
