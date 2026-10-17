# PingPong: table tennis tactical control

GPT-6.1 Sol selects a persistent return-placement policy from public images,
public feedback and a camera-derived opponent-position estimate. A rule player
owns stereo tracking, contact prediction, serving and joint execution. This is
hierarchical tactical control; the model does not generate the 100 Hz joint rows.

## Continuous execution

The native physics owner advances at a 10 ms target period, scheduled from the
previous actual tick. It never waits for perception, rendering, planning or model
responses, and never compensates a late tick with accelerated catch-up steps.
Two native planning processes prepare and rehearse trajectories on robot-only
copies. Installation requires the exact prepared frame and matching command
anchor. A newer observation suppresses an older pending calibration. Public
camera sheets arrive at up to 20 Hz; the reference controller also runs at 20 Hz.

The return solver jointly screens paddle face and normal speed using the public
contact law and flight prior. Candidates aim at the selected placement and screen
for a 10 cm net margin. A geometric fallback retains its explicit provenance.
The rail supplies part of the forward stroke velocity (65% of requested y speed,
capped at 0.85 m/s); the arm supplies the remainder. Native joint range, velocity
and acceleration checks and the unchanged physical servo constrain execution.
After a short follow-through the arm returns to a forward-tilted receiving pose,
rather than unwinding its face to the flat initial pose after every shot.

The planner uses existing native IK/trajectory helpers, lazily computes table
avoidance poses only when needed, and scores calibration with physical servo
rehearsals. Rehearsal time stays on the servo/reflex state's actual time base.
The native environment files, opponent and physical limits stay read-only.
Services share one absolute wind-up/toss/contact schedule.

## Model workers and provenance

API control uses four staggered workers, at most four in-flight requests, with
newest-observation arbitration. Busy slots drop observation opportunities instead
of queuing old screenshots. This follows the bounded actor scheduling used by
the rhythm project and the response validation/provenance approach used by the
Touhou project. It is not a same-observation four-way race.

API evaluation requires a valid model strategy before starting the physical clock. This
initialization call is labeled separately. During gameplay, the last accepted
model strategy persists until replaced. A flight freezes its strategy when its
first stroke is committed. A response cannot change an already committed flight.
There is no silent default policy when the model is slow; actual geometric
fallbacks are logged and displayed. Observation age and reply cadence are separate
metrics: more workers improve throughput, not the age of an individual reply.

Every request has an observation frame, local sequence ID, terminal model/tier
receipt and accounting. Reply records include worker identity and observation
age. Every installed return records the model decision ID that selected it.
The model returns `policy`, `decision_summary` and `memory`. The short public
decision summary is displayed verbatim; it is not private chain of thought.
API images contain the latest two public camera views; the rule controller uses
the full public history sheets. Offline simulator contacts never enter prompts.

## Commands

Use the pinned RoboOlympics revision
`da1f787f775ea6524d698c0b063157ded4c0fef9` through `TABLETENNIS_ENV_ROOT`.
Set `MUJOCO_EGL_DEVICE_ID` to the allocated renderer GPU. Install the dependencies
in a separate environment (the root workspace pins a different NumPy version):

```bash
python3.11 -m venv .venv-tabletennis
.venv-tabletennis/bin/pip install -r environments/tabletennis/requirements.txt
source .venv-tabletennis/bin/activate
export TABLETENNIS_ENV_ROOT=/absolute/path/to/the/pinned/roboolympics
export MUJOCO_EGL_DEVICE_ID=0  # use an allocated GPU
```

On the existing development server, `.runtime-libs` supplies the isolated Numba
runtime through PYTHONPATH. Commands below are run from the repository root.
The installed `sol` launcher also accepts `sol eval pingpong` and
`sol simulate pingpong` and `sol report pingpong`; `tabletennis` is an alias for the same implementation.

```bash
python scripts/tabletennis.py eval --source rules --rules-policy safe_center \
  --slowdown 1 --duration 240 --output runs/tabletennis/rules-new

python scripts/tabletennis.py eval --source api --model-workers 4 \
  --seed 11 --request-interval-s .65 --slowdown 1 --duration 300 --max-calls 120 \
  --api-key-file /absolute/path/to/existing/private/key \
  --api-budget-file /absolute/path/to/existing/api_budget.jsonl \
  --api-limit-usd 20 --stage-cap-usd 6 --output runs/tabletennis/api-new

python scripts/tabletennis.py report --output runs/tabletennis/api-new
```

The API model is `gpt-6.1-sol`, reasoning effort `low`, service tier `ultrafast`;
terminal responses must confirm all three. The cumulative ledger is append-only
and includes in-flight reservations. Stage ceilings also count existing spending
in the `tabletennis_realtime` scope. No ledger or credits are reset. Subscription
`--source sol` remains a separate single-worker transport with no API fallback.
Output directories must be new; STOP or SIGTERM preserves partial evidence.

