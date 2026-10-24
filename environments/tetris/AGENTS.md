Read the root AGENTS.md before running this environment.

The actor sees only the rendered screen (three timestamped screenshots per request), its own applied
placements and the measured delay statement. Never pass the board array, the bag, gravity or lock timers,
the sampled delay or the rules baseline's choice to the actor; `--provider rules` is an evaluator-side
comparison and exists only for `simulate`.

The executor presses a key script computed from the answer and the piece letter read from the public
spawn rows. Do not let it read engine state, do not add hover/wait behaviour, and do not rotate or move
pieces on the actor's behalf beyond the answered placement. A reply whose piece has already locked is
discarded, never redirected to the next piece.

One request in flight; the next capture is the first observation tick after the previous reply was
executed. The 2x slowdown in `recipes/tetris.json` is a declared condition stated in the actor's text;
`recipes/tetris-1x.json` is the normal-speed comparison. Register every run with `sol record`, keep
failed runs, and replay before quoting a number (`sol replay tetris RUN`).

The `claude` provider is a stateless Claude Code CLI call; the repository's Codex subscription transport is
`--provider subscription`. Do not start subscription (GPT) runs without the user's explicit instruction.
