#!/usr/bin/env bash
# SGOD data pipeline — one resumable run (LLM stages run on the reference infrastructure; they need OPENAI_API_KEY):
#   generate -> label -> verify -> irrelevance -> replay -> assemble -> audit
# Each stage is SKIPPED when its output already exists and is non-empty (delete the file, or pass
# --force, to redo it). Everything is written under data/sgod/ (OUT_DIR).
#
#   bash datagen/run_pipeline.sh                      # full run, all stages
#   bash datagen/run_pipeline.sh --pilot              # 50-row pilot -> data/sgod/pilot_train.jsonl
#   bash datagen/run_pipeline.sh --stage generate,label
#   bash datagen/run_pipeline.sh --stage audit        # offline stages need no key
#   bash datagen/run_pipeline.sh --help
#
# Env knobs (defaults in brackets):
#   OPENAI_API_KEY (required for generate/label/verify/irrelevance), OPENAI_BASE_URL (optional gateway)
#   OUT_DIR [data/sgod]   SCALE [1.0]   IRREL_COUNT [300]   MAX_TOTAL [0 = plan size]
#   GEN_WORKERS [12]  LBL_WORKERS [16]  VER_WORKERS [16]
#   GEN_MODEL / LABEL_MODELS / ARBITER_MODEL  [from datagen/config_sgod.py]
#   PROMPT_DIR [datagen/prompts]   PREAMBLE [prompts/system_preamble_v1.txt]
#   TOOL_DEFS_PATH / TOOL_POLICY_PATH / ROLES_PATH  [tools/sgod/*.json]
#   VERIFY_MODE [review-only | full | offline]  (review-only = stage C on _needs_review rows only)
# Exit codes: 0 ok · 2 missing OPENAI_API_KEY / bad args · 1x = stage x failed.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
REPO="$PWD"
PY="${PYTHON:-python3}"

usage() { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; }

STAGES_ALL="generate label verify irrelevance replay assemble audit"
STAGES="$STAGES_ALL"
PILOT=0
FORCE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --stage) shift; STAGES="$(echo "${1:-}" | tr ',' ' ')";;
    --stage=*) STAGES="$(echo "${1#--stage=}" | tr ',' ' ')";;
    --pilot) PILOT=1;;
    --force) FORCE=1;;
    -h|--help) usage; exit 0;;
    *) echo "unknown argument: $1" >&2; usage; exit 2;;
  esac
  shift
done
for s in $STAGES; do
  case " $STAGES_ALL " in *" $s "*) ;; *) echo "unknown stage: $s (choose from: $STAGES_ALL)" >&2; exit 2;; esac
done
has_stage() { case " $STAGES " in *" $1 "*) return 0;; *) return 1;; esac; }

# ── config from config_sgod.py (single source of truth for models / paths) ────
cfg() { "$PY" -c "import sys; sys.path.insert(0,'datagen'); import config_sgod as c; v=getattr(c,'$1'); print(' '.join(v) if isinstance(v,(list,tuple)) else v)"; }
OUT_DIR="${OUT_DIR:-$(cfg DATA_DIR)}"
GEN_MODEL="${GEN_MODEL:-$(cfg GEN_MODEL)}"
LABEL_MODELS="${LABEL_MODELS:-$(cfg LABEL_MODELS)}"
PROMPT_DIR="${PROMPT_DIR:-$(cfg PROMPT_DIR)}"
PREAMBLE="${PREAMBLE:-$(cfg PREAMBLE_V1_PATH)}"
REPLAY_RAW="$(cfg REPLAY_CONFIG | "$PY" -c "import sys,ast; print(ast.literal_eval(sys.stdin.read())['local_path'])" 2>/dev/null || echo data/public/xlam_raw_2k.jsonl)"
REPLAY_SEED="$("$PY" -c "import sys; sys.path.insert(0,'datagen'); import config_sgod as c; print(c.REPLAY_CONFIG['converter_seed'])")"
SCALE="${SCALE:-1.0}"
IRREL_COUNT="${IRREL_COUNT:-300}"
MAX_TOTAL="${MAX_TOTAL:-0}"
GEN_WORKERS="${GEN_WORKERS:-12}"
LBL_WORKERS="${LBL_WORKERS:-16}"
VER_WORKERS="${VER_WORKERS:-16}"
VERIFY_MODE="${VERIFY_MODE:-review-only}"

