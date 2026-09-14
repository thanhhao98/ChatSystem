#!/usr/bin/env bash
# Serve a Qwen2.5 base model (+ optional LoRA adapter) with vLLM's OpenAI-compatible server in a
# LOCAL docker container, then print the predict_toolcall.py command that targets it.
#
# Ported from the POC v1 serving script minus the remote-host parts: this runs directly on the
# machine that has the GPU (the GPU box of the reference infrastructure). For Colab/Kaggle -- no
# docker -- see the pip alternative at the bottom of this file.
#
# Usage (all knobs are environment variables; the only accepted argument is -h/--help):
#   bash training/serve_vllm.sh --help                                 # print this header, start nothing
#   DRY_RUN=1 bash training/serve_vllm.sh                              # print the docker command, start nothing
#   bash training/serve_vllm.sh                                        # Qwen/Qwen2.5-0.5B-Instruct as 'qwen2.5-0.5b'
#   MODEL=Qwen/Qwen2.5-1.5B-Instruct SERVED=qwen2.5-1.5b bash training/serve_vllm.sh
#   ADAPTER=/abs/path/to/adapter SERVED=qwen-sgod-ft bash training/serve_vllm.sh   # serve a PEFT LoRA
#   DTYPE=half PORT=8001 GPU=1 MAX_LEN=4096 bash training/serve_vllm.sh
#
#   IMAGE          vllm/vllm-openai:${IMAGE_TAG:-v0.22.0}   (or set IMAGE to a full image ref)
#   MODEL          HF id or local dir of the base model
#   SERVED         served-model-name (what --model in predict_toolcall.py must be)
#   ADAPTER        PEFT adapter dir; bind-mounted at the SAME path inside the container
#   MAX_LORA_RANK  --max-lora-rank (default 16; must be >= the adapter's r)
#   PORT           host port (default 8000) -> base URL http://localhost:$PORT/v1
#   MAX_LEN        --max-model-len (default 8192; contract rows are <= 4096 tokens)
#   GPU            CUDA device index (default 0)
#   DTYPE          auto (default) | half | bfloat16 | float16. "auto" picks "half" when the GPU's compute
#                  capability is < 8 (T4 = 7.5 has no bf16), else leaves vLLM's own auto.
#   GPU_MEM_UTIL   --gpu-memory-utilization (default 0.85)
#   HF_CACHE       host HF cache mounted into the container (default ~/.cache/huggingface)
#   HF_TOKEN       forwarded to the container when set (gated models); never written anywhere
#   VLLM_VERSION   ONLY for the printed Colab/Kaggle pip line (docker uses IMAGE_TAG). The single
#                  authoritative pin lives in docs/serving.md section 5 ("VLLM_VERSION"), filled in after
#                  the first verified T4 run; until it exists the pip line is unpinned (same as notebook 03).
#   DRY_RUN        1 = print the resolved `docker run` command and exit 0 without touching docker
#
# The image is ~10 GB: the script warns when docker will have to pull it before the server starts.
# Stop:  docker rm -f vllm-$SERVED
set -euo pipefail

# ── argument handling: --help must never start (or pull) anything ──────────────────────────────
case "${1:-}" in
  -h|--help) awk 'NR > 1 && !/^#/ { exit } NR > 1 { sub(/^# ?/, ""); print }' "$0"; exit 0 ;;
  "") ;;
  *) echo "ERROR: unknown argument '$1' (all knobs are environment variables; see --help)" >&2; exit 2 ;;
esac
DRY_RUN="${DRY_RUN:-0}"

IMAGE_TAG="${IMAGE_TAG:-v0.22.0}"
IMAGE="${IMAGE:-vllm/vllm-openai:${IMAGE_TAG}}"
MODEL="${MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"
SERVED="${SERVED:-qwen2.5-0.5b}"
ADAPTER="${ADAPTER:-}"
MAX_LORA_RANK="${MAX_LORA_RANK:-16}"
PORT="${PORT:-8000}"
MAX_LEN="${MAX_LEN:-8192}"
GPU="${GPU:-0}"
DTYPE="${DTYPE:-auto}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.85}"
HF_CACHE="${HF_CACHE:-$HOME/.cache/huggingface}"
NAME="vllm-${SERVED}"
HEALTH_TRIES="${HEALTH_TRIES:-90}"          # x 5 s = 7.5 min (first start pulls the image + weights)
VLLM_VERSION="${VLLM_VERSION:-}"            # Colab pip pin from docs/serving.md section 5; empty = unpinned
PIP_VLLM_SPEC="vllm${VLLM_VERSION:+==${VLLM_VERSION}}"

