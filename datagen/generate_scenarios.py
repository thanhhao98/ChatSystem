#!/usr/bin/env python3
"""Stage 1: generate genuinely NEW Vietnamese queries (not paraphrases), balanced across
(category, role) buckets — or (tool, category, role) buckets with --trackb — and leak-free
against the frozen eval set(s) + any existing train file.

No labels are assigned here — Stage 2 (label_scenarios.py) assigns expected_tool / params /
permission by multi-LLM consensus, so labels are independent of how queries were generated.
Batched (many queries per call) to keep cost low. Single-turn only.

Anti-leakage (two indices, two thresholds, both trigram-blocked):
  leak : eval sets (config_sgod.EVAL_SETS_FOR_LEAKAGE) + --train. STRICT (< --sim-threshold, 0.65).
  seen : already-generated queries. LOOSE (< --intra-threshold, 0.92) so legitimate
         parameter variations ("...kho tầng 1" vs "...kho miền Nam") survive.

Output rows: {"id": "SC<bucket><n>", "category", "user_role", "input", "seed_tool"?}

Usage (LLM stage — runs on the reference infrastructure, needs OPENAI_API_KEY; --plan-only needs no key):
  python3 datagen/generate_scenarios.py --plan-only                 # inspect the bucket plan, no key
  OPENAI_API_KEY=... python3 datagen/generate_scenarios.py --trackb --max-total 50 \
      --output data/sgod/raw.json                                    # 50-row pilot
  OPENAI_API_KEY=... python3 datagen/generate_scenarios.py --trackb --scale 1.0 --output data/sgod/raw.json
"""
import argparse
import json
import random
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_sgod as cfg  # noqa: E402
import simindex  # noqa: E402


def category_hint(category, prompt_dir):
    default = cfg.CATEGORY_HINTS.get(category, category)
    return cfg.load_prompt(f"category_{category}", default, prompt_dir)


def gen_batch(client, system_text, category, hint, role, n, model, param_hints=None):
    up = (f"Vai trò người dùng: {role}. Loại tình huống: {category} — {hint}.\n"
          f"Tạo {n} câu truy vấn tiếng Việt KHÁC NHAU cho tình huống này. Mỗi câu là MỘT yêu cầu "
          f"duy nhất (không nối nhiều bước). Mảng JSON thuần.")
    if param_hints:
        slots = "; ".join("/".join(f"{k}={v}" for k, v in h.items()) for h in param_hints if h)
        if slots:
            up = (f"Vai trò người dùng: {role}. Tình huống: {category} — {hint}.\n"
                  f"Mỗi câu phải đề cập một trong các BỘ THỰC THỂ sau (mỗi câu một bộ KHÁC NHAU), "
                  f"diễn đạt tự nhiên như người dùng thật, KHÔNG nêu tên tham số kỹ thuật:\n  {slots}\n"
                  f"Trộn văn phong (trang trọng/thân mật/viết tắt/lỗi chính tả nhẹ). Mỗi câu là MỘT yêu cầu "
                  f"duy nhất. Tạo {n} câu truy vấn tiếng Việt KHÁC NHAU. Mảng JSON thuần.")
    last = None
    for attempt in range(5):  # retry transient connection/network drops
        try:
            r = client.chat.completions.create(
                model=model, temperature=1.15, max_tokens=1500, timeout=60,
                messages=[{"role": "system", "content": system_text}, {"role": "user", "content": up}],
            )
            cfg.METER.add(r)
            txt = (r.choices[0].message.content or "").strip()
            txt = txt[txt.find("["): txt.rfind("]") + 1] if "[" in txt else "[]"
            arr = json.loads(txt)
            return [s.strip() for s in arr if isinstance(s, str) and len(s.strip()) >= 5]
        except json.JSONDecodeError:
            return []
        except Exception as exc:  # noqa: BLE001
            last = exc
            cfg.METER.errors += 1
            time.sleep(3 * (attempt + 1))
    raise last if last else RuntimeError("gen_batch failed")