if [ "$PILOT" = 1 ]; then
  MAX_TOTAL=50; IRREL_COUNT=8; GEN_WORKERS=4; LBL_WORKERS=4; VER_WORKERS=4
  RAW="$OUT_DIR/pilot_raw.json"; LABELED="$OUT_DIR/pilot_labeled.json"
  VERIFIED="$OUT_DIR/pilot_verified.json"; QUAR="$OUT_DIR/pilot_quarantine.json"
  IRREL="$OUT_DIR/pilot_irrelevance.json"; REPORT_PFX="$OUT_DIR/pilot_"
  TRAIN_OUT="$OUT_DIR/pilot_train.jsonl"
else
  RAW="$OUT_DIR/raw.json"; LABELED="$OUT_DIR/labeled.json"
  VERIFIED="$OUT_DIR/verified.json"; QUAR="$OUT_DIR/quarantine.json"
  IRREL="$OUT_DIR/irrelevance.json"; REPORT_PFX="$OUT_DIR/"
  TRAIN_OUT="$OUT_DIR/train.jsonl"
fi
REPLAY_PFX="$OUT_DIR/replay"
mkdir -p "$OUT_DIR"

# ── secrets: only OPENAI_API_KEY / OPENAI_BASE_URL are read, never printed ────
NEEDS_KEY=0
for s in generate label irrelevance; do has_stage "$s" && NEEDS_KEY=1; done
has_stage verify && [ "$VERIFY_MODE" != offline ] && NEEDS_KEY=1
if [ "$NEEDS_KEY" = 1 ] && [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "LỖI: thiếu biến môi trường OPENAI_API_KEY. Các bước generate/label/verify/irrelevance gọi LLM nên chạy trên hạ tầng tham chiếu" >&2
  echo "     (export OPENAI_API_KEY=...; tuỳ chọn OPENAI_BASE_URL=https://<gateway>/v1). Bước offline: --stage replay,assemble,audit" >&2
  exit 2
fi

ts() { date +"%F %T"; }
stage() { echo; echo "=== [$(ts)] $* ==="; }
skip_if_done() { [ "$FORCE" = 0 ] && [ -s "$1" ]; }
count_rows() { "$PY" -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "$1" 2>/dev/null || echo "?"; }

echo "pipeline: stages=[$STAGES] pilot=$PILOT out=$OUT_DIR gen_model=$GEN_MODEL label_models=[$LABEL_MODELS] prompt_dir=$PROMPT_DIR"

# ── STAGE 1: generate net-new domain scenarios ───────────────────────────────
if has_stage generate; then
  if skip_if_done "$RAW"; then stage "SKIP generate ($RAW exists, $(count_rows "$RAW") rows)"; else
    stage "STAGE 1 generate (trackb, scale=$SCALE, max_total=$MAX_TOTAL, workers=$GEN_WORKERS)"
    "$PY" datagen/generate_scenarios.py --trackb --scale "$SCALE" --max-total "$MAX_TOTAL" \
        --gen-workers "$GEN_WORKERS" --model "$GEN_MODEL" --prompt-dir "$PROMPT_DIR" \
        --train "$OUT_DIR/train.jsonl" --output "$RAW" || exit 11
  fi
fi

# ── STAGE 2: multi-LLM consensus labeling ────────────────────────────────────
if has_stage label; then
  if skip_if_done "$LABELED"; then stage "SKIP label ($LABELED exists)"; else
    stage "STAGE 2 label ([$LABEL_MODELS], workers=$LBL_WORKERS)"
    # shellcheck disable=SC2086
    "$PY" datagen/label_scenarios.py --input "$RAW" --models $LABEL_MODELS --workers "$LBL_WORKERS" \
        --prompt-dir "$PROMPT_DIR" --output "$LABELED" --report "${REPORT_PFX}label_report.json" || exit 12
  fi
fi

# ── STAGE 3: 3-stage verification gate ───────────────────────────────────────
if has_stage verify; then
  if skip_if_done "$VERIFIED"; then stage "SKIP verify ($VERIFIED exists)"; else
    stage "STAGE 3 verify (mode=$VERIFY_MODE, workers=$VER_WORKERS)"
    case "$VERIFY_MODE" in
      offline) VFLAGS="--no-semantic";;
      full) VFLAGS="--consensus-min 2";;
      *) VFLAGS="--consensus-min 2 --semantic-review-only";;
    esac
    # shellcheck disable=SC2086
    "$PY" datagen/verify_trainset.py --input "$LABELED" --models $LABEL_MODELS --workers "$VER_WORKERS" \
        --prompt-dir "$PROMPT_DIR" $VFLAGS --pass-out "$VERIFIED" --quarantine-out "$QUAR" \
        --report "${REPORT_PFX}verify_report.json" || exit 13
  fi
