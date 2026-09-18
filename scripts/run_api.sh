#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export USE_TF=0 USE_FLAX=0
export HF_HOME="$PWD/data/cache/huggingface"
exec .venv/bin/python -m uvicorn aquarium.api:app --host 127.0.0.1 --port 8765
