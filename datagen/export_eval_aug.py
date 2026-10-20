#!/usr/bin/env python3
"""Eval augmentation, last step (D Việc 4): labeled/polished eval-aug cases -> eval records of contract 2.

`run_pipeline.sh --eval-aug` generates queries with datagen/prompts_eval/ (BUCKET_PLAN), labels them with
LABEL_MODELS and lets ARBITER_MODEL (≠ the GPT under test) fix labels + alternates. This step turns those
cases into records shaped like data/sgod/eval_human_core.jsonl (docs/contracts/eval_metric.md §1):
  - user_role in the chat-role vocabulary (ROLE_MAP: "admin" -> "company_admin");
  - source = "gpt_aug"; expected_tool_alternates is always a list;
  - denied rows keep the BLOCKED tool as expected_tool (contract 3 §6, like the human core) — the labeler
    stored it in `_blocked_tool` because the training format needs null there;
  - category by the rule used for the human core: null -> out_of_scope, denied -> permission_denial,
    ≥ 2 expected_params keys -> multi_constraint, else single_tool (generation category kept in _gen_category);
  - the offline gates of verify_trainset (stage A/B) run on every row; findings go to `_issues`.
No row is dropped and no id is renumbered: the Data team reviews (`_needs_review`, `_issues`), assigns the
sgod-XXXX ids and strips the `_` keys when building eval_v1.json.

Usage:
  python3 datagen/export_eval_aug.py --input data/sgod/eval_aug_polished.json --output data/sgod/eval_aug.json
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_sgod as cfg  # noqa: E402
import audit_test_cases as audit  # noqa: E402
import verify_trainset as vt  # noqa: E402

KEEP_PRIVATE = ("_needs_review", "_seed_tool")


def category_for(rec):
    if rec["expected_permission"] == "denied":
        return "permission_denial"
    if rec["expected_tool"] is None:
        return "out_of_scope"
    return "multi_constraint" if len(rec["expected_params"]) >= 2 else "single_tool"


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", default=f"{cfg.DATA_DIR}/eval_aug_polished.json",
                   help="eval_aug_polished.json (or eval_aug_labeled.json when polish was skipped)")
    p.add_argument("--output", default=f"{cfg.DATA_DIR}/eval_aug.json")
    audit.add_catalogue_args(p)
    args = p.parse_args()

    tools, perms = audit.load_catalogue(args)
    meta = audit.load_tool_meta(args.tools)
    valid = set(tools)
    cases = json.loads(cfg.repo_path(args.input).read_text(encoding="utf-8"))
    out = []
    for tc in cases:
        issues = vt.stage_a_format(tc, valid, perms) or vt.stage_b_schema(tc, tools, perms, meta)
        role = tc.get("user_role", "employee")
        rec = {"id": str(tc.get("id")), "category": "", "user_role": cfg.ROLE_MAP.get(role, role),
               "input": tc.get("input", ""), "expected_tool": tc.get("expected_tool"),
               "expected_params": tc.get("expected_params") or {},
               "expected_permission": tc.get("expected_permission", "allowed"),
               "expected_tool_alternates": sorted(tc.get("expected_tool_alternates") or []),
               "source": "gpt_aug"}
        if rec["expected_permission"] == "denied":
            if tc.get("_blocked_tool"):
                rec["expected_tool"], rec["expected_params"] = tc["_blocked_tool"], {}
            else:
                issues = list(issues) + ["denied without _blocked_tool: expected_tool must name the blocked tool"]
        rec["category"] = category_for(rec)
        if tc.get("category"):
            rec["_gen_category"] = tc["category"]
        for k in KEEP_PRIVATE:
            if k in tc:
                rec[k] = tc[k]
        if issues:
            rec["_issues"] = issues
        out.append(rec)

    out_path = cfg.repo_path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    n = len(out) or 1
    n_null = sum(1 for r in out if r["expected_tool"] is None)
    n_denied = sum(1 for r in out if r["expected_permission"] == "denied")
    print("by tool:", dict(Counter(r["expected_tool"] for r in out).most_common()))
    print("by user_role:", dict(Counter(r["user_role"] for r in out)))
    print("by category:", dict(Counter(r["category"] for r in out)))
    print(f"SUMMARY export_eval_aug: rows={len(out)} null={n_null} ({n_null / n:.0%}) denied={n_denied} "
          f"({n_denied / n:.0%}) needs_review={sum(1 for r in out if r.get('_needs_review'))} "
          f"issues={sum(1 for r in out if r.get('_issues'))} -> {out_path}")
    return 0 if out else 1


if __name__ == "__main__":
    raise SystemExit(main())
