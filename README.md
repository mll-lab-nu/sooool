# Sooool!

**GPT-Sol learns to act under latency. In real-time evaluation, the game keeps moving while the model thinks.**

Sooool! uses an auto-research loop to get GPT-Sol to play real-time games, in both computer use and robotic settings. GPT-Sol sees the  current observation (visual frames), decides what to do, and sends an action. Then it sees what happened and decides the next action again. During real-time evaluation the environment keeps moving while the model thinks, so a good decision can arrive too late. Development simulation uses a virtual clock and can wait for model computation.

The gameplay decisions come from GPT-Sol on each turn. The surrounding code handles observations, timing and execution, with each game declaring its control setup below.

<table>
<tr>
<td width="50%" align="center"><a href="assets/gameplay/touhou.mp4"><img src="assets/gameplay/touhou.gif" alt="GPT-Sol dodging Kaguya's bullet patterns with live English decision summaries" width="440"></a><br><b>Touhou</b> · Real-time API · 1×</td>
<td width="50%" align="center"><a href="assets/gameplay/racing.mp4"><img src="assets/gameplay/racing.gif" alt="GPT-Sol selecting racing targets through bends and obstacles, with live decisions" width="440"></a><br><b>Racing</b> · Real-time API · Hybrid steering</td>
</tr>
<tr>
<td width="50%" align="center"><a href="assets/gameplay/asterix.mp4"><img src="assets/gameplay/asterix.gif" alt="GPT-Sol collecting food in Asterix alongside original public decision summaries" width="440"></a><br><b>Asterix</b> · Profile simulation replay · 5× slowdown</td>
<td width="50%" align="center"><a href="assets/gameplay/badminton.mp4"><img src="assets/gameplay/badminton.gif" alt="SOL badminton: opening serve and rally, with both camera views and original English decision summaries" width="440"></a><br><b>Badminton</b> · Real-time API replay · S3 slowdown · 15s</td>
</tr>
<tr>
<td width="50%" align="center"><a href="assets/gameplay/rhythm.mp4"><img src="assets/gameplay/rhythm.gif" alt="GPT-SOL choosing literal DFJK tap times:24 Perfect,1 Great,zero misses,two empty presses" height="270"></a><br><b>Rhythm</b> · Real-time API · 1× · 24 Perfect / 1 Great / 0 Miss</td>
<td width="50%" align="center"><a href="assets/tabletennis/seed11-full.mp4"><img src="assets/gameplay/pingpong.gif" alt="GPT-SOL playing table tennis with both camera views and live public decision summaries" width="440"></a><br><b>PingPong</b> · Real-time API · 1×</td>
</tr>
</table>

You can watch GPT-Sol dodge bullets, race a rival, collect food, play robot table tennis and badminton, or hit notes with the music. Then inspect its decisions, change the policy, and send it back into the game.

**Simulated latency. Real model decisions.** During development, cheaper inference drives fresh decisions from actual game frames, with actions delivered under a measured API latency profile. Freeze a candidate, then evaluate it with the real API while the game clock keeps running. The repository includes the environments, prompts, profiles, runners and experiment records for this loop.

## Games

[Current results and execution conditions](docs/results.md) maps each selected policy to its clocks, controls and evidence.

