# Profile inventory

Badminton’s selected goal-v2 recipes use `badminton/conditional-api-10.json`: 10 serial API Ultrafast samples retaining complete-valid-JSON readiness and terminal service time from the realtime transport. Both simulation and actual API evaluation use S3 (3× slowdown); subscription simulation disables Fast and samples this profile, while actual API delivery uses real response timing. The older API20 and API100 profiles remain historical evidence. See [Badminton](../docs/badminton.md).

Default simulation recipes select one exact profile each; older profiles are archived separately for development provenance.

| Default | Raw representation | Sampling and clock |
|---|---|---|
| Rhythm `selected-native-joint.json` | 85 completed selected-v21 API rows: action readiness, frame age, transport overhead and terminal occupancy | Whole-row empirical resampling; continuous virtual seconds; sampled future delays hidden |
| Touhou `profile-control-tracking-safe-intercept-v2-transport-v1.json` | 19 modeled four-candidate readiness/terminal vectors, transporting selected-task serial timing into historical race cohorts | Whole-vector resampling, at 60 visual-clock frames/s; terminal slots remain occupied |
| Asterix `latency_v16_actual_5x_512cap.json` | 536 valid capture-to-complete delays from the historical V16 API campaign | Empirical IID, `ceil(seconds × 12)` raw frames at 5× slowdown; long tails retained |
| Tetris `claude-opus-low-serial-v0.json` | 68 capture-to-apply wall seconds from a serial real-clock Claude Opus (low effort) run of an earlier, longer prompt of the policy lineage (mean 6.15 s, median 5.93 s) | Empirical IID, `ceil(seconds / slowdown × 60)` frames; a new profile is the wall times of a serial `sol eval tetris` run |

Asterix's earlier 1/8-speed `sol-ultrafast-v*` directories include `profile.json`, fitted quantile distribution and temporal burst companions. Their original interpolated inverse-CDF sampler is retained under `vendor/`; they are not silently selected for V28 5× simulation.

Touhou’s default `recipes/touhou.json` selects the transported v2 profile. It is a model of selected-task timing, not a fresh concurrent measurement. `profile-control-early-study-v1.json` retains the earlier empirical development condition used for the original policy comparisons. Those historical scores retain that older profile identity.

Rhythm’s default profile is derived from `artifacts/rhythm/selected/requests.jsonl`, matching the selected 17s, 2.5s-approach experiment. The older native-v17 profile is historical research evidence.

`artifacts/calibration-inputs.tar.gz` contains Rhythm's historical raw native-v17 request source and Touhou's tracking serial inputs/measurements. Asterix's original 596 source requests are included in `artifacts/asterix-calibration-requests.tar.gz`; both source file hashes were checked against the empirical profile. No fresh API latency measurement is implied by these exports.

## Racing

`racing/profile.json` and `measurements.jsonl` preserve the 32 strictly serial paid API measurements used for early development. Minimum 0.984s, median 1.350s, P95 2.258s. This measured one-frame direct steering, not the selected two-frame lane-goal workload or concurrent traffic; its use in current simulations is explicitly a historical proxy. `scripts/racing.py profile` measures selected-policy recorded inputs serially and saves a new profile without overwriting this reference. See [Racing](../docs/racing.md).

The selected Asterix serial recipe uses the historical V16 valid-response sample list, with delay RNG seed `91 + game_seed`. It retains long tails and does not model provider failures. `latency_5x_empirical.json` remains the earlier 596-row calibration reference and is not the selected recipe. Native realtime evaluation records actual subscription time instead of sampling this profile.
