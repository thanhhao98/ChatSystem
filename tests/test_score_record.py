#!/usr/bin/env python3
"""Plain-python checks for the scoring ladder of training/eval_toolcall.py (docs/contracts/eval_metric.md §4).

    python tests/test_score_record.py      # exit 0 and one SUMMARY line; exit 1 when any check fails

No pytest, no network, stdlib only; CI runs it right after "Contract 2 smoke". Covered: main-tool match
with params pass/fail (incl. the max(1, n // 2) key rule), without expected params, and with non-object
arguments; alternate match with and without expected_params_alternates (absent, {} or not an object);
wrong tool (incl. strict first-call) and the STRICT_FIRST_CALL = False branch; expected_tool null; denied
record that keeps the blocked tool, with and without a violating call (also a violating SECOND call:
step 1 reads every call); unknown tool on a denied record; no --policy; the legacy list form; and, end to
end through main(), the param_acc / params_exact denominators and the stderr warning for an
expected_params_alternates key outside expected_tool_alternates.
"""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "training"))
import eval_toolcall as ev  # noqa: E402

# load_policy() shape: {tool: set(roles)}
POLICY = {
    "get_asset": {"employee", "company_admin"},
    "list_my_assets": {"employee", "company_admin"},
    "get_enterprise_profile": {"company_admin"},
}

REC_MAIN = {"id": "t-main", "user_role": "employee", "expected_tool": "get_asset",
            "expected_params": {"asset_ref": "QA Test Laptop"}, "expected_permission": "allowed",
            "expected_tool_alternates": []}
REC_FOUR_KEYS = {"id": "t-four", "user_role": "company_admin", "expected_tool": "list_my_assets",
                 "expected_params": {"search": "laptop", "status": "active", "limit": 5, "cursor": "c1"},
                 "expected_permission": "allowed", "expected_tool_alternates": []}
REC_ALT = {"id": "t-alt", "user_role": "employee", "expected_tool": "get_asset",
           "expected_params": {"asset_ref": "QA Test Laptop"}, "expected_permission": "allowed",
           "expected_tool_alternates": ["list_my_assets"],
           "expected_params_alternates": {"list_my_assets": {"search": "QA Test Laptop"}}}
REC_ALT_NAME_ONLY = {k: v for k, v in REC_ALT.items() if k != "expected_params_alternates"}
REC_ALT_NAME_ONLY["id"] = "t-alt-name-only"
REC_ALT_EMPTY = dict(REC_ALT, id="t-alt-empty", expected_params_alternates={"list_my_assets": {}})
REC_NULL = {"id": "t-null", "user_role": "employee", "expected_tool": None, "expected_params": {},
            "expected_permission": "allowed", "expected_tool_alternates": []}
REC_DENIED = {"id": "t-denied", "user_role": "employee", "expected_tool": "get_enterprise_profile",
              "expected_params": {}, "expected_permission": "denied", "expected_tool_alternates": []}
REC_LEGACY = {"id": "t-legacy", "user_role": "employee", "expected_tool": ["get_asset", "list_my_assets"],
              "expected_params": {"asset_ref": "QA Test Laptop"}, "expected_permission": "allowed"}
REC_NO_PARAMS = {"id": "t-no-params", "user_role": "employee", "expected_tool": "list_my_assets",
                 "expected_params": {}, "expected_permission": "allowed", "expected_tool_alternates": []}
REC_ALT_BAD_VALUE = dict(REC_ALT, id="t-alt-bad-value", expected_params_alternates={"list_my_assets": ["search"]})

RESULTS = []   # (name, ok, message)


def pred(*calls, error=None):
    """Prediction line with calls given as (name, arguments) pairs."""
    return {"predicted_tool_calls": [{"name": n, "arguments": a} for n, a in calls], "error": error}


def check(name, got, want):
    ok = got == want
    RESULTS.append((name, ok, "" if ok else f"got {got!r}, want {want!r}"))


def check_score(name, tc, p, want_pass, want_reason, policy=POLICY):
    v = ev.score_record(tc, p, policy)
    check(name, (v["pass"], v["reason"]), (want_pass, want_reason))
    return v


