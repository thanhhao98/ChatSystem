#!/usr/bin/env bash
# Remote half of scripts/verify_on_gpu.sh — runs ON the GPU box. Do not call directly unless you are on the box.
case "${1:-}" in
  -h|--help|"")
    echo "usage: bash scripts/verify_on_gpu_remote.sh <repo-dir>   (runs ON the GPU box; env knobs: GPU MODEL LIMIT MAX_ROWS MAX_LEN SKIP_VLLM VLLM_IMAGE HF_HOME_REMOTE)"
    exit 0;;
esac
set -uo pipefail
DIR="$1"
# Fail fast: without -e a failed cd would leave us running (venv, pip install ...) in the caller's cwd.
[ -d "$DIR" ] || { echo "not a directory: $DIR" >&2; exit 2; }
cd "$DIR" || exit 2
GPU="${GPU:-0}"; export CUDA_VISIBLE_DEVICES="$GPU"
MODEL="${MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"
LIMIT="${LIMIT:-60}"; MAX_ROWS="${MAX_ROWS:-200}"
# --max-len for the dry-run and the short run. Default = finetune_qlora.DEFAULT_MAX_LEN (module level is
# stdlib-only, so this works before the venv exists) so verification follows the T4 default instead of a
# hard-coded number that can drift from the script.
MAX_LEN="${MAX_LEN:-$(python3 -c 'import sys; sys.path.insert(0, "training"); import finetune_qlora as f; print(f.DEFAULT_MAX_LEN)')}"
echo "knobs: MODEL=$MODEL LIMIT=$LIMIT MAX_ROWS=$MAX_ROWS MAX_LEN=$MAX_LEN"
OUT="$DIR/verify_out"; mkdir -p "$OUT"; : > "$OUT/SUMMARY.md"
[ -n "${HF_HOME_REMOTE:-}" ] && export HF_HOME="$HF_HOME_REMOTE"
export FORCE_FP16=1   # exercise the Colab-T4 code path even on a bf16-capable GPU

pass() { echo "| $1 | PASS | $2 |" >> "$OUT/SUMMARY.md"; echo "PASS  $1"; }
fail() { echo "| $1 | FAIL | $2 |" >> "$OUT/SUMMARY.md"; echo "FAIL  $1 :: $2"; }
run()  { local name="$1"; shift; local log="$OUT/$(echo "$name" | tr ' /' '__').log"
         if "$@" > "$log" 2>&1; then pass "$name" "$(tail -n 1 "$log" | cut -c1-160)"; return 0
         else fail "$name" "exit $? — $(tail -n 3 "$log" | tr '\n' ' ' | cut -c1-200)"; return 1; fi; }

echo "| step | result | note |" > "$OUT/SUMMARY.md"; echo "|---|---|---|" >> "$OUT/SUMMARY.md"
nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv,noheader > "$OUT/gpu.txt" 2>&1 || true
echo "GPU: $(cat "$OUT/gpu.txt")"

# 1. fresh venv with the pinned requirements
if [ ! -d .venv ]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip > "$OUT/pip_upgrade.log" 2>&1
run "pip install torch" pip install -q torch --index-url https://download.pytorch.org/whl/cu128
run "pip install requirements-train.txt" pip install -q -r requirements-train.txt
pip install -q openai jupyter nbconvert nbformat ipykernel matplotlib > "$OUT/pip_extra.log" 2>&1 || true
pip freeze > "$OUT/pip_freeze.txt"
python - <<'EOF' > "$OUT/versions.txt" 2>&1
import torch, transformers, trl, peft, bitsandbytes, accelerate, datasets
cap = torch.cuda.get_device_capability() if torch.cuda.is_available() else None
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), "cap", cap, "name", torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
print("transformers", transformers.__version__, "trl", trl.__version__, "peft", peft.__version__, "bitsandbytes", bitsandbytes.__version__, "accelerate", accelerate.__version__, "datasets", datasets.__version__)
EOF
cat "$OUT/versions.txt"

# 2. CPU-side gates
run "py_compile" bash -c 'python -m py_compile $(find datagen training tools scripts -name "*.py")'
run "validate_dataset public splits" python training/validate_dataset.py data/public/xlam_2k.train.jsonl data/public/xlam_2k.val.jsonl data/public/xlam_2k.test.jsonl
run "convert_xlam reproducible" bash -c 'python datagen/convert_xlam.py --in data/public/xlam_raw_2k.jsonl --out-prefix /tmp/vx --system-file prompts/system_preamble_v0.txt --seed 20260913 && cmp /tmp/vx.train.jsonl data/public/xlam_2k.train.jsonl && cmp /tmp/vx.test.jsonl data/public/xlam_2k.test.jsonl'
run "validate_tools" python tools/sgod/validate_tools.py
run "eval_toolcall sample" python training/eval_toolcall.py --gold data/public/xlam_2k.eval.json --pred data/public/sample_pred.jsonl --out "$OUT/sample_a.json" --md "$OUT/sample_a.md"
run "eval_toolcall sample_b" python training/eval_toolcall.py --gold data/public/xlam_2k.eval.json --pred data/public/sample_pred_b.jsonl --out "$OUT/sample_b.json"
run "bootstrap_ci pair" python training/bootstrap_ci.py --run a="$OUT/sample_a.json" --run b="$OUT/sample_b.json" --pair a b --md "$OUT/sample_ci.md"

