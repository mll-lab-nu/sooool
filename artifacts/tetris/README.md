# Tetris evidence

- `evaluations.jsonl`: the append-only registry written by `sol record` (shared schema version 2), one row per
  run with the run and per-episode summaries and the researcher decision: the selected `v11-short` policy on the
  actual clock at 2× (`claude-eval-2x`, retain), its simulation at 2× and evaluation at 1×, the rules baseline
  simulations at 2× and 1×, and the rejected `v12c-tradeoff` candidate on the actual clock at 2×
  (`claude-eval-2x-v12c`, reject). [`docs/tetris.md`](../../docs/tetris.md) reads these rows.
- `records/claude-eval-2x/`: what zero-model replay of the selected run needs: `manifest.json` (the frozen recipe)
  and, per episode, `summary.json` and `decisions.jsonl` (observation frame, target piece, image frames and
  SHA-256s, delivery frame, public answer, call timing, status). No screenshots are retained; replay re-renders
  every issued frame and re-derives the key scripts, drops and every summary number:
  `uv run sol replay tetris artifacts/tetris/records/claude-eval-2x` (also `tests/test_tetris.py`). The run was
  registered with decision `retain` and produced with Python 3.12.3, Pillow 12.1.1 (the renderer's font decides
  the image hashes), numpy 1.26.4 and Claude Code CLI 2.1.310 at branch commit `99ba620`; the other registered
  runs keep only their registry rows.
- `v12c-prompt.diff`: the rejected candidate's only difference from the selected policy.
- `../../assets/tetris/claude-eval-2x-level5.gif`: deterministic replay rendering of the selected run's level-5
  episode (`records/claude-eval-2x/episode-02-s2-l5-p20`, left) beside the rules baseline's `rules-sim-2x`
  episode under the same sampled delays (right), drawn by `scripts/tetris_render.py` at one GIF second per game
  second with zero model calls; not a screen capture. SHA-256 `d1e118d8d5f8931b7e4310cdf59c6354a64e9ed013398b97ef01b37112196a6f`, 1748611 bytes.

Absolute `run` paths in the records point at the original output directories on the machine that produced them,
as for the other games.
