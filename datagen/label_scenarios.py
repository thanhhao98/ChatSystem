#!/usr/bin/env python3
"""Stage 2: assign labels to net-new queries (from generate_scenarios.py) by multi-LLM consensus
on the tool + RULE-based permission + schema param filtering.

Per query:
  - Ask >= 2 models INDEPENDENTLY (full tool catalogue + role) for the single tool that best
    fulfils the request (ignoring permissions) + its params.
  - Consensus: agree -> that tool; disagree -> primary model's tool + alternates, flagged _needs_review.
  - PERMISSION is rule-based via tool_policy.json (audit_test_cases.role_allows): tool not allowed
    for the role -> expected_tool=null, expected_permission="denied". Never model-judged.
  - Params schema-filtered to the tool's properties (dropped keys are logged, not silent).

Output: --output (labeled cases, ids SC... -> SN...) + --report (proposals/agreement per row).

Usage (LLM stage — runs on the reference infrastructure, needs OPENAI_API_KEY):
  OPENAI_API_KEY=... python3 datagen/label_scenarios.py --input data/sgod/raw.json \
      --output data/sgod/labeled.json        # --models defaults to config_sgod.LABEL_MODELS
"""
import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_sgod as cfg  # noqa: E402
import audit_test_cases as audit  # noqa: E402  (load_catalogue, build_tool_catalogue, role_allows, fix_params_for_tool)

LABEL_SYS_DEFAULT = """Bạn gán nhãn cho dữ liệu kiểm thử của một chatbot quản lý tài sản tiếng Việt (nền tảng SGOD).
Cho một câu truy vấn và DANH MỤC CÔNG CỤ, hãy chọn DUY NHẤT một công cụ phù hợp nhất để thực hiện yêu cầu
(BỎ QUA quyền hạn — cứ chọn công cụ đúng về mặt ý định). Nếu truy vấn KHÔNG cần công cụ nào (lạc đề / mơ hồ /
chỉ trò chuyện / hỏi cách làm), trả tool = null. Chỉ một công cụ, không chuỗi nhiều bước.
Trả về JSON thuần: {"tool": "<tên công cụ hoặc null>", "params": {<tham số nếu rõ, đúng tên theo schema>}}. KHÔNG giải thích."""


