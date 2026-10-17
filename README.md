<h1 align="center">Sooool!</h1>

<p align="center"><strong>Can GPT-6 Sol (a coding agent) play real-time games, where the world keeps moving while it thinks?</strong></p>

<p align="center">
<a href="#autoresearch-for-latency-awareness">Autoresearch for latency awareness</a> · <a href="#how-a-game-runs">How a game runs</a> · <a href="#how-the-latency-simulator-works">Latency simulator</a> · <a href="#games-and-controls">Games &amp; results</a> · <a href="#quick-start">Quick start</a> · <a href="#find-your-way-around-the-code">Code guide</a> · <a href="#citation">Citation</a>
</p>

Sooool! uses an autoresearch loop to get GPT-6 Sol, working as Agent as Policy, to play real-time games. It sees the current game screen, decides what to do, and sends an action. Then it sees what happened and decides again. The challenge is that the game keeps moving while it thinks. To understand the method, start with [Autoresearch for latency awareness](#autoresearch-for-latency-awareness). To run a game, jump to [Quick start](#quick-start). To check the evidence, see [results and execution conditions](docs/results.md).

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

These are selected runs, not win-rate estimates. Captions distinguish actual API play from simulation and replay, and state the game speed. [Clip sources and editing details](assets/gameplay/README.md).

## Autoresearch for latency awareness

We give Codex a game, a goal, an experiment budget, and feedback. It tries to improve how GPT-6 Sol plays under response delays: anticipating where a bullet will move or whether a target will still be useful when an action arrives.

1. **Find a failure.** Run the game and inspect screenshots, actions, timing, and outcomes.
2. **Propose a change.** Revise the gameplay instructions, memory, or permitted control settings to address a specific problem.
3. **Compare.** Test the candidate against the previous strategy on the same cases and timing conditions.
4. **Keep or reject it.** Check safety as well as score, then test promising candidates through complete games.
5. **Test in real time.** Fix the selected strategy and settings, run with actual response delays, and use the results to guide the next experiment. Keep failures alongside wins.

**For example,** in Touhou the model often chased where the boss had been before it started thinking. Codex tested instructions that anticipated the boss's next position. Some changes increased damage but caused more hits, so they were rejected. Adding safety checks for the action's start, movement path, and stopped position produced a candidate that passed comparisons on 12 fixed cases, then went on to full-game simulation and real-time testing. [Full case study](docs/touhou-research-record.md).

A **policy** is the gameplay instructions, fixed notes supplied with each request (called memory), output format, and request settings. The selected Touhou policy changed these rather than model weights. Autoresearch took place in Codex Goal mode with human guidance; `sol simulate` runs one game experiment, while Codex handles the analysis and edits across experiments. [Research stories for each game](docs/autoresearch-summaries.md).

## How a game runs

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

In Touhou, movement stops when the plan ends; shooting and focus keep their last settings. A newer accepted decision replaces the unfinished plan. Older observations cannot override a decision already accepted from a newer one.

### Several requests can be waiting at once

An answer can take seconds. Sending requests while earlier ones are still waiting can keep decisions coming more often, or provide several chances to get an answer sooner. The selected configurations use three patterns:

| Game | Requests | How answers are used |
|---|---|---|
| **Touhou** | Send the same observation to **four requests at once**. Start another group after a winner takes effect, movement finishes, and enough slots are free. | Use the first valid answer; the other answers for that observation cannot replace it. |
| **Rhythm** | Try a new screenshot **every 0.2 seconds**, with **up to 16 requests waiting**. Skip sending when full. | Execute the model's tap times, skip expired taps, and prevent duplicate presses using action IDs. |
| **Asterix** | **One request at a time.** Observe again after the previous reply. | Hold the chosen direction until a new answer replaces it. |

More requests also mean more calls, cost, and potentially outdated answers. Asterix's serial setup followed limited trials in which overlapping requests appeared to encourage repeated movement. [Request ordering, capacity, and experiment details](docs/latency-aware-learning.md).

A **recipe** is a JSON file selecting a policy, latency profile, and run settings. See the selected recipes: [Touhou simulation](recipes/touhou.json), [Touhou real-time](recipes/touhou-realtime.json), [Rhythm](recipes/rhythm.json), and [Asterix](recipes/asterix.json).

## How the latency simulator works

Development uses subscription calls to try strategies under delays measured from the target API. For Touhou and Rhythm, the commands divide the work like this:

| Command | What happens | What it uses |
|---|---|---|
| `sol profile` | Send saved inputs one at a time and measure response times. No game actions are executed. | Paid API calls with a budget cap |
| `sol simulate` | Play a new game and use sampled delays to schedule answers. Virtual time can wait for the model. | ChatGPT subscription calls and a latency profile |
| `sol eval` | Play with a continuously running clock and actual response times. | Paid API calls with a budget cap |

A **latency profile** stores measured response times, including slow replies. The simulator draws from it to decide when each new answer becomes available.

Suppose a screenshot is taken at frame 100 and the drawn delay is half a second. At 60 FPS, the answer can be used at frame 130. Until then, the game advances with the controls already in effect. If the model finishes early, its answer waits; if it is still computing at frame 130, virtual time waits for it. The model never sees the drawn delay. Both game time and actual computing time are recorded.

In real-time evaluation, a three-second response means the game also moves forward for three seconds. Asterix uses subscription response times for this test and keeps its declared slowdown; other games have separate [setup guides](docs/release-guide.md).

The simulator also accounts for concurrent requests: Touhou samples groups of delays together, while Rhythm includes screenshot age. Changing prompts, images, or concurrency may require a new profile. Simulated scores do not establish real-time success. [Timing and calibration details](docs/timing.md).

**Replay** can restore a fixed starting state before candidates make new decisions, or reproduce an entire saved action sequence to check timing and make videos. The latter makes no new decisions and is not a new performance result. [Development and replay workflow](docs/development.md).

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

The game actors do not receive hidden game coordinates or future sampled delays. Evaluators may inspect game state to score outcomes. [Observation boundaries](docs/observation-contract.md).

**Results and limits.** Original Touhou runs defeated the boss in real time; Rhythm's selected run scored 24 Perfect, 1 Great, zero Miss, and two empty presses. These results have not been reproduced by the portable launcher: its fresh Touhou simulation lost, its full paid Touhou test is pending, and its live Rhythm run failed. The selected Badminton match lost 8:11; Racing's documented comparison recorded 7/7 wins with GPT targets and 3/7 with fixed goals. See [all results and execution conditions](docs/results.md), [validation including failures](docs/validation.md), and [Badminton evidence](artifacts/badminton/README.md) for the complete records.

<details>
<summary>Game sources and inspirations</summary>

- **Racing, PingPong, and Badminton:** [Embodied Olympics Exam](https://olympics.embodied-first-exam.ai/), using the pinned [RoboOlympics source](https://github.com/CHIGUI0/roboolympics/tree/da1f787f775ea6524d698c0b063157ded4c0fef9).
- **Asterix:** the Atari 2600 game through [ALE](https://ale.farama.org/environments/asterix/), using `ALE/Asterix-v5`.
- **Rhythm:** a custom four-lane browser game inspired by Tencent's [Rhythm Master / 节奏大师](https://apps.apple.com/cn/app/%E8%8A%82%E5%A5%8F%E5%A4%A7%E5%B8%88/id493901993).
- **Touhou:** a simplified Kaguya practice encounter based on [Touhou Eiyashou ~ Imperishable Night](https://www16.big.or.jp/~zun/html/th08top.html), with original-game presentation assets.

</details>

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

Other games have their own setup requirements: [Rhythm](docs/rhythm.md), [Racing](docs/racing.md), [PingPong](docs/tabletennis.md), [Badminton](docs/badminton.md), and [Asterix](docs/release-guide.md). The [release guide](docs/release-guide.md) includes profiling commands; the [development guide](docs/development.md) explains how to compare candidates.

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

Evidence archives are optional. Text shown with actions is a model-written public summary, not an internal reasoning transcript.

## Citation

If you use Sooool in your research, please cite this repository:

```bibtex
@misc{wang2026sooool,
  title        = {Sooool!},
  author       = {Wang, Zihan and Li, Xinyuan and Li, Zeju and Lin, Yuxiang and Gui, Chi and Pei, Jiaxin and Li, Manling},
  year         = {2026},
  howpublished = {GitHub repository},
  url          = {https://github.com/sooool-project/sooool}
}
```