def build_plan(args):
    """Return (buckets, trackb: bool). Track B buckets are (tool, cat, role, n); else (cat, role, n)."""
    if args.trackb:
        plan = cfg.TRACKB_BUCKET_PLAN
        if args.only_categories:
            keep = {c.strip() for c in args.only_categories.split(",")}
            plan = [b for b in plan if b[1] in keep]
            print(f"Targeted regen: only categories {sorted(keep)} -> {len(plan)} buckets")
        buckets = [(t, c, r, max(1, int(round(n * args.scale)))) for (t, c, r, n) in plan]
    elif getattr(cfg, "BUCKET_PLAN", None) and not args.uniform:
        buckets = [(c, r, max(1, int(round(n * args.scale)))) for (c, r, n) in cfg.BUCKET_PLAN]
    else:
        if not args.seeds:
            raise SystemExit("--uniform needs --seeds <case file> to derive (category, role) buckets")
        seeds = json.loads(cfg.repo_path(args.seeds).read_text(encoding="utf-8"))
        buckets = [(c, r, args.per_bucket)
                   for (c, r) in sorted({(x["category"], x["user_role"]) for x in seeds})]
    if args.max_total:
        total = sum(b[-1] for b in buckets)
        if total > args.max_total:
            f = args.max_total / total
            buckets = [(*b[:-1], max(1, int(round(b[-1] * f)))) for b in buckets]
            # trim remainder deterministically from the largest buckets
            while sum(b[-1] for b in buckets) > args.max_total:
                i = max(range(len(buckets)), key=lambda k: buckets[k][-1])
                if buckets[i][-1] <= 1:
                    break
                buckets[i] = (*buckets[i][:-1], buckets[i][-1] - 1)
    return buckets, bool(args.trackb)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--output", default=f"{cfg.DATA_DIR}/raw.json")
    p.add_argument("--train", default=f"{cfg.DATA_DIR}/train.jsonl",
                   help="existing parity train file to anti-leak against (skipped if missing)")
    p.add_argument("--extra-leakage", nargs="*", default=[],
                   help="extra case files (with 'input') to ALSO reject against")
    p.add_argument("--seeds", default="", help="case file for --uniform bucket derivation")
    p.add_argument("--per-bucket", type=int, default=20, help="rows per bucket with --uniform")
    p.add_argument("--batch", type=int, default=12, help="queries requested per LLM call")
    p.add_argument("--sim-threshold", type=float, default=cfg.LEAKAGE_THRESHOLD,
                   help="STRICT anti-leakage threshold vs eval/train sets")
    p.add_argument("--intra-threshold", type=float, default=0.92,
                   help="LOOSE near-exact-dup threshold among generated queries")
    p.add_argument("--model", default=cfg.GEN_MODEL)
    p.add_argument("--prompt-dir", default=cfg.PROMPT_DIR,
                   help="datagen/prompts (training) or datagen/prompts_eval (eval augmentation)")
    p.add_argument("--uniform", action="store_true", help="ignore BUCKET_PLAN; derive buckets from --seeds")
    p.add_argument("--trackb", action="store_true",
                   help="use TRACKB_BUCKET_PLAN (tool,category,role,count) + PARAM_SAMPLER entity hints")
    p.add_argument("--scale", type=float, default=1.0, help="multiply every bucket count")
    p.add_argument("--max-total", type=int, default=0, help="cap the whole plan at N rows (pilot = 50)")
    p.add_argument("--gen-workers", type=int, default=12, help="concurrent buckets in flight")
    p.add_argument("--only-categories", default="", help="comma-separated categories (targeted regen)")
    p.add_argument("--seed", type=int, default=cfg.DEFAULT_SEED, help="base seed for per-bucket RNGs")
    p.add_argument("--plan-only", action="store_true", help="print the bucket plan and exit (no API key)")
    args = p.parse_args()

    buckets, trackb = build_plan(args)
    total = sum(b[-1] for b in buckets)
    print(f"Plan: {len(buckets)} buckets, target ≈ {total} rows "
          f"(mode={'trackb' if trackb else 'bucket_plan'}, scale={args.scale}, max_total={args.max_total or '-'})")
    if args.plan_only:
        for b in buckets:
            print("  ", b)
        print(f"SUMMARY plan-only: buckets={len(buckets)} target={total}")
        return 0

    client = cfg.require_openai_client()
    system_text = cfg.load_prompt("domain_system", cfg.DOMAIN_SYSTEM, args.prompt_dir)

    leak = simindex.build_leak_index(
        list(cfg.EVAL_SETS_FOR_LEAKAGE) + list(args.extra_leakage),
        train_paths=[args.train] if cfg.repo_path(args.train).exists() else [])
    print(f"Leakage index: {len(leak)} reference queries (threshold {args.sim_threshold})")
    seen = simindex.SimIndex()

    out = []
    out_lock = threading.Lock()
    out_path = cfg.repo_path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def gen_bucket(bi, bucket):
        if trackb:
            target_tool, cat, role, target = bucket
        else:
            target_tool, (cat, role, target) = None, bucket
        hint = category_hint(cat, args.prompt_dir)
        brng = random.Random(args.seed + bi)
        got = tries = 0
        while got < target and tries < target // args.batch + 6:
            tries += 1
            param_hints = None
            if target_tool:
                param_hints = [cfg.sample_param_hint(target_tool, brng) for _ in range(args.batch)]
            try:
                cands = gen_batch(client, system_text, cat, hint, role, min(args.batch, max(4, target - got)),
                                  args.model, param_hints=param_hints)
            except Exception as exc:  # noqa: BLE001
                print(f"  {cat}/{role} batch error: {exc}")
                time.sleep(1)
                continue
            for q in cands:
                if got >= target:
                    break
                if leak.max_sim(q) < args.sim_threshold and seen.check_and_add(q, args.intra_threshold):
                    rec = {"id": f"SC{bi:03d}{got:04d}", "category": cat, "user_role": role, "input": q}
                    if target_tool:
                        rec["seed_tool"] = target_tool  # hint only; the labeler decides independently
                    with out_lock:
                        out.append(rec)
                    got += 1
        return bi, f"{target_tool or cat}/{role}", got, target

    done = 0
    with ThreadPoolExecutor(max_workers=args.gen_workers) as ex:
        futs = {ex.submit(gen_bucket, bi, b): bi for bi, b in enumerate(buckets)}
        for fut in as_completed(futs):
            bi, label, got, target = fut.result()
            done += 1
            print(f"  [{done}/{len(buckets)}] {label}: {got}/{target}", flush=True)
            with out_lock:  # atomic checkpoint after each bucket
                tmp = out_path.with_suffix(out_path.suffix + ".tmp")
                tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
                tmp.replace(out_path)

    out.sort(key=lambda r: r["id"])
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("by category:", dict(Counter(c["category"] for c in out)))
    print(f"SUMMARY generate: rows={len(out)} target={total} fill={len(out) / max(total, 1):.0%} "
          f"-> {out_path} | {cfg.METER.summary()}")
    return 0 if out else 1


if __name__ == "__main__":
    raise SystemExit(main())