if [ "$DRY_RUN" != "1" ]; then
  command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found. On Colab/Kaggle use the pip alternative at the bottom of this file."; exit 1; }
fi

# ── dtype: "half" when compute capability < 8 (fp16 for T4/V100), computed from nvidia-smi ──
DTYPE_REASON="explicit DTYPE=${DTYPE}"
if [ "$DTYPE" = "auto" ]; then
  CC=""
  if command -v nvidia-smi >/dev/null 2>&1; then
    CC="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader -i "$GPU" 2>/dev/null | head -n1 | tr -d ' ' || true)"
  fi
  if [ -n "$CC" ]; then
    CC_MAJOR="${CC%%.*}"
    if [ "$CC_MAJOR" -lt 8 ] 2>/dev/null; then
      DTYPE="half"; DTYPE_REASON="compute capability ${CC} < 8 -> fp16"
    else
      DTYPE="auto"; DTYPE_REASON="compute capability ${CC} >= 8 -> vLLM auto (bf16)"
    fi
  else
    DTYPE_REASON="nvidia-smi unavailable -> vLLM auto (set DTYPE=half on a T4)"
  fi
fi

# ── LoRA: mount the adapter at the same absolute path so --lora-modules resolves in-container ──
ADAPTER_ARGS=()
ADAPTER_MOUNT=()
if [ -n "$ADAPTER" ]; then
  ADAPTER="$(cd "$ADAPTER" && pwd)"                       # absolute path
  [ -f "$ADAPTER/adapter_config.json" ] || { echo "ERROR: $ADAPTER/adapter_config.json not found (not a PEFT adapter dir)"; exit 1; }
  ADAPTER_ARGS=(--enable-lora --max-lora-rank "$MAX_LORA_RANK" --lora-modules "${SERVED}=${ADAPTER}")
  ADAPTER_MOUNT=(-v "${ADAPTER}:${ADAPTER}:ro")
  BASE_IN_ADAPTER="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('base_model_name_or_path',''))" "$ADAPTER/adapter_config.json" 2>/dev/null || true)"
  if [ -n "$BASE_IN_ADAPTER" ] && [ "$BASE_IN_ADAPTER" != "$MODEL" ]; then
    echo "WARNING: adapter was trained on '$BASE_IN_ADAPTER' but MODEL='$MODEL'"
  fi
fi

HF_ENV=()
[ -n "${HF_TOKEN:-}" ] && HF_ENV=(-e "HF_TOKEN=${HF_TOKEN}" -e "HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}")

echo "=== vLLM ${IMAGE} on gpu${GPU}: ${MODEL} as '${SERVED}' :${PORT}  dtype=${DTYPE} (${DTYPE_REASON})  max_len=${MAX_LEN} ==="
[ -n "$ADAPTER" ] && echo "    LoRA adapter: ${ADAPTER} (max rank ${MAX_LORA_RANK})"
# `${arr[@]+"${arr[@]}"}` expands an EMPTY array safely under `set -u` on bash 3.2 (macOS) as well.
DOCKER_CMD=(docker run -d --name "$NAME" --gpus "\"device=${GPU}\""
  -v "${HF_CACHE}:/root/.cache/huggingface"
  ${ADAPTER_MOUNT[@]+"${ADAPTER_MOUNT[@]}"} ${HF_ENV[@]+"${HF_ENV[@]}"}
  -p "${PORT}:8000"
  "$IMAGE"
  --model "$MODEL" --served-model-name "$SERVED"
  --dtype "$DTYPE" --max-model-len "$MAX_LEN" --gpu-memory-utilization "$GPU_MEM_UTIL"
  --enable-auto-tool-choice --tool-call-parser hermes
  ${ADAPTER_ARGS[@]+"${ADAPTER_ARGS[@]}"})

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY_RUN=1 — would run (token values elided):"
  printf '  %q' "${DOCKER_CMD[@]}" | sed -E 's/(HF_TOKEN|HUGGING_FACE_HUB_TOKEN)=[^ ]*/\1=***/g'; echo
  echo "serve_vllm: DRY_RUN ok — nothing started"
  exit 0
fi
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "NOTE: image ${IMAGE} is not present locally — docker will pull it (~10 GB) before the server starts"
fi
docker rm -f "$NAME" >/dev/null 2>&1 || true
"${DOCKER_CMD[@]}"

