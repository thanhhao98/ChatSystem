#!/usr/bin/env python3
"""Offline scorer for single-shot tool-selection predictions (docs/contracts/eval_metric.md).

    python training/eval_toolcall.py --gold <eval.json> --pred <predictions.jsonl> --out <results.json>
        [--tools tools/sgod/sgod_tools.json] [--policy tools/sgod/tool_policy.json] [--preamble <file>]
        [--group-by source] [--no-header-check] [--md <results.md>] [--ids-from-pred]

Which gold records are scored
-----------------------------
Default: EVERY gold record; an id with no prediction line fails as ``missing_prediction``. That is
the only mode for a reported number. Two ways to RESTRICT scoring to the gold ids that actually have
a prediction (smoke runs): automatically when the predictions header carries a non-null ``limit``
(written by ``predict_toolcall.py --limit N``), or explicitly with ``--ids-from-pred``. A restricted
run records ``restricted: true``, ``restrict_reason`` and ``n_gold_total`` in results.json, and the
Markdown axis note says so ("KHÔNG dùng cho số báo cáo").

Header check (provenance gate)
------------------------------
The first line of the predictions file is a header written by ``training/predict_toolcall.py`` with
the sha256 of the eval file (and of the tool catalogue / preamble when they were used). The scorer
recomputes the sha256 of the LOCAL ``--gold`` (file bytes) and, when given and the header value is
non-null, of ``--tools`` (file bytes) and ``--preamble`` (content after ``.strip()``), and REFUSES
to score (exit 2) when they differ -- predictions made on a different eval axis must never land in
the same table. ``--no-header-check`` downgrades this to a warning (investigation only; say so in the
RUNLOG, never for a reported number).

Scoring ladder (eval_metric.md section 4; ported from the POC v1 benchmark's evaluate())
------------------------------------------------------------------------------------------------
   no prediction line for the id                 -> fail  "missing_prediction"
0. prediction has ``error`` set                  -> fail  "api_error"
1. expected_permission == "denied"               -> pass iff no predicted call names a tool whose
   ``tool_policy.json`` roles do not contain the record's user_role; a tool absent from the policy
   (hallucinated name) counts as not allowed for any role. Needs --policy. Without --policy: zero
   predicted calls -> pass; any call -> fail "policy_missing".            reason "permission_check"
2. expected_tool is null                         -> pass iff zero predicted calls   ("no_tool_expected")
3. tool name must be in {expected_tool} U expected_tool_alternates       -> otherwise fail "wrong_tool"
   STRICT_FIRST_CALL = True: only the FIRST predicted call is considered (strict accuracy).
   False: the first call whose name is accepted is used (POC v1 behaviour, eval_metric.md wording).
4. params: at least max(1, len(expected_params)//2) expected keys present in the matched call's
   arguments (keys only, values not compared)     -> otherwise fail "missing_params"
   pass                                           -> reason "ok"

Secondary metrics (reported, never decide H1): ``tool_name_acc`` (step 3 passed, over records with a
non-null expected_tool and permission allowed), ``param_acc`` (step 4 passed, over records where the
tool matched and expected_params is non-empty), ``params_exact`` (every expected key present with an
equal value after str() coercion, same denominator as param_acc), ``json_valid_rate`` (every
``<tool_call>`` tag in raw_text parses; with no tags: a structured call or a JSON body), latency
p50/p95 (ms, over records that have a latency), and breakdowns ``by_source`` / ``by_role`` /
``by_group`` (``--group-by <field>``).

Output ``results.json``::

    {"model", "eval_set", "eval_path", "eval_sha256", "n", "n_gold_total", "restricted", "restrict_reason",
     "passed", "accuracy",
     "tool_name_acc", "param_acc", "params_exact", "json_valid_rate", "latency_p50_ms", "latency_p95_ms",
     "by_reason", "by_source", "by_role", "by_group", "header", "scorer", "header_check", "policy",
     "results": [{"id", "pass", "reason", "expected_tool", "actual_tool", "source", "user_role",
                  "category", "json_valid", "latency_ms", "detail"}]}

``training/bootstrap_ci.py`` reads ``results[].id`` / ``results[].pass``.
Exit codes: 0 scored, 1 usage/file error, 2 header mismatch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

STRICT_FIRST_CALL = True   # see docstring step 3; flipping this is a scorer change = new measurement axis
# Note: no percent sign in this string -- it is printed into reports that scripts/check_provenance.py scans.
SCORER_VERSION = ("eval_toolcall/1.2 (" + ("strict first-call" if STRICT_FIRST_CALL else "any-call match")
                  + "; params >= half of keys; unknown tool = violation)")
TOOL_CALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)


# ───────────────────────────────────────────────────────────────────── helpers ──
def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """sha256 of text after .strip() -- the contract's convention for the preamble hash."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def load_gold(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        for key in ("records", "cases", "data"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON list of eval records")
    return data


