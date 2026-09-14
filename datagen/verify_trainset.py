#!/usr/bin/env python3
"""Stage 3: 3-stage verification gate (APIGen / xLAM style) for LABELED cases BEFORE they enter
the trainset. Input rows: {id, category, user_role, input, expected_tool, expected_params,
expected_permission, expected_tool_alternates?, _needs_review?}.

Stage A — FORMAT/EXISTENCE (offline):
  input non-empty; expected_tool null OR in the catalogue; params is a dict; permission in
  {allowed, denied}; denied => tool null; allowed tool => permitted for the role (tool_policy.json).
Stage B — SCHEMA/PARAM VALIDITY (offline, audit_test_cases.schema_audit + extras):
  param keys ∈ schema; enum membership; required params present (id/reference slots may be absent
  — they are resolved at serve time, see ID_SLOT rules below).
Stage C — SEMANTIC CONSENSUS (network, label_scenarios.review):
  N models independently pick the tool; PASS if >= --consensus-min agree with the label.
  Otherwise QUARANTINE (kept aside for human review — never silently dropped).

Outputs: --pass-out (A+B(+C) survivors), --quarantine-out (with _reject_stage/_issues), --report.

Usage:
  python3 datagen/verify_trainset.py --input data/sgod/labeled.json --no-semantic      # offline gate
  OPENAI_API_KEY=... python3 datagen/verify_trainset.py --input data/sgod/labeled.json \
      --consensus-min 2 --semantic-review-only   # stage C runs on the reference infrastructure;
                                                 # --models defaults to config_sgod.LABEL_MODELS
"""
import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_sgod as cfg  # noqa: E402
import audit_test_cases as audit  # noqa: E402
import label_scenarios as labeler  # noqa: E402  (review)

# TODO(SGOD): the reference system (POC v1) hardcoded the context/lookup slots that may be missing from a label
# ("id", "asset_id", "user_id", "office_id", ...). For SGOD we derive them: any required param whose
# name is "id", ends with "_id"/"_ids"/"_ref", or is listed in x_sgod.id_params. Revisit once
# sgod_tools.json v1 is tagged (`tools-v1`).
ID_SLOT_SUFFIXES = ("_id", "_ids", "_ref")

# list-shaped tools should usually carry >= 1 real filter; pagination keys don't count.
NONFILTER_KEYS = {"page", "per_page", "limit", "cursor", "offset"}


def is_id_slot(name: str, tool: str, meta: dict) -> bool:
    if name == "id" or name.endswith(ID_SLOT_SUFFIXES):
        return True
    return name in set((meta.get(tool) or {}).get("id_params") or [])


def stage_a_format(tc, valid_tools, perms=None):
    issues = []
    if not (tc.get("input") or "").strip():
        issues.append("empty input")
    et = tc.get("expected_tool")
    if isinstance(et, list):
        issues.append("multi-step label not supported (single tool only)")
        return issues
    if et is not None and et not in valid_tools:
        issues.append(f"unknown tool {et!r}")
    if et is not None and not isinstance(tc.get("expected_params", {}), dict):
        issues.append("params not a dict")
    if tc.get("expected_permission") not in ("allowed", "denied"):
        issues.append("bad permission value")
    if tc.get("expected_permission") == "denied" and et is not None:
        issues.append("denied but expected_tool not null")
    if et is not None and tc.get("expected_permission") == "allowed":
        if not audit.role_allows(tc.get("user_role", "employee"), et, perms):
            issues.append(f"role {tc.get('user_role')} not permitted for {et}")
    return issues