echo "Waiting for http://127.0.0.1:${PORT}/v1/models ..."
for i in $(seq 1 "$HEALTH_TRIES"); do
  if curl -fsS "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "vLLM is up. Served models:"
    curl -fsS "http://127.0.0.1:${PORT}/v1/models" | head -c 600; echo
    break
  fi
  if ! docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
    echo "ERROR: container exited. Last log lines:"; docker logs --tail 60 "$NAME"; exit 1
  fi
  sleep 5
  if [ "$i" = "$HEALTH_TRIES" ]; then echo "TIMEOUT. Logs:"; docker logs --tail 60 "$NAME"; exit 1; fi
done

cat <<EOF

=== Next steps ===
1. Smoke-test one tool call (Vietnamese user turn, hermes parser -> structured tool_calls):
     curl -s http://localhost:${PORT}/v1/chat/completions -H 'Content-Type: application/json' -d '{
       "model": "${SERVED}", "temperature": 0,
       "messages": [{"role":"system","content":"Bạn là trợ lý gọi công cụ."},
                    {"role":"user","content":"Tìm tài sản có mã LAP-001"}],
       "tools": [{"type":"function","function":{"name":"get_asset","description":"Tra cứu một tài sản theo mã",
                  "parameters":{"type":"object","properties":{"asset_ref":{"type":"string"}},"required":["asset_ref"]}}}],
       "tool_choice": "auto"}' | head -c 800; echo

2. Predict on an eval set (public: per-record tools, no --tools):
     python training/predict_toolcall.py --eval data/public/xlam_2k.eval.json \\
       --out results/${SERVED}_pred.jsonl --backend openai \\
       --base-url http://localhost:${PORT}/v1 --model ${SERVED} --system prompts/system_preamble_v0.txt
   SGOD eval (catalogue + policy + preamble v1):
     python training/predict_toolcall.py --eval data/sgod/eval_v1.json --out results/sgod_eval_v1/${SERVED}_\$(date +%F).predictions.jsonl \\
       --backend openai --base-url http://localhost:${PORT}/v1 --model ${SERVED} \\
       --tools tools/sgod/sgod_tools.json --system prompts/system_preamble_v1.txt

3. Score:  python training/eval_toolcall.py --gold <eval.json> --pred <predictions.jsonl> --out <results.json> --md <results.md>

Colab / Kaggle (no docker): see the comment block at the end of this script; pip spec = "${PIP_VLLM_SPEC}"
   (pin: docs/serving.md section 5, VLLM_VERSION; docker here used image ${IMAGE}).

Stop the server:  docker rm -f ${NAME}
Logs:             docker logs -f ${NAME}
EOF

# ──────────────────────────────────────────────────────────────────────────────────────────────
# Colab / Kaggle alternative (no docker). Same flags, run in a notebook cell; T4 -> --dtype half.
# vLLM pin: ONE place only -- docs/serving.md section 5 ("VLLM_VERSION: x.y.z", written after the
# first successful T4 run; requirements-train.txt deliberately does not list vllm because it drags its own
# torch). Until that line exists, install unpinned exactly like notebooks/finetune/03_serve_vllm_colab.ipynb
# does, and paste the versions the notebook prints (vllm / torch / transformers) into the task comment.
#
#   VLLM_VERSION = ""                          # <- copy from docs/serving.md section 5 when it is set
#   !pip install -q "vllm{'==' + VLLM_VERSION if VLLM_VERSION else ''}"
#   import subprocess, os
#   srv = subprocess.Popen(
#       ["python", "-m", "vllm.entrypoints.openai.api_server",
#        "--model", "Qwen/Qwen2.5-0.5B-Instruct", "--served-model-name", "qwen2.5-0.5b",
#        "--dtype", "half", "--max-model-len", "4096", "--gpu-memory-utilization", "0.85",
#        "--enable-auto-tool-choice", "--tool-call-parser", "hermes", "--port", "8000",
#        # LoRA (adapter unzipped from Drive; served name = the adapter name below):
#        # "--enable-lora", "--max-lora-rank", "16", "--lora-modules", "qwen-ft=/content/adapter",
#       ], stdout=open("/content/vllm.log", "w"), stderr=subprocess.STDOUT)
#   # poll:  !until curl -fsS localhost:8000/v1/models; do sleep 5; done
#   # then:  !python training/predict_toolcall.py --eval data/public/xlam_2k.eval.json --out results/pred.jsonl \
#   #            --backend openai --base-url http://localhost:8000/v1 --model qwen2.5-0.5b
# ──────────────────────────────────────────────────────────────────────────────────────────────
