#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

repository=mll-lab-nu/latency-aware-agents
release=python-v0.1.2
wheel=latency_sensitive_bench-0.1.2-py3-none-any.whl
destination="vendor/$wheel"

if [[ -f "$destination" ]]; then
    exit 0
fi

mkdir -p vendor
download_dir="$(mktemp -d)"
trap 'rm -rf "$download_dir"' EXIT

# Authenticated downloads also work while the benchmark repository is private.
if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
    gh release download "$release" --repo "$repository" \
        --pattern "$wheel" --dir "$download_dir"
else
    curl --fail --location \
        "https://github.com/$repository/releases/download/$release/$wheel" \
        --output "$download_dir/$wheel"
fi
mv "$download_dir/$wheel" "$destination"
