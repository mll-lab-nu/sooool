# Actor and evaluator boundaries

The selected SOL policies use screenshots/cameras and permitted public control feedback from their declared environments. Touhou is a simplified practice engine; Racing and the two sports use the pinned external native engine. They never receive the privileged Gym state or a sampled future response delay.

| Game | Default SOL input | Evaluator / environment-only state |
|---|---|---|
| Rhythm | Actual screenshot PNG, public capture/monotonic clocks, model-authored pending taps, raw execution receipts, historical RTT, model-authored memory, public receptor/speed calibration and approximate screenshot-time bias | Chart notes/seed, future note times, actual judgement truth, future sampled latency calendar |
| Touhou | Canvas/HUD PNGs, public viewport/control protocol, prior own visual estimates and applied plans, historical delay summary | True player/Boss/projectile coordinates, engine internals, future RNG/delays, scoring branches |
| Asterix | Three timestamped 224×224 visual frames, allowed applied-action history, current held action, historical delay summary | ALE internal state, future sprites/RNG, reward/lives used only by offline evaluation, future latency draw |
| Tetris | Three timestamped 2×-upscaled plain game screenshots (oldest/middle/newest of a 9-tick window at one-second observation ticks: board, ghost outline, HOLD, one NEXT piece, score/lines/level), own applied-placement history with ages, profile delay summary | Board array, bag, gravity/lock timers, future delay draw; hole/height metrics read the true board only after the fact; the rules baseline is evaluator-side |
| Racing | Recent front-camera images, public telemetry/feedback and pixel-derived road measurements; model selects speed, offset and lookahead | Simulator-private truth and future state; continuous visual steering is a declared controller, not a model action |
| PingPong | Latest public stereo camera views, public feedback, camera-derived opponent estimate and model memory; model selects a persistent shot policy | Offline contact truth, native-pose diagnostics and future state; rule tracking/serving/joint planning are declared execution |
| Badminton | Public two-camera history sheets, filtered public state/feedback, model history/memory and historical latency context; model supplies conditional goals | Simulator truth, future delays and offline trajectory audits; camera interception and native stroke planning are declared execution |

The original `RhythmEnv` Gym wrapper exposes next-note structured observations, and `KaguyaEnv` exposes structured player/Boss/bullet state for environment research. They are installed for reuse and API compatibility; **these observations are not the screenshot-only SOL benchmark interface**. The portable runners use `ModelVisualEnv`, `BrowserEnv`, and actual ALE camera pixels instead.

The generic controllers implement declared mechanical semantics: literal timestamp forwarding, button edges/chunks and capacity/order/stale-result rules. Archived controllers may use other semantics; they are not the selected Rhythm executor. Calibration and offline scoring may inspect privileged truth. Their results must not be passed into the online actor as hidden-state guidance.

This portable research runtime requests read-only native sandboxing and disables tools; it rejects tool/approval events. It does not claim the original external bubblewrap/official benchmark seat isolation. Evaluation validity and adversarial isolation are separate claims.