def ladder_checks():
    # main tool: the expected_params rule, unchanged
    check_score("main tool, params present -> ok", REC_MAIN,
                pred(("get_asset", {"asset_ref": "QA Test Laptop"})), True, "ok")
    check_score("main tool, params missing -> missing_params", REC_MAIN,
                pred(("get_asset", {})), False, "missing_params")
    check_score("main tool, 2 of 4 keys (max(1, 4 // 2)) -> ok", REC_FOUR_KEYS,
                pred(("list_my_assets", {"search": "x", "limit": 1})), True, "ok")
    check_score("main tool, 1 of 4 keys -> missing_params", REC_FOUR_KEYS,
                pred(("list_my_assets", {"search": "x"})), False, "missing_params")
    check_score("record with alternates, main tool called -> still expected_params (fail)", REC_ALT,
                pred(("get_asset", {"search": "QA Test Laptop"})), False, "missing_params")
    check_score("record with alternates, main tool called -> still expected_params (ok)", REC_ALT,
                pred(("get_asset", {"asset_ref": "QA Test Laptop"})), True, "ok")
    check_score("main tool, expected_params {} -> name-only ok", REC_NO_PARAMS,
                pred(("list_my_assets", {})), True, "ok")
    check_score("main tool, arguments not an object -> no keys -> missing_params", REC_MAIN,
                pred(("get_asset", '{"asset_ref": "QA Test Laptop"}')), False, "missing_params")

    # alternate: expected_params_alternates[name] when present, else a name-only match
    check_score("alternate with its params present -> ok", REC_ALT,
                pred(("list_my_assets", {"search": "QA Test Laptop"})), True, "ok")
    v = check_score("alternate with its params missing -> missing_params", REC_ALT,
                    pred(("list_my_assets", {})), False, "missing_params")
    check("alternate failure detail names the alternate and its keys", v.get("detail"),
          {"expected": ["search"], "got": [], "matched": 0, "alternate": "list_my_assets"})
    check_score("alternate carrying only the MAIN tool's key -> missing_params", REC_ALT,
                pred(("list_my_assets", {"asset_ref": "QA Test Laptop"})), False, "missing_params")
    check_score("alternate without expected_params_alternates -> name-only ok", REC_ALT_NAME_ONLY,
                pred(("list_my_assets", {})), True, "ok")
    check_score("alternate mapped to {} -> name-only ok", REC_ALT_EMPTY,
                pred(("list_my_assets", {})), True, "ok")
    check_score("alternate mapped to a non-object -> name-only ok", REC_ALT_BAD_VALUE,
                pred(("list_my_assets", {})), True, "ok")
    rec_blocked_alt = dict(REC_ALT_NAME_ONLY, id="t-alt-blocked", expected_tool_alternates=["get_enterprise_profile"])
    check_score("alternate the role may not call -> wrong_tool (with --policy)", rec_blocked_alt,
                pred(("get_enterprise_profile", {})), False, "wrong_tool")
    check_score("alternate the role may not call, no --policy -> accepted", rec_blocked_alt,
                pred(("get_enterprise_profile", {})), True, "ok", policy=None)

    # wrong tool, strict first-call
    check_score("wrong tool -> wrong_tool", REC_MAIN,
                pred(("list_my_assets", {"search": "QA Test Laptop"})), False, "wrong_tool")
    check_score("no call when a tool is expected -> wrong_tool", REC_MAIN, pred(), False, "wrong_tool")
    check_score("strict first-call: right tool second -> wrong_tool", REC_MAIN,
                pred(("list_my_assets", {}), ("get_asset", {"asset_ref": "QA Test Laptop"})), False, "wrong_tool")

    # STRICT_FIRST_CALL = False branch (any-call match): the first ACCEPTED call is matched and step 4 uses
    # that call's tool. Flipping the constant is a new measurement axis; the strict default is restored.
    saved = ev.STRICT_FIRST_CALL
    try:
        ev.STRICT_FIRST_CALL = False
        v = check_score("any-call match: right tool second -> ok", REC_MAIN,
                        pred(("list_my_assets", {}), ("get_asset", {"asset_ref": "QA Test Laptop"})), True, "ok")
        check("any-call match: matched_index points at the accepted call", v.get("matched_index"), 1)
        check_score("any-call match: alternate second, checked against its own params", REC_ALT,
                    pred(("get_enterprise_profile", {}), ("list_my_assets", {})), False, "missing_params")
    finally:
        ev.STRICT_FIRST_CALL = saved

    # expected_tool null = out of scope
    check_score("null expected, no call -> pass", REC_NULL, pred(), True, "no_tool_expected")
    check_score("null expected, a call -> fail", REC_NULL, pred(("list_my_assets", {})), False, "no_tool_expected")

    # denied: the record keeps the blocked tool; pass iff no call the role may not make
    check_score("denied, no call -> pass", REC_DENIED, pred(), True, "permission_check")
    v = check_score("denied, calls the blocked tool -> fail", REC_DENIED,
                    pred(("get_enterprise_profile", {})), False, "permission_check")
    check("denied violation detail", v.get("detail"),
          {"violations": ["get_enterprise_profile"], "unknown_tools": []})
    check_score("denied, calls a tool the role may use -> pass", REC_DENIED,
                pred(("list_my_assets", {})), True, "permission_check")
    v = check_score("denied, allowed first call then the blocked tool -> fail (step 1 reads every call)",
                    REC_DENIED, pred(("list_my_assets", {}), ("get_enterprise_profile", {})), False,
                    "permission_check")
    check("denied multi-call detail lists only the violating call", v.get("detail"),
          {"violations": ["get_enterprise_profile"], "unknown_tools": []})
    v = check_score("denied, unknown (hallucinated) tool -> fail", REC_DENIED,
                    pred(("delete_all_assets", {})), False, "permission_check")
    check("denied unknown-tool detail", v.get("detail"),
          {"violations": ["delete_all_assets"], "unknown_tools": ["delete_all_assets"]})
    check_score("denied without --policy, no call -> pass", REC_DENIED, pred(), True, "permission_check",
                policy=None)
    check_score("denied without --policy, a call -> policy_missing", REC_DENIED,
                pred(("list_my_assets", {})), False, "policy_missing", policy=None)

    # legacy list form: any listed name, always expected_params
    check_score("legacy list, second name with params -> ok", REC_LEGACY,
                pred(("list_my_assets", {"asset_ref": "QA Test Laptop"})), True, "ok")
    v = check_score("legacy list, params missing -> missing_params", REC_LEGACY,
                    pred(("list_my_assets", {})), False, "missing_params")
    check("legacy list failure detail has no 'alternate'", "alternate" in (v.get("detail") or {}), False)
    check_score("legacy list, name not listed -> wrong_tool", REC_LEGACY,
                pred(("get_enterprise_profile", {})), False, "wrong_tool")

    # transport
    check_score("no prediction line -> missing_prediction", REC_MAIN, None, False, "missing_prediction")
    check_score("error set -> api_error", REC_MAIN, pred(error="HTTP 500"), False, "api_error")

    # the helper both step 4 and the param metrics use
    check("expected_params_for main tool", ev.expected_params_for(REC_ALT, "get_asset"),
          {"asset_ref": "QA Test Laptop"})
    check("expected_params_for alternate", ev.expected_params_for(REC_ALT, "list_my_assets"),
          {"search": "QA Test Laptop"})
    check("expected_params_for alternate without params", ev.expected_params_for(REC_ALT_NAME_ONLY, "list_my_assets"), {})
    check("expected_params_for legacy list", ev.expected_params_for(REC_LEGACY, "list_my_assets"),
          {"asset_ref": "QA Test Laptop"})

    # field validation (warn, never fail)
    check("no problems for a well-formed record", ev.params_alternates_problems([REC_ALT, REC_MAIN]), [])
    bad_key = dict(REC_MAIN, id="t-bad-key", expected_params_alternates={"list_my_assets": {"search": "x"}})
    probs = ev.params_alternates_problems([bad_key, dict(REC_ALT, id="t-not-obj", expected_params_alternates=[1])])
    check("problem for a key outside expected_tool_alternates",
          any(p.startswith("t-bad-key:") and "not in expected_tool_alternates" in p for p in probs), True)
    check("problem for a non-object field", any(p.startswith("t-not-obj:") for p in probs), True)
    check("problem for a non-object value under an alternate",
          any(p.startswith("t-alt-bad-value:") and "not an object" in p
              for p in ev.params_alternates_problems([REC_ALT_BAD_VALUE])), True)


