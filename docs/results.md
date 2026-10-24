# Current results and execution conditions

The root recipes select one task policy per game. Autoresearch trains these
policies through repeated interaction, prompt/memory refinement and strategy
search, with frozen base-model weights. This page identifies the active setup
and the evidence behind each displayed result. Practice, simulation, live
execution and replay each answer a different question.

| Game / environment | Model decisions and execution | Displayed or selected result | Current launcher validation |
|---|---|---|---|
| Rhythm: custom DFJK practice game | GPT outputs each key and absolute tap time; generic executor queues unchanged times. 1× music, 2.5s visual approach. | Selected 17s/25-note API run: 24 Perfect, 1 Great, 0 Miss, two empty presses. | Fresh portable simulation: 25/25 Perfect. Portable API trial completed but failed clock integrity; the headline score remains source-harness evidence. [Records](rhythm.md). |
| Touhou: simplified Kaguya practice arena with original-game presentation assets | GPT selects every movement, shot, focus, bomb and duration. Four-way same-observation race; 1× engine. | Selected English source-harness API run: boss defeat in 58.47 game seconds, two hits. | Fresh paid full-game validation of the portable launcher is pending. Earlier portable simulation loss remains recorded. [Records](touhou-research-record.md). |
| Racing: pinned native RoboOlympics L1 | GPT selects tactical goals; 5Hz visual tracker steers and limits bend speed. | GPT-guided policy won 7/7 recorded matches versus 3/7 fixed-goal baseline on the same seeds: six subscription/profile runs plus one actual 1× API run. Seed304 API won 2:0; English-summary retake won 2:1. | Historical input/image conditions and mixed clocks are documented alongside the positive comparison. [Records](../research/racing/EVALUATION.md). |
| PingPong: pinned native RoboOlympics L1 | GPT selects persistent shot policy; public-camera reference serves, tracks and executes joints. Four staggered workers, 1× target. | Two actual API matches with the same implementation: seed11 won 5:1; seed12 lost 3:5. | Complete recorded matches and native-pose video are retained. These are two task outcomes, not an estimated stable win rate. [Records](../artifacts/tabletennis/README.md). |
| Badminton: pinned native RoboOlympics L1 | GPT supplies conditional placement/recovery goals; camera/native planner executes. Simulation and actual API use S3 = 3× slowdown. | Latest retained actual API match: 8:11, 90/97 legal returns, 5/9 legal serves, 47 confirmed Ultrafast responses and zero rule fallbacks over 90 controlled rally strokes. | Native replay matched all 27,609 steps. The recorded match predates the latest public-input acknowledgement filter correction; later code changes are not attributed to this outcome. [Records](../artifacts/badminton/README.md). |
| Asterix: ALE game, selected direct serial V28 | GPT selects held joystick action; one request in flight. 12 raw FPS = 5× slowdown. | Fresh paid API repeat: 300 points, two lives, 720 frames / 60 wall seconds (12 game seconds); 31 settled requests. | The first completed API trial under the same conditions scored 50 points/one life; both runs and all terminal usage are retained. Historical 500-point sampled-delay simulation and subscription checks remain separate. [API evidence](../artifacts/asterix/api-validation/20261017/README.md) · [Historical validation](validation.md#selected-asterix-direct-serial-v28). |
| Tetris: our deterministic engine, classic one-piece preview, selected `v11-short` | Claude Opus (low effort, stateless CLI) names one placement per piece from three timestamped screenshots at one-second ticks; a key script executes it without reading the board; one request in flight. 2× slowdown declared. | Fresh portable actual-clock run, three 60-second episodes at start levels 1/3/5: 5.67 lines and 0.33 new holes per episode, 3/3 alive, one of 55 decisions created an avoidable hole, wall delay median 5.3 s. | True-board rules baseline under the sampled profile: 5.67 lines, 1.67 holes, 3/3. A longer-rule candidate (`v12c`) fixed one decision on fixed screenshots but answered more slowly (up to 1.5 s per call) and lost pieces to stale answers at level 6: rejected. Normal speed fails level 5 for policy and baseline alike. All runs replay without model calls. [Records](tetris.md). |
| PCBA test cell: our MuJoCo workcell with a recirculating belt, fixture and magazines | GPT outputs every literal 50 ms XYZ/yaw step, vacuum and fixture request; executor only validates limits and guards. Two staggered workers. | Subscription simulation on a virtual clock (modeled ultrafast delays, mean 3.87 s): best run picked 5, tested 4 and correctly sorted 4 boards, 3 before the 150 s deadline; no run has finished all five on time. | 26 retained simulations on the revised belt; live Fast runs on the loop sorted no board, the stopped-line live run sorted 4/5 in 600 s. [README section](../README.md#pcba-test-cell-belt-to-magazine) · [Records](../artifacts/pcba/simulations.json). |

“Actual API” means actions were produced by live API inference while that run’s
clock advanced; it does not imply native game speed. “Subscription simulation”
uses fresh model decisions but can wait for computation outside virtual time.
“Replay” verifies or presents saved actions and makes no new decisions. A video
can be a live screen capture or a verified offline render; [clip provenance](../assets/gameplay/README.md)
identifies which. Public decision summaries are model-authored output, not private
reasoning or certified observations.

The CLI’s `--seed` is game-specific. Rhythm simulation changes delay draws on a
retained chart; native Rhythm evaluation uses that fixed chart. Other games retain
their declared environment seeds. A new seed or a fresh run must not silently be
promoted to a new-chart or unseen-task claim.

[Learning and control](latency-aware-learning.md) · [Workflows](file-map.md) ·
[Validation history](validation.md) · [Profile inventory](../profiles/README.md)
