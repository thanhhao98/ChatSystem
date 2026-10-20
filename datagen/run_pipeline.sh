#!/usr/bin/env bash
# SGOD data pipeline — one resumable run (LLM stages run on the reference infrastructure; they need OPENAI_API_KEY):
#   training : generate -> label -> verify -> irrelevance -> replay -> assemble -> audit
#   eval-aug : generate -> label -> polish -> export          (eval_v1 GPT augmentation, D Việc 4)
# Each stage is SKIPPED when its output already exists and is non-empty (delete the file, or pass --force, to
# redo it). Stages checkpoint to <output>.partial and write <output> only when they finish, so an interrupted
# stage is re-run, never skipped. Everything is written under OUT_DIR; file names never collide between modes
# (pilot_*, eval_aug_*). An offline preflight (datagen/preflight.py) runs before any LLM stage.
#
#   bash datagen/run_pipeline.sh                      # full training run, all stages
#   bash datagen/run_pipeline.sh --pilot              # pilot -> data/sgod/pilot_train.jsonl (60 planned + 8 irrelevance; no replay)
#   bash datagen/run_pipeline.sh --eval-aug           # datagen/prompts_eval + BUCKET_PLAN -> data/sgod/eval_aug.json
#   bash datagen/run_pipeline.sh --check [--pilot|--eval-aug]   # preflight only: no key, no LLM call
#   bash datagen/run_pipeline.sh --stage generate,label
#   bash datagen/run_pipeline.sh --stage audit        # offline stages need no key
#   bash datagen/run_pipeline.sh --help
#
# Env knobs (defaults in brackets):
#   OPENAI_API_KEY (required for LLM stages), OPENAI_BASE_URL (optional gateway)
#   GEN_MODEL / LABEL_MODELS (space-separated) / ARBITER_MODEL  [placeholders in datagen/config_sgod.py]
#   SCORED_MODEL  the GPT under test (S Việc 8); a GEN/LABEL/ARBITER model with the same name (after the last
#                 "/") is refused (contract 2). REQUIRED with --eval-aug.
#   OUT_DIR [data/sgod]   SCALE [1.0]   MAX_TOTAL [0 = plan size; pilot 60]   IRREL_COUNT [300; pilot 8]
#   GEN_WORKERS [12; pilot 4]  LBL_WORKERS [16; pilot 4]  VER_WORKERS [16; pilot 4]
#   PROMPT_DIR [datagen/prompts; eval-aug datagen/prompts_eval — PROMPT_DIR=datagen/prompts_eval selects eval-aug]
#   PREAMBLE [prompts/system_preamble_v1.txt]   TOOL_DEFS_PATH / TOOL_POLICY_PATH / ROLES_PATH [tools/sgod/*.json]
#   VERIFY_MODE [review-only | full | offline]  (review-only = stage C on _needs_review rows only)
#   LLM_TIMEOUT [120 s per request]   LLM_MAX_RETRIES [3, transient errors only]
# Output of each invocation: OUT_DIR/<prefix>pipeline.log (git-ignored); last line SUMMARY with the LLM calls
# and tokens of all stages, per model alias.
# Exit codes: 0 ok · 2 missing OPENAI_API_KEY / bad args / preflight error · 11 generate · 12 label · 13 verify
#   · 14 irrelevance · 15 replay · 16 assemble · 17 audit · 18 polish · 19 export.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
REPO="$PWD"
PY="${PYTHON:-python3}"

usage() { awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; }

PILOT=0
EVAL_AUG=0
FORCE=0
CHECK_ONLY=0
STAGES=""
while [ $# -gt 0 ]; do
  case "$1" in
    --stage) shift; STAGES="$(echo "${1:-}" | tr ',' ' ')";;
    --stage=*) STAGES="$(echo "${1#--stage=}" | tr ',' ' ')";;
    --pilot) PILOT=1;;
    --eval-aug) EVAL_AUG=1;;
    --check) CHECK_ONLY=1;;
    --force) FORCE=1;;
    -h|--help) usage; exit 0;;
    *) echo "unknown argument: $1" >&2; usage; exit 2;;
  esac
  shift
done
if [ "$PILOT" = 1 ] && [ "$EVAL_AUG" = 1 ]; then echo "LỖI: --pilot và --eval-aug loại trừ nhau" >&2; exit 2; fi