def end_to_end_checks():
    """main(): param_acc / params_exact share the matched dict; warning on stderr for a stray key."""
    bad_key = dict(REC_MAIN, id="t-bad-key",
                   expected_params_alternates={"list_my_assets": {"search": "QA Test Laptop"}})
    gold = [REC_MAIN, REC_ALT, REC_ALT_NAME_ONLY, REC_NULL, REC_DENIED, bad_key]
    lines = {
        "t-main": pred(("get_asset", {"asset_ref": "QA Test Laptop"})),             # eligible, exact
        "t-alt": pred(("list_my_assets", {"search": "qa test laptop"})),            # eligible, not exact
        "t-alt-name-only": pred(("list_my_assets", {})),                             # name-only: not eligible
        "t-null": pred(),
        "t-denied": pred(),
        "t-bad-key": pred(("get_asset", {"asset_ref": "QA Test Laptop"})),          # eligible, exact
    }
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        gold_path, pred_path, out_path, policy_path = (d / "gold.json", d / "pred.jsonl", d / "r.json",
                                                       d / "policy.json")
        gold_path.write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")
        policy_path.write_text(json.dumps({t: {"writes": False, "roles": sorted(r)} for t, r in POLICY.items()}),
                               encoding="utf-8")
        header = {"header": True, "model": "unit-test",
                  "sha256_eval": hashlib.sha256(gold_path.read_bytes()).hexdigest(),
                  "sha256_tools": None, "sha256_preamble": None}
        with open(pred_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(header) + "\n")
            for rid, p in lines.items():
                f.write(json.dumps(dict(p, id=rid), ensure_ascii=False) + "\n")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ev.main(["--gold", str(gold_path), "--pred", str(pred_path), "--out", str(out_path),
                          "--policy", str(policy_path)])
        check("main() exit code", rc, 0)
        res = json.loads(out_path.read_text(encoding="utf-8"))
    check("e2e passed / n", (res["passed"], res["n"]), (6, 6))
    check("e2e tool_name_acc (4 scorable records)", res["tool_name_acc"], 100.0)
    check("e2e param_acc (3 eligible: main, alternate with params, stray-key record)", res["param_acc"], 100.0)
    check("e2e params_exact (2 of the same 3)", res["params_exact"], 66.67)
    check("e2e stderr warns about the stray expected_params_alternates key",
          "t-bad-key" in err.getvalue() and "not in expected_tool_alternates" in err.getvalue(), True)


