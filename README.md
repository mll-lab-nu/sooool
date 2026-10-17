<h1 align="center">Sooool!</h1>

<p align="center"><strong>Can GPT-6 Sol play real-time games, where the world keeps moving while it thinks?</strong></p>

<p align="center">
<a href="#what-is-sooool">Overview</a> · <a href="#autoresearch-for-latency-awareness">Autoresearch for latency awareness</a> · <a href="#how-a-game-runs">How a game runs</a> · <a href="#how-the-latency-simulator-works">Latency simulator</a> · <a href="#games-and-controls">Games &amp; results</a> · <a href="#quick-start">Quick start</a> · <a href="#find-your-way-around-the-code">Code guide</a> · <a href="#citation">Citation</a>
</p>

To understand the method, start with [Autoresearch for latency awareness](#autoresearch-for-latency-awareness). To run a game, jump to [Quick start](#quick-start). To check the evidence, see [results and execution conditions](docs/results.md).

## What is Sooool?

Sooool! uses an autoresearch loop to get GPT-6 Sol, working as a coding agent, to play real-time games. It sees the current game screen, decides what to do, and sends an action. Then it sees what happened and decides again. The challenge is that the game keeps moving while it thinks: a bullet gets closer, an opponent changes direction, or a note passes. A good move can arrive too late.

We give Codex a game, a goal, and an experiment budget, then let it work through trial and error. It plays, looks at what went wrong, changes its strategy, and tries again. During these experiments, a latency simulator recreates the delays measured from actual API calls. Selected strategies are then tested against a real-time game clock, with the game running while the agent thinks.

## Demos

Click a preview to watch the video.

<table>
<tr>
<td width="50%" align="center"><a href="assets/gameplay/touhou.mp4"><img src="assets/gameplay/touhou.gif" alt="GPT-6 Sol dodging Kaguya's bullet patterns with live English decision summaries" width="440"></a><br><b>Touhou</b> · Real-time API · 1×</td>
<td width="50%" align="center"><a href="assets/tabletennis/seed11-full.mp4"><img src="assets/gameplay/pingpong.gif" alt="GPT-6 Sol playing table tennis with both camera views and live public decision summaries" width="440"></a><br><b>PingPong</b> · Real-time API · 1×</td>
</tr>
<tr>
<td width="50%" align="center"><a href="assets/gameplay/asterix.mp4"><img src="assets/gameplay/asterix.gif" alt="GPT-6 Sol collecting food in Asterix alongside original public decision summaries" width="440"></a><br><b>Asterix</b> · Profile simulation replay · 5× slowdown</td>
<td width="50%" align="center"><a href="assets/gameplay/badminton.mp4"><img src="assets/gameplay/badminton.gif" alt="SOL badminton: opening serve and rally, with both camera views and original English decision summaries" width="440"></a><br><b>Badminton</b> · Real-time API replay · S3 slowdown · 15s</td>
</tr>
<tr>
<td width="50%" align="center"><a href="assets/gameplay/rhythm.mp4"><img src="assets/gameplay/rhythm.gif" alt="GPT-6 Sol choosing literal DFJK tap times:24 Perfect,1 Great,zero misses,two empty presses" height="270"></a><br><b>Rhythm</b> · Real-time API · 1× · 24 Perfect / 1 Great / 0 Miss</td>
<td width="50%" align="center"><a href="assets/gameplay/racing.mp4"><img src="assets/gameplay/racing.gif" alt="GPT-6 Sol selecting racing targets through bends and obstacles, with live decisions" width="440"></a><br><b>Racing</b> · Real-time API · Hybrid steering</td>
</tr>
</table>

These clips come from individual runs, rather than repeated win-rate tests. Each caption identifies how that run was timed. The Asterix clip is a replay of a delay-simulated run; the Touhou, Racing, Rhythm, and PingPong clips used actual API calls while the game was running. The Badminton clip replays a recorded real-time API run at 3x slowdown. Racing uses a steering controller, and PingPong uses a controller to execute shots. [Clip sources and editing details](assets/gameplay/README.md).

## Autoresearch for latency awareness

We ask Codex to improve how GPT-6 Sol plays a game through repeated experiments. It studies failed runs, proposes a change, edits the gameplay instructions or permitted control settings, and tests whether the change helps. The aim is to account for what happens while the model thinks: where a bullet will move, when a note must be pressed, or whether a target will still be useful when the action arrives. Humans supply the goal, budget, constraints, and feedback.

Here is how an autoresearch session proceeds:

1. **Give it a goal.** Choose a game, an objective, a budget, and rules about what it may change. Humans can provide demonstrations and feedback along the way.
2. **Find out what failed.** Codex inspects screenshots, actions, timing, and outcomes. Did it mistake a friendly effect for a bullet? Did it chase where the opponent used to be? Did it react too late?
3. **Try a specific change.** It revises the gameplay instructions or an allowed control setting, then compares the candidate with the previous strategy on the same cases and timing conditions.
4. **Keep or reject it.** A change that scores more points but causes more deaths may fail the comparison. Promising candidates also have to work through complete games.
5. **Test in real time.** Fix the selected strategy and its settings, then run it with the actual response delays. Record what happened, including failures, and use those results to guide the next experiment.

Here, a **policy** is the gameplay instructions, fixed notes supplied with each request (called memory), output format, and request settings. The selected Touhou policy was developed through repeated play, prompt and memory refinement, and experiments. Its base-model weights remain frozen. These autoresearch sessions were carried out in Codex Goal mode with human guidance. Running `sol simulate` starts one game experiment; Codex carries out the analysis, edits, and comparisons across experiments.

[See a concrete Touhou example below](#an-example-learning-to-stop-chasing-the-boss), or [read the autoresearch stories for each game](docs/autoresearch-summaries.md).

## How a game runs

During each experiment, GPT-6 Sol plays by repeating these steps:

```text
See the game screen → choose an action → apply it when ready → see what changed
         ↑                                                        |
         +--------------------------------------------------------+
```

The instructions, recent screenshots, and allowed feedback tell the model what it can see and do. Each game defines its controls: in Touhou, for example, the model chooses movement, shooting, focus, bombs, and how long to hold them. Other games let it choose targets that a controller carries out.

### From screenshots to actions

Take Touhou as an example:

1. **Capture.** The runner collects up to three recent screenshots with their frame numbers. Comparing the images helps the model judge which way the boss and bullets are moving.
2. **Ask.** Send those images with the game instructions, controls already in effect, historical delay information, and the model's own earlier position estimates. The model does not receive hidden game coordinates or the delay drawn for this request.
3. **Answer.** GPT-6 Sol returns JSON containing its visual estimates and an action plan.
4. **Execute.** The runner checks the format, waits until the answer is allowed to take effect, and applies the chosen buttons. Invalid actions are rejected and recorded. The position estimates do not become automatic dodge or tracking commands.

One action in the plan might be:

```json
{"move": 3, "shoot": 1, "focus": 1, "bomb": 0, "duration": 12}
```

This means: move right, keep shooting, use slow focused movement, do not use a bomb, and hold for 12 game frames (0.2 seconds at 60 FPS). The model chooses both the direction and the duration.

Once the plan ends, movement stops and shooting/focus keep their last settings while the runner waits for another answer. A newer accepted decision replaces the unfinished part of the previous plan. An answer based on an older observation cannot override a decision already accepted from a newer one.

### Several requests can be waiting at once

Waiting for an answer can take seconds. We tried different ways to keep decisions coming, rather than assuming one request at a time would work for every game. The selected configurations use three different patterns:

| Game | When requests are sent | What happens to the answers |
|---|---|---|
| **Touhou** | Send the same screenshots and prompt to **four requests at once**. Wait for a valid answer to take effect and its movement to finish before sending the next group; enough request slots must also be free. | Use the first valid answer for that observation. Other answers for the same observation cannot replace it. |
| **Rhythm** | Try to send a new screenshot **every 0.2 seconds**, with **up to 16 requests waiting at once**. Skip sending when all slots are occupied. | Answers specify keys and tap times. The executor follows those times, skips expired taps, and uses action IDs to prevent duplicate presses. |
| **Asterix** | Allow **one request at a time**. Capture the next observation after the previous answer arrives. | Hold the chosen direction unchanged until the model replaces it. There is no automatic stop or row hop. |

Touhou's real-time configuration allows four requests in total; its simulation allows eight so older requests can finish after a winner has been used. Choosing a winner does not immediately free the other requests' slots. Rhythm overlaps decisions from successive observations instead of racing several answers to the same screenshot. Its older answers cannot cancel or replace newer instructions, though they can still add a tap that is valid and has not already been scheduled.

The prompts also ask the model to anticipate where the boss and bullets will be when its action arrives. [Latency-aware learning and control](docs/latency-aware-learning.md) describes this strategy development alongside request scheduling.

Concurrency can help an answer arrive sooner or keep observations flowing while earlier requests are waiting. It also means more calls, more cost, and more answers that may already be out of date. Asterix's serial setup was selected after overlapping requests appeared to encourage repeated movement; the limited trials motivate that choice rather than proving it is always better.

Each **recipe** is a JSON file that selects the strategy, latency profile, and run settings. These are the selected configurations, not fixed rules for all experiments: [Touhou simulation](recipes/touhou.json), [Touhou real-time](recipes/touhou-realtime.json), [Rhythm](recipes/rhythm.json), and [Asterix](recipes/asterix.json). The [games and controls table](#games-and-controls) below explains what the model chooses and what each game's controller handles.

## How the latency simulator works

We want to try strategies under realistic delays without requiring every development run to use the target API. Development runs use the subscription model to make decisions and the latency simulator to decide when those decisions take effect.

For Touhou and Rhythm, the three commands divide the work like this:

| Command | What happens | What it uses |
|---|---|---|
| `sol profile` | Send saved screenshots and prompts to the API, one request at a time, and measure how long answers take. No game actions are executed. | Paid API calls with a budget cap |
| `sol simulate` | Play a new game. Use measured delays to decide when each answer can affect the game; virtual time can wait for the model. | ChatGPT subscription calls and a latency profile |
| `sol eval` | Play with a continuously running game clock. The actual time taken by each answer affects the outcome. | Paid API calls with a budget cap |

Asterix uses subscription calls for real-time evaluation too. PingPong also supports `sol simulate pingpong`, using fresh subscription decisions with a clearly labeled historical API timing proxy. See its [simulation setup and limits](docs/tabletennis.md#subscription-simulation). The other games have separate commands and dependencies in their [setup guides](docs/release-guide.md).


### 1. Measure the delay (`sol profile`)

Send representative screenshots and instructions to the target API and record how long answers take. Keep the individual measurements, including slow responses, in a **latency profile**. This describes the timing of a particular prompt, image setup, and request configuration.

### 2. Play a new game with those delays (`sol simulate`)

The game runs on a virtual clock that the runner advances. For each request, the simulator draws a delay from the profile and schedules when the answer can be used.

For example, suppose a screenshot is taken at frame 100 and the sampled delay is half a second. At 60 frames per second, the answer becomes available at frame 130. Until then, the game advances using the controls already in effect.

The model still makes a new decision from the screenshots. If it finishes early, the simulator holds the answer until frame 130. If it has not finished by then, the runner waits for it without advancing the virtual clock. Both the game time and the actual time spent computing are recorded.

This lets us ask: **would this strategy work if its answers arrived with the delays we measured?** It does not tell us how fast the current model call actually was.

The implementation also tracks requests that are still in progress and prevents old answers from replacing newer decisions. Touhou's selected setup sends four requests the same observation and uses the first valid answer. Its simulator samples their delays together to preserve the relationships measured between concurrent requests. Rhythm also accounts for how old a screenshot is when a request is sent. [Timing details](docs/timing.md).

### 3. Test the selected strategy in real time (`sol eval`)

In the real-time test, the game keeps running while the agent responds. If a response takes three seconds, the game moves forward for three seconds. There is no waiting for the model outside game time.

Touhou and Rhythm use the paid API for this test. Asterix uses actual subscription response times and retains its declared game slowdown. Each game's documentation specifies its clock, speed, and model connection.

A changed prompt, image count, or concurrency setting can change response times, so the profile may need to be measured again. Simulated results and real-time results are recorded separately.

### Reproduction: subscription and realtime timing

The selected runners request **`gpt-6.1-sol`, reasoning effort `low`**. Match the recipe, policy, seed, delay seed, game speed and transport when reproducing a result. Subscription simulation makes fresh model calls but schedules delivery on a virtual clock; realtime evaluation uses actual response timing with a continuously advancing clock. **Realtime does not inject the profile delays below.**

| Game | Subscription simulation (`simulate`) | Realtime evaluation (`eval`) | Game speed |
|---|---|---|---|
| [Touhou](docs/release-guide.md#touhou-realtime-api-evaluation) | Tier inherited; 4 native workers, 8 slots; four-way race | API Ultrafast; 4 workers/slots; four-way race | 1× |
| [Rhythm](docs/rhythm.md) | Priority requested; 16 actors/slots; 200 ms cadence | API Ultrafast; up to 16 requests; 200 ms cadence | 1×; selected 17 s / 25 notes |
| [Asterix](docs/release-guide.md#run) | Tier inherited; 1 native worker/slot; serial | **Subscription**, tier inherited; serial; actual wall timing | **5× slowdown**; selected 20 game seconds |
| [Racing](docs/racing.md) | Ultrafast requested, subscription tier unverified; 3 native workers / 8 virtual slots; 600 ms cadence | API Ultrafast; up to 8 requests; 600 ms cadence | 1×; L1 |
| [Badminton](docs/badminton.md) | **Default tier, Fast disabled**; serial | API Ultrafast; serial | **3× slowdown (S3)**; L1 |
| [PingPong](docs/tabletennis.md) | Priority requested; 1 native worker / 4 virtual slots; 650 ms cadence | API Ultrafast; 4 workers/slots; 650 ms cadence; select `--source api` explicitly | 1×; L1 |

“Tier inherited” means the runner does not pin a subscription tier. Requested subscription tiers do not establish the same latency or routing as the paid Ultrafast API. PingPong `eval` defaults to rules unless a model source is explicitly selected.

The following are summaries of the **retained simulation timing profiles**, not measurements of today's subscription speed or predictions of a new realtime run. Units are **milliseconds**; `std` is the **population standard deviation (`ddof=0`)** of the retained samples, not a standard error. Timing endpoints differ between games.

| Game / selected profile | Samples | Timing endpoint | Mean (ms) | Std (ms) |
|---|---:|---|---:|---:|
| [Touhou](profiles/touhou/profile-control-tracking-safe-intercept-v2-transport-v1.json) | 19 four-way cohorts | Earliest legal action in each cohort + apply overhead | 2638.9 | 372.6 |
| [Rhythm](profiles/rhythm/selected-native-joint.json) | 85 joint rows | Legal action JSON ready (`api_rtt_s`) | 1432.7 | 282.2 |
| [Asterix](profiles/asterix/latency_v16_actual_5x_512cap.json) | 536 valid calls | Capture to full completion | 1665.4 | 1373.2 |
| [Racing](profiles/racing/profile.json) | 32 serial calls | Full response | 1472.1 | 378.6 |
| [Badminton](profiles/badminton/conditional-api-10.json) | 10 serial calls | Legal action JSON ready (`latency_ms`) | 2070.7 | 323.8 |
| [PingPong](profiles/tabletennis/historical-api-proxy.json) | 12 serial calls | Legal action JSON ready (`delays_s`) | 1326.8 | 552.9 |

- **Profile scope matters.** Touhou's table pools 19 **modeled** four-way cohorts; the simulator samples within image-count strata. It is not a freshly measured concurrent profile. Racing's one-image direct-steering profile is a proxy for its current two-image lane goals. PingPong's earlier direct-action profile is a proxy for its current tactical policies. Asterix retains a historical V16 profile for V28; its 536 valid samples exclude 2 failed attempts and include a 25,537 ms slow response.
- **Readiness and occupancy differ.** Rhythm resamples complete joint rows, including screenshot age, overhead and request occupancy; occupancy is 1634.0 ± 305.6 ms, and completion is 1577.3 ± 304.1 ms. Its selected content/timestamp bias is 50 ms. Badminton retains paired terminal timing of 2132.5 ± 332.3 ms; PingPong retains 1392.9 ± 561.5 ms. A readiness-only mean does not specify when a request slot becomes free.
- **Record actual timing too.** Keep subscription computation time and virtual delivery time separately. For realtime, calculate latency mean/std from that run's receipts; the stored profiles above are not its observed latency. If the workload or observed API distribution changes, measure the exact prompt/image/transport condition under an explicit API budget and retain it as a new profile rather than silently replacing the comparison condition.
- **Match the runtime.** Use the per-game dependency and renderer setup, the pinned RoboOlympics revision for native games, and the declared seeds. Native preparation deadlines, rendering and provider failures also affect outcomes. Badminton requires NVIDIA EGL; native games also need enough CPU capacity to meet planning deadlines. A matching model name or profile mean alone does not guarantee the demonstrated score. Preserve incomplete and failed runs alongside successes.

## Where replay fits

Replay serves two purposes in the research process:

- **Compare from the same starting point.** Restore a game to a recorded failure state, then ask each candidate for a new action. The candidates start from the same situation, but their actions can lead to different outcomes.
- **Check a saved run.** Execute the recorded actions at their recorded times to reproduce a trajectory, check timing, or make a video. This does not ask the model for new decisions and is not a new gameplay result.

A normal simulation run makes new decisions as it plays. It does not simply replay a saved sequence of answers.

## An example: learning to stop chasing the boss

In Touhou, an early strategy moved toward the boss's position in the screenshot. By the time the move began, the boss had often changed direction. The player missed shots and sometimes moved into danger.

Codex tested instructions that asked the model to aim for where the boss would be after the response delay and the shots' travel time. Some candidates dealt more damage but also took more hits, so they were rejected.

The next change asked the model to check safety at three points: when the action starts, along the movement path, and where the player stops while waiting for the next answer. Codex compared the candidates on 12 fixed cases, then ran complete games with matched delay samples. The selected candidate was subsequently tested with the real API.

This is what autoresearch means here: turn a failure into a hypothesis, test a change, and keep the evidence that explains the decision. [Full Touhou research story and results](docs/touhou-research-record.md).

## Games and controls

[Current results and execution conditions](docs/results.md) lists each selected strategy, game speed, and supporting records. Touhou is a simplified Kaguya practice encounter rather than the full original game.

| Game | What GPT-6 Sol decides | What the surrounding code does |
|---|---|---|
| **Touhou / Kaguya** | Movement, shooting, focus, bombs, and duration | Runs the game, captures screenshots, checks and applies actions |
| **Racing** | Speed, racing targets, offset, and lookahead | A visual controller supplies steering and limits speed through bends |
| **Rhythm** | DFJK keys and the times to press them | Forwards the chosen tap times and records execution |
| **PingPong** | Where to place a shot | Controllers handle serving and execute the robot's motion |
| **Badminton** | Shot placement and recovery goals | Controllers handle contact planning and native game mechanics |
| **Atari Asterix** | Which direction to hold | Applies the model's action unchanged until a newer one replaces it |

The screenshot-based game actors do not receive hidden game coordinates or future sampled delays. Evaluators can inspect game state to score outcomes. [Observation and evaluation boundaries](docs/observation-contract.md).

The demos use selected runs, and success has not been reproduced under every setup. The original Touhou runs include real-time boss defeats, while a fresh simulation with the portable launcher lost; a full paid real-time test of that launcher remains pending. Rhythm's selected original run had 24 Perfect, 1 Great, zero Miss, and two empty presses, but a later run with the portable launcher did not reproduce that result. [Validation results, including failures](docs/validation.md).

The Badminton clip shows the opening serve and rally from one seed-101, L1/S3 match. The full match lost **8:11**, with **90/97 legal returns**, **47 confirmed Ultrafast responses**, zero rule fallbacks across 90 controlled rally strokes, and four serve failures. Its native replay matched all 27,609 steps. [Protocol and evidence](artifacts/badminton/README.md).

Racing also retains a [recorded GPT and fixed-goal comparison](research/racing/EVALUATION.md#recorded-gpt-and-no-gpt-comparison): 7/7 wins for GPT targets and 3/7 for fixed goals under the documented conditions.

## Game sources and inspirations

| Game | Source / original game |
|---|---|
| **Car Racing** | [RoboOlympics](https://olympics.embodied-first-exam.ai/), using the pinned [RoboOlympics source](https://github.com/CHIGUI0/roboolympics/tree/da1f787f775ea6524d698c0b063157ded4c0fef9). |
| **Badminton** | [RoboOlympics](https://olympics.embodied-first-exam.ai/), using the same pinned native environment. |
| **PingPong / Table Tennis** | [RoboOlympics](https://olympics.embodied-first-exam.ai/), using the same pinned native environment. |
| **Atari Asterix** | The Atari 2600 game through the [Arcade Learning Environment (ALE)](https://ale.farama.org/environments/asterix/), using `ALE/Asterix-v5`. |
| **Rhythm** | Inspired by Tencent’s [Rhythm Master / 节奏大师](https://apps.apple.com/cn/app/%E8%8A%82%E5%A5%8F%E5%A4%A7%E5%B8%88/id493901993); implemented here as a custom four-lane DFJK browser game and practice chart. |
| **Touhou / Kaguya** | Follows [Touhou Eiyashou ~ Imperishable Night](https://www16.big.or.jp/~zun/html/th08top.html) by ZUN / Team Shanghai Alice; implemented here as a simplified Kaguya practice encounter with original-game presentation assets. |

Environment and media attribution details are recorded in [source and media provenance](docs/provenance.md).

## Quick start

Start with Touhou in the latency simulator. The tested setup uses Linux, Python 3.10-3.12, Chromium dependencies, and a standalone Codex CLI signed in with a ChatGPT subscription that supports the configured model. The tested CLI version is 0.162.1.

```bash
uv sync --locked --python 3.12
uv run playwright install --with-deps chromium
codex login

uv run sol doctor --game touhou --auth
uv run sol simulate touhou --output runs/touhou-dev-001
```

This uses subscription calls for decisions and historical API measurements for delays. It does not fall back to paid API calls.

To test Touhou in real time, provide an API key through `OPENAI_API_KEY` or the hidden prompt, and set a spending limit:

```bash
uv run sol eval touhou \
  --seed 1 \
  --budget-usd 5 \
  --max-calls 100 \
  --output runs/touhou-api-001
```

Runs save their configuration and source snapshot, model inputs and outputs, applied actions, timing, and results. The Touhou real-time runner also records video and API costs. [Real-time setup and budgets](docs/realtime.md).

To measure API response times using the inputs saved from a simulation:

```bash
uv run sol profile touhou \
  --episode runs/touhou-dev-001/episode \
  --budget-usd 2 \
  --max-calls 21 \
  --output runs/touhou-profile-001
```

Other games have their own setup requirements: [Rhythm](docs/rhythm.md), [Racing](docs/racing.md), [PingPong](docs/tabletennis.md), [Badminton](docs/badminton.md), and [Asterix](docs/release-guide.md). The [release guide](docs/release-guide.md) collects commands and the [development guide](docs/development.md) explains how to compare your own candidates.

## Find your way around the code

| Path | Start here to understand... |
|---|---|
| [`runtime/cli.py`](runtime/cli.py) | How `simulate`, `profile`, and `eval` launch a run |
| [`runtime/subscription.py`](runtime/subscription.py) | How screenshots and instructions are sent through the Codex CLI |
| [`environments/`](environments/) | Game engines, observation interfaces, and action execution |
| [`policies/`](policies/) | The gameplay instructions and expected response formats |
| [`recipes/`](recipes/) | Which strategy and settings an experiment uses |
| [`profiles/`](profiles/) | The measured delays used by the simulator |
| [`research/`](research/) | Hypotheses, comparisons, and research history |
| [`artifacts/`](artifacts/), [`assets/`](assets/) | Run records, replay evidence, videos, and demo clips |

[Detailed file map](docs/file-map.md) · [Evaluation records](docs/evaluation-records.md) · [Optional evidence downloads](artifacts/README.md)

Large evidence archives are optional. Short explanations shown with actions are model-written public summaries, not internal reasoning transcripts. Media sources and editing are documented with each artifact.

## Citation

If you use Sooool in your research, please cite this repository:

```bibtex
@misc{wang2026sooool,
  title        = {Sooool!},
  author       = {Wang, Zihan and Li, Xinyuan and Li, Zeju and {Yuxiang} and Gui, Chi and Pei, Jiaxin and Li, Manling},
  year         = {2026},
  howpublished = {GitHub repository},
  url          = {https://github.com/sooool-project/sooool}
}
```

This is a private research package. Repository access does not grant an additional license to upstream code or media. See [source and media provenance](docs/provenance.md) before redistribution.
