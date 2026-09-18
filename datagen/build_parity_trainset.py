#!/usr/bin/env python3
"""Build TRAIN/SERVE-PARITY training rows (docs/contracts/training_row_format.md) from labeled cases.

Training prompts must be identical to serving:
  - system  = prompts/system_preamble_v1.txt with {role_vi}/{full_name}/{user_id} (+ optional {role})
    filled from GENERIC_CONTEXT / role_names_vi for the row's role — NO tools embedded
    (finetune_qlora.py renders them via tokenizer.apply_chat_template(tools=...), exactly like
    vLLM at serve time). That is why each row carries "role".
  - user    = the case input.
  - assistant = <tool_call>{"name":..,"arguments":{..}}</tool_call>  for a tool label,
                REFUSAL_VI for expected_permission == "denied",
                DEFLECT_VI for expected_tool == null (out-of-scope / chitchat / ambiguous).
    Fixed replies come from prompts/fixed_replies.json.

Row: {"id": <case id>, "role": <chat role>, "messages": [system, user, assistant]}. Roles are mapped
through config_sgod.ROLE_MAP ("admin" -> "company_admin") so "role" is always in the roles.json vocabulary.

Usage:
  python3 datagen/build_parity_trainset.py --sources data/sgod/verified.json --out-dir data/sgod
  python3 datagen/build_parity_trainset.py --sources data/sgod/verified.json --out-dir data/sgod \
      --train-name pilot_train.jsonl --val-ratio 0            # pilot: one file, no split
Machine gate afterwards: python training/validate_dataset.py data/sgod/train.jsonl --preamble prompts/system_preamble_v1.txt
"""
import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_sgod as cfg  # noqa: E402


PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")
KNOWN_SLOTS = {"role", "role_vi", "full_name", "user_id"}


class Preamble:
    """Renders the serve preamble for a role from the v1 template.

    Slots filled (str.replace, so JSON braces elsewhere in the template are safe):
      {role}      -> chat role key (employee / company_admin)
      {role_vi}   -> config_sgod.ROLE_NAMES_VI[role]  (from roles.json "role_names_vi")
      {full_name} -> config_sgod.GENERIC_CONTEXT["full_name"]   (same values as tools/sgod/validate_tools.py)
      {user_id}   -> config_sgod.GENERIC_CONTEXT["user_id"]
    keep_placeholders=True emits the template verbatim (no slot filled) — only for tooling that
    compares the system turn literally against the template file.
    """

    def __init__(self, template_path=None, fixed_replies_path=None, keep_placeholders=False):
        tp = cfg.repo_path(template_path or cfg.PREAMBLE_V1_PATH)
        if not tp.exists():
            raise FileNotFoundError(f"preamble template not found: {tp} (owner: S Việc 3, due 09-27)")
        self.template = tp.read_text(encoding="utf-8").strip()
        self.keep_placeholders = keep_placeholders
        fp = cfg.repo_path(fixed_replies_path or cfg.FIXED_REPLIES_PATH)
        if not fp.exists():
            raise FileNotFoundError(f"fixed replies not found: {fp}")
        replies = json.loads(fp.read_text(encoding="utf-8"))
        self.refusal = replies["REFUSAL_VI"]
        self.deflect = replies["DEFLECT_VI"]
        self._cache = {}
        unknown = set(PLACEHOLDER_RE.findall(self.template)) - KNOWN_SLOTS
        if unknown:
            print(f"WARNING: preamble has unknown placeholders {sorted(unknown)} — they stay literal "
                  f"(known: {sorted(KNOWN_SLOTS)})", file=sys.stderr)

    def chat_role(self, case_role):
        return cfg.ROLE_MAP.get(case_role, case_role)

    def render(self, case_role):
        role_key = self.chat_role(case_role)
        if role_key not in self._cache:
            txt = self.template
            if not self.keep_placeholders:
                txt = txt.replace("{role}", role_key)
                txt = txt.replace("{role_vi}", cfg.ROLE_NAMES_VI.get(role_key, role_key))
                for slot, val in cfg.GENERIC_CONTEXT.items():
                    txt = txt.replace("{" + slot + "}", val)
            self._cache[role_key] = txt.strip()
        return self._cache[role_key]

    def assistant_for(self, tc):
        tool = tc.get("expected_tool")
        if tc.get("expected_permission") == "denied" or (tool is None and tc.get("category") == "permission_denial"):
            return self.refusal
        if tool is None:
            return self.deflect
        call = {"name": tool, "arguments": tc.get("expected_params") or {}}
        return "<tool_call>" + json.dumps(call, ensure_ascii=False) + "</tool_call>"

    def row(self, tc, stream=None):
        role = tc.get("user_role", "employee")
        r = {"id": str(tc.get("id")), "role": self.chat_role(role), "messages": [
            {"role": "system", "content": self.render(role)},
            {"role": "user", "content": tc["input"]},
            {"role": "assistant", "content": self.assistant_for(tc)},
        ]}
        if stream:
            r["stream"] = stream
        return r

    def target_kind(self, row):
        c = row["messages"][-1]["content"]
        if "<tool_call>" in c:
            return "tool"
        return "refusal" if c == self.refusal else "deflect"


