#!/usr/bin/env python3
"""Stage 7: pre-train ALIGNMENT AUDIT — assert the assembled parity rows match the CURRENT catalogue.

Labels are generated once; if sgod_tools.json / tool_policy.json change afterwards (git tag
`tools-v1` -> v1.1), the data drifts from the API. This audit re-reads every domain row of the
parity JSONL — the exact rows that train — inverts build_parity_trainset (tool_call / REFUSAL /
DEFLECT -> case) and re-runs the offline gates:
  - verify_trainset.stage_a_format : tool exists, permission consistent with tool_policy.json
  - verify_trainset.stage_b_schema : param keys ∈ schema, enum membership, required present
  - preamble check: messages[0].content == preamble(role) rendered from the CURRENT template
Replay rows (carry `replay_tools`, foreign catalogue) are skipped on purpose.

Exit 1 (block the fine-tune) if ANY row is misaligned. Writes <data-dir>/alignment_report.json.

Usage:
  python3 datagen/audit_trainset_vs_api.py --data-dir data/sgod            # train.jsonl + val.jsonl
  python3 datagen/audit_trainset_vs_api.py --data-dir data/sgod --files pilot_train.jsonl
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_sgod as cfg  # noqa: E402
import audit_test_cases as audit  # noqa: E402
import verify_trainset as vt  # noqa: E402
import build_parity_trainset as bp  # noqa: E402

_TOOLCALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


def row_to_case(row, idx, pre):
    """Invert Preamble.assistant_for(). None for replay rows."""
    if row.get("replay_tools") or row.get("replay"):
        return None
    msgs = row.get("messages", [])
    user = next((m.get("content", "") for m in msgs if m.get("role") == "user"), "")
    asst = (msgs[-1].get("content", "") if msgs else "") or ""
    tc = {"id": str(row.get("id", f"row{idx}")), "user_role": row.get("role", "employee"),
          "input": user, "category": ""}
    calls = _TOOLCALL_RE.findall(asst)
    if calls:
        if len(calls) != 1:
            tc.update(expected_tool="<multi-call>", expected_params={}, expected_permission="allowed")
            return tc
        try:
            call = json.loads(calls[0])
        except json.JSONDecodeError:
            tc.update(expected_tool="<unparseable>", expected_params={}, expected_permission="allowed")
            return tc
        tc.update(expected_tool=call.get("name"), expected_params=call.get("arguments") or {},
                  expected_permission="allowed")
    elif asst.strip() == pre.refusal:
        tc.update(expected_tool=None, expected_params={}, expected_permission="denied", category="permission_denial")
    elif asst.strip() == pre.deflect:
        tc.update(expected_tool=None, expected_params={}, expected_permission="allowed")
    else:
        tc.update(expected_tool="<free-text>", expected_params={}, expected_permission="allowed")
    return tc


def audit_file(path, tools, perms, meta, valid, pre):
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    bad, n_checked = [], 0
    for i, row in enumerate(rows):
        tc = row_to_case(row, i, pre)
        if tc is None:
            continue
        n_checked += 1
        issues = []
        msgs = row.get("messages", [])
        if len(msgs) != 3 or [m.get("role") for m in msgs] != ["system", "user", "assistant"]:
            issues.append("messages must be exactly [system, user, assistant]")
        elif msgs[0].get("content", "").strip() != pre.render(row.get("role", "employee")):
            issues.append("system turn != current preamble(role)")
        if row.get("role") not in cfg.CHAT_ROLES:
            issues.append(f"role {row.get('role')!r} not in roles vocabulary {cfg.CHAT_ROLES}")
        if tc["expected_tool"] in ("<multi-call>", "<unparseable>", "<free-text>"):
            issues.append(f"assistant target {tc['expected_tool']} (must be one tool_call, REFUSAL_VI or DEFLECT_VI)")
        if not issues:
            issues = vt.stage_a_format(tc, valid, perms)
        if not issues:
            issues = vt.stage_b_schema(tc, tools, perms, meta)
        if issues:
            bad.append({"id": tc["id"], "tool": tc.get("expected_tool"), "params": tc.get("expected_params"),
                        "role": tc.get("user_role"), "issues": issues, "input": tc.get("input", "")[:80]})
    return len(rows), n_checked, bad


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", default=cfg.DATA_DIR)
    p.add_argument("--files", nargs="*", default=["train.jsonl", "val.jsonl"])
    p.add_argument("--preamble", default=cfg.PREAMBLE_V1_PATH)
    p.add_argument("--fixed-replies", default=cfg.FIXED_REPLIES_PATH)
    p.add_argument("--report", default="alignment_report.json", help="written inside --data-dir")
    p.add_argument("--keep-placeholders", action="store_true",
                   help="rows were built with build_parity_trainset.py --keep-placeholders")
    audit.add_catalogue_args(p)
    args = p.parse_args()

    tools, perms = audit.load_catalogue(args)
    meta = audit.load_tool_meta(args.tools)
    valid = set(tools)
    pre = bp.Preamble(args.preamble, args.fixed_replies, keep_placeholders=args.keep_placeholders)
    print(f"Auditing against {len(valid)} tools from {cfg.repo_path(args.tools)}")

    all_bad, total, checked = [], 0, 0
    d = cfg.repo_path(args.data_dir)
    for name in args.files:
        f = d / name
        if not f.exists():
            print(f"  skip {name} (missing)")
            continue
        nrows, nchk, bad = audit_file(f, tools, perms, meta, valid, pre)
        total += nrows
        checked += nchk
        all_bad.extend(bad)
        print(f"  {name}: {nrows} rows, {nchk} domain rows checked, {len(bad)} misaligned")

    by_issue = Counter(iss.split(":")[0].split(" not in")[0][:48] for b in all_bad for iss in b["issues"])
    report = {"total_rows": total, "checked": checked, "misaligned": len(all_bad),
              "by_issue": dict(by_issue), "examples": all_bad[:50]}
    d.mkdir(parents=True, exist_ok=True)
    (d / args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if all_bad:
        for k, v in by_issue.most_common(8):
            print(f"  {v:4}  {k}")
        print(f"  report -> {d / args.report}")
        print(f"SUMMARY alignment FAIL: {checked - len(all_bad)}/{checked} rows OK, {len(all_bad)} misaligned "
              f"— fix data or catalogue before fine-tuning")
        return 1
    print(f"SUMMARY alignment OK: {checked}/{checked} domain rows align with the current catalogue "
          f"({total} rows incl. replay) -> {d / args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
