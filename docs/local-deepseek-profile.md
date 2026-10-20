# Local DeepSeek task latency experiment

This measures inference against frozen public observations, not game scores or a
continuously advancing game. No paid API fallback is permitted.

Model: `deepseek-ai/DeepSeek-V4.1-Flash-1017`, revision
`1bae0e1088993b9b82de08f59de5be5a34e42170`. Serve with vLLM 0.31.0,
TP=8, image encoder enabled, no CPU offload, thinking disabled, temperature 0.
The launch script pins all engine flags and allows only loopback inference.

## Corpus

| Task | Distinct observations | Source |
|---|---:|---|
| Asterix | 33 | Native offline observations, scripted actions, seeds 5/9/17 |
| Badminton | 30 | Retained native realtime observations from research machine |
| Racing | 30 | Native offline reference-controller trajectories, seeds 101/304/305 |
| Rhythm | 30 | Retained selected-v21 native observations |
| Roadster | 10 | Retained seeded native scripted trajectory |
| Table tennis | 30 | Retained native realtime observations from research machine |
| Touhou | 21 | Native tracking-safe-intercept serial fixtures |

`collect_*_profile_inputs.py` generates public observations only.
`export_sports_profile_inputs.py` exports allowlisted inputs read-only;
`assemble_profile_records.py` combines the sources.
`build_local_profile_corpus.py` preserves original PNGs and prompts, validates
source image hashes where available, removes duplicate inputs and writes
content-addressed images and provenance. Original system messages are retained.
Historical latency/history text in original prompts is context, not a new
measurement. Validator metadata is not added to the model's messages.

## Measurement

Run on the GPU host against `127.0.0.1:8000/v1`:

```bash
python -m runtime.local_profile --corpus corpus/corpus.json \
  --output results/serial --concurrency 1 --repeats 3
python -m runtime.local_profile --corpus corpus/corpus.json \
  --output results/concurrency4 --concurrency 4 --repeats 3
```

Each task gets one excluded warmup, followed by three repetitions of its corpus.
Concurrency 4 uses a closed-loop worker pool within each task; tasks run
sequentially. This is not a fixed arrival-rate load test. Prefix/multimodal
caches are left at the serving engine defaults; repeats are separately labeled.
The concurrent run follows the serial run and therefore has a warm server.

Record TTFT, first complete valid action, finish, stream DONE, transport
completion, usage, raw timestamped SSE, errors, and terminal-verified validity.
The terminal action must equal the first complete action. Rhythm emits an action
before its public commentary. Truncated, invalid and wrong-model outputs remain
failures. No retry or output repair is applied. Summaries condition latency on
valid completed responses and disclose all attempted/valid/failed counts.
P50 is the median; P90/P99 use nearest rank and are descriptive for this small
sample, not reliable population-tail estimates.

Output constraints are provided by the original prompts and checked by native
validators; this experiment does not enable grammar-constrained decoding.
Historical provider runs using structured-output schemas are therefore not an
identical serving configuration.

Timing includes local client serialization, HTTP and action validation; it
excludes screenshot capture, offline input preparation and executing actions.
It cannot establish that a provider API has the same latency: network, batching,
replicas and queueing require a separate matched-input API benchmark.

## Resource lifecycle

`launch_local_profile_h200.py` validates all seven tasks before creation.
Without `--execute` it prints the command. It requests one `a3-ultragpu-8g`
Flex-start VM with a 600-second capacity wait, a 14,400-second maximum runtime,
termination action DELETE and auto-deleted 1 TB boot disk. Installation and model
download consume part of that runtime. No service account is attached. The model
server listens only on loopback; SSH uses an instance-scoped public key.

Verify the actual cloud scheduling fields after creation. Copy results and
serving logs off the disposable VM before expiry. GPU cost estimate at the
checked $42.40/hour rate is $169.60 for the full four hours, plus disk/network;
this is not a billed invoice. Capacity or bootstrap failures must be recorded
as failures, never reported as latency results.