# ── config from config_sgod.py (single source of truth for models / paths) ────
cfg() { "$PY" -c "import sys; sys.path.insert(0,'datagen'); import config_sgod as c; v=getattr(c,'$1'); print(' '.join(v) if isinstance(v,(list,tuple)) else v)"; }
real_dir() { (cd "$1" 2>/dev/null && pwd -P) || echo "$1"; }

MODE=train
[ "$PILOT" = 1 ] && MODE=pilot
[ "$EVAL_AUG" = 1 ] && MODE=eval-aug
# PROMPT_DIR=datagen/prompts_eval (the documented eval-aug form) switches to eval-aug, so eval prompts can
# never write the training files raw.json / labeled.json (and the training run never reuses eval rows).
if [ -n "${PROMPT_DIR:-}" ] && [ "$MODE" != eval-aug ] \
   && [ "$(real_dir "$PROMPT_DIR")" = "$(real_dir "$(cfg PROMPT_DIR_EVAL)")" ]; then
  if [ "$MODE" = pilot ]; then
    echo "LỖI: --pilot sinh dữ liệu huấn luyện, không dùng prompt eval ($PROMPT_DIR); dùng --eval-aug" >&2; exit 2
  fi
  echo "PROMPT_DIR=$PROMPT_DIR là bộ prompt eval -> chế độ --eval-aug (đầu ra eval_aug_*)"
  MODE=eval-aug
fi

case "$MODE" in
  eval-aug) STAGES_ALL="generate label polish export"; STAGES_DEFAULT="$STAGES_ALL"; PFX="eval_aug_"
            PROMPT_DIR="${PROMPT_DIR:-$(cfg PROMPT_DIR_EVAL)}";;
  pilot)    STAGES_ALL="generate label verify irrelevance replay assemble audit"
            STAGES_DEFAULT="generate label verify irrelevance assemble audit"; PFX="pilot_"   # pilot never uses replay
            PROMPT_DIR="${PROMPT_DIR:-$(cfg PROMPT_DIR)}";;
  *)        STAGES_ALL="generate label verify irrelevance replay assemble audit"; STAGES_DEFAULT="$STAGES_ALL"; PFX=""
            PROMPT_DIR="${PROMPT_DIR:-$(cfg PROMPT_DIR)}";;
esac
STAGES="${STAGES:-$STAGES_DEFAULT}"
for s in $STAGES; do
  case " $STAGES_ALL " in *" $s "*) ;; *) echo "unknown stage for mode $MODE: $s (choose from: $STAGES_ALL)" >&2; exit 2;; esac
done
has_stage() { case " $STAGES " in *" $1 "*) return 0;; *) return 1;; esac; }

OUT_DIR="${OUT_DIR:-$(cfg DATA_DIR)}"
GEN_MODEL="${GEN_MODEL:-$(cfg GEN_MODEL)}"
LABEL_MODELS="${LABEL_MODELS:-$(cfg LABEL_MODELS)}"
ARBITER_MODEL="${ARBITER_MODEL:-$(cfg ARBITER_MODEL)}"
PREAMBLE="${PREAMBLE:-$(cfg PREAMBLE_V1_PATH)}"
REPLAY_RAW="$(cfg REPLAY_CONFIG | "$PY" -c "import sys,ast; print(ast.literal_eval(sys.stdin.read())['local_path'])" 2>/dev/null || echo data/public/xlam_raw_2k.jsonl)"
REPLAY_SEED="$("$PY" -c "import sys; sys.path.insert(0,'datagen'); import config_sgod as c; print(c.REPLAY_CONFIG['converter_seed'])")"
SCALE="${SCALE:-1.0}"
if [ "$MODE" = pilot ]; then   # pilot defaults; an explicit env value still wins (e.g. a tiny smoke run)
  MAX_TOTAL="${MAX_TOTAL:-60}"; IRREL_COUNT="${IRREL_COUNT:-8}"
  GEN_WORKERS="${GEN_WORKERS:-4}"; LBL_WORKERS="${LBL_WORKERS:-4}"; VER_WORKERS="${VER_WORKERS:-4}"
else
  MAX_TOTAL="${MAX_TOTAL:-0}"; IRREL_COUNT="${IRREL_COUNT:-300}"
  GEN_WORKERS="${GEN_WORKERS:-12}"; LBL_WORKERS="${LBL_WORKERS:-16}"; VER_WORKERS="${VER_WORKERS:-16}"
fi
VERIFY_MODE="${VERIFY_MODE:-review-only}"

