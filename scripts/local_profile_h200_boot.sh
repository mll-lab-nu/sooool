#!/usr/bin/env bash
# Dedicated disposable experiment VM only. The GCP maxRunDuration is the billing guard.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
export VLLM_ENGINE_READY_TIMEOUT_S=3600
mkdir -p /opt/sooool-profile
exec > >(tee -a /opt/sooool-profile/bootstrap.log) 2>&1
date -u
apt-get update
apt-get install -y python3-venv
python3 -m venv /opt/sooool-profile/venv
/opt/sooool-profile/venv/bin/pip install --upgrade pip
/opt/sooool-profile/venv/bin/pip install 'vllm==0.31.0' 'jsonschema>=4.25,<5' requests
nvidia-smi -q > /opt/sooool-profile/gpu-before.txt
/opt/sooool-profile/venv/bin/pip freeze > /opt/sooool-profile/packages.txt
touch /opt/sooool-profile/bootstrap-ready
exec /opt/sooool-profile/venv/bin/vllm serve deepseek-ai/DeepSeek-V4.1-Flash-1017 \
  --revision 1bae0e1088993b9b82de08f59de5be5a34e42170 \
  --tokenizer-mode deepseek_v41 \
  --tensor-parallel-size 8 \
  --engram-config '{"cpu_offload":false}' \
  --max-model-len 16384 \
  --max-num-seqs 16 \
  --max-num-batched-tokens 8192 \
  --limit-mm-per-prompt '{"image":8}' \
  --gpu-memory-utilization 0.90 \
  --host 127.0.0.1 --port 8000 \
  --download-dir /opt/sooool-profile/weights
