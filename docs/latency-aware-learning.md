# Learn to act while inference is still in flight

SOOOOL’s objective is to learn a policy that succeeds under a real response
budget. It combines repeated task practice, predictions about the state when
an action will arrive, and overlapping inference so decisions can keep flowing
while other requests are still thinking.

## Overlap decisions to sustain control

Single-request latency and decision cadence measure different things. As an
idealized illustration, a decision can take two seconds while staggered requests
launched every 200ms produce a new answer every 200ms after the pipeline fills,
provided capacity and service throughput are sufficient. Each answer must still
account for the movement since its screenshot. This illustration is not a
measurement or a guarantee about the model service.

The familiar systems analogy is CPU pipelining: overlapping work improves the
completion rate even when an individual instruction still takes multiple stages.
[Cornell’s architecture notes](https://www.cs.cornell.edu/courses/cs5220/2020fa/lec/2020-09-10-arch.html)
explain that distinction. Here the useful objective is sustained, timely control:
observe again while an earlier request is in flight, predict ahead, and install
a legal plan before its deadline.

The games use two different mechanisms:

- **Staggered observations:** Rhythm starts requests on successive screenshots,
  with bounded concurrency. GPT predicts absolute future tap times; its queue
  retains pending commands while new decisions arrive. Racing and PingPong also
  overlap observations, with their declared stale-response arbitration.
- **Same-observation races:** Touhou sends multiple candidates the same input and
  selects the first complete legal response. This supplies additional chances to
  meet that observation’s action deadline. It does not create additional distinct
  observations. Losing requests still occupy slots and incur accounted costs.

These are control-design choices, not a requirement to demonstrate faster
single-request inference. Report cadence, observation-to-action age, deadline
misses, complete gameplay outcomes, capacity and cost together. A high request
rate alone is not a high useful-action rate. The selected Touhou two-/four-way
runs are demonstrations, not enough repetitions to estimate a race-specific
performance improvement.

## Selected request-handling details

Touhou allows four requests in its real-time recipe and eight in simulation. A
winning action can take effect before all other requests finish; the remaining
requests keep their slots until completion. Another observation group needs a
winner to have taken effect, movement to have finished, and enough free slots.
See the [simulation recipe](../recipes/touhou.json) and
[real-time recipe](../recipes/touhou-realtime.json).

Rhythm's executor prevents older replies from cancelling or replacing newer
instructions. An older additive reply may still schedule a valid tap whose ID
has not already been used. Taps expire according to the model's `expires_ms`,
not simply because their target time has passed. These rules are implemented in
[model-executor.js](../environments/rhythm/dist/model-executor.js).

Asterix's selected serial configuration followed limited comparisons of one and
eight in-flight requests. Both serial trials survived longer, but the score
ordering depended on the output format. This motivates further testing rather
than establishing that serial control is always better. See the
[research comparison](asterix-autoresearch.md#4-compare-scheduling-and-public-explanations).

## Autoresearch is task-policy training

Repeatedly playing a fixed task, inspecting failures, exploring alternatives and
retaining a useful strategy is the learning process studied here. The trained
artifact is the task policy: prompts, model-authored memory and the selected
control/scheduling configuration. Base-model weights remain frozen. This is
policy training through interaction and search, not a claim of weight fine-tuning.

Touhou makes the distinction concrete. Practice against Kaguya exposes delayed
tracking, unsafe stopping positions and late defensive actions. The research loop
turns those failures into whole-interval safety checks, shot-intercept guidance
and preventive bomb timing. Every online movement and bomb still comes from a
new visual model decision. Learning a repeatable strategy for this encounter is
an intended result, as it is when a human practices a difficult spell card.

The primary question is whether that learned policy can execute successfully
while the game keeps moving under actual inference delay. Transfer to unseen
patterns, different games or new speeds is a separate evaluation question.
Label practice, confirmation and transfer conditions so the demonstrated skill
is clear; repeated practice on the target encounter is not itself evidence of
data leakage or a scripted executor.

For Rhythm, the earlier 30s/52-note development charts and the selected 17s/25-note
chart are different task inputs. The selected 2.5s-approach demonstration reuses
the aligned 17s chart from its immediate 1.8s comparator to examine planning lead.
Its frozen manifest explicitly records this matched-chart design. Simulation
`--seed` controls delay sampling on the retained chart; a different delay seed
alone does not generate a new chart. Preserve this distinction when describing
training versus a fresh-chart test.

[Rhythm learning record](rhythm-autoresearch.md) ·
[Touhou learning record](touhou-research-record.md) ·
[Timing and scheduling](timing.md)