RAW="$OUT_DIR/${PFX}raw.json"; LABELED="$OUT_DIR/${PFX}labeled.json"
VERIFIED="$OUT_DIR/${PFX}verified.json"; QUAR="$OUT_DIR/${PFX}quarantine.json"
IRREL="$OUT_DIR/${PFX}irrelevance.json"; POLISHED="$OUT_DIR/${PFX}polished.json"
REPORT_PFX="$OUT_DIR/$PFX"; TRAIN_OUT="$OUT_DIR/${PFX}train.jsonl"; EXPORT="$OUT_DIR/eval_aug.json"
REPLAY_PFX="$OUT_DIR/replay"

# ── secrets: only OPENAI_API_KEY / OPENAI_BASE_URL are read, never printed ────
NEEDS_KEY=0
for s in generate label irrelevance polish; do has_stage "$s" && NEEDS_KEY=1; done
has_stage verify && [ "$VERIFY_MODE" != offline ] && NEEDS_KEY=1

# ── preflight (offline): config + prompt dir checked before any LLM call ─────
if [ "$CHECK_ONLY" = 1 ] || [ "$NEEDS_KEY" = 1 ]; then
  "$PY" datagen/preflight.py --mode "$MODE" --prompt-dir "$PROMPT_DIR" --scale "$SCALE" --stages "$STAGES" \
      --max-total "$MAX_TOTAL" --irrel-count "$IRREL_COUNT" || { echo "LỖI: preflight thất bại (xem ERROR ở trên)" >&2; exit 2; }
  [ "$CHECK_ONLY" = 1 ] && exit 0
fi

