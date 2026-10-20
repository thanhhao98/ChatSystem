#!/usr/bin/env python3
"""Offline preflight of config_sgod.py + the prompt directory, BEFORE any LLM call (no key, no network).

The Data team runs it on their branch before opening a prompts/config PR; datagen/run_pipeline.sh runs it
before every LLM stage and stops (exit 2) when it reports an error, so a typo never costs LLM calls.

ERROR (exit 1):
  - a plan row (TRACKB_BUCKET_PLAN for train/pilot, BUCKET_PLAN for eval-aug) with a bad shape, a count that
    is not a positive integer, a role that is not a chat role of roles.json, or (TRACKB) a tool that is not
    in sgod_tools.json;
  - a PARAM_SAMPLER entry for an unknown tool, or one that raises / does not return a dict;
  - an irrelevance kind with neither IRRELEVANCE_CONFIG["<kind>_hint"] nor irrelevance_<kind>.md;
  - a missing prompt directory; training prompts used for eval augmentation or the reverse;
  - eval-aug generation without <prompt dir>/domain_system.md (it would fall back to the TRAINING
    DOMAIN_SYSTEM, contract 2 §1: the gpt_aug part is generated with its own prompt set).
WARNING: a category with neither CATEGORY_HINTS entry nor category_<name>.md (the bare name is sent to the
  model) or, for eval-aug, without its own category_<name>.md (the training hint would be sent), a *.md file
  the run never reads (typo?), an empty prompt file, catalogue tools the training plan does not cover,
  fractions that do not sum to 1.
INFO: which prompt files override which defaults, leakage sets found, models (aliases), plan size and an
  estimate of the LLM calls of the run.

Usage:
  python3 datagen/preflight.py                         # training plan + datagen/prompts
  python3 datagen/preflight.py --mode pilot --max-total 60 --irrel-count 8
  python3 datagen/preflight.py --mode eval-aug         # BUCKET_PLAN + datagen/prompts_eval
  bash datagen/run_pipeline.sh --check [--pilot | --eval-aug]
"""
import argparse
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_sgod as cfg  # noqa: E402
import audit_test_cases as audit  # noqa: E402
import generate_scenarios as gen  # noqa: E402  (build_plan: same scaling / max-total capping as the run)