def load_cases(path):
    data = json.loads(cfg.repo_path(path).read_text(encoding="utf-8"))
    return [tc for tc in data if tc.get("input")]


def write_jsonl(path, rows):
    path = cfg.repo_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({k: v for k, v in r.items() if k != "stream"}, ensure_ascii=False) + "\n")
    return path


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sources", nargs="+", default=[f"{cfg.DATA_DIR}/verified.json"],
                   help="labeled/verified case files (JSON lists)")
    p.add_argument("--out-dir", default=cfg.DATA_DIR)
    p.add_argument("--train-name", default="train.jsonl")
    p.add_argument("--val-name", default="val.jsonl")
    p.add_argument("--val-ratio", type=float, default=0.1, help="0 -> no val file")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--preamble", default=cfg.PREAMBLE_V1_PATH)
    p.add_argument("--fixed-replies", default=cfg.FIXED_REPLIES_PATH)
    p.add_argument("--skip-needs-review", action="store_true", help="drop rows flagged _needs_review")
    p.add_argument("--keep-placeholders", action="store_true",
                   help="emit the preamble template verbatim ({role_vi}/{full_name}/{user_id} NOT filled)")
    args = p.parse_args()

    pre = Preamble(args.preamble, args.fixed_replies, keep_placeholders=args.keep_placeholders)
    rows, seen_ids, dup = [], set(), 0
    for s in args.sources:
        for tc in load_cases(s):
            if args.skip_needs_review and tc.get("_needs_review"):
                continue
            rid = str(tc.get("id"))
            if rid in seen_ids:
                dup += 1
                continue
            seen_ids.add(rid)
            rows.append(pre.row(tc))
    if not rows:
        print("SUMMARY build_parity: no rows built (empty sources?)")
        return 1
    random.Random(args.seed).shuffle(rows)
    nval = int(len(rows) * args.val_ratio) if args.val_ratio > 0 else 0
    val, train = rows[:nval], rows[nval:]
    train_path = write_jsonl(Path(args.out_dir) / args.train_name, train)
    val_path = write_jsonl(Path(args.out_dir) / args.val_name, val) if nval else None
    print("targets:", dict(Counter(pre.target_kind(r) for r in rows)))
    print("roles:", dict(Counter(r["role"] for r in rows)))
    if dup:
        print(f"skipped {dup} duplicate ids")
    print(f"SUMMARY build_parity: train={len(train)} val={len(val)} seed={args.seed} "
          f"preamble={cfg.repo_path(args.preamble)} -> {train_path}" + (f", {val_path}" if val_path else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