fi

# ── STAGE 4: genuine irrelevance (~10%) ──────────────────────────────────────
if has_stage irrelevance; then
  if skip_if_done "$IRREL"; then stage "SKIP irrelevance ($IRREL exists)"; else
    stage "STAGE 4 irrelevance (count=$IRREL_COUNT)"
    "$PY" datagen/generate_irrelevance.py --count "$IRREL_COUNT" --model "$GEN_MODEL" \
        --prompt-dir "$PROMPT_DIR" --train "$OUT_DIR/train.jsonl" --output "$IRREL" || exit 14
  fi
fi

# ── STAGE 5: xLAM replay from the committed public slice (no HF download) ────
if has_stage replay; then
  if skip_if_done "$REPLAY_PFX.train.jsonl"; then stage "SKIP replay ($REPLAY_PFX.train.jsonl exists)"; else
    stage "STAGE 5 replay (convert_xlam from $REPLAY_RAW, seed=$REPLAY_SEED)"
    "$PY" datagen/convert_xlam.py --in "$REPLAY_RAW" --out-prefix "$REPLAY_PFX" \
        --system-file prompts/system_preamble_v0.txt --seed "$REPLAY_SEED" || exit 15
    if [ -f data/public/xlam_2k.train.jsonl ]; then
      if cmp -s "$REPLAY_PFX.train.jsonl" data/public/xlam_2k.train.jsonl; then
        echo "  replay.train.jsonl is bit-identical to data/public/xlam_2k.train.jsonl (public test split stays disjoint)"
      else
        echo "  WARN: replay.train.jsonl differs from data/public/xlam_2k.train.jsonl — check seed/preamble v0" >&2
      fi
    fi
  fi
fi

# ── STAGE 6: assemble parity trainset (pilot: build_parity only) ─────────────
if has_stage assemble; then
  if [ "$PILOT" = 1 ]; then
    stage "STAGE 6 build_parity (pilot) -> $TRAIN_OUT"
    "$PY" datagen/build_parity_trainset.py --sources "$VERIFIED" "$IRREL" --out-dir "$OUT_DIR" \
        --train-name "$(basename "$TRAIN_OUT")" --val-ratio 0 --preamble "$PREAMBLE" || exit 16
  else
    stage "STAGE 6 assemble -> $OUT_DIR/{train,val}.jsonl"
    "$PY" datagen/assemble_trackb_trainset.py --domain "$VERIFIED" --irrelevance "$IRREL" \
        --replay "$REPLAY_PFX.train.jsonl" --out-dir "$OUT_DIR" --val-ratio 0.05 --preamble "$PREAMBLE" || exit 16
  fi
fi

# ── STAGE 7: alignment audit against the current catalogue ───────────────────
if has_stage audit; then
  stage "STAGE 7 audit trainset vs catalogue"
  if [ "$PILOT" = 1 ]; then FILES="$(basename "$TRAIN_OUT")"; else FILES="train.jsonl val.jsonl"; fi
  # shellcheck disable=SC2086
  "$PY" datagen/audit_trainset_vs_api.py --data-dir "$OUT_DIR" --files $FILES --preamble "$PREAMBLE" || exit 17
fi

stage "DONE — outputs under $OUT_DIR/"
ls -la "$OUT_DIR" 2>/dev/null | sed 's/^/  /'
echo "SUMMARY run_pipeline: stages=[$STAGES] pilot=$PILOT out_dir=$OUT_DIR status=ok"
