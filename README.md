<h1 align="center">Sooool! Agent as Real-Time Policies</h1>

<p align="center"><strong>&#xA0;GPT Sol doing real-time tasks. World keeps moving while it thinks.</strong></p>

<p align="center">
<a href="#latency-profiling-and-simulation">Latency profiling and simulation</a> · <a href="#autoresearch-for-latency-aware-agents">Autoresearch for latency-aware agents</a> · <a href="#how-a-game-runs">How a game runs</a> · <a href="#games-and-controls">Games &amp; controls</a> · <a href="https://github.com/sooool-project/sooool/blob/main/docs/results.md">Results</a> · <a href="#quick-start">Quick start</a> · <a href="#code-guide">Code guide</a> · <a href="#citation">Citation</a>
</p>

Sooool! uses an autoresearch loop to get GPT-6 Sol to play real-time games, with Agent as Policy. It sees the current game screen, decides what to do, and sends an action. Then it sees what happened and decides again. The challenge is that the game keeps moving while it thinks.

<table>
<tr>
<td width="50%" align="center"><a href="assets/gameplay/touhou.mp4"><img src="assets/gameplay/touhou.gif" alt="The coding agent dodging Kaguya's bullet patterns with live English decision summaries" width="390"></a><br><b>Touhou</b> · Live API run</td>
<td width="50%" align="center"><a href="assets/tabletennis/seed11-full.mp4"><img src="assets/gameplay/pingpong.gif" alt="The coding agent playing table tennis with both camera views and live public decision summaries" width="390"></a><br><b>PingPong</b> · Live API run</td>
</tr>
<tr>
<td width="50%" align="center"><a href="assets/gameplay/rhythm.mp4"><img src="assets/gameplay/rhythm.gif" alt="The coding agent choosing literal DFJK tap times:24 Perfect,1 Great,zero misses,two empty presses" width="390"></a><br><b>Rhythm</b> · Live API run</td>
<td width="50%" align="center"><a href="assets/gameplay/racing.mp4"><img src="assets/gameplay/racing.gif" alt="The coding agent selecting racing targets through bends and obstacles, with live decisions" width="390"></a><br><b>Racing</b> · Live API run</td>
</tr>
<tr>
<td width="50%" align="center"><a href="assets/asterix/v28-api-60s.mp4"><img src="assets/gameplay/asterix.gif" alt="GPT-6 Sol playing Asterix with real API decisions: 300 points, two lives, 60 wall seconds at 12 FPS" width="390"></a><br><b>Asterix</b> · Live API run</td>
<td width="50%" align="center"><a href="assets/gameplay/badminton.mp4"><img src="assets/gameplay/badminton.gif" alt="The coding agent playing badminton: opening serve and rally, with both camera views and original English decision summaries" width="390"></a><br><b>Badminton</b> · Live API run</td>
</tr>
</table>

## Latency profiling and simulation

Our workflow is **profile → simulate → eval**: measure target API latency, develop strategies with subscription calls on a reproducible virtual clock, then test selected strategies in a live API/subscription run.

### Profile the latency

Send representative screenshots and prompts to the target API and record when a valid action is ready and when the response finishes. These can be different: an action may be usable while the request is still finishing and occupying a slot. Keep the individual timings, including slow replies, in a **latency profile**.

Start with requests sent one at a time. Concurrent runs provide additional measurements of how requests finish together and how long they keep their slots. Touhou's selected profile uses groups of four readiness and completion times; Rhythm also includes screenshot age and transport overhead. Some profiles combine measurements from earlier workloads with modeled timing. Changing the prompt, image setup, or concurrency may require new measurements. [Profiles and measurement sources](profiles/README.md) · [Timing details](docs/timing.md).

We computed the latency profiles below; timings may vary across API setups, and simulated mode lets you reproduce our timing setup.

| Game / selected profile | Samples | Timing endpoint | Mean (ms) | Std (ms) |
|---|---:|---|---:|---:|
| [Touhou (modeled)](profiles/touhou/profile-control-tracking-safe-intercept-v2-transport-v1.json) | 19 groups of four requests | First action ready + apply overhead | 2638.9 | 372.6 |
| [PingPong (proxy)](research/updates/2026-10-16/ubuntu/pingpong/results/profile-stream-serial-v1/profile.json) | 12 serial calls | Action ready | 1326.8 | 552.9 |
| [Asterix](profiles/asterix/latency_v16_actual_5x_512cap.json) | 536 valid calls | Capture to completion | 1665.4 | 1373.2 |
| [Badminton](profiles/badminton/conditional-api-10.json) | 10 serial calls | Action ready | 2070.7 | 323.8 |
| [Rhythm](profiles/rhythm/selected-native-joint.json) | 85 timing samples | Action ready | 1432.7 | 282.2 |
| [Racing (proxy)](profiles/racing/profile.json) | 32 serial calls | Response complete | 1472.1 | 378.6 |

