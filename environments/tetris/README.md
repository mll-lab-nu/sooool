# Tetris: single-player placement under response delay

A small deterministic Tetris engine with the classic one-piece preview. The actor sees the game screen at fixed
observation ticks and names where the falling piece should go; a fixed key script carries the placement out. The
piece keeps falling while the answer is in flight, so a late answer arrives after the piece has locked and is
discarded. [Run, evaluate, replay and results](../../docs/tetris.md).

**Engine** (`engine.py`): 60 logic frames per second, 10×20 visible cells plus two hidden spawn rows, 7-bag
randomiser, SRS rotation with kicks, DAS/ARR on held left/right, 30-frame lock delay with 15 resets, guideline
scoring and gravity. Level = start level + lines/10. Seeded and deterministic (`tests/test_tetris.py`).

**Observation** (`render.py`, `runner.py`, `task.py`): the complete public screen — board including the two dark
spawn rows, the piece in play, its ghost outline, HOLD, one NEXT piece, SCORE/LINES/LEVEL; nothing annotated. The
runner captures it every `observation_stride_frames` (60 = once per game second) into a 9-tick window and, as in
Asterix, sends the window's oldest, middle and newest frames with their frame numbers, upscaled 2×. The request
text is Asterix's form: the prefix with the protocol and the profile's mean/median/P95 delay in game seconds ("the
actual delay of your request is unknown"), the policy, the output instructions, then the current frame, the image
frames and the actor's own last eight applied placements with their ages. The actor never receives the board
array, the bag, gravity timers or the sampled delay.

**Action and executor** (`executor.py`): the actor returns `{"rot": 1, "col": 3, "reason": "..."}`. The executor
reads the falling piece's letter from its colour in the spawn rows and presses keys computed only from that letter,
the answer and the published spawn column: rotate clockwise `rot` times (three turns as one counter-clockwise
press), move until the piece's left edge is at `col`, hard drop; press and release frames alternate. It never reads
the piece position or the board. A new piece is recognised when the NEXT box changes, when the executor pressed
hard drop, or when the spawn rows go from empty to occupied with a colour other than the piece being moved (a
rotation can lift the piece in play back into the spawn rows). An answer for a piece that already locked is
`stale`; an unparseable answer is `invalid`; both are discarded and counted.

**Protocol** (`runner.py`): Asterix's loop. One request in flight; a new request is captured at the first
observation tick after the previous reply arrived and its keys were pressed; other ticks are `drops`. `simulate`
delivers after a delay sampled from the recipe profile (the actor's computation pauses the virtual clock); `eval`
delivers when the answer actually arrives on a continuously advancing wall clock at 60/slowdown frames per wall
second. The slowdown (`args.slowdown`, 2 in the selected recipe) is a declared condition like Asterix's 5×.

**Providers** (`cli.py`): `claude` (default; stateless `claude -p`, no tools, no session, one fresh process per
request, `claude_cli.py`), `subscription` (the repository's ChatGPT/Codex transport, unchanged), `rules`
(simulate only; the El-Tetris heuristic reading the true board — an evaluator-side comparison, never an actor
input, `baseline.py`).

**Episodes and replay**: episodes start from deterministic mid-game states (`prefix` pieces placed by the rules
baseline at zero delay). Summaries report lines, new holes, height change, pieces, survival, calls, drops,
stale/invalid answers and capture-to-apply delay. `sol replay tetris RUN` rebuilds every episode from the recorded
answers and delivery frames without a model and re-derives every issued image hash, key script, drop and summary
number. Hole and height metrics read the true board only after the fact.

Retained differences from Asterix: screenshots are 2× upscaled instead of 224×224 (cells must stay legible); the
action is a placement executed as a key script instead of a held direction; episodes start from rules-placed
mid-game states; the delay statement is in game time (profile seconds divided by the slowdown). Known limit: a
piece that locks while part of it is still inside the spawn rows (stack within two rows of the top) can be
misidentified; the game is effectively lost at that point.