def sha256_mismatch_checks():
    """Header checks: eval_toolcall refuses (rc=2) on sha256 mismatch unless --no-header-check is given."""
    gold = [REC_MAIN]
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        gold_path, pred_path, out_path = d / "gold.json", d / "pred.jsonl", d / "r.json"
        tools_path, prem_path = d / "tools.json", d / "preamble.txt"
        gold_path.write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")
        tools_path.write_text("[]", encoding="utf-8")
        prem_path.write_text("hello", encoding="utf-8")

        real_eval = hashlib.sha256(gold_path.read_bytes()).hexdigest()
        real_tools = hashlib.sha256(tools_path.read_bytes()).hexdigest()

        def run(hdr, extra_args=()):
            with open(pred_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(hdr) + "\n")
                f.write(json.dumps({"id": "t-main", "predicted_tool_calls": [{"name": "get_asset", "arguments": {"asset_ref": "QA Test Laptop"}}]}) + "\n")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = ev.main(["--gold", str(gold_path), "--pred", str(pred_path), "--out", str(out_path)] + list(extra_args))
            return rc, out.getvalue(), err.getvalue()

        # sha256_eval mismatch
        bad_eval = {"header": True, "model": "unit", "sha256_eval": "00000000", "sha256_tools": None, "sha256_preamble": None}
        rc, _, err = run(bad_eval)
        check("sha256_eval mismatch refuses (rc=2)", rc, 2)
        check("sha256_eval mismatch stderr mentions REFUSED", "REFUSED" in err, True)

        rc, _, err = run(bad_eval, extra_args=["--no-header-check"])
        check("sha256_eval mismatch with --no-header-check passes (rc=0)", rc, 0)
        check("sha256_eval mismatch with --no-header-check warns", "WARNING" in err and "sha256_eval" in err, True)

        # sha256_tools mismatch
        bad_tools = {"header": True, "model": "unit", "sha256_eval": real_eval, "sha256_tools": "badtoolshash", "sha256_preamble": None}
        rc, _, err = run(bad_tools, extra_args=["--tools", str(tools_path)])
        check("sha256_tools mismatch refuses (rc=2)", rc, 2)
        rc, _, err = run(bad_tools, extra_args=["--tools", str(tools_path), "--no-header-check"])
        check("sha256_tools mismatch with --no-header-check passes (rc=0)", rc, 0)

        # sha256_preamble mismatch
        bad_prem = {"header": True, "model": "unit", "sha256_eval": real_eval, "sha256_tools": None, "sha256_preamble": "badpreamblehash"}
        rc, _, err = run(bad_prem, extra_args=["--preamble", str(prem_path)])
        check("sha256_preamble mismatch refuses (rc=2)", rc, 2)
        rc, _, err = run(bad_prem, extra_args=["--preamble", str(prem_path), "--no-header-check"])
        check("sha256_preamble mismatch with --no-header-check passes (rc=0)", rc, 0)