if [ "$NEEDS_KEY" = 1 ] && [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "LỖI: thiếu biến môi trường OPENAI_API_KEY. Các bước generate/label/verify/irrelevance/polish gọi LLM nên chạy trên hạ tầng tham chiếu" >&2
  echo "     (export OPENAI_API_KEY=...; tuỳ chọn OPENAI_BASE_URL=https://<gateway>/v1). Bước offline: --stage replay,assemble,audit" >&2
  exit 2
fi
# contract 2: the judge/arbiter (and generator/labelers) must not be the GPT under test
if [ "$NEEDS_KEY" = 1 ]; then
  if [ "$MODE" = eval-aug ] && [ -z "${SCORED_MODEL:-}" ]; then
    echo "LỖI: --eval-aug cần SCORED_MODEL = model GPT sẽ được chấm (S Việc 8) để kiểm arbiter ≠ GPT bị chấm (hợp đồng 2)" >&2
    exit 2
  fi
  if [ -n "${SCORED_MODEL:-}" ]; then
    for m in $GEN_MODEL $LABEL_MODELS $ARBITER_MODEL; do
      if [ "${m##*/}" = "${SCORED_MODEL##*/}" ]; then
        echo "LỖI: model ${m##*/} của pipeline trùng model GPT bị chấm (SCORED_MODEL) — hợp đồng 2: arbiter ≠ GPT bị chấm" >&2
        exit 2
      fi
    done
  fi
fi

mkdir -p "$OUT_DIR"
# one invocation per OUT_DIR + mode: two concurrent runs would overwrite each other's stage files
LOCK="$OUT_DIR/.${PFX}pipeline.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  OTHER="$(cat "$LOCK/pid" 2>/dev/null || echo "?")"
  if [ "$OTHER" != "?" ] && kill -0 "$OTHER" 2>/dev/null; then
    echo "LỖI: một lần chạy khác (pid $OTHER) đang ghi vào $OUT_DIR (chế độ $MODE); chờ nó xong" >&2
    echo "     (chắc chắn không còn lần chạy nào: rm -rf $LOCK)" >&2
    exit 2
  fi
  echo "  WARN: bỏ khoá cũ $LOCK (pid $OTHER không còn chạy)" >&2
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT
LOG="$OUT_DIR/${PFX}pipeline.log"   # git-ignored (*.log); this invocation only
: > "$LOG"
ts() { date +"%F %T"; }
stage() { echo; echo "=== [$(ts)] $* ==="; }
run() { PYTHONUNBUFFERED=1 "$PY" "$@" 2>&1 | tee -a "$LOG"; }
skip_if_done() { [ "$FORCE" = 0 ] && [ -s "$1" ]; }
stale_warn() {   # $1 = output, $2 = its input: a re-generated input does not re-run the next stage by itself
  if [ -s "$1" ] && [ -s "$2" ] && [ "$2" -nt "$1" ]; then
    echo "  WARN: $2 mới hơn $1 — nếu đã sinh lại đầu vào, chạy lại bước này với --force" >&2
  fi
}
count_rows() { "$PY" -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "$1" 2>/dev/null || echo "?"; }
alias_list() { local out="" m; for m in "$@"; do out="$out ${m##*/}"; done; echo "${out# }"; }

echo "pipeline: mode=$MODE stages=[$STAGES] out=$OUT_DIR gen_model=${GEN_MODEL##*/} label_models=[$(alias_list $LABEL_MODELS)] arbiter=${ARBITER_MODEL##*/} prompt_dir=$PROMPT_DIR" | tee -a "$LOG"

# ── STAGE 1: generate net-new scenarios ──────────────────────────────────────
if has_stage generate; then
  if skip_if_done "$RAW"; then stage "SKIP generate ($RAW exists, $(count_rows "$RAW") rows)"; else
    if [ "$MODE" = eval-aug ]; then PLAN_FLAG=""; PLAN_NAME="BUCKET_PLAN"; else PLAN_FLAG="--trackb"; PLAN_NAME="TRACKB_BUCKET_PLAN"; fi
    stage "STAGE 1 generate ($PLAN_NAME, scale=$SCALE, max_total=$MAX_TOTAL, workers=$GEN_WORKERS)"
    # shellcheck disable=SC2086
    run datagen/generate_scenarios.py $PLAN_FLAG --scale "$SCALE" --max-total "$MAX_TOTAL" \
        --gen-workers "$GEN_WORKERS" --model "$GEN_MODEL" --prompt-dir "$PROMPT_DIR" \
        --train "$OUT_DIR/train.jsonl" --output "$RAW" || exit 11
  fi
fi

# ── STAGE 2: multi-LLM consensus labeling ────────────────────────────────────
if has_stage label; then
  if skip_if_done "$LABELED"; then stage "SKIP label ($LABELED exists)"; stale_warn "$LABELED" "$RAW"; else
    stage "STAGE 2 label ([$(alias_list $LABEL_MODELS)], workers=$LBL_WORKERS)"
    # shellcheck disable=SC2086
    run datagen/label_scenarios.py --input "$RAW" --models $LABEL_MODELS --workers "$LBL_WORKERS" \
        --prompt-dir "$PROMPT_DIR" --output "$LABELED" --report "${REPORT_PFX}label_report.json" || exit 12
  fi
fi

# ── STAGE 3: 3-stage verification gate ───────────────────────────────────────
if has_stage verify; then
  if skip_if_done "$VERIFIED"; then stage "SKIP verify ($VERIFIED exists)"; stale_warn "$VERIFIED" "$LABELED"; else
    stage "STAGE 3 verify (mode=$VERIFY_MODE, workers=$VER_WORKERS)"
    case "$VERIFY_MODE" in
      offline) VFLAGS="--no-semantic";;
      full) VFLAGS="--consensus-min 2";;
      *) VFLAGS="--consensus-min 2 --semantic-review-only";;
    esac
    # shellcheck disable=SC2086
    run datagen/verify_trainset.py --input "$LABELED" --models $LABEL_MODELS --workers "$VER_WORKERS" \
        --prompt-dir "$PROMPT_DIR" $VFLAGS --pass-out "$VERIFIED" --quarantine-out "$QUAR" \
        --report "${REPORT_PFX}verify_report.json" || exit 13
  fi
fi

# ── STAGE 4: genuine irrelevance (~10%) ──────────────────────────────────────
if has_stage irrelevance; then
  if skip_if_done "$IRREL"; then stage "SKIP irrelevance ($IRREL exists)"; else
    stage "STAGE 4 irrelevance (count=$IRREL_COUNT)"
    run datagen/generate_irrelevance.py --count "$IRREL_COUNT" --model "$GEN_MODEL" \
        --prompt-dir "$PROMPT_DIR" --train "$OUT_DIR/train.jsonl" --output "$IRREL" || exit 14
  fi
fi