### Build the simulator

During development, subscription calls produce new decisions while the simulator draws delays from the profile. Suppose a screenshot is taken at frame 100 and the drawn delay is half a second. At 60 FPS, the answer can be used at frame 130. Until then, the game advances with the controls already in effect. If the agent finishes early, its answer waits; if it is still computing at frame 130, virtual time waits for it. The agent never sees the drawn delay.

This lets Codex compare strategies under the same delay conditions, even when the actual subscription calls take different amounts of time.

### Live API/subscription run

Fix the selected strategy and run it with actual response times. The game keeps running while the agent responds: a three-second response means the game also moves forward for three seconds.

These commands cover Touhou, Rhythm, and Asterix; `sol profile` is available for Touhou and Rhythm:

| Command | What happens | What it uses |
|---|---|---|
| `sol profile` | Send saved inputs one at a time and measure response times. No game actions are executed. | Paid API calls with a budget cap |
| `sol simulate` | **Simulation:** use sampled delays to schedule new decisions; virtual time can wait for the agent. | ChatGPT subscription calls and a latency profile |
| `sol eval` | **Live API/subscription run:** the game keeps running while the agent responds. | API or subscription calls; paid API calls require a budget cap. |

**Replay** can restore a fixed starting state before candidates make new decisions, or reproduce a saved action sequence to check timing and make videos. Replaying saved actions makes no new decisions and is not a new performance result. [Development and replay workflow](docs/development.md).

## Autoresearch for latency-aware agents

With the simulator, Codex can try changes, compare strategies, and inspect failures before testing in real time. We give it a game, a goal, an experiment budget, and feedback. It improves how the coding agent plays under response delays: anticipating where a bullet will move or whether a target will still be useful when an action arrives.

1. **Find a failure.** Run the game and inspect screenshots, actions, timing, and outcomes.
2. **Propose a change.** Revise the gameplay instructions, memory, or permitted control settings to address a specific problem.
3. **Compare.** Test the candidate against the previous strategy on the same cases and timing conditions.
4. **Keep or reject it.** Check safety as well as score, then test promising candidates through complete games.
5. **Test in real time.** Fix the selected strategy and settings, run with actual response delays, and use the results to guide the next experiment.

**For example,** in Touhou the coding agent often chased where the boss had been before it started thinking. Codex tested instructions that anticipated the boss's next position. Some changes increased damage but caused more hits, so they were rejected. Adding safety checks for the action's start, movement path, and stopped position produced a candidate that passed comparisons on 12 fixed cases, then went on to full-game simulation and a live API/subscription run. [Full case study](docs/touhou-research-record.md).

A **policy** is the gameplay instructions, fixed notes supplied with each request (called memory), output format, and request settings. Codex improves the prompts and settings without changing the model's weights.

Autoresearch took place in Codex Goal mode with human guidance; `sol simulate` runs one game experiment, while Codex handles the analysis and edits across experiments. [Research stories for each game](docs/autoresearch-summaries.md).

## How a game runs

Take Touhou as an example:

1. **Capture.** The runner collects up to three recent screenshots with their frame numbers. Comparing the images helps the agent judge which way the boss and bullets are moving.
2. **Ask.** Send those images with the game instructions, controls already in effect, historical delay information, and the agent's own earlier position estimates. The agent does not receive hidden game coordinates or the delay drawn for this request.
3. **Answer.** The coding agent returns JSON containing its visual estimates and an action plan.
4. **Execute.** The runner checks the format, waits until the answer is allowed to take effect, and applies the chosen buttons. The position estimates do not become automatic dodge or tracking commands.

### Concurrent requests

An answer can take seconds. Sending requests while earlier ones are still waiting can keep decisions coming more often, or provide several chances to get an answer sooner. The games use three request patterns:

| Game | Requests | How answers are used |
|---|---|---|
| **Touhou** | **Four requests per observation**; next group after the selected move finishes and slots are available. | Use the first valid answer; the other answers for that observation cannot replace it. |
| **Asterix** | **One request at a time.** Observe again after the previous reply. | Hold the chosen direction until a new answer replaces it. |
| **Rhythm** | Try a new screenshot **every 0.2 seconds**, with **up to 16 requests waiting**. Skip sending when full. | Execute the model's tap times, skip expired taps, and prevent duplicate presses using action IDs. |

More requests also mean more calls, cost, and potentially outdated answers. Asterix's serial setup followed limited trials in which overlapping requests appeared to encourage repeated movement. [Request ordering, capacity, and experiment details](docs/latency-aware-learning.md).