def load_predictions(path: str) -> tuple[dict | None, dict[str, dict], int]:
    """Return (header or None, {id: record}, duplicate_count)."""
    header, preds, dups = None, {}, 0
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON ({exc})") from exc
            if lineno == 1 and isinstance(obj, dict) and obj.get("header") is True:
                header = obj
                continue
            rid = obj.get("id")
            if rid in preds:
                dups += 1
            preds[rid] = obj
    return header, preds, dups


def load_policy(path: str | None) -> dict | None:
    """tool_policy.json = {tool: {"writes": bool, "roles": [...]}} (a bare roles list is accepted too)."""
    if not path:
        return None
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    policy = {}
    for tool, entry in raw.items():
        roles = entry.get("roles") if isinstance(entry, dict) else entry
        policy[tool] = set(roles or [])
    return policy


def _loads_ok(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def json_valid_of(pred: dict | None, calls: list[dict]) -> bool:
    """Contract: every <tool_call> tag in raw_text parses; with no tags, a structured call or a JSON body."""
    if pred is None:
        return False
    raw = pred.get("raw_text") or ""
    blocks = TOOL_CALL_RE.findall(raw)
    if blocks:
        return all(_loads_ok(b) for b in blocks)
    return bool(calls) or (bool(raw.strip()) and _loads_ok(raw.strip()))


def percentile(values: list, q: float):
    if not values:
        return None
    vals = sorted(values)
    return vals[min(len(vals) - 1, int(round(q * (len(vals) - 1))))]


def pct(a: int, b: int) -> float | None:
    return round(100.0 * a / b, 2) if b else None


# ─────────────────────────────────────────────────────────────────── the ladder ──
def score_record(tc: dict, pred: dict | None, policy: dict | None) -> dict:
    """Returns {"pass", "reason", "detail"?, "matched_index"? (steps 3/4 reached)}."""
    if pred is None:
        return {"pass": False, "reason": "missing_prediction"}
    if pred.get("error"):
        return {"pass": False, "reason": "api_error", "detail": str(pred["error"])[:300]}

    expected_tool = tc.get("expected_tool")
    expected_params = tc.get("expected_params") or {}
    expected_perm = tc.get("expected_permission", "allowed")
    alternates = tc.get("expected_tool_alternates") or []
    role = tc.get("user_role") or pred.get("user_role") or "employee"
    calls = [c for c in (pred.get("predicted_tool_calls") or []) if isinstance(c, dict) and c.get("name")]
    names = [c["name"] for c in calls]

    # (1) denial: no predicted tool the caller's role may not call (unknown tool = may not call).
    if expected_perm == "denied":
        if policy is None:
            if not calls:
                return {"pass": True, "reason": "permission_check"}
            return {"pass": False, "reason": "policy_missing",
                    "detail": f"predicted {names} but no --policy to decide if the role may call them"}
        violations = [n for n in names if n not in policy or role not in policy[n]]
        unknown = [n for n in names if n not in policy]
        detail = {"violations": violations, "unknown_tools": unknown} if violations else None
        return {"pass": not violations, "reason": "permission_check", "detail": detail}

    # (2) nothing expected
    if expected_tool is None:
        return {"pass": not calls, "reason": "no_tool_expected",
                "detail": None if not calls else f"predicted {names}"}

    # (3) tool name
    if isinstance(expected_tool, list):          # legacy "any of these" form
        accepted = set(expected_tool)
    else:
        accepted = {expected_tool, *alternates}
    if STRICT_FIRST_CALL:
        idx = 0 if names and names[0] in accepted else None
    else:
        idx = next((i for i, n in enumerate(names) if n in accepted), None)
    if idx is None:
        return {"pass": False, "reason": "wrong_tool",
                "detail": f"expected one of {sorted(accepted)}, got {names or 'none'}"}

    # (4) params: at least half of the expected keys (min 1) present in the matched call's arguments (keys only)
    if expected_params and isinstance(expected_params, dict):
        args = calls[idx].get("arguments")
        args = args if isinstance(args, dict) else {}
        matched = sum(1 for k in expected_params if k in args)
        if matched < max(1, len(expected_params) // 2):
            return {"pass": False, "reason": "missing_params", "matched_index": idx,
                    "detail": {"expected": sorted(expected_params), "got": sorted(args), "matched": matched}}
    return {"pass": True, "reason": "ok", "matched_index": idx}


def params_exact_of(tc: dict, call: dict) -> bool:
    expected = tc.get("expected_params") or {}
    args = call.get("arguments")
    args = args if isinstance(args, dict) else {}
    return all(k in args and str(args[k]) == str(v) for k, v in expected.items())


# ───────────────────────────────────────────────────────────── header + report ──
def check_header(header: dict | None, args) -> list[str]:
    """Return a list of mismatch descriptions (empty = OK)."""
    if header is None:
        return ["predictions file has no header line ({\"header\": true, ...})"]
    problems = []
    local_eval = sha256_file(args.gold)
    if header.get("sha256_eval") != local_eval:
        problems.append(f"sha256_eval header={header.get('sha256_eval')} local={local_eval}")
    if args.tools and header.get("sha256_tools") is not None:
        local = sha256_file(args.tools)
        if header["sha256_tools"] != local:
            problems.append(f"sha256_tools header={header['sha256_tools']} local={local}")
    if args.preamble and header.get("sha256_preamble") is not None:
        local = sha256_text(Path(args.preamble).read_text(encoding="utf-8"))
        if header["sha256_preamble"] != local:
            problems.append(f"sha256_preamble header={header['sha256_preamble']} local={local} (stripped content)")
    return problems


def _fmt(v, suffix=""):
    return "n/a" if v is None else f"{v}{suffix}"


def _pct(v):
    """A percentage cell WITH the % sign so scripts/check_provenance.py sees it as a reportable number."""
    return "n/a" if v is None else f"{v}%"


def _short(sha):
    return f"`{sha[:8]}`" if sha else "n/a"


def build_markdown(res: dict, args, max_fail: int = 25) -> str:
    """Markdown report. Conventions agreed with scripts/check_provenance.py: every metric cell carries
    its % sign (so the gate sees it), the axis note ends with ``<!-- no-prov -->`` (it quotes the
    sampling JSON, not a result), and diagnostics (by_reason, failed records) sit inside a
    ``<!-- no-prov-start -->`` ... ``<!-- no-prov-end -->`` region. No literal percentage appears in
    labels (write "nửa số khoá", not "50%")."""
    hdr = res.get("header") or {}
    restricted_note = ""
    if res.get("restricted"):
        restricted_note = (f" · **CHỈ CHẤM {res['n']}/{res['n_gold_total']} bản ghi có dự đoán "
                           f"({res.get('restrict_reason')}) — KHÔNG dùng cho số báo cáo**")
    axis = (f"> **Ghi chú trục đo** — eval: `{res['eval_path']}` @ {_short(res['eval_sha256'])} · "
            + (f"tools: {_short(hdr.get('sha256_tools'))}" if hdr.get("sha256_tools") else "tools: theo từng bản ghi")
            + (f" · policy: `{args.policy}`" if args.policy else "")
            + (f" · preamble: {_short(hdr.get('sha256_preamble'))}" if hdr.get("sha256_preamble") else "")
            + f" · scorer: `{SCORER_VERSION}` · sampling: `{json.dumps(hdr.get('sampling') or {}, ensure_ascii=False)}`"
            + (" · **header check TẮT — không dùng cho số báo cáo**" if args.no_header_check else "")
            + restricted_note
            + ". Không so sánh với bảng ở trục khác. <!-- no-prov -->")
    lines = [
        f"# Kết quả chấm: `{res['model']}` trên `{res['eval_set']}`",
        "",
        axis,
        "",
        "| Số đo | Giá trị |",
        "|---|---|",
        f"| n | {res['n']}" + (f" (trong {res['n_gold_total']} gold)" if res.get("restricted") else "") + " |",
        f"| passed (strict) | {res['passed']} |",
        f"| **accuracy (strict)** | **{_pct(res['accuracy'])}** |",
        f"| tool_name_acc | {_pct(res['tool_name_acc'])} |",
        f"| param_acc (≥ nửa số khoá) | {_pct(res['param_acc'])} |",
        f"| params_exact | {_pct(res['params_exact'])} |",
        f"| json_valid_rate | {_pct(res['json_valid_rate'])} |",
        f"| latency p50 / p95 (ms) | {_fmt(res['latency_p50_ms'])} / {_fmt(res['latency_p95_ms'])} |",
        f"| model · backend | {res['model']} · {hdr.get('backend', '?')} |",
        f"| date · git_sha (dự đoán) | {hdr.get('date', '?')} · {(hdr.get('git_sha') or 'null')[:12]} |",
    ]

    def table(title, groups):
        out = ["", f"## {title}", "", "| group | n | passed | accuracy |", "|---|---|---|---|"]
        for g, v in sorted(groups.items(), key=lambda x: str(x[0])):
            out.append(f"| {g} | {v['n']} | {v['passed']} | {_pct(v['accuracy'])} |")
        return out

    lines += table("Theo `source`", res["by_source"])
    lines += table("Theo `user_role`", res["by_role"])
    if res.get("by_group") and args.group_by not in ("source", "user_role"):
        lines += table(f"Theo `{args.group_by}`", res["by_group"])

    # Diagnostics: counts per reason and the failed records are not reported numbers -> no-prov region.
    lines += ["", "<!-- no-prov-start -->", "## Theo lý do (chẩn đoán)", "", "| reason | count | tỷ lệ |", "|---|---|---|"]
    for reason, cnt in res["by_reason"].items():
        lines.append(f"| {reason} | {cnt} | {_pct(pct(cnt, res['n']))} |")
    fails = [r for r in res["results"] if not r["pass"]]
    if fails:
        lines += ["", f"## Bản ghi sai (tối đa {max_fail} / {len(fails)})", "",
                  "| id | reason | expected | actual | detail |", "|---|---|---|---|---|"]
        for r in fails[:max_fail]:
            detail = json.dumps(r.get("detail"), ensure_ascii=False) if r.get("detail") is not None else ""
            lines.append(f"| {r['id']} | {r['reason']} | {r['expected_tool']} | {r['actual_tool']} | "
                         f"{detail[:120].replace('|', '/')} |")
    lines.append("<!-- no-prov-end -->")

    cmd = f"python training/eval_toolcall.py --gold {args.gold} --pred {args.pred} --out {args.out}"
    for flag, val in (("--tools", args.tools), ("--policy", args.policy), ("--preamble", args.preamble),
                      ("--group-by", args.group_by), ("--md", args.md)):
        if val:
            cmd += f" {flag} {val}"
    if args.no_header_check:
        cmd += " --no-header-check"
    if args.ids_from_pred:
        cmd += " --ids-from-pred"
    lines += ["", f"_Lệnh_: `{cmd}`", ""]
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────── main ──
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--gold", required=True, help="eval JSON (list of records)")
    p.add_argument("--pred", required=True, help="predictions JSONL from predict_toolcall.py")
    p.add_argument("--out", required=True, help="results JSON to write")
    p.add_argument("--tools", default=None, help="tool catalogue used for prediction (sha256 check only)")
    p.add_argument("--policy", default=None, help="tool_policy.json {tool: {writes, roles}} for denial scoring")
    p.add_argument("--preamble", default=None, help="preamble file used for prediction (sha256 check only)")
    p.add_argument("--group-by", default=None, help="record field to break accuracy down by (e.g. source)")
    p.add_argument("--no-header-check", action="store_true", help="warn instead of refusing on sha256 mismatch")
    p.add_argument("--md", default=None, help="also write a Markdown report to this path")
    p.add_argument("--ids-from-pred", action="store_true",
                   help="score only the gold ids that have a prediction line (smoke runs; implied when the "
                        "predictions header has a non-null 'limit'); results.json gets restricted=true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    for path, label in ((args.gold, "--gold"), (args.pred, "--pred"), (args.tools, "--tools"),
                        (args.policy, "--policy"), (args.preamble, "--preamble")):
        if path and not Path(path).exists():
            print(f"error: {label} file not found: {path}", file=sys.stderr)
            return 1

    gold = load_gold(args.gold)
    header, preds, dups = load_predictions(args.pred)
    policy = load_policy(args.policy)

    problems = check_header(header, args)
    if problems:
        for pr in problems:
            print(f"{'WARNING' if args.no_header_check else 'REFUSED'} header check: {pr}", file=sys.stderr)
        if not args.no_header_check:
            print("SUMMARY eval_toolcall: REFUSED (header sha256 mismatch; use --no-header-check only for smoke tests)",
                  file=sys.stderr)
            return 2
    if dups:
        print(f"WARNING: {dups} duplicate id(s) in predictions; last occurrence wins", file=sys.stderr)
    extra = set(preds) - {r.get("id") for r in gold}
    if extra:
        print(f"WARNING: {len(extra)} prediction id(s) not in gold (ignored)", file=sys.stderr)

    # Restrict to predicted ids: explicit flag, or implied by a --limit smoke run (header.limit non-null).
    n_gold_total = len(gold)
    restrict_reason = None
    if args.ids_from_pred:
        restrict_reason = "--ids-from-pred"
    elif header is not None and header.get("limit") is not None:
        restrict_reason = f"header.limit={header['limit']}"
    if restrict_reason:
        gold = [tc for tc in gold if tc.get("id") in preds]
        print(f"WARNING: RESTRICTED scoring ({restrict_reason}): {len(gold)}/{n_gold_total} gold records have a "
              f"prediction; accuracy is over those {len(gold)} only -- smoke test, NOT a reportable number",
              file=sys.stderr)
    if policy is None and any(r.get("expected_permission") == "denied" for r in gold):
        print("WARNING: gold has expected_permission='denied' records but no --policy was given; any predicted "
              "tool on those records is scored 'policy_missing' (fail)", file=sys.stderr)

    results = []
    by_reason = Counter()
    groups = {"source": defaultdict(lambda: {"n": 0, "passed": 0}),
              "user_role": defaultdict(lambda: {"n": 0, "passed": 0})}
    if args.group_by and args.group_by not in groups:
        groups[args.group_by] = defaultdict(lambda: {"n": 0, "passed": 0})
    n_tool_expected = n_tool_correct = 0
    n_param_eligible = n_param_ok = n_param_exact = 0
    n_json_valid = 0
    latencies = []

    for tc in gold:
        pred = preds.get(tc.get("id"))
        verdict = score_record(tc, pred, policy)
        calls = [c for c in ((pred or {}).get("predicted_tool_calls") or []) if isinstance(c, dict) and c.get("name")]
        actual_tool = (pred or {}).get("predicted_tool") or (calls[0]["name"] if calls else None)
        json_valid = json_valid_of(pred, calls)
        n_json_valid += 1 if json_valid else 0
        lat = (pred or {}).get("latency_ms")
        if isinstance(lat, (int, float)):
            latencies.append(lat)

        scorable_tool = tc.get("expected_tool") is not None and tc.get("expected_permission", "allowed") != "denied"
        if scorable_tool:
            n_tool_expected += 1
            if verdict.get("matched_index") is not None:
                n_tool_correct += 1
                if tc.get("expected_params"):
                    n_param_eligible += 1
                    n_param_ok += 1 if verdict["reason"] == "ok" else 0
                    n_param_exact += 1 if params_exact_of(tc, calls[verdict["matched_index"]]) else 0

        by_reason[verdict["reason"]] += 1
        for field, table in groups.items():
            g = tc.get(field, "<none>")
            table[g]["n"] += 1
            table[g]["passed"] += 1 if verdict["pass"] else 0
        results.append({
            "id": tc.get("id"),
            "pass": bool(verdict["pass"]),
            "reason": verdict["reason"],
            "expected_tool": tc.get("expected_tool"),
            "actual_tool": actual_tool,
            "source": tc.get("source"),
            "user_role": tc.get("user_role"),
            "category": tc.get("category"),
            "json_valid": json_valid,
            "latency_ms": lat,
            "detail": verdict.get("detail"),
        })

    def finish(table):
        return {g: {"n": v["n"], "passed": v["passed"], "accuracy": pct(v["passed"], v["n"])} for g, v in table.items()}

    n = len(results)
    passed = sum(1 for r in results if r["pass"])
    out = {
        "model": (header or {}).get("model") or "unknown",
        "eval_set": Path(args.gold).name,
        "eval_path": str(args.gold),
        "eval_sha256": sha256_file(args.gold),
        "n": n,
        "n_gold_total": n_gold_total,
        "restricted": bool(restrict_reason),
        "restrict_reason": restrict_reason,
        "passed": passed,
        "accuracy": pct(passed, n),
        "tool_name_acc": pct(n_tool_correct, n_tool_expected),
        "param_acc": pct(n_param_ok, n_param_eligible),
        "params_exact": pct(n_param_exact, n_param_eligible),
        "json_valid_rate": pct(n_json_valid, n),
        "latency_p50_ms": percentile(latencies, 0.50),
        "latency_p95_ms": percentile(latencies, 0.95),
        "by_reason": dict(sorted(by_reason.items(), key=lambda x: -x[1])),
        "by_source": finish(groups["source"]),
        "by_role": finish(groups["user_role"]),
        "by_group": finish(groups[args.group_by]) if args.group_by else None,
        "header": header,
        "scorer": SCORER_VERSION,
        "header_check": "skipped" if args.no_header_check else "passed",
        "policy": args.policy,
        "results": results,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(build_markdown(out, args))

    reasons = ", ".join(f"{k}={v}" for k, v in out["by_reason"].items())
    restricted_tag = f" RESTRICTED({restrict_reason}; n_gold_total={n_gold_total})" if restrict_reason else ""
    print(f"SUMMARY eval_toolcall: model={out['model']} eval={out['eval_set']} n={n}{restricted_tag} passed={passed} "
          f"accuracy={_fmt(out['accuracy'], '%')} tool_name_acc={_fmt(out['tool_name_acc'], '%')} "
          f"param_acc={_fmt(out['param_acc'], '%')} params_exact={_fmt(out['params_exact'], '%')} "
          f"json_valid={_fmt(out['json_valid_rate'], '%')} p50={_fmt(out['latency_p50_ms'], 'ms')} "
          f"[{reasons}] -> {args.out}" + (f" + {args.md}" if args.md else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