# ── STAGE 4b (eval-aug): arbiter ≠ GPT under test fixes labels + alternates ──
if has_stage polish; then
  if skip_if_done "$POLISHED"; then stage "SKIP polish ($POLISHED exists)"; stale_warn "$POLISHED" "$LABELED"; else
    stage "STAGE 4b polish (arbiter=${ARBITER_MODEL##*/})"
    run datagen/polish_scenarios.py --input "$LABELED" --output "$POLISHED" \
        --report "${REPORT_PFX}polish_report.json" --model "$ARBITER_MODEL" --prompt-dir "$PROMPT_DIR" || exit 18
  fi
fi

# ── STAGE 5: xLAM replay from the committed public slice (no HF download) ────
if has_stage replay; then
  if skip_if_done "$REPLAY_PFX.train.jsonl"; then stage "SKIP replay ($REPLAY_PFX.train.jsonl exists)"; else
    stage "STAGE 5 replay (convert_xlam from $REPLAY_RAW, seed=$REPLAY_SEED)"
    run datagen/convert_xlam.py --in "$REPLAY_RAW" --out-prefix "$REPLAY_PFX" \
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
  if [ "$MODE" = pilot ]; then
    stage "STAGE 6 build_parity (pilot) -> $TRAIN_OUT"
    run datagen/build_parity_trainset.py --sources "$VERIFIED" "$IRREL" --out-dir "$OUT_DIR" \
        --train-name "$(basename "$TRAIN_OUT")" --val-ratio 0 --preamble "$PREAMBLE" || exit 16
  else
    stage "STAGE 6 assemble -> $OUT_DIR/{train,val}.jsonl"
    run datagen/assemble_trackb_trainset.py --domain "$VERIFIED" --irrelevance "$IRREL" \
        --replay "$REPLAY_PFX.train.jsonl" --out-dir "$OUT_DIR" --val-ratio 0.05 --preamble "$PREAMBLE" || exit 16
  fi
fi

# ── STAGE 6b (eval-aug): contract-2 eval records for the Data team to review ─
if has_stage export; then
  SRC="$POLISHED"; XFLAG=""
  if [ ! -s "$SRC" ]; then   # contract 2: alternates come from the arbiter; unpolished rows are flagged
    SRC="$LABELED"; XFLAG="--unpolished"
    echo "  WARN: chưa có $POLISHED — xuất từ $LABELED (chưa qua arbiter), mọi bản ghi gắn _needs_review" >&2
  fi
  stage "STAGE 6b export $SRC -> $EXPORT"
  # shellcheck disable=SC2086
  run datagen/export_eval_aug.py --input "$SRC" --output "$EXPORT" $XFLAG || exit 19
fi

# ── STAGE 7: alignment audit against the current catalogue ───────────────────
if has_stage audit; then
  stage "STAGE 7 audit trainset vs catalogue"
  if [ "$MODE" = pilot ]; then FILES="$(basename "$TRAIN_OUT")"; else FILES="train.jsonl val.jsonl"; fi
  # shellcheck disable=SC2086
  run datagen/audit_trainset_vs_api.py --data-dir "$OUT_DIR" --files $FILES --preamble "$PREAMBLE" \
      --report "${PFX}alignment_report.json" || exit 17
fi

# ── total LLM calls / tokens of this invocation (sum of the stages' SUMMARY lines) ─
METER_TOTAL="$("$PY" - "$LOG" <<'EOF'
import re, sys
tot, per = [0, 0, 0, 0], {}
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    m = re.search(r"llm_calls=(\d+) prompt_tokens=(\d+) completion_tokens=(\d+) errors=(\d+)", line)
    if not line.startswith("SUMMARY ") or not m:
        continue
    tot = [a + int(b) for a, b in zip(tot, m.groups())]
    b = re.search(r"by_model=(\S+)", line)
    for part in (b.group(1).split(",") if b else []):
        name, nums = part.rsplit(":", 1)
        per[name] = [a + int(x) for a, x in zip(per.get(name, [0, 0, 0, 0]), nums.split("/"))]
print(f"llm_calls={tot[0]} prompt_tokens={tot[1]} completion_tokens={tot[2]} errors={tot[3]}"
      + (" by_model=" + ",".join(f"{k}:{'/'.join(map(str, v))}" for k, v in sorted(per.items())) if per else ""))
EOF
)"

stage "DONE — outputs under $OUT_DIR/"
ls -la "$OUT_DIR" 2>/dev/null | sed 's/^/  /'
echo "SUMMARY run_pipeline: mode=$MODE stages=[$STAGES] out_dir=$OUT_DIR status=ok elapsed=${SECONDS}s | $METER_TOTAL" | tee -a "$LOG"