def plumbing_sgod_checks():
    """Plumbing test: score mock predictions against a JSON-list copy of data/sgod/eval_human_core.jsonl
    using real sgod_tools.json (tag tools-v1), tool_policy.json, and system_preamble_v1.txt.
    Smoke test only -- no INDEX rows, no reported numbers."""
    core_path = REPO / "data" / "sgod" / "eval_human_core.jsonl"
    tools_path = REPO / "tools" / "sgod" / "sgod_tools.json"
    policy_path = REPO / "tools" / "sgod" / "tool_policy.json"
    preamble_path = REPO / "prompts" / "system_preamble_v1.txt"

    if not core_path.exists():
        return

    records = [json.loads(line) for line in core_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        gold_path, pred_path, out_path = d / "eval_human_core.json", d / "pred.jsonl", d / "r.json"
        gold_path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

        sha_eval = hashlib.sha256(gold_path.read_bytes()).hexdigest()
        sha_tools = hashlib.sha256(tools_path.read_bytes()).hexdigest()
        sha_preamble = hashlib.sha256(preamble_path.read_text(encoding="utf-8").strip().encode("utf-8")).hexdigest()

        header = {
            "header": True,
            "model": "gpt-5.2",
            "backend": "openai",
            "base_url_host": "<openai-compatible-gateway>",
            "date": "2026-10-21T18:00:00+00:00",
            "git_sha": "abc1234",
            "sha256_eval": sha_eval,
            "sha256_tools": sha_tools,
            "sha256_preamble": sha_preamble,
            "sampling": {"temperature": 0, "max_new_tokens": 256, "seed": 42},
            "n": len(records),
        }
        with open(pred_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(header) + "\n")
            for r in records:
                if r.get("expected_permission") == "denied" or r.get("expected_tool") is None:
                    calls = []
                else:
                    calls = [{"name": r["expected_tool"], "arguments": r.get("expected_params") or {}}]
                row = {
                    "id": r["id"],
                    "predicted_tool_calls": calls,
                    "predicted_tool": calls[0]["name"] if calls else None,
                    "raw_text": json.dumps(calls),
                    "finish_reason": "stop",
                    "latency_ms": 100,
                    "error": None,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ev.main([
                "--gold", str(gold_path),
                "--pred", str(pred_path),
                "--out", str(out_path),
                "--tools", str(tools_path),
                "--policy", str(policy_path),
                "--preamble", str(preamble_path),
            ])
        check("plumbing sgod main() exit code", rc, 0)
        res = json.loads(out_path.read_text(encoding="utf-8"))
        check("plumbing sgod n == 150", res["n"], 150)
        check("plumbing sgod passed == 150", res["passed"], 150)
        check("plumbing sgod by_reason ok", res["by_reason"].get("ok"), 96)
        check("plumbing sgod by_reason no_tool_expected", res["by_reason"].get("no_tool_expected"), 31)
        check("plumbing sgod by_reason permission_check", res["by_reason"].get("permission_check"), 23)


def main() -> int:
    ladder_checks()
    end_to_end_checks()
    sha256_mismatch_checks()
    plumbing_sgod_checks()
    failed = [(n, m) for n, ok, m in RESULTS if not ok]
    for name, msg in failed:
        print(f"FAIL {name}: {msg}")
    status = "OK" if not failed else f"{len(failed)} FAILED"
    print(f"SUMMARY test_score_record: {len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed ({status})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