def stage_b_schema(tc, tools, perms, meta=None):
    meta = meta or {}
    res = audit.schema_audit([tc], tools, perms)[0]
    issues = list(res["issues"])
    et = tc.get("expected_tool")
    if et and et in tools:
        schema = tools[et].get("parameters", {}) or {}
        props = schema.get("properties", {}) or {}
        params = tc.get("expected_params", {}) or {}
        for k, v in params.items():
            enum = (props.get(k) or {}).get("enum") if isinstance(props.get(k), dict) else None
            if enum and isinstance(v, str) and v not in enum:
                issues.append(f"{et}.{k}={v!r} not in enum {enum}")
        for req in schema.get("required", []) or []:
            if req in params or is_id_slot(req, et, meta):
                continue
            issues.append(f"{et} missing required param {req!r}")
    return issues


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", default=f"{cfg.DATA_DIR}/labeled.json")
    p.add_argument("--pass-out", default=f"{cfg.DATA_DIR}/verified.json")
    p.add_argument("--quarantine-out", default=f"{cfg.DATA_DIR}/quarantine.json")
    p.add_argument("--report", default=f"{cfg.DATA_DIR}/verify_report.json")
    p.add_argument("--models", nargs="+", default=list(cfg.LABEL_MODELS))
    p.add_argument("--consensus-min", type=int, default=2,
                   help="min #models that must agree with the label to PASS stage C")
    p.add_argument("--no-semantic", action="store_true", help="skip stage C entirely (offline, no key)")
    p.add_argument("--semantic-review-only", action="store_true",
                   help="run stage C only on _needs_review rows; label-agreed rows pass on A+B (cuts cost ~60%%)")
    p.add_argument("--workers", type=int, default=16)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--require-filter-coverage", action="store_true",
                   help="exit 1 if too few list_*/search rows carry a filter param")
    p.add_argument("--min-filter-coverage", type=float, default=0.5)
    p.add_argument("--prompt-dir", default=cfg.PROMPT_DIR)
    audit.add_catalogue_args(p)
    args = p.parse_args()

    client = None
    if not args.no_semantic:
        client = cfg.require_openai_client()   # exits 2 with the Vietnamese message when the key is missing
    tools, perms = audit.load_catalogue(args)
    meta = audit.load_tool_meta(args.tools)
    catalogue = audit.build_tool_catalogue(tools)
    valid = set(tools)
    cases = json.loads(cfg.repo_path(args.input).read_text(encoding="utf-8"))
    if args.limit:
        cases = cases[:args.limit]
    print(f"Verifying {len(cases)} labeled cases (semantic={'off' if args.no_semantic else 'on'}) "
          f"against {len(valid)} tools")

    passed, quarantined, report = [], [], []
    n_a = n_b = n_c = 0
    to_semantic = []
    for tc in cases:
        a = stage_a_format(tc, valid, perms)
        b = stage_b_schema(tc, tools, perms, meta) if not a else []
        rec = {"id": tc.get("id"), "stage_a": a, "stage_b": b}
        if a:
            quarantined.append({**tc, "_reject_stage": "A", "_issues": a})
            rec["verdict"] = "format_fail"
            report.append(rec)
            continue
        n_a += 1
        if b:
            quarantined.append({**tc, "_reject_stage": "B", "_issues": b})
            rec["verdict"] = "schema_fail"
            report.append(rec)
            continue
        n_b += 1
        if args.no_semantic:
            passed.append(tc)
            rec["verdict"] = "pass_structural"
            report.append(rec)
            continue
        if args.semantic_review_only and not tc.get("_needs_review"):
            passed.append(tc)
            rec["verdict"] = "pass_consensus"
            report.append(rec)
            continue
        to_semantic.append((tc, rec))

    label_system = cfg.load_prompt("label_system", labeler.LABEL_SYS_DEFAULT, args.prompt_dir)

    def stage_c(tc, rec):
        et = tc.get("expected_tool")
        role = tc.get("user_role", "employee")
        votes = []
        for m in args.models:
            try:
                tool, _ = labeler.review(client, catalogue, tc["input"], role, m, label_system)
            except Exception as exc:  # noqa: BLE001
                cfg.METER.errors += 1
                rec.setdefault("errors", []).append(f"{m}: {exc}")
                continue
            votes.append(tool if tool in valid else None)
        if et is None and tc.get("expected_permission") == "allowed":
            agree = sum(1 for v in votes if v is None)
        elif tc.get("expected_permission") == "denied":
            non_null = [v for v in votes if v is not None]
            agree = max(Counter(non_null).values()) if non_null else 0
        else:
            alts = set(tc.get("expected_tool_alternates") or [])
            agree = sum(1 for v in votes if v == et or v in alts)
        rec["votes"] = votes
        rec["agree"] = agree
        return ("pass" if agree >= min(args.consensus_min, len(args.models)) else "quarantine"), rec

    pass_out = cfg.repo_path(args.pass_out)
    pass_out.parent.mkdir(parents=True, exist_ok=True)
    if to_semantic:
        done = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(stage_c, tc, rec): tc for tc, rec in to_semantic}
            for fut in as_completed(futs):
                tc = futs[fut]
                verdict, rec = fut.result()
                if verdict == "pass":
                    passed.append(tc)
                    rec["verdict"] = "pass"
                    n_c += 1
                else:
                    quarantined.append({**tc, "_reject_stage": "C", "_votes": rec.get("votes")})
                    rec["verdict"] = "quarantine_semantic"
                report.append(rec)
                done += 1
                if done % 200 == 0:
                    print(f"  stage C {done}/{len(to_semantic)} | passed={n_c} quarantine={len(quarantined)}",
                          flush=True)
                    pass_out.write_text(json.dumps(passed, ensure_ascii=False, indent=2), encoding="utf-8")

    passed.sort(key=lambda t: str(t.get("id")))
    quarantined.sort(key=lambda t: str(t.get("id")))
    report.sort(key=lambda r: str(r.get("id")))
    pass_out.write_text(json.dumps(passed, ensure_ascii=False, indent=2), encoding="utf-8")
    cfg.repo_path(args.quarantine_out).write_text(json.dumps(quarantined, ensure_ascii=False, indent=2),
                                                  encoding="utf-8")
    cfg.repo_path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    n = len(cases) or 1
    print(f"\n=== Verification pass-rates (n={len(cases)}) ===")
    print(f"  Stage A (format/exist): {n_a}/{len(cases)} = {n_a / n:.1%}")
    print(f"  Stage B (schema/param): {n_b}/{n_a} = {n_b / (n_a or 1):.1%} of A-pass")
    if not args.no_semantic:
        n_consensus = sum(1 for r in report if r.get("verdict") == "pass_consensus")
        if n_consensus:
            print(f"  Consensus-passed (skipped C): {n_consensus} (label-agreed, A+B only)")
        print(f"  Stage C (semantic):     {n_c}/{len(to_semantic) or 1} = "
              f"{n_c / (len(to_semantic) or 1):.1%} of {len(to_semantic)} reviewed")
    print(f"  quarantine by stage: {dict(Counter(q['_reject_stage'] for q in quarantined))}")

    rc = 0
    listish = [c for c in passed if (c.get("expected_tool") or "").startswith(("list_", "search"))]
    with_filter = [c for c in listish if any(k not in NONFILTER_KEYS for k in (c.get("expected_params") or {}))]
    if listish:
        cov = len(with_filter) / len(listish)
        print(f"  filter coverage (list_*/search with ≥1 filter): {len(with_filter)}/{len(listish)} = {cov:.0%}")
        if args.require_filter_coverage and cov < args.min_filter_coverage:
            print(f"  FAIL: filter coverage {cov:.0%} < {args.min_filter_coverage:.0%} — regenerate with more "
                  f"multi-filter queries.")
            rc = 1
    print(f"SUMMARY verify: n={len(cases)} passed={len(passed)} ({len(passed) / n:.1%}) "
          f"quarantined={len(quarantined)} -> {pass_out} | {cfg.METER.summary()}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