def review(client, catalogue, q, role, model, system_text=None):
    """One model's proposal for (tool, params). Raises on transport errors."""
    up = f"DANH MỤC CÔNG CỤ:\n{catalogue}\n\nVai trò: {role}\nTruy vấn: {q!r}\nChọn công cụ + tham số. JSON thuần."
    r = client.chat.completions.create(
        model=model, temperature=0.0, max_tokens=300,
        messages=[{"role": "system", "content": system_text or LABEL_SYS_DEFAULT},
                  {"role": "user", "content": up}])
    cfg.METER.add(r)
    t = (r.choices[0].message.content or "").strip()
    t = t[t.find("{"): t.rfind("}") + 1] if "{" in t else "{}"
    try:
        d = json.loads(t)
        return d.get("tool"), (d.get("params") or {})
    except json.JSONDecodeError:
        return None, {}


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", default=f"{cfg.DATA_DIR}/raw.json")
    p.add_argument("--output", default=f"{cfg.DATA_DIR}/labeled.json")
    p.add_argument("--report", default=f"{cfg.DATA_DIR}/label_report.json")
    p.add_argument("--models", nargs="+", default=list(cfg.LABEL_MODELS),
                   help="first model is the primary vote on disagreement")
    p.add_argument("--workers", type=int, default=16, help="concurrent queries (I/O-bound)")
    p.add_argument("--limit", type=int, default=0, help="label only the first N rows")
    p.add_argument("--prompt-dir", default=cfg.PROMPT_DIR, help="optional label_system.md override")
    audit.add_catalogue_args(p)
    args = p.parse_args()

    client = cfg.require_openai_client()
    system_text = cfg.load_prompt("label_system", LABEL_SYS_DEFAULT, args.prompt_dir)
    tools, perms = audit.load_catalogue(args)
    valid = set(tools)
    catalogue = audit.build_tool_catalogue(tools)
    queries = json.loads(cfg.repo_path(args.input).read_text(encoding="utf-8"))
    if args.limit:
        queries = queries[:args.limit]
    print(f"Labelling {len(queries)} queries with {args.models} against {len(valid)} tools")

    def process_one(qc):
        q, role = qc["input"], qc.get("user_role", "employee")
        proposals = []
        for m in args.models:
            try:
                tool, params = review(client, catalogue, q, role, m, system_text)
            except Exception as exc:  # noqa: BLE001
                cfg.METER.errors += 1
                return None, {"id": qc["id"], "error": str(exc)}
            proposals.append((m, tool, params))
        norm = [t if t in valid else None for _, t, _ in proposals]
        if not norm:
            return None, {"id": qc["id"], "error": "no proposals"}
        agree = len(set(norm)) == 1
        primary = norm[0] if norm[0] is not None else next((t for t in norm if t), None)
        alternates = sorted({t for t in norm if t and t != primary})

        permission, expected_tool = "allowed", primary
        if primary and not audit.role_allows(role, primary, perms):
            permission, expected_tool = "denied", None
        params = next((pp for _, t, pp in proposals if t == primary), {})
        dropped = []
        if expected_tool:
            params, dropped = audit.fix_params_for_tool(expected_tool, params, tools)

        tc = {"id": qc["id"].replace("SC", "SN", 1), "category": qc.get("category", ""),
              "user_role": role, "input": q,
              "expected_tool": expected_tool, "expected_params": params if expected_tool else {},
              "expected_permission": permission}
        if qc.get("seed_tool"):
            tc["_seed_tool"] = qc["seed_tool"]
        if alternates and expected_tool:
            tc["expected_tool_alternates"] = alternates
        if not agree:
            tc["_needs_review"] = True
        rep = {"id": tc["id"], "proposals": [(m, t) for m, t, _ in proposals], "agree": agree,
               "expected_tool": expected_tool, "permission": permission, "dropped_params": dropped}
        return tc, rep

    out, report = [], []
    out_path = cfg.repo_path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_one, qc): qc for qc in queries}
        for fut in as_completed(futs):
            tc, rep = fut.result()
            report.append(rep)
            if tc is not None:
                out.append(tc)
            done += 1
            if done % 200 == 0:
                nr = sum(1 for t in out if t.get("_needs_review"))
                print(f"  {done}/{len(queries)} | kept={len(out)} review={nr}", flush=True)
                out_path.write_text(json.dumps(sorted(out, key=lambda t: t["id"]), ensure_ascii=False, indent=2),
                                    encoding="utf-8")

    out.sort(key=lambda t: t["id"])
    report.sort(key=lambda r: r.get("id", ""))
    n_review = sum(1 for t in out if t.get("_needs_review"))
    n_denied = sum(1 for t in out if t["expected_permission"] == "denied")
    n_none = sum(1 for t in out if t["expected_tool"] is None and t["expected_permission"] == "allowed")
    n_err = sum(1 for r in report if "error" in r)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    cfg.repo_path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("by category:", dict(Counter(c["category"] for c in out)))
    print("by expected_tool (top):", dict(Counter(c["expected_tool"] for c in out).most_common(12)))
    drop_by_tool = Counter(f"{r.get('expected_tool')}.{k}" for r in report for k in r.get("dropped_params", []))
    if drop_by_tool:
        print(f"DROPPED params (not in schema) — {sum(drop_by_tool.values())} total:",
              dict(drop_by_tool.most_common(15)))
    agree_rate = (len(out) - n_review) / max(len(out), 1)
    print(f"SUMMARY label: labeled={len(out)} needs_review={n_review} agree_rate={agree_rate:.0%} "
          f"denied={n_denied} no_tool={n_none} errors={n_err} -> {out_path} | {cfg.METER.summary()}")
    return 0 if out else 1


if __name__ == "__main__":
    raise SystemExit(main())
