# Tetris: run, evaluate, replay, results

Tetris is a local environment on our own deterministic engine ([contract](../environments/tetris/README.md)). The
actor sees the plain game screen at one-second observation ticks (three timestamped frames per request, as in
Asterix) and answers one placement for the falling piece; a declared key script executes it. The selected
condition is [`recipes/tetris.json`](../recipes/tetris.json): policy `v11-short`, one request in flight, the
measured delay profile, a declared 2× game slowdown, three 60-second mid-game episodes (seeds 0/1/2 at start
levels 1/3/5).

```bash
uv run sol env setup tetris
uv run sol simulate tetris --provider rules   --output runs/tetris-rules   # true-board baseline, sampled delays
uv run sol simulate tetris --provider claude  --output runs/tetris-sim     # Claude Code CLI decisions, sampled delays
uv run sol eval     tetris --provider claude  --output runs/tetris-live    # actual wall clock and actual latency
uv run sol replay   tetris runs/tetris-live                                # zero-model replay check
uv run sol record   runs/tetris-live --decision retain --note "..."
```

`--provider subscription` selects the repository's ChatGPT/Codex transport; `--provider rules` exists only for
`simulate`. `--seed/--level/--prefix/--duration/--slowdown` override one episode or one condition and are folded
into the frozen manifest; a recipe the runner cannot honour (slowdown below 1, a window smaller than the three
images sent, more than one request in flight) is rejected before any run directory exists.
[`recipes/tetris-1x.json`](../recipes/tetris-1x.json) is the normal-speed comparison.

| Command | Clock | Delay | Proves |
|---|---|---|---|
| `sol simulate tetris` | virtual, pauses while the actor computes | sampled from the recipe profile, seeded per episode | closed-loop development under a declared delay model |
| `sol eval tetris` | wall, 60/slowdown frames per second | actual response time of the selected transport | measured behaviour of this transport at this slowdown |
| `sol replay tetris RUN` | none | recorded delivery frames | every issued image, request target, executor status, key script, drop count and summary number re-derived; no model calls |

A run retains `manifest.json` (the recipe actually run), `task.txt`, `provenance.json` (interpreter, Pillow, numpy,
commit), `transport-worker/transport.json` (adapter, CLI version, resolved model ids), `source_snapshot/` and per
episode `issued.jsonl`, `decisions.jsonl`, `deliveries.json`, `actions.json`, `steps.jsonl`, `calls/call-*/` (exact
prompt, images, answer) and `summary.json`; `evaluation-record.json` follows the shared schema and `sol record`
appends it to [`artifacts/tetris/evaluations.jsonl`](../artifacts/tetris/evaluations.jsonl).

## Delay profile and slowdown

[`profiles/tetris/claude-opus-low-serial-v0.json`](../profiles/tetris/claude-opus-low-serial-v0.json): 68
capture-to-apply wall seconds from a serial real-clock run of the same transport on an earlier, longer prompt of
this lineage (median 5.9 s, p90 7.4 s, p95 9.0 s). The task prefix states its mean, median and P95 in game seconds
for the run's slowdown and says the actual delay is unknown. A new profile is the `call_wall_seconds` column of a
serial `sol eval tetris` run, saved in the same form and named in a copied recipe.

At normal speed a piece at level 5 locks about 3.5 s after it spawns on a half-full board, below the ~6 s delay of
every transport we measured (Claude CLI and the Codex subscription alike), so answers arrive for the wrong piece.
The selected recipe therefore declares a 2× slowdown, as Asterix declares 5× and Badminton 3×; the actor's text
says so.

## Results (three 60-second episodes, means)

| Run | Policy | Clock | Slowdown | Lines | New holes | Alive | Stale | Capture→apply (game s) |
|---|---|---|---|---:|---:|---|---:|---:|
| `claude-eval-2x` **(selected)** | `v11-short` | wall | 2× | 5.67 | 0.33 | 3/3 | 0 | 2.85 (wall median 5.3 s) |
| `claude-eval-2x-v12c` (rejected) | `v12c-tradeoff` | wall | 2× | 3.67 | 5.33 | 3/3 | 3 | 3.12 (wall median 6.2 s) |
| `claude-sim-2x` | `v11-short` | virtual | 2× | 3.67 | 8.67 | 2/3 | 3 | 2.77 |
| `rules-sim-2x` (true board) | — | virtual | 2× | 5.67 | 1.67 | 3/3 | 0 | 2.77 |
| `claude-eval-1x` | `v11-short` | wall | 1× | 1.67 | 5.67 | 2/3 | 5 | 6.26 |
| `rules-sim-1x` | — | virtual | 1× | 1.00 | 8.33 | 2/3 | 7 | 6.43 |

The actor is Claude Opus (low effort) through a stateless Claude Code CLI call, not SOL; GPT-6.1-sol was measured
during development (~6 s per answer, like every transport on a subscription) but no GPT run is registered. "New
holes" are empty cells left under placed pieces; the rules baseline is the El-Tetris heuristic reading the true
board under the same sampled delays, an evaluator-side comparison that never reaches the actor.

- On the actual clock at 2× the policy clears lines at the baseline's rate with fewer holes; one of 55 applied
  decisions made a hole the baseline would have avoided. `assets/tetris/claude-eval-2x-level5.gif` shows the
  level-5 episode beside the baseline's (deterministic replay rendering, `scripts/tetris_render.py`).
- `v12c-tradeoff` adds one rule to `v11-short` (fill a deep well when it completes two rows; the diff is
  `artifacts/tetris/v12c-prompt.diff`). On fixed screenshots it fixed that decision four times in five, and it made
  it in the live level-5 episode (one vertical I, three rows), but the longer text lengthened the answers (median
  416–443 output tokens per episode against 279–368) and the calls (wall median 6.2/6.5/5.7 s against
  4.7/5.9/5.7 s); after the clear raised the level to 6, three answers arrived after their pieces had locked and
  the untouched pieces left 14 holes. Rejected: a longer policy is a slower policy.
- About one answer in five mis-counts a column height by one, with any prompt; only repeated reads or a stronger
  reader would change that.
- The simulation is harsher than the live run because the profile's tail (p95 9.0 s) is heavier than the current
  transport's; its draws lost the level-5 episode after a four-row clear raised the level to 6.
- Normal speed is latency-bound for the baseline as much as for the model.

Development before the portable runner (a six-placement protocol discarded after a serial delay measurement of
40 s; screen labels and an engine-reading controller withdrawn; the gap-free rule and fit table chosen on fixed
screenshots) is not retained as evidence. Next: a profile re-measured on the current prompt, more seeds at 2×,
voting over repeated reads.
