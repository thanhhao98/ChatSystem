#!/usr/bin/env python3
"""Recover a raw xLAM-style slice {id, query, tools, answers} from the POC v1 replay JSONL.

One-off, run on the reference infrastructure (output committed as data/public/xlam_raw_2k.jsonl).
The POC v1 replay file holds 6,500 rows of Salesforce/xlam-function-calling-60k already normalised
to the parity row format (tools in `replay_tools`, gold call(s) as <tool_call> tags). This script
inverts that so the interns get a dataset that looks like the public source, without the gated
Hugging Face download.

Filters: exactly --max-calls gold calls, --min-tools..--max-tools tools, gold tool present in the
row's tools, unique query. Sampling: proportional per #tools stratum, seeded.

Usage:
  python scripts/recover_xlam_raw.py --in <poc_v1>/replay.jsonl \
      --out data/public/xlam_raw_2k.jsonl --n 2000 --seed 20260913
"""
import argparse, hashlib, json, random, re
from collections import defaultdict

TAG = re.compile(r"<tool_call>(.*?)</tool_call>", re.S)


def raw_tools(replay_tools):
    out = []
    for t in replay_tools:
        fn = t.get("function", t)
        params = (fn.get("parameters") or {}).get("properties") or {}
        out.append({"name": fn["name"], "description": fn.get("description", ""), "parameters": params})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260913)
    ap.add_argument("--min-tools", type=int, default=1)
    ap.add_argument("--max-tools", type=int, default=4)
    ap.add_argument("--max-calls", type=int, default=1)
    a = ap.parse_args()

    seen, by_stratum, total_in = set(), defaultdict(list), 0
    with open(a.inp, encoding="utf-8") as f:
        for line in f:
            total_in += 1
            r = json.loads(line)
            msgs = {m["role"]: m["content"] for m in r["messages"]}
            query = msgs.get("user", "").strip()
            answers = []
            for m in TAG.findall(msgs.get("assistant", "")):
                try:
                    c = json.loads(m)
                except json.JSONDecodeError:
                    answers = None
                    break
                answers.append({"name": c.get("name"), "arguments": c.get("arguments", {})})
            tools = raw_tools(r.get("replay_tools") or [])
            if not query or not answers or len(answers) != a.max_calls:
                continue
            if not (a.min_tools <= len(tools) <= a.max_tools):
                continue
            names = {t["name"] for t in tools}
            if any(x["name"] not in names for x in answers):
                continue
            if query in seen:
                continue
            seen.add(query)
            rid = "xlam-" + hashlib.sha1((query + json.dumps(answers, sort_keys=True, ensure_ascii=False)).encode("utf-8")).hexdigest()[:8]
            by_stratum[len(tools)].append({"id": rid, "query": query, "tools": tools, "answers": answers})

    eligible = sum(len(v) for v in by_stratum.values())
    rng = random.Random(a.seed)
    picked = []
    # proportional allocation, largest-remainder rounding
    quotas = {k: a.n * len(v) / eligible for k, v in by_stratum.items()}
    base = {k: int(q) for k, q in quotas.items()}
    rem = a.n - sum(base.values())
    for k in sorted(quotas, key=lambda k: quotas[k] - base[k], reverse=True)[:rem]:
        base[k] += 1
    for k in sorted(by_stratum):
        rows = sorted(by_stratum[k], key=lambda r: r["id"])
        rng.shuffle(rows)
        picked.extend(rows[: base[k]])
    picked.sort(key=lambda r: r["id"])
    with open(a.out, "w", encoding="utf-8") as f:
        for r in picked:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"rows_in={total_in} eligible={eligible} written={len(picked)} seed={a.seed}")
    print("per #tools:", {k: base[k] for k in sorted(base)})


if __name__ == "__main__":
    main()
