#!/bin/bash
SCRIPT_DIR=$(cd "$(dirname "$0")"; pwd)
python3 main.py \
  --evaluation_path "${SCRIPT_DIR}/dataset/benchmark_test.jsonl" \
  --write_path "${SCRIPT_DIR}/experiments/test" \
  --pdf