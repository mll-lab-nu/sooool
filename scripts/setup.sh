#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/fetch-latency.sh
uv sync --locked --python 3.12
uv run playwright install --with-deps chromium
uv run sol doctor
