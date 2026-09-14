#!/usr/bin/env python3
"""Stage 2b (optional): a STRONG arbiter corrects + polishes each labeled sample, replacing noisy
consensus labels (POC v1: the two labeler models agreed on only 62% of rows).

Per case the arbiter sees: the query, the user role, the full tool catalogue, and the current
label. It returns the corrected expected_tool (+alternates), params, and a lightly polished query
(grammar/clarity only — intent, asset names/codes and register are kept). PERMISSION is then
recomputed by RULE (tool_policy.json) — never model-judged — and params are schema-filtered.
Output is a new file so the input is untouched.

For eval_v1 augmentation the arbiter model MUST differ from the GPT under test (contract 2).

Resilient: checkpoints to <output>.partial every 20 cases; rerun resumes from there.

Usage (LLM stage — runs on the reference infrastructure, needs OPENAI_API_KEY):
  OPENAI_API_KEY=... python3 datagen/polish_scenarios.py --input data/sgod/labeled.json \
      --output data/sgod/labeled.polished.json   # --model defaults to config_sgod.ARBITER_MODEL
"""
import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_sgod as cfg  # noqa: E402
import audit_test_cases as audit  # noqa: E402

ARB_SYS_DEFAULT = """Bạn là chuyên gia gán nhãn cao cấp cho bộ dữ liệu kiểm thử của một chatbot quản lý tài sản tiếng Việt (nền tảng SGOD).
Với MỖI mẫu, bạn nhận: câu truy vấn, vai trò người dùng, DANH MỤC CÔNG CỤ thật, và nhãn hiện tại (có thể sai).
Nhiệm vụ:
1. Chọn expected_tool ĐÚNG NHẤT về mặt ý định (BỎ QUA quyền hạn — quyền sẽ do hệ thống tính bằng luật). Nếu
   truy vấn không cần công cụ (lạc đề/mơ hồ/chỉ trò chuyện/hỏi cách làm), trả tool=null. Chỉ MỘT công cụ.
2. Nếu có nhiều công cụ hợp lý ngang nhau, liệt kê chúng trong "alternates".
3. params: chỉ các tham số rõ ràng từ câu (đúng tên tham số theo schema công cụ). KHÔNG bịa mã doanh nghiệp.
4. polished_query: bản sửa nhẹ của câu (sửa lỗi chính tả/ngữ pháp, giữ NGUYÊN ý định, mã/tên tài sản, tên riêng,
   văn phong). Nếu câu đã ổn, trả lại y nguyên.
Chỉ trả JSON: {"tool": <str|null>, "alternates": [<str>...], "params": {...}, "polished_query": <str>}."""


def arbiter(client, model, catalogue, tc, system_text=None):
    up = (f"DANH MỤC CÔNG CỤ:\n{catalogue}\n\n"
          f"Vai trò: {tc['user_role']}\n"
          f"Câu truy vấn: {tc['input']!r}\n"
          f"Nhãn hiện tại: tool={tc.get('expected_tool')!r}, params={tc.get('expected_params')!r}, "
          f"alternates={tc.get('expected_tool_alternates')!r}\n\n"
          f"Sửa và đánh bóng. Trả JSON thuần.")
    r = client.chat.completions.create(
        model=model, max_completion_tokens=1500, temperature=0.0,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system_text or ARB_SYS_DEFAULT}, {"role": "user", "content": up}])
    cfg.METER.add(r)
    return json.loads(r.choices[0].message.content or "{}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", default=f"{cfg.DATA_DIR}/labeled.json")
    p.add_argument("--output", default=f"{cfg.DATA_DIR}/labeled.polished.json")
    p.add_argument("--report", default=f"{cfg.DATA_DIR}/polish_report.json")
    p.add_argument("--model", default=cfg.ARBITER_MODEL)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--prompt-dir", default=cfg.PROMPT_DIR, help="optional arbiter_system.md override")
    audit.add_catalogue_args(p)
    args = p.parse_args()

    client = cfg.require_openai_client()
    system_text = cfg.load_prompt("arbiter_system", ARB_SYS_DEFAULT, args.prompt_dir)
    tools, perms = audit.load_catalogue(args)
    valid = set(tools)
    catalogue = audit.build_tool_catalogue(tools)
    cases = json.loads(cfg.repo_path(args.input).read_text(encoding="utf-8"))
    if args.limit:
        cases = cases[:args.limit]

    out_path = cfg.repo_path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    partial = out_path.with_suffix(out_path.suffix + ".partial")
    done = {}
    if partial.exists():
        done = {c["id"]: c for c in json.loads(partial.read_text(encoding="utf-8"))}
        print(f"Resuming: {len(done)} already polished")

    out, report = [], []
    changed_tool = polished_q = errors = 0
    for i, tc in enumerate(cases):
        if tc["id"] in done:
            out.append(done[tc["id"]])
            continue
        try:
            a = arbiter(client, args.model, catalogue, tc, system_text)
        except Exception as exc:  # noqa: BLE001
            errors += 1
            cfg.METER.errors += 1
            print(f"  [{tc['id']}] ERR {str(exc)[:80]} — keeping old label")
            out.append(tc)
            time.sleep(1)
            continue

        tool = a.get("tool")
        tool = tool if tool in valid else None
        alts = [t for t in (a.get("alternates") or []) if t in valid and t != tool]
        params = a.get("params") or {}
        pq = (a.get("polished_query") or tc["input"]).strip() or tc["input"]

        permission, expected_tool = "allowed", tool   # permission by RULE, not arbiter
        if tool and not audit.role_allows(tc["user_role"], tool, perms):
            permission, expected_tool, alts = "denied", None, []
        params = audit.fix_params_for_tool(expected_tool, params, tools)[0] if expected_tool else {}

        new = {"id": tc["id"], "category": tc.get("category", ""), "user_role": tc["user_role"],
               "input": pq, "expected_tool": expected_tool,
               "expected_params": params, "expected_permission": permission}
        if alts and expected_tool:
            new["expected_tool_alternates"] = sorted(set(alts))
        for k in ("source", "_seed_tool"):
            if k in tc:
                new[k] = tc[k]
        out.append(new)
        changed_tool += (new["expected_tool"] or None) != (tc.get("expected_tool") or None)
        polished_q += pq != tc["input"]
        report.append({"id": tc["id"], "old_tool": tc.get("expected_tool"), "new_tool": expected_tool,
                       "polished": pq != tc["input"]})
        if (i + 1) % 20 == 0:
            partial.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
            print(f"  {i + 1}/{len(cases)} | tool_changed={changed_tool} polished={polished_q}")

    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    cfg.repo_path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if partial.exists():
        partial.unlink()
    print("new tool dist (top):", dict(Counter(c.get("expected_tool") for c in out).most_common(10)))
    print(f"SUMMARY polish: cases={len(out)} tool_changed={changed_tool} polished={polished_q} "
          f"errors={errors} -> {out_path} | {cfg.METER.summary()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