STATIC_PROMPTS = {  # <name>.md -> script that reads it
    "domain_system": "generate_scenarios",
    "label_system": "label_scenarios + verify_trainset",
    "arbiter_system": "polish_scenarios",
    "reviewer_system": "audit_test_cases",
    "irrelevance_system": "generate_irrelevance",
}
GEN_BATCH, IRREL_BATCH = 12, 15   # generate_scenarios --batch / generate_irrelevance --batch defaults
REVIEW_SHARE = 0.4                # share of rows sent to verify stage C in review-only mode (POC v1: 62% agreed)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["train", "pilot", "eval-aug"], default="train")
    p.add_argument("--prompt-dir", default=None,
                   help="default: datagen/prompts (train/pilot) or datagen/prompts_eval (eval-aug)")
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--max-total", type=int, default=0)
    p.add_argument("--irrel-count", type=int, default=300, help="for the call estimate (train/pilot)")
    p.add_argument("--stages", default="", help="stages this run executes, space-separated (run_pipeline.sh "
                                                  "passes them); default: every stage of the mode")
    audit.add_catalogue_args(p)
    args = p.parse_args()

    errors, warns, infos = [], [], []
    eval_mode = args.mode == "eval-aug"
    stages = set(args.stages.split()) or None   # None = every stage of the mode
    runs_generate = stages is None or "generate" in stages
    prompt_dir = args.prompt_dir or (cfg.PROMPT_DIR_EVAL if eval_mode else cfg.PROMPT_DIR)
    pd = cfg.repo_path(prompt_dir).resolve()
    if pd == cfg.repo_path(cfg.PROMPT_DIR).resolve() and eval_mode:
        errors.append(f"--eval-aug với prompt huấn luyện {cfg.PROMPT_DIR}: hai bộ prompt phải tách rời "
                      f"(datagen/prompts_eval/README.md)")
    if pd == cfg.repo_path(cfg.PROMPT_DIR_EVAL).resolve() and not eval_mode:
        errors.append(f"dữ liệu huấn luyện sinh bằng prompt eval {cfg.PROMPT_DIR_EVAL} = rò rỉ phân phối; "
                      f"dùng --eval-aug")
    if not pd.is_dir():
        errors.append(f"không có thư mục prompt {prompt_dir}")
    elif eval_mode and runs_generate:
        f = pd / "domain_system.md"
        if not (f.is_file() and f.read_text(encoding="utf-8").strip()):
            errors.append(f"--eval-aug cần {prompt_dir}/domain_system.md: thiếu tệp này thì generate dùng DOMAIN_SYSTEM "
                          f"của tập huấn luyện, trong khi phần gpt_aug phải sinh bằng bộ prompt riêng (hợp đồng 2 §1, "
                          f"datagen/prompts_eval/README.md)")

    tools, _perms = audit.load_catalogue(args)
    catalogue = set(tools)
    chat_roles = set(cfg.CHAT_ROLES)

    # ── plan rows ────────────────────────────────────────────────────────────
    plan_name = "BUCKET_PLAN" if eval_mode else "TRACKB_BUCKET_PLAN"
    plan = getattr(cfg, plan_name)
    arity = 3 if eval_mode else 4
    categories, plan_tools = set(), set()
    for i, row in enumerate(plan):
        if not isinstance(row, (tuple, list)) or len(row) != arity:
            errors.append(f"{plan_name}[{i}] = {row!r}: cần {arity} phần tử")
            continue
        *head, n = row
        tool = head[0] if not eval_mode else None
        cat, role = head[-2], head[-1]
        if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
            errors.append(f"{plan_name}[{i}] {row!r}: count phải là số nguyên dương")
        if cfg.ROLE_MAP.get(role, role) not in chat_roles:
            errors.append(f"{plan_name}[{i}] {row!r}: role {role!r} không thuộc roles.json {sorted(chat_roles)} "
                          f"(hoặc alias trong ROLE_MAP)")
        if tool is not None:
            plan_tools.add(tool)
            if tool not in catalogue:
                errors.append(f"{plan_name}[{i}] {row!r}: tool {tool!r} không có trong {args.tools}")
        categories.add(cat)
    if not plan:
        errors.append(f"{plan_name} rỗng")

    for cat in sorted(categories):
        f = pd / f"category_{cat}.md"
        has_file = f.is_file() and f.read_text(encoding="utf-8").strip()
        if not has_file and cat not in cfg.CATEGORY_HINTS:
            warns.append(f"category {cat!r} không có CATEGORY_HINTS và không có {f.name}: model chỉ nhận tên {cat!r}")
        elif not has_file and eval_mode and runs_generate:
            warns.append(f"category {cat!r}: không có {f.name} trong {prompt_dir} nên generate dùng CATEGORY_HINTS "
                         f"của tập huấn luyện")

    # ── PARAM_SAMPLER (train/pilot generation steers each query with it) ─────
    for tool, fn in cfg.PARAM_SAMPLER.items():
        if tool not in catalogue:
            errors.append(f"PARAM_SAMPLER[{tool!r}]: tool không có trong {args.tools}")
            continue
        for seed in range(25):
            try:
                hint = fn(random.Random(seed))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"PARAM_SAMPLER[{tool!r}] lỗi với seed {seed}: {type(exc).__name__}: {exc}")
                break
            if not isinstance(hint, dict):
                errors.append(f"PARAM_SAMPLER[{tool!r}] phải trả dict, nhận {type(hint).__name__}")
                break
    kinds = {}
    if not eval_mode:
        no_sampler = sorted(t for t in plan_tools & catalogue if t not in cfg.PARAM_SAMPLER)
        if no_sampler:
            warns.append(f"tool trong {plan_name} chưa có PARAM_SAMPLER (sinh câu không có gợi ý thực thể): {no_sampler}")
        uncovered = sorted(catalogue - plan_tools)
        if uncovered:
            warns.append(f"{len(uncovered)}/{len(catalogue)} tool chưa có dòng nào trong {plan_name}: {uncovered}")
        kinds = dict(cfg.IRRELEVANCE_CONFIG.get("kinds") or {})
        if kinds and abs(sum(kinds.values()) - 1.0) > 0.01:
            warns.append(f"IRRELEVANCE_CONFIG['kinds'] cộng lại = {sum(kinds.values()):.2f} (≠ 1)")
        for k in kinds:
            if f"{k}_hint" not in cfg.IRRELEVANCE_CONFIG and not (pd / f"irrelevance_{k}.md").is_file():
                errors.append(f"irrelevance kind {k!r}: thiếu IRRELEVANCE_CONFIG['{k}_hint'] và irrelevance_{k}.md")
    mix = cfg.MIX_TARGETS
    if abs(mix.get("domain_verified", 0) + mix.get("replay", 0) + mix.get("irrelevance", 0) - 1.0) > 0.01:
        warns.append("MIX_TARGETS domain_verified + replay + irrelevance ≠ 1")

    # ── prompt files: which ones this run reads ──────────────────────────────
    read_here = {"domain_system", "label_system"} | ({"arbiter_system"} if eval_mode else {"irrelevance_system"})
    read_here |= {f"category_{c}" for c in categories} | {f"irrelevance_{k}" for k in kinds}
    if pd.is_dir():
        for f in sorted(pd.glob("*.md")):
            if f.name == "README.md":
                continue
            if not f.read_text(encoding="utf-8").strip():
                warns.append(f"{f.name} rỗng: script dùng chuỗi mặc định trong code")
            elif f.stem in read_here:
                infos.append(f"prompt {f.name} ghi đè mặc định")
            elif f.stem in STATIC_PROMPTS:
                infos.append(f"prompt {f.name} (dùng bởi {STATIC_PROMPTS[f.stem]}, không chạy ở chế độ {args.mode})")
            else:
                warns.append(f"{f.name} không được bước nào đọc ở chế độ {args.mode} (sai tên? tên hợp lệ: "
                             f"{', '.join(sorted(read_here))})")
        if not any(i.startswith("prompt ") for i in infos):
            infos.append(f"{prompt_dir}: không tệp .md nào ghi đè mặc định — mọi bước dùng chuỗi mặc định trong code")

    # ── leakage sets, models ─────────────────────────────────────────────────
    for s in cfg.EVAL_SETS_FOR_LEAKAGE:
        infos.append(f"leakage {s}: {'có' if cfg.repo_path(s).exists() else 'CHƯA CÓ (bỏ qua)'}")
    infos.append(f"models (alias): gen={cfg.model_alias(cfg.GEN_MODEL)} "
                 f"label={[cfg.model_alias(m) for m in cfg.LABEL_MODELS]} arbiter={cfg.model_alias(cfg.ARBITER_MODEL)}")

    # ── plan size + call estimate (same build_plan as generate_scenarios) ────
    buckets, _ = gen.build_plan(argparse.Namespace(
        trackb=not eval_mode, only_categories="", scale=args.scale, uniform=False, seeds="",
        per_bucket=20, max_total=args.max_total))
    rows = sum(b[-1] for b in buckets)
    n_label = len(cfg.LABEL_MODELS)
    est = {"generate": sum(math.ceil(b[-1] / GEN_BATCH) for b in buckets), "label": rows * n_label}
    if eval_mode:
        est["polish"] = rows
    else:
        est["verify"] = math.ceil(rows * REVIEW_SHARE) * n_label
        est["irrelevance"] = sum(math.ceil(max(1, round(args.irrel_count * f)) / IRREL_BATCH) for f in kinds.values())
    est = {k: v for k, v in est.items() if stages is None or k in stages}   # only the stages that run
    infos.append(f"plan {plan_name}: {len(buckets)} bucket, {rows} hàng (scale={args.scale}, "
                 f"max_total={args.max_total or '-'}); ước tính ≈ {sum(est.values())} lần gọi LLM {est}")

    for line in infos:
        print(f"  INFO  {line}")
    for line in warns:
        print(f"  WARN  {line}")
    for line in errors:
        print(f"  ERROR {line}")
    print(f"SUMMARY preflight: mode={args.mode} prompt_dir={prompt_dir} errors={len(errors)} warnings={len(warns)} "
          f"plan_rows={rows} est_llm_calls={sum(est.values())}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