A **recipe** is a JSON file selecting a policy, latency profile, and run settings. See the selected recipes: [Touhou simulation](recipes/touhou.json), [Touhou live run](recipes/touhou-realtime.json), [Rhythm](recipes/rhythm.json), and [Asterix](recipes/asterix.json).

### Action example

One action in the plan might be:

```json
{"move": 3, "shoot": 1, "focus": 1, "bomb": 0, "duration": 12}
```

This means: move right, keep shooting, use slow focused movement, do not use a bomb, and hold for 12 game frames (0.2 seconds at 60 FPS).

In Touhou, movement stops when the plan ends; shooting and focus keep their last settings. A newer accepted decision replaces the unfinished plan. Older observations cannot override a decision already accepted from a newer one.

## Games and controls

The coding agent chooses button presses in screen-based games and tactical goals in robot games.

| Game | Agent input | Agent action | Code execution |
|---|---|---|---|
| [Touhou / Kaguya](docs/touhou-research-record.md) | Recent screenshots, frame times, prior controls | Direction, shooting, focus, bombs, duration | Apply chosen buttons for the specified duration |
| [PingPong](docs/tabletennis.md) | Two camera views, feedback, opponent estimate | One of four return-placement plans | Track the ball, serve, plan contact, execute joint motion |
| [Asterix](docs/asterix-autoresearch.md) | Three timestamped screenshots, action history | Joystick direction | Hold direction until replaced |
| [Badminton](docs/badminton.md) | Recent frames from two cameras, public feedback | Conditional shot goals, recovery position, goal duration | Plan contact and swing; execute stroke |
| [Rhythm](docs/rhythm.md) | Screenshot, public clock, pending taps | DFJK keys, absolute tap times | Queue and execute specified taps |
| [Racing](docs/racing.md) | Front-camera views, telemetry, visual road measurements | Speed, lane offset, lookahead | Steer toward goal, limit speed through bends |

Evaluators may inspect game state to score outcomes. [Observation boundaries](docs/observation-contract.md).

## Game environments

| Game | Implementation | Source / inspiration |
|---|---|---|
| **Touhou / Kaguya** | Our simplified practice environment | [Touhou: Imperishable Night](https://www16.big.or.jp/~zun/html/th08top.html); original-game presentation assets |
| **PingPong** | Upstream environment; our agent interface and controller adaptations | [Embodied Olympics Exam](https://olympics.embodied-first-exam.ai/) |
| **Asterix** | Atari game through ALE; our agent runner | [Arcade Learning Environment](https://ale.farama.org/environments/asterix/) |
| **Badminton** | Upstream environment; our agent interface and controller | [Embodied Olympics Exam](https://olympics.embodied-first-exam.ai/) |
| **Rhythm** | Our four-lane browser game | Inspired by [Rhythm Master](https://apps.apple.com/cn/app/%E8%8A%82%E5%A5%8F%E5%A4%A7%E5%B8%88/id493901993) |
| **Racing** | Upstream environment; our agent interface and steering controller | [Embodied Olympics Exam](https://olympics.embodied-first-exam.ai/) |

[Full results and comparisons](https://github.com/sooool-project/sooool/blob/main/docs/results.md) · [Validation history](https://github.com/sooool-project/sooool/blob/main/docs/validation.md).

## Quick start

While the benchmark repository is private, install GitHub CLI and run
`gh auth login` before downloading the framework wheel. Public downloads use curl.

```bash
bash scripts/fetch-latency.sh
uv sync --locked --python 3.12
uv run playwright install --with-deps chromium
codex login

uv run sol doctor --game touhou --auth
uv run sol simulate touhou --output runs/touhou-dev-001
```

For a live API/subscription run of Touhou, provide an API key through `OPENAI_API_KEY` or the hidden prompt, and set a spending limit:

```bash
uv run sol eval touhou \
  --seed 1 \
  --budget-usd 5 \
  --max-calls 100 \
  --output runs/touhou-api-001
```

Game setup: [Touhou](docs/realtime.md) · [PingPong](docs/tabletennis.md) · [Asterix](docs/release-guide.md) · [Badminton](docs/badminton.md) · [Rhythm](docs/rhythm.md) · [Racing](docs/racing.md)

More commands: [Release guide](docs/release-guide.md) · Comparing strategies: [Development guide](docs/development.md)

## Code guide

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

## Citation

```bibtex
@misc{wang2026sooool,
  title        = {{Sooool! Agent as Real-Time Policies}},
  author       = {Wang, Zihan and Li, Xinyuan and Li, Zeju and Lin, Yuxiang and Gui, Chi and Pei, Jiaxin and Li, Manling},
  year         = {2026},
  url          = {https://github.com/sooool-project/sooool}
}
```