## Replay and evidence

Every native pose is recorded in `presentation.jsonl` for offline use only.
The report renders the complete wall-clock match at 50 FPS and 1920x1080, using
the badminton video's navy frame, blue headings and yellow strategy label.
Both native camera angles run throughout: the behind view fills the main panel,
and the side view remains visible in a lower-left inset. The right sidebar shows
the live decision summary and recent model summaries. The orange ball ring
and 120 ms trail are explicitly labeled offline highlights, including through
occlusion. Point resets and toss-device placement are labeled, never interpolated
into fabricated flight. The sidebar shows the received model strategy, its public
summary, observation age, last installed return, commitment state and in-flight
requests. `decision_timeline.json` preserves the public summaries and applications
for later video editing. Failed points are retained without cuts or speed changes.
The large summary is the latest accepted reply, describing its labeled observation
time, not the current physical instant. `NEXT` is its persistent policy for the
next uncommitted flight; the execution caption separately identifies the reply
that owns the current stroke. `display_timeline.jsonl` records the native pose,
summary reply and installed policy shown in every video frame for alignment audits.

The run's source snapshot, requests, receipts, budget snapshots, camera images,
native ticks and offline contact diagnostics remain under its run directory.
Compact validation reports live under `artifacts/tabletennis`. Earlier direct,
synchronous, single-worker and failed development runs retain their own clocks
and source snapshots; they are not equivalent input/control conditions.

## Fixed implementation and observed results

The current actual API implementation completed seed 11 at 5:1 with 4/4 legal
serves and 6/7 legal returns, then seed 12 at 3:5 with 3/4 legal serves and 5/9
legal returns. Both used L1, 1x, GPT-6.1 Sol Low / Ultrafast, four model workers
and the same gameplay code. Seed 12 managed two consecutive legal returns before
an own-half fault. Stable cross-seed serving and long rallies remain open.
See [the evidence index](../artifacts/tabletennis/README.md) and
[complete dual-view seed-11 video](../assets/tabletennis/seed11-full.mp4).

This implementation replaces the selected README demonstration from the earlier
S=10 direct-action experiment. Those historical source records remain under
`research/in-progress/pingpong` and `research/updates`; they are not the current
1x tactical controller or evidence of its performance.

Run native regression suites for different sports in separate Python processes.
The external engine uses top-level module names such as `skill_api` and `duel`;
loading table tennis and badminton into one interpreter causes import collisions.
The game launchers already use separate processes. For example:

```bash
python -m unittest tests.test_tabletennis tests.test_tabletennis_realtime \
  tests.test_tabletennis_replay tests.test_pingpong_cli
```

## Subscription simulation

```bash
sol simulate pingpong --seed 11 --output runs/tabletennis/sim-new
```

This makes fresh `gpt-6.1-sol / low` subscription calls, with no API fallback or
paid API calls. One native subscription worker computes replies for four virtual request slots
(`--model-workers` selects virtual capacity in this mode) using the recipe's priority tier;
actual subscription computation time is recorded separately from sampled API
latency. Physics uses a virtual clock with 100 Hz native steps. At each 20 Hz
camera/control boundary the coordinator admits the next five native frames.
Replies cannot be used before their sampled delivery frame, rounded up to a
camera boundary. If subscription computation has not finished at that frame,
the simulator waits there. The same sampled row retains its paired terminal time;
a delivered request keeps its worker slot until that virtual terminal boundary. Rendering and rule-control time can also slow the
run. This is development simulation, never actual wall-clock API acceptance.
The camera controller and native robot planning remain the same as evaluation.
Native planning cannot gain free virtual compute during a model wait: each
prepared result is also gated by its measured worker duration in virtual time;
missed installation deadlines are still rejected.

The default profile is `profiles/tabletennis/historical-api-proxy.json`: 12 retained
serial Sol/Low/Ultrafast API calls from an earlier direct-action streaming workload.
Median JSON readiness is 1.149 s and nearest-rank P95 is 3.015 s. It is a **proxy**
for the current persistent tactical-policy task, not an exact workload or four-worker
calibration. Only valid paired calls are represented; provider failures are not
sampled. Use `--profile /path/to/profile.json` and `--delay-seed N` to override it.
The run freezes the full selected profile, its SHA256 and delay seed. Future sampled
delays stay in scheduler logs and never enter model prompts. Summaries distinguish
subscription wall latency, sampled API latency and gameplay clock mode. A new
same-workload API profile requires a separately authorized paid measurement run.
