#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  if [[ -x ".venv/bin/python" ]]; then
    PYTHON=".venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

"$PYTHON" -m pip install -e ".[ts-dfm,dev]"

rm -rf \
  reproductions/ts_dfm_2511_17229/data \
  reproductions/ts_dfm_2511_17229/outputs \
  reproductions/ts_dfm_2511_17229/checkpoints

"$PYTHON" -m reproductions.ts_dfm_2511_17229.cli make-synthetic \
  --output reproductions/ts_dfm_2511_17229/data/synthetic.jsonl \
  --count 8 \
  --atoms 4

"$PYTHON" -m reproductions.ts_dfm_2511_17229.cli train \
  --config reproductions/ts_dfm_2511_17229/configs/smoke.yaml

"$PYTHON" -m reproductions.ts_dfm_2511_17229.cli eval \
  --config reproductions/ts_dfm_2511_17229/configs/smoke.yaml

"$PYTHON" -m pytest tests/test_ts_dfm_cli.py tests/test_ts_dfm_reproduction.py
