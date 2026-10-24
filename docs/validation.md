# Package validation

This page retains validation from multiple releases. [Current results and conditions](results.md) provides the six-game overview; historical test counts below describe their own source checkpoints. For the current Rhythm v21 result and portable checks, start at [Selected Rhythm v21 package](#selected-rhythm-v21-package). The older 30-second Rhythm results below belong to an earlier release, not the current 17-second demo.

Initial validation used an isolated Ubuntu directory and new Python virtual environment with this repository’s runtime and assets. The source machine’s suite is not required by the launcher; an explicitly selected native Codex executable supplies the existing ChatGPT login.

## Historical initial-release cold replays

- Touhou: all 19 applied actions reproduced the exact final engine state of the original 51.05-second API win, with two hits. This is replay of saved API actions, not a new API or policy win.
- Rhythm: all 215 saved capture times and model delivery events were replayed; the exact evaluator state matched (50 PERFECT, 1 GREAT, 1 MISS, 2 empty presses). Screenshot PNG hashes differed on the new browser/machine and are explicitly not claimed identical. The historical summary's legacy `passed` flag does not meet the current strict full-combo criterion.

Reports are retained with validation evidence. Those earlier Rhythm/Touhou records retain their original engines and policies. The selected Asterix runtime has since changed to direct serial actions; its validation is separate below.

## Tests

Six package contracts cover fitted inverse-CDF interpolation/reproducibility, clock conversion, readiness versus terminal capacity, immutable shared cohort inputs and full profile inventories. Existing Rhythm joint-timing tests (3), Asterix timing tests (5), HopControllerV3 tests (6), and Touhou engine tests (8) passed. Local doctor reset ALE and launched Chromium; Ubuntu doctor additionally confirmed a ChatGPT subscription login.

## Historical initial-release subscription simulations

The frozen runs from that release use real `gpt-6.1-sol / low` decisions, with imposed historical profile timing. That release’s Rhythm run completed 30.001 seconds: 50 PERFECT, 1 GREAT, 1 MISS, one empty press, max combo 33; 203 requests, 191 delivered plans, zero provider errors and zero transaction rejections. It matches the historical score of 50,700 but does not meet strict full-combo acceptance.

The final Touhou seed-9 run completed as a game loss at 48.8167 game seconds: three hits, no lives/bombs remaining, Boss HP 260; 68 model requests, 16 applied plans, zero invalid actions. This single fresh run does not reproduce the prior development win and does not establish stable success. The failure evidence is retained. Earlier adapter attempts include another loss and are labeled migration diagnostics, not additional fixed-condition trials.


A shallow clone of the committed source branch was installed in another fresh Python 3.12 virtual environment and passed doctor plus all six package contracts without fetching the evidence branch. The default tracked source/assets are approximately 16 MB.

The earlier validation installed the Rhythm and Touhou Gym packages through the root uv workspace. Current setup installs each package in its game’s independent venv. Their Gym API checkers, registered environment creation and complete environment episodes passed; those checks use no SOL policy and are not performance evidence.

The initial package validation used historical profile simulation and real subscription decisions. No paid API evaluation was run during that initial validation. Subsequent Touhou results are separately recorded in its record index. The frozen policies were not retuned to hide losses.

## Selected Asterix: direct serial V28

The default is V28 with one request, unchanged direct actions and brief public English summaries. Historical seed-5 profile simulation completed 20 game seconds at 500 points/two lives; the action-only comparison scored 250/one life. Both retain raw records under `artifacts/asterix/serial-selected/`. The previous Hop3 three-seed scores are a different execution condition and are not claimed by this release.

The new portable loop passes a whole-trajectory zero-model confirmation using the 44 saved public replies: all 1,200 step actions/rewards/lives and all request screenshot hashes reproduce, at 500 points/two lives. This check ran locally with Python 3.12.3, ALE 0.11.2 and the locked dependencies. It is replay evidence, not a fresh independent performance trial.

The root tests additionally cover an actual-clock loop with a delayed response, no game pause during model waiting, invalid-reply interruption preservation, exact selected task bytes, schema validation and append-only assessment provenance. Real subscription checks are recorded separately under `artifacts/asterix/portable-validation/` as they complete. A short realtime smoke test verifies transport/clock behavior, not 20-second realtime reliability.

The desktop-managed CLI on the local machine timed out at app-server initialization before any model request. The standalone native 0.162.1 executable on the existing Ubuntu experiment host passed subscription authentication. `SOL_CODEX_BIN` must point to a functioning native app-server executable; a matching version string alone is insufficient.

## Fresh selected-policy portable runs

Both commands completed using the standalone native CLI 0.162.1 and real ChatGPT subscription replies. No paid API calls occurred. [Frozen manifests, public outputs and assessments](../artifacts/asterix/portable-validation/) record the exact source; its runtime hashes match immutable commit `0bcfc45`.

| Mode | New model calls | Result | Clock |
|---|---:|---|---|
| Fresh portable simulation, seed 5 | 44 | 20 game seconds, 300 points, one life | Historical sampled API delays; native computation paused outside virtual time |
| Actual-clock subscription smoke, seed 5 | 4 | 5 game seconds, 50 points, three lives | 25.00026 wall seconds; maximum frame lag 4.29ms; three unchanged model actions applied |

The fresh simulation did not reproduce the historical 500-point score. Both use the selected strategy, but the original suite transport and portable app-server are separately recorded conditions, and model decisions are stochastic. The historical replay remains available as development evidence; the current README demonstration uses the later paid API repeat documented below. The short actual-clock test verifies functional transport and continuous timing, not full-game reliability or ultrafast API latency.

The source host used Python 3.10.22, Gymnasium 0.29.1 and ALE 0.8.1 for these real calls. Local locked-environment replay used Python 3.12.3, Gymnasium 1.2.3 and ALE 0.11.2 and reproduced the selected trajectory exactly. Both successful and interrupted migration checks remain explicitly distinguished. The merged Racing dispatch and subsequent failure-record fixes do not change the successful Asterix action path; their tests remain part of the final branch.

## Fresh Asterix paid API validation

Two seed-5 V28 trials completed 720 frames / 60 wall seconds at 12 raw FPS (5× slowdown). The first scored 50 points/one life with 25 settled calls; the repeat scored 300 points/two lives with 31 settled calls. Each used `gpt-6.1-sol / low / ultrafast`, one in-flight request and unchanged held model actions. Recorded wall times were 60.001717s and 60.000341s. Neither trial establishes native-speed performance or an independent reliability estimate.

The full repeat-run video is a saved-action replay, with all 720 rewards, scores and life counts checked against ALE. It preserves 60-second timing; its original procedural music and game-panel color adjustment are documented separately. Both raw run archives include prompts, PNG inputs, public responses, transport metadata, applied actions, source snapshots and frozen manifests. The earlier unknown reservation remains charged; all 67 requests in the new cumulative ledger are settled. [Run table, budgets and replay instructions](../artifacts/asterix/api-validation/20261017/README.md).

## Selected v2 realtime workflow

The portable `sol eval touhou` and strictly serial `sol profile touhou` paths are now available. Current validation is recorded per run, with exact source hashes, clocks, terminal accounting and outcome. See [the case study](touhou-research-record.md) and [record requirements](evaluation-records.md); these entries do not overwrite the earlier portable seed9 loss.

Fresh paid full-game validation of the new portable CLI is **pending at the user's request**. Offline checks: 149 Touhou research tests (6 skipped), 24 root entrypoint/record tests (including the merged Racing checks) and 8 engine tests passed; local and isolated Ubuntu doctors launched Chromium145. A three-input serial API smoke collected valid measurements, then exposed a console entrypoint returning a dictionary as an error exit. That exit bug was fixed with an offline regression test; no additional paid profile or realtime run was started. Existing live successes remain historical source-harness evidence, not claims about the new launcher.

## Selected Rhythm v21 package

The active recipe replaces v19 with the exact selected memory, aligned25-note17s chart,2.5s approach and original streamed API action/comment protocol. Earlier validation above describes historical releases. The selected source-harness API result is24 Perfect,1 Great,zero Miss,two empty presses,98.8%; it is not full combo. New portable entrypoint validation is recorded separately; see [the case study](rhythm-autoresearch.md).

The first portable API migration attempt was interrupted after authentication rejection, not counted as gameplay validation. Its32 unknown reservations remain counted under the existing cumulative ceiling. Admission now stops immediately on401/403 and the native loop stops issuing captures for decisions; a separate fresh run verifies the corrected transport. No failed record is overwritten.

Fresh portable validation completed: subscription simulation17s scored25/25 Perfect,zeroMiss,zeroempty,with85 actual subscription requests and zero API calls. The corrected real API run completed25 judgments with71 settled calls and zero provider errors, but scored9P/1Great/2Good/13Miss/13empty and had0.692095s audio/external-clock drift. It fails the source-harness0.2s clock gate and full-combo gate. These conditions differ in host/browser from the selected Ubuntu case; the reason for the drift is not yet isolated. This verifies live transport/accounting, not portable reproduction of the headline score. All diagnostics remain under`artifacts/rhythm/portable-validation/`; no paid retry was made.

Offline validation: 47 root tests and 73 Rhythm contract/streaming/financial tests passed. The shared-ledger symlink test verifies one canonical lock,retained unknown charges and immutable registry IDs.

The portable confirmation used USD1.985646 in known charges. The malformed-credential migration attempt retains USD2.644320 in conservative reservations; it was not silently released. Cumulative experiment commitment is USD77.767684 of the user's USD80 ceiling,including all older uncertain reservations. No further paid test was started.

After merging the latest PingPong main changes, root discovery ran 63 tests successfully (5 skipped) with its separate Numba, SciPy and video dependencies installed. The 73 Rhythm tests also passed. No hosted checks were configured on the PR at submission.

## Independent environment setup (2026-10-22)

The root venv contains only the `sol` launcher. Asterix, Touhou and Rhythm were
prepared in separate Python 3.12 venvs. PCBA retained Python 3.11. All three
original-game doctors passed, including Chromium 145.0.7632.6. The browser setup
used verified upstream archives through a loopback mirror after a CDN interruption.

- 28 launcher, preparation and record tests passed. Local Git fixtures cover
  external-source setup, dependency changes, failed installs, arguments, working
  directories, exit status and process termination.
- 17 Asterix tests passed. Saved-action replay verified all 1,200 frames and 44
  retained observations at the historical 500-point/two-life result. This is
  replay evidence with zero model calls.
- 149 Touhou research tests passed with six browser tests initially skipped.
  Those six browser tests then passed against the local frontend. Eight Node
  engine tests, seven root policy/record tests and the Gym checker also passed.
- 73 Rhythm research tests, seven workflow tests and the Gym checker passed.
- 29 PCBA tests passed in Python 3.11. The registered `realtime-smoke` command
  rendered both cameras while physics advanced and rejected a stale command.

These checks made no subscription or paid API model calls. External game build
scripts and assets were not rebuilt for this launcher migration.

## Tetris environment (2026-10-24)

Selected `v11-short` run with `sol eval tetris` (actual clock, 2× slowdown, three 60-second episodes, 57 serial
Claude Code CLI calls), plus simulation, rules baseline and 1× comparison, all registered in
[`artifacts/tetris/evaluations.jsonl`](../artifacts/tetris/evaluations.jsonl). The selected run replays from the
repository copy with zero model calls (Python 3.12.3, Pillow 12.1.1, Claude Code CLI 2.1.310). 17 offline tests
and the shared/environment CI checks pass; no GPT runs were made. [Details](tetris.md).

## Shared experiment workflows (2026-10-22)

The follow-up keeps each game's selected provider, control abstraction and clock.
Installation supports explicit game selections and `all`. New experiment runs use
shared records and registration. Browser libraries remain host prerequisites;
`ready` records installed sources and packages.

- 30 launcher, preparation, parameter and registration tests passed. The fixtures
  cover multiple selections, alias deduplication, existing-output protection,
  initialization failures, immutable IDs and mismatched game/run identities.
- 149 Touhou research tests passed against a loopback frontend, including browser
  startup, image capture, literal actions and cleanup.
- 73 Rhythm research tests and six workflow tests passed. An additional browser
  probe loaded the actual page in virtual and native modes, captured 390×844
  images, executed a literal key event and confirmed browser shutdown.
- Eight Asterix runner/default tests and 12 API/failure/Touhou-record tests passed.
  Saved-action replay retained the historical 1,200-frame, 44-reply, 500-point,
  two-life result. This is replay evidence with zero new model calls.
- 15 Racing transport/controller unit tests passed with an import fixture and
  mocked HTTP. These checks did not run the native Racing engine.
- 12 Badminton and 19 TableTennis contract tests passed. Three Badminton and five
  TableTennis tests were skipped because their pinned native runtime was not
  prepared. The new TableTennis credential test used mocked HTTP and verified
  usage settlement and the absence of credentials in retained files.
- 43 PCBA tests passed in Python 3.11. Shared records contain aggregate metrics
  and link the full report. The registered process-clock preflight captured three
  camera views, advanced 1.330 simulated seconds in 1.330 wall seconds, reported
  zero late ticks and passed its timing gate.

The selected Asterix, Touhou, Rhythm and PCBA environments were prepared through
one multi-game setup invocation. Python compilation, shell syntax and the locked
root dependency check passed. No subscription or paid API model calls were made.
PvZ/VERA20K native builds and resource-dependent gameplay were not rerun. Their
setup remains separate from model-runner integration.
