#!/usr/bin/env bash
# End-to-end verification of every CLI script on a GPU box (runs on the GPU box of the reference
# infrastructure; verify_out/SUMMARY.md is what gets committed / pasted into the task comment).
#
# What it does (remote side, in a FRESH venv so the pins in requirements-train.txt are what gets tested):
#   1. sync this repo to $REMOTE:$REMOTE_DIR (rsync; excludes .git, runs/, _ref/)
#   2. python -m venv + pip install torch (CUDA wheel) + -r requirements-train.txt ; record `pip freeze`
#   3. validate_dataset on the 3 public splits
#   4. finetune_qlora.py --dry-run, then a SHORT real QLoRA run (0.5B, --max-rows 200, 1 epoch) with FORCE_FP16=1
#      so the fp16 path a Colab T4 will take is the one exercised
#   5. predict_toolcall.py (transformers backend) for base and adapter on 60 eval records → eval_toolcall → bootstrap_ci pair
#   6. vLLM (docker image, LoRA enabled, hermes parser) serving the adapter → predict_toolcall (openai backend) → eval_toolcall
#   7. writes everything under $REMOTE_DIR/verify_out/ and prints a PASS/FAIL table
#
# Usage:
#   bash scripts/verify_on_gpu.sh <ssh-host> [gpu-index] [remote-dir]
#   bash scripts/verify_on_gpu.sh <gpu-host> 0          # <gpu-host> = an entry in your ~/.ssh/config
# Env knobs: SKIP_VLLM=1 (skip step 6), VLLM_IMAGE=vllm/vllm-openai:v0.22.0, MODEL=Qwen/Qwen2.5-0.5B-Instruct,
#            LIMIT=60 (eval records), MAX_ROWS=200 (train rows), HF_HOME_REMOTE=<hf cache dir on the box>,
#            MAX_LEN=<n> (--max-len for the dry-run and the short run; default = finetune_qlora.DEFAULT_MAX_LEN)
set -euo pipefail
# -h/--help prints the header block above and exits before anything touches ssh/rsync.
case "${1:-}" in -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0;; esac
REMOTE="${1:?ssh host required, e.g. <gpu-host> from your ~/.ssh/config}"
GPU="${2:-0}"
REMOTE_DIR="${3:-\$HOME/chatsystem_verify}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"

echo "== [local] rsync $HERE -> $REMOTE:$REMOTE_DIR"
ssh "$REMOTE" "mkdir -p $REMOTE_DIR"
rsync -az --delete --exclude .git --exclude runs --exclude _ref --exclude '.venv' --exclude '__pycache__' --exclude 'verify_out' \
  "$HERE/" "$REMOTE:$REMOTE_DIR/"

echo "== [remote] running scripts/verify_on_gpu_remote.sh"
ssh "$REMOTE" "GPU=$GPU SKIP_VLLM=${SKIP_VLLM:-0} VLLM_IMAGE=${VLLM_IMAGE:-vllm/vllm-openai:v0.22.0} MODEL=${MODEL:-Qwen/Qwen2.5-0.5B-Instruct} LIMIT=${LIMIT:-60} MAX_ROWS=${MAX_ROWS:-200} MAX_LEN=${MAX_LEN:-} HF_HOME_REMOTE=${HF_HOME_REMOTE:-} bash $REMOTE_DIR/scripts/verify_on_gpu_remote.sh $REMOTE_DIR"

echo "== [local] fetching verify_out"
mkdir -p "$HERE/verify_out"
rsync -az "$REMOTE:$REMOTE_DIR/verify_out/" "$HERE/verify_out/"
echo "Done. See verify_out/SUMMARY.md and verify_out/pip_freeze.txt (use it to update requirements-train.txt)."
