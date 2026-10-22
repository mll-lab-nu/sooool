#!/usr/bin/env bash
# Run inside the unpacked task bundle on the disposable GPU VM.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=/opt/sooool-profile/venv/bin/python
mkdir -p results
exec > >(tee -a results/suite.log) 2>&1
date -u
curl --fail --silent http://127.0.0.1:8000/v1/models > results/served-models.json
nvidia-smi -q > results/gpu.txt
nvidia-smi topo -m > results/gpu-topology.txt
sha256sum corpus/corpus.json > results/corpus.sha256
"$PY" -m runtime.local_profile --corpus corpus/corpus.json \
  --output results/serial --concurrency 1 --repeats 3
"$PY" -m runtime.local_profile --corpus corpus/corpus.json \
  --output results/concurrency4 --concurrency 4 --repeats 3
date -u > results/completed-at.txt