# 3. training: dry-run then short real run (fp16 forced)
run "finetune dry-run" python training/finetune_qlora.py --dry-run --data data/public/xlam_2k.train.jsonl --max-len "$MAX_LEN"
RUN="$OUT/run_smoke"; rm -rf "$RUN"
run "finetune short run (0.5B, ${MAX_ROWS} rows, 1 epoch, fp16)" python training/finetune_qlora.py --data data/public/xlam_2k.train.jsonl --val data/public/xlam_2k.val.jsonl \
    --model "$MODEL" --output-dir "$RUN" --epochs 1 --max-rows "$MAX_ROWS" --max-len "$MAX_LEN" --batch-size 4 --grad-accum 4 --save-steps 5 --logging-steps 1 --seed 42
ls -la "$RUN" > "$OUT/adapter_ls.txt" 2>&1 || true
CK=$(ls -d "$RUN"/checkpoint-* 2>/dev/null | head -n 1 || true)
if [ -n "$CK" ]; then
  run "finetune resume from $(basename "$CK")" python training/finetune_qlora.py --data data/public/xlam_2k.train.jsonl --val data/public/xlam_2k.val.jsonl \
    --model "$MODEL" --output-dir "$RUN" --epochs 1 --max-rows "$MAX_ROWS" --max-len "$MAX_LEN" --batch-size 4 --grad-accum 4 --save-steps 5 --logging-steps 1 --seed 42 --resume-from-checkpoint "$CK"
else
  fail "finetune resume" "no checkpoint-* directory produced"
fi

# 4. predictions + scoring (transformers backend)
run "predict base (transformers)" python training/predict_toolcall.py --backend transformers --model-path "$MODEL" --eval data/public/xlam_2k.eval.json --limit "$LIMIT" --out "$OUT/base_pred.jsonl" --system prompts/system_preamble_v0.txt
run "predict adapter (transformers)" python training/predict_toolcall.py --backend transformers --model-path "$MODEL" --adapter "$RUN" --eval data/public/xlam_2k.eval.json --limit "$LIMIT" --out "$OUT/ft_pred.jsonl" --system prompts/system_preamble_v0.txt
run "eval base" python training/eval_toolcall.py --gold data/public/xlam_2k.eval.json --pred "$OUT/base_pred.jsonl" --out "$OUT/base.json" --md "$OUT/base.md"
run "eval adapter" python training/eval_toolcall.py --gold data/public/xlam_2k.eval.json --pred "$OUT/ft_pred.jsonl" --out "$OUT/ft.json" --md "$OUT/ft.md"
run "bootstrap_ci base vs ft" python training/bootstrap_ci.py --run base="$OUT/base.json" --run ft="$OUT/ft.json" --pair base ft --md "$OUT/base_vs_ft.md"

# 5. vLLM serving of the adapter (docker) + openai-backend predictions
if [ "${SKIP_VLLM:-0}" != "1" ]; then
  NAME=vllm-chatsystem-verify; PORT=18000
  docker rm -f $NAME > /dev/null 2>&1 || true
  HFC="${HF_HOME:-$HOME/.cache/huggingface}"
  docker run -d --name $NAME --gpus "\"device=$GPU\"" -v "$HFC:/root/.cache/huggingface" -v "$RUN:$RUN:ro" -p $PORT:8000 \
      "${VLLM_IMAGE:-vllm/vllm-openai:v0.22.0}" --model "$MODEL" --served-model-name base --max-model-len 4096 --gpu-memory-utilization 0.35 \
      --enable-auto-tool-choice --tool-call-parser hermes --enable-lora --max-lora-rank 16 --lora-modules ft="$RUN" > "$OUT/vllm_docker.log" 2>&1
  ok=0; for i in $(seq 1 60); do if curl -fsS "http://127.0.0.1:$PORT/v1/models" > "$OUT/vllm_models.json" 2>/dev/null; then ok=1; break; fi; sleep 10; done
  if [ $ok = 1 ]; then pass "vLLM up" "$(cut -c1-120 "$OUT/vllm_models.json")"
    export DUMMY_KEY=x
    run "predict ft (vLLM openai backend)" python training/predict_toolcall.py --backend openai --base-url "http://127.0.0.1:$PORT/v1" --model ft --api-key-env DUMMY_KEY --eval data/public/xlam_2k.eval.json --limit "$LIMIT" --out "$OUT/vllm_ft_pred.jsonl" --system prompts/system_preamble_v0.txt
    run "eval ft (vLLM)" python training/eval_toolcall.py --gold data/public/xlam_2k.eval.json --pred "$OUT/vllm_ft_pred.jsonl" --out "$OUT/vllm_ft.json" --md "$OUT/vllm_ft.md"
  else fail "vLLM up" "no /v1/models after 10 min — see vllm_docker.log"; docker logs --tail 40 $NAME >> "$OUT/vllm_docker.log" 2>&1 || true; fi
  docker rm -f $NAME > /dev/null 2>&1 || true
fi

# 6. notebooks: execute the finetune notebooks headless? They are Colab-oriented (Drive mounts); we only validate + run their dry-run cells locally on CPU side.
run "nbformat validate" python -c "import nbformat,glob; [nbformat.validate(nbformat.read(f, 4)) for f in glob.glob('notebooks/*/*.ipynb')]; print('ok')"

echo; echo "===== SUMMARY ====="; cat "$OUT/SUMMARY.md"; echo; echo "versions: $(tail -n 1 "$OUT/versions.txt")"
grep -q "| FAIL |" "$OUT/SUMMARY.md" && exit 1 || exit 0
