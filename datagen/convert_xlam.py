#!/usr/bin/env python3
"""Convert raw xLAM-style rows into ChatSystem parity training rows + a public eval file.

Stdlib only; runs on CPU in seconds. This is the reference implementation of
docs/contracts/training_row_format.md for PUBLIC (replay) rows.

Input  (--in):  JSONL, one row per line: {"id", "query", "tools", "answers"}
                tools   = xLAM shape [{name, description, parameters: {param: {type, description, default?}}}]
                          (OpenAI function shape is also accepted)
                answers = [{name, arguments}]  (gold call(s); strings are accepted and parsed)
Output (--out-prefix P):
    P.train.jsonl / P.val.jsonl / P.test.jsonl   parity rows
        {"id": "pub-xxxxxxxx", "role": "employee", "replay": true,
         "replay_tools": [ {type:function, function:{name, description, parameters}} ],
         "messages": [ {system: <preamble v0>}, {user: query}, {assistant: "<tool_call>{...}</tool_call>"} ]}
    P.eval.json                                    eval records (docs/contracts/eval_metric.md) built from the TEST split,
                                                   each carrying its own `tools` list because public tools are per-row.

Splitting: rows are grouped by their sorted tool-name set; whole groups go to one split, so no
tool-set is shared across train/val/test (leakage control). Deterministic for a given --seed.

Example:
  python datagen/convert_xlam.py --in data/public/xlam_raw_2k.jsonl --out-prefix data/public/xlam_2k \
      --system-file prompts/system_preamble_v0.txt --seed 20260913
"""
import argparse, hashlib, json, random
from collections import defaultdict


def as_obj(x):
    return json.loads(x) if isinstance(x, str) else x


def to_openai_tool(t):
    fn = t.get("function", t)
    params = fn.get("parameters") or {}
    if "type" not in params or "properties" not in params:
        props = params
        required = [p for p, spec in props.items() if isinstance(spec, dict) and "default" not in spec]
        params = {"type": "object", "properties": props, "required": required}
    return {"type": "function", "function": {"name": fn["name"], "description": fn.get("description", ""), "parameters": params}}


def tool_call_text(answers):
    return "".join(
        "<tool_call>" + json.dumps({"name": a["name"], "arguments": a.get("arguments", {})}, ensure_ascii=False) + "</tool_call>"
        for a in answers
    )


def sha256_ids(rows):
    return hashlib.sha256("\n".join(r["id"] for r in rows).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out-prefix", required=True)
    ap.add_argument("--system-file", default="prompts/system_preamble_v0.txt")
    ap.add_argument("--seed", type=int, default=20260913)
    ap.add_argument("--ratios", default="0.8,0.1,0.1")
    ap.add_argument("--min-tools", type=int, default=1)
    ap.add_argument("--max-tools", type=int, default=4)
    ap.add_argument("--max-calls", type=int, default=1)
    ap.add_argument("--role", default="employee")
    a = ap.parse_args()

    with open(a.system_file, encoding="utf-8") as f:
        preamble = f.read().strip()

    rows = []
    with open(a.inp, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            tools = [to_openai_tool(t) for t in (as_obj(r.get("tools")) or [])]
            answers = [x for x in (as_obj(r.get("answers")) or []) if x.get("name")]
            if not r.get("query") or not (a.min_tools <= len(tools) <= a.max_tools) or len(answers) != a.max_calls:
                continue
            names = {t["function"]["name"] for t in tools}
            if any(x["name"] not in names for x in answers):
                continue
            rid = r.get("id") or "xlam-" + hashlib.sha1(r["query"].encode("utf-8")).hexdigest()[:8]
            rows.append({
                "id": "pub-" + rid.split("-", 1)[-1],
                "role": a.role,
                "replay": True,
                "replay_tools": tools,
                "messages": [
                    {"role": "system", "content": preamble},
                    {"role": "user", "content": r["query"]},
                    {"role": "assistant", "content": tool_call_text(answers)},
                ],
                "_gold": answers,
            })

    groups = defaultdict(list)
    for r in rows:
        groups[tuple(sorted(t["function"]["name"] for t in r["replay_tools"]))].append(r)
    keys = sorted(groups)
    random.Random(a.seed).shuffle(keys)
    ratios = [float(x) for x in a.ratios.split(",")]
    names = ["train", "val", "test"]
    targets = [len(rows) * x for x in ratios]
    splits = {n: [] for n in names}
    for k in keys:
        fill = [len(splits[n]) / max(targets[i], 1e-9) for i, n in enumerate(names)]
        splits[names[fill.index(min(fill))]].extend(groups[k])

    for n in names:
        splits[n].sort(key=lambda r: r["id"])
        with open(f"{a.out_prefix}.{n}.jsonl", "w", encoding="utf-8") as f:
            for r in splits[n]:
                f.write(json.dumps({k: v for k, v in r.items() if k != "_gold"}, ensure_ascii=False) + "\n")

    eval_records = []
    for r in splits["test"]:
        g = r["_gold"][0]
        eval_records.append({
            "id": r["id"], "category": "public", "user_role": a.role, "source": "public",
            "input": r["messages"][1]["content"],
            "expected_tool": g["name"], "expected_params": g.get("arguments", {}),
            "expected_permission": "allowed", "expected_tool_alternates": [],
            "tools": r["replay_tools"],
        })
    with open(f"{a.out_prefix}.eval.json", "w", encoding="utf-8") as f:
        json.dump(eval_records, f, ensure_ascii=False, indent=1)

    shared = set()
    for i, n1 in enumerate(names):
        s1 = {tuple(sorted(t["function"]["name"] for t in r["replay_tools"])) for r in splits[n1]}
        for n2 in names[i + 1:]:
            s2 = {tuple(sorted(t["function"]["name"] for t in r["replay_tools"])) for r in splits[n2]}
            shared |= s1 & s2
    print(f"rows={len(rows)} tool_sets={len(groups)} seed={a.seed} preamble_sha256={hashlib.sha256(preamble.encode()).hexdigest()[:16]}")
    for n in names:
        print(f"  {n}: {len(splits[n])} rows, ids_sha256={sha256_ids(splits[n])[:16]}")
    print(f"  tool-sets shared across splits: {len(shared)}")
    print(f"  eval records: {len(eval_records)} -> {a.out_prefix}.eval.json")


if __name__ == "__main__":
    main()