| Game | Job | Demo |
|---|---|---|
| **Touhou / Kaguya practice arena** | Dodge bullets. Defeat the boss in a simplified Touhou-inspired environment. | Real-time API at 1×. GPT-Sol chooses movement, shooting, focus, bombs and duration. |
| **Racing** | Find a line. Beat your rival. | Real-time API at 1×. GPT-Sol chooses speed and racing targets; a coded controller supplies steering. [Recorded comparison: GPT 7/7, fixed goals 3/7](research/racing/EVALUATION.md#recorded-gpt-and-no-gpt-comparison). |
| **Rhythm** | Hit the right key at the right time. | Real-time API at 1×. GPT-Sol chooses each DFJK key and its absolute tap timestamp. [Setup](docs/rhythm.md). |
| **PingPong** | Serve, return, win the point. | Real-time API at 1×; subscription simulation with a historical API timing proxy. GPT-Sol selects shot placement; rules handle serving and execution. [Setup](docs/tabletennis.md). |
| **Badminton** | Place the shot. Recover for the next one. | Actual API at 3× slowdown (S3); SOL selects tactical goals, native mechanics execute them. [Setup](docs/badminton.md) · [Evidence](artifacts/badminton/README.md). |
| **Atari Asterix** | Collect food. Avoid enemies. Stay alive. | Historical delay simulation at 5× slowdown, with model actions applied unchanged. |

The GIFs are continuous excerpts at their source playback speed. Racing uses hybrid steering. Touhou, Racing, PingPong, Badminton and Asterix show original public decision summaries. Rhythm shows original English action-plus-commentary responses; its 17s run has two empty presses and is not a full combo. These are selected demonstrations, not win-rate estimates. [Clip sources and cuts](assets/gameplay/README.md).

The Badminton clip shows the opening serve and rally from one seed-101, L1/S3 match. The full match lost **8:11**, with **90/97 legal returns**, **47 confirmed Ultrafast responses**, zero rule fallbacks across 90 controlled rally strokes, and four serve failures. Its native replay matched all 27,609 steps. [Protocol and evidence](artifacts/badminton/README.md).

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

## How it works

We developed these policies by giving Codex a goal in **Goal mode** and letting it work through trial and error. We supplied the environment, objective, constraints and occasional feedback; Codex ran experiments, inspected failures, proposed changes and tried again. This is the **autoresearch** loop behind the demos.

1. **Set a goal.** Give the agent a game, a target outcome and an experiment budget.
2. **Profile and play.** Measure the target API’s latency, then develop with fresh GPT-Sol decisions under sampled delays.
3. **Try, inspect, revise.** The agent runs episodes, reads trajectories and replays, changes the instructions or permitted control setup, and compares candidates. Human feedback can steer the next experiment.
4. **Freeze and verify.** Select a candidate from the recorded comparisons, freeze its configuration, and test it against the real clock. Keep the failures, timing, costs and outcomes alongside the wins.

Codex runs the research loop; GPT-Sol makes the online gameplay decisions. Repeated play trains the task policy through prompts, memory and strategy search, with base-model weights frozen. The demos show the resulting task skills under their recorded game speeds and control abstractions.

**Keep decisions flowing while the model thinks.** Overlapping requests lets the system observe again before earlier inference finishes. The policy learns to predict when its actions will arrive and plan ahead; staggered requests sustain decision cadence, while same-observation races provide additional chances to meet a deadline. [Latency-aware learning and control](docs/latency-aware-learning.md) explains the two mechanisms and their evaluation.

**[Check autoresearch summaries →](docs/autoresearch-summaries.md)**

### Rhythm: from delayed decisions to near-perfect timing

The selected v21 policy reads full-board screenshots and outputs each DFJK key, ID, absolute tap timestamp and expiry. Timestamps use the executor’s monotonic clock. The executor queues those exact commands and presses at the supplied times; it does not convert note coordinates into tap times or correct the model’s predictions. Public note-speed and screenshot-time calibration are provided to the model.

The selected real-time API run achieved **24 Perfect / 1 Great / 0 Miss (98.8% weighted accuracy)** over a 17-second preview, with two empty presses. Music runs at 1×, with 2.5 seconds of visual note approach. This is one reused-chart episode; the two empty presses broke the combo.

[Selected research path](docs/rhythm-autoresearch.md) · [Run/profile/record and portability limits](docs/rhythm.md) · [Machine-readable evaluation history](research/rhythm/evaluation-history.jsonl)

```bash
uv run sol simulate rhythm --output runs/rhythm-dev-001
uv run sol profile rhythm --episode artifacts/rhythm/selected --budget-usd 1 --max-calls 20 --output runs/rhythm-profile-001
uv run sol eval rhythm --budget-usd 5 --max-calls 90 --output runs/rhythm-api-001
uv run sol record runs/rhythm-api-001 --registry artifacts/rhythm/evaluations.jsonl
```

## Play a round

Start with a development run. You need Linux, Python 3.10–3.12, Chromium-compatible dependencies, and a Codex CLI signed in with a ChatGPT subscription supporting the configured model. The tested native CLI is 0.162.1.

```bash
uv sync --locked --python 3.12
uv run playwright install --with-deps chromium
codex login

uv run sol doctor --game touhou --auth
uv run sol simulate touhou
```

This sends actual game screenshots and prompts to the subscription model and schedules actions using a historical latency profile. Simulation can wait for model computation; scores from this mode are development results. There is no paid API fallback.

To evaluate Touhou against the real clock:

```bash
uv run sol eval touhou \
  --seed 1 \
  --budget-usd 5 \
  --max-calls 100 \
  --output runs/touhou-api-001
```

Real-time Touhou evaluation requires an OpenAI API key, read from process memory or prompted without echo. The game keeps running while requests are in flight. The runner records inputs, public decision summaries, applied actions, timing, video and cost. The retained source-harness demo defeated Kaguya; fresh full-game paid validation of the portable launcher is pending. [Setup, budgets and timing](docs/realtime.md).

Racing and PingPong use separate native dependencies. See the [Racing workflow](docs/racing.md), [PingPong tactical setup](docs/tabletennis.md), [Badminton setup](docs/badminton.md), and [complete release guide](docs/release-guide.md) for their conditions and entrypoints.

## Make it play better

The fun part is watching a policy fail, figuring out why, and trying again.

Did it dodge where the bullet was, instead of where it was going? Did it commit to a turn too late? Did a useful explanation delay the action that could have saved it?

Inspect the replay, change the prompt or control representation, evaluate the candidate, and keep the evidence. Freeze a candidate before real-time evaluation. The research records preserve failed attempts alongside the selected policies.

The selected Touhou policy was trained through repeated play, prompt and memory refinement, human feedback and evaluation. Its base-model weights remain frozen; the learned artifact is the task policy.

- [Touhou research](docs/touhou-research-record.md): feedback, policy changes and the selected boss-defeat run.
- [Racing experiments](research/racing/EVALUATION.md): candidate policies, full cohorts and transfer to real-time gameplay.
- [Asterix experiments](docs/asterix-autoresearch.md): direct model actions and the selected serial policy.
- [PingPong research](docs/tabletennis.md): tactical policies, asynchronous execution and actual API results.
- [Evaluation records](docs/evaluation-records.md): conditions, replays and appended research decisions.

## Code

| Path | Contents |
|---|---|
| `runtime/` | Subscription transport, launchers and run records |
| `environments/` | Game engines, interfaces and game-specific controllers |
| `policies/`, `recipes/` | Prompts, output formats and executable configurations |
| `profiles/` | Measured latency samples and provenance |
| `research/` | Development records, comparisons and retained discussions |
| `artifacts/`, `assets/` | Evidence indexes, videos and README highlights |

[Current results and conditions](docs/results.md) · [File map](docs/file-map.md) · [Validation](docs/validation.md) · [Timing](docs/timing.md) · [Optional evidence](artifacts/README.md)

Large evidence archives are optional; you can run the source package without downloading them. Public decision summaries are short model-authored outputs, not internal reasoning transcripts. GIFs have no audio; source-video music and editing are documented per artifact.

This is a private research package. Repository access does not grant an additional license to upstream code or media. See [source and media provenance](docs/provenance.md) before redistribution.
