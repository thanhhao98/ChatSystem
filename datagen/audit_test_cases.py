#!/usr/bin/env python3
"""Audit + fix labels in a case file (eval or labeled training cases) against the SGOD catalogue.

This module is ALSO the single place the whole datagen package reads tools and permissions from:
  - load_tools()        -> {tool_name: OpenAI function dict}   (tools/sgod/sgod_tools.json, x_sgod stripped)
  - load_tool_meta()    -> {tool_name: x_sgod dict}            (id_params, service, path ...)
  - load_permissions()  -> ROLE_TOOLS / ADMIN_ONLY_TOOLS derived from tools/sgod/tool_policy.json
  - is_tool_allowed(role, tool) / role_allows(case_role, tool)
No other datagen module may read permission data from anywhere else (no permission_map, no chat_policy).

Pass 1 (programmatic, offline): hard schema bugs
  - expected_tool not in the catalogue; expected_params keys outside the tool's schema
  - role/permission mismatch (role cannot call the tool yet expected_permission='allowed', or vice versa)
  - list-valued expected_tool (multi-step) -> rejected: phase 2 is single-turn, single-call
Pass 2 (LLM semantic review, needs OPENAI_API_KEY): is expected_tool the BEST tool for the query?
  The reviewer may confirm, propose a fix, or mark the case ambiguous with expected_tool_alternates.

Outputs: --audit-out (review report) and --fixed-out (proposed corrected file). The input is never
overwritten — the operator diffs and applies explicitly.

Usage:
    python3 datagen/audit_test_cases.py --input data/sgod/labeled.json --dry-run      # schema only
    OPENAI_API_KEY=... python3 datagen/audit_test_cases.py --input data/sgod/eval_human_core.json \
        --pass2-limit 50                      # --model defaults to config_sgod.ARBITER_MODEL
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_sgod as cfg  # noqa: E402

# ── catalogue + policy loaders ───────────────────────────────────────────────


def _read_tool_list(path):
    p = cfg.repo_path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"tool catalogue not found: {p} (set TOOL_DEFS_PATH or --tools; owner: D Việc 1 / S Việc 4)")
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("tools") or []
    if not isinstance(data, list):
        raise ValueError(f"{p}: expected a JSON list of tool objects")
    return data


def load_tools(path=None) -> dict:
    """{name: function_dict} from sgod_tools.json. `x_sgod` metadata is stripped: only the
    `function` object is ever rendered to a model (contract 4)."""
    out = {}
    for t in _read_tool_list(path or cfg.TOOL_DEFS_PATH):
        fn = t.get("function", t)
        name = fn.get("name")
        if not name:
            continue
        fn = {k: v for k, v in fn.items() if k != "x_sgod"}
        fn.setdefault("parameters", {"type": "object", "properties": {}, "required": []})
        out[name] = fn
    return out


def load_tool_meta(path=None) -> dict:
    """{name: x_sgod dict} — executor-side metadata (id_params, resolve, service ...)."""
    out = {}
    for t in _read_tool_list(path or cfg.TOOL_DEFS_PATH):
        fn = t.get("function", t)
        if fn.get("name"):
            out[fn["name"]] = dict(t.get("x_sgod") or fn.get("x_sgod") or {})
    return out


def load_policy(path=None) -> dict:
    """{tool: {"writes": bool, "roles": [...]}} from tool_policy.json."""
    p = cfg.repo_path(path or cfg.POLICY_PATH)
    if not p.exists():
        raise FileNotFoundError(
            f"tool policy not found: {p} (set TOOL_POLICY_PATH or --policy; owner: D Việc 1)")
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "tools" in data and isinstance(data["tools"], dict):
        data = data["tools"]
    pol = {}
    for tool, spec in data.items():
        spec = spec or {}
        pol[tool] = {"writes": bool(spec.get("writes", False)),
                     "roles": [str(r) for r in (spec.get("roles") or [])]}
    return pol


_ADMIN_LIKE = {"company_admin", "system_admin"}


def load_permissions(policy_path=None, roles_path=None, tools=None) -> dict:
    """Derive ROLE_TOOLS / ADMIN_ONLY_TOOLS from tool_policy.json.

    Rules: a tool is allowed to exactly the roles listed under "roles"; writes==true forces
    admin-only (employee is removed even if listed — tighten, never loosen). Tools present in the
    catalogue but absent from the policy are reported and treated as admin-only.
    Returns {role: set(tools) for every chat role, "admin_only": set, "_policy": policy}.
    """
    chat_roles, _ = cfg.load_roles(roles_path)
    policy = load_policy(policy_path)
    if tools:
        missing = sorted(set(tools) - set(policy))
        extra = sorted(set(policy) - set(tools))
        if missing:
            print(f"WARNING: {len(missing)} tool(s) missing from tool_policy.json -> treated as admin-only: "
                  f"{missing}", file=sys.stderr)
            for t in missing:
                policy[t] = {"writes": True, "roles": sorted(_ADMIN_LIKE)}
        if extra:
            print(f"WARNING: {len(extra)} policy entr(y/ies) without a catalogue tool: {extra}", file=sys.stderr)
    allowed = {}
    for tool, spec in policy.items():
        roles = set(spec["roles"])
        if spec["writes"]:
            roles &= _ADMIN_LIKE | {r for r in roles if r.endswith("admin")}
        allowed[tool] = roles
    perms = {role: {t for t, rs in allowed.items() if role in rs} for role in chat_roles}
    perms["admin_only"] = {t for t, rs in allowed.items() if "employee" not in rs}
    perms["_policy"] = policy
    perms["_allowed"] = allowed
    return perms


_PERMS_CACHE = {}


def _perms(policy_path=None, roles_path=None):
    key = (str(policy_path or cfg.POLICY_PATH), str(roles_path or cfg.ROLES_PATH))
    if key not in _PERMS_CACHE:
        _PERMS_CACHE[key] = load_permissions(policy_path, roles_path)
    return _PERMS_CACHE[key]


def is_tool_allowed(role: str, tool: str, perms=None) -> bool:
    """`role` is a CHAT role (company_admin / employee / system_admin)."""
    perms = perms or _perms()
    return role in perms.get("_allowed", {}).get(tool, set())


def role_allows(case_role: str, tool: str, perms=None) -> bool:
    """`case_role` is a CASE role ("admin"/"employee"); mapped through ROLE_MAP first."""
    return is_tool_allowed(cfg.ROLE_MAP.get(case_role, case_role), tool, perms)


def add_catalogue_args(p: argparse.ArgumentParser):
    p.add_argument("--tools", default=cfg.TOOL_DEFS_PATH, help="sgod_tools.json (env TOOL_DEFS_PATH)")
    p.add_argument("--policy", default=cfg.POLICY_PATH, help="tool_policy.json (env TOOL_POLICY_PATH)")
    p.add_argument("--roles", default=cfg.ROLES_PATH, help="roles.json (env ROLES_PATH)")
    return p


def load_catalogue(args):
    """Convenience for scripts: (tools, perms) honouring --tools/--policy/--roles."""
    tools = load_tools(args.tools)
    perms = load_permissions(args.policy, args.roles, tools=tools)
    _PERMS_CACHE[(str(args.policy), str(args.roles))] = perms
    _PERMS_CACHE[(str(cfg.POLICY_PATH), str(cfg.ROLES_PATH))] = perms   # role_allows() default
    return tools, perms


# ── params ───────────────────────────────────────────────────────────────────

# TODO(SGOD): the reference system (POC v1) had a PARAM_RENAME table ({"get_asset": {"asset_id": "id"}, ...})
# that encoded app-specific slot renames. It is NOT ported. Phase 2 only schema-filters keys; if labelers
# keep proposing a wrong-but-obvious key for an SGOD tool, add a rename here with a comment.
PARAM_RENAME = {}


def fix_params_for_tool(tool: str, params, tools: dict):
    """Schema-filter `params` to the tool's declared properties. Returns (kept, dropped_keys)."""
    if not isinstance(params, dict):
        return {}, []
    out = dict(params)
    for wrong, right in PARAM_RENAME.get(tool, {}).items():
        if wrong in out and right not in out:
            out[right] = out.pop(wrong)
        elif wrong in out:
            out.pop(wrong)
    props = set((tools.get(tool, {}).get("parameters", {}) or {}).get("properties", {}).keys())
    dropped = [k for k in out if k not in props]
    return {k: v for k, v in out.items() if k in props}, dropped


# ── pass 1: schema audit ─────────────────────────────────────────────────────


def schema_audit(tcs: list, tools: dict, perms: dict) -> list:
    """Mark each case with issues (list of strings). Single-call only."""
    findings = []
    for tc in tcs:
        issues = []
        expected_tool = tc.get("expected_tool")
        expected_params = tc.get("expected_params", {}) or {}
        expected_perm = tc.get("expected_permission", "allowed")
        role = tc.get("user_role", "employee")
        role_key = cfg.ROLE_MAP.get(role, role)
        if role_key not in perms or role_key.startswith("_"):
            issues.append(f"unknown role {role!r} (chat roles: {sorted(k for k in perms if not k.startswith('_') and k != 'admin_only')})")

        if isinstance(expected_tool, list) or isinstance(expected_params, list):
            issues.append("multi-step label (list-valued expected_tool/params) not supported in phase 2")
            findings.append({"id": tc.get("id"), "issues": issues, "tc": tc})
            continue

        if expected_tool is not None:
            if expected_tool not in tools:
                issues.append(f"unknown tool: {expected_tool}")
            else:
                schema = tools[expected_tool]
                valid_keys = set(schema.get("parameters", {}).get("properties", {}).keys())
                if isinstance(expected_params, dict):
                    for k in expected_params:
                        if k not in valid_keys:
                            issues.append(f"{expected_tool}: invalid param '{k}' (allowed: {sorted(valid_keys)})")
                else:
                    issues.append(f"{expected_tool}: expected_params is not a dict")
                allowed_roles = perms.get("_allowed", {}).get(expected_tool, set())
                if expected_perm == "allowed" and role_key not in allowed_roles:
                    issues.append(f"{expected_tool}: role {role_key!r} cannot call this tool "
                                  f"yet expected_permission='allowed'")
                elif expected_perm == "denied" and role_key in allowed_roles:
                    issues.append(f"{expected_tool}: role {role_key!r} IS allowed to call this tool, "
                                  f"yet expected_permission='denied'")
        findings.append({"id": tc.get("id"), "issues": issues, "tc": tc})
    return findings


# ── pass 2: LLM semantic review ──────────────────────────────────────────────


def build_tool_catalogue(tools: dict) -> str:
    lines = []
    for name, fn in sorted(tools.items()):
        params = fn.get("parameters", {}).get("properties", {})
        required = set(fn.get("parameters", {}).get("required", []))
        psum = ", ".join(
            f"{k}{('!' if k in required else '')}"
            f"{(':' + str(p.get('enum')[0]) + '...' if isinstance(p, dict) and p.get('enum') else '')}"
            for k, p in params.items()
        )
        lines.append(f"- {name}({psum}) — {fn.get('description', '')}")
    return "\n".join(lines)


def describe_permissions(perms: dict) -> str:
    lines = []
    for role in sorted(k for k in perms if not k.startswith("_") and k != "admin_only"):
        lines.append(f"- {role}: {', '.join(sorted(perms[role])) or '(none)'}")
    return "\n".join(lines)


# TODO(SGOD): rule 3 below is the POC v1 AMBIGUITY LIST (search vs list_assets, dashboard vs stats,
# get_my_profile vs list_assets). Replace it with the SGOD pairs once sgod_tools.json v1 is tagged
# (e.g. list_my_assets(q=) vs get_asset(asset_ref) for a named asset; list_maintenance_schedules vs
# a maintenance-records tool). A file datagen/prompts/reviewer_system.md overrides this text.
REVIEWER_SYSTEM_DEFAULT = """You are a strict but fair test-label reviewer for a Vietnamese asset-management chatbot eval set (SGOD platform). Your job: given a single test case and the production tool catalogue, decide whether the expected_tool is the BEST tool for the user's query.

Decision rules:
1. The query is in Vietnamese (sometimes mixed Vietnamese/English). Interpret it as a Vietnamese-speaking enterprise user would.
2. "Tài sản" = asset; "danh mục" = category; "vị trí/kho" = location; "bảo trì/lịch bảo trì" = maintenance schedule; "chuyển giao" = transfer; "thống kê/dashboard/tổng quan" = statistics; "tìm/kiếm/search" = search/find; "danh sách/liệt kê" = list; "chi tiết" = detail.
3. Ambiguity classes you MUST handle by listing alternates rather than failing the test:
   - TODO(SGOD): <tool A> vs <tool B> for <query shape> — fill from the SGOD catalogue.
   - A named asset ("xem máy in Canon") may be answered by the detail tool with a name reference OR by the list tool with a free-text filter; mark as alternates when both exist.
4. Asset codes in SGOD are sequential digits (e.g. 000000012) and asset names are free text; a detail tool that accepts a name/code reference is preferred over a list when exactly one asset is meant.
5. For `permission_denial` cases (a role asking for a tool it may not call): expected_tool should be null (text response) and expected_permission='denied'. If the test case has any other shape, fix it.
6. Always check `expected_params` keys are valid for the tool. If you change the tool, regenerate the params. Never invent parameters named like company/tenant/enterprise id — the JWT scopes those.
7. Exactly ONE tool call per case (single turn). Never propose a list of tools.

Return STRICT JSON with this shape:
{
  "verdict": "ok" | "fix" | "ambiguous",
  "reasoning": "one short sentence",
  "expected_tool": <string or null>,            // canonical answer (keep original if ok)
  "expected_params": <dict>,                    // canonical params for the chosen tool
  "expected_permission": "allowed" | "denied",
  "expected_tool_alternates": [<other acceptable tools>]   // OPTIONAL — only if "ambiguous"
}

Do NOT add prose around the JSON. Output JSON only."""


def gpt_review(client, tool_catalogue: str, perms_text: str, tc: dict, model: str,
               system_text: str = None) -> dict:
    user_prompt = f"""TOOL CATALOGUE
{tool_catalogue}

ROLE PERMISSIONS (derived from tool_policy.json — permission is decided by rule, not by you)
{perms_text}

TEST CASE
- id: {tc.get('id')}
- category: {tc.get('category')}
- user_role: {tc.get('user_role')}
- input: {tc['input']!r}
- current expected_tool: {tc.get('expected_tool')!r}
- current expected_params: {tc.get('expected_params')!r}
- current expected_permission: {tc.get('expected_permission')!r}

Audit this label. Return JSON only."""

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_text or REVIEWER_SYSTEM_DEFAULT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    cfg.METER.add(resp)
    raw = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"verdict": "ok", "reasoning": "parse failed", "_raw": raw}


def apply_review(tc: dict, review: dict, tools: dict) -> dict:
    """Return a possibly-modified copy of tc honouring the reviewer's verdict.
    Permission is re-derived by RULE from the final tool + role (never trusted from the model)."""
    out = dict(tc)
    verdict = review.get("verdict", "ok")
    if verdict == "ok":
        return out
    if "expected_tool" in review:
        et = review["expected_tool"]
        out["expected_tool"] = et if (et is None or et in tools) else out.get("expected_tool")
    if isinstance(review.get("expected_params"), dict) and out.get("expected_tool"):
        out["expected_params"], _ = fix_params_for_tool(out["expected_tool"], review["expected_params"], tools)
    if verdict == "ambiguous":
        alts = [a for a in (review.get("expected_tool_alternates") or []) if a in tools and a != out.get("expected_tool")]
        if alts:
            out["expected_tool_alternates"] = sorted(set(alts))
    et = out.get("expected_tool")
    if et is not None and not role_allows(out.get("user_role", "employee"), et):
        out["expected_permission"] = "denied"
        out["expected_tool"] = None
        out["expected_params"] = {}
        out.pop("expected_tool_alternates", None)
    elif et is not None:
        out["expected_permission"] = "allowed"
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True, help="case file (JSON list) to audit")
    p.add_argument("--audit-out", default=f"{cfg.DATA_DIR}/audit_report.json")
    p.add_argument("--fixed-out", default=f"{cfg.DATA_DIR}/audit_fixed.json")
    p.add_argument("--dry-run", action="store_true", help="schema audit only; no LLM, no API key needed")
    p.add_argument("--pass2-limit", type=int, default=0, help="cap LLM review at N cases (0 = all)")
    p.add_argument("--model", default=cfg.ARBITER_MODEL)
    p.add_argument("--prompt-dir", default=cfg.PROMPT_DIR,
                   help="directory with optional reviewer_system.md override")
    add_catalogue_args(p)
    args = p.parse_args()

    tcs = json.loads(cfg.repo_path(args.input).read_text(encoding="utf-8"))
    tools, perms = load_catalogue(args)
    print(f"Loaded {len(tcs)} cases | catalogue: {len(tools)} tools | roles: "
          f"{sorted(k for k in perms if not k.startswith('_') and k != 'admin_only')}")

    pass1 = schema_audit(tcs, tools, perms)
    n_with_issues = sum(1 for r in pass1 if r["issues"])
    print(f"\nPass 1 (schema): {n_with_issues}/{len(tcs)} cases with issues")
    for r in pass1:
        if r["issues"]:
            print(f"  {r['id']}: {r['issues']}")

    audit_out = cfg.repo_path(args.audit_out)
    audit_out.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        audit_out.write_text(json.dumps([{"id": r["id"], "issues": r["issues"]} for r in pass1],
                                        ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"SUMMARY audit dry-run: cases={len(tcs)} schema_issues={n_with_issues} -> {audit_out}")
        return 0

    client = cfg.require_openai_client()
    system_text = cfg.load_prompt("reviewer_system", REVIEWER_SYSTEM_DEFAULT, args.prompt_dir)
    catalogue = build_tool_catalogue(tools)
    perms_text = describe_permissions(perms)
    reviews, fixed_tcs = [], []
    cap = args.pass2_limit or len(tcs)
    print(f"\nPass 2 ({args.model} review): {cap} cases")
    for i, tc in enumerate(tcs):
        if i >= cap:
            fixed_tcs.append(tc)
            continue
        try:
            review = gpt_review(client, catalogue, perms_text, tc, args.model, system_text)
        except Exception as exc:  # noqa: BLE001 — keep going, record the error
            cfg.METER.errors += 1
            print(f"  {tc.get('id')}: review failed ({exc})")
            review = {"verdict": "ok", "reasoning": f"error: {exc}"}
        reviews.append({"id": tc.get("id"), "review": review,
                        "schema_issues": next((r["issues"] for r in pass1 if r["id"] == tc.get("id")), [])})
        fixed_tcs.append(apply_review(tc, review, tools))
        verdict = review.get("verdict", "?")
        marker = {"ok": " ", "fix": "F", "ambiguous": "A"}.get(verdict, "?")
        print(f"  [{marker}] {str(tc.get('id')):10s} {verdict:10s} {review.get('reasoning', '')[:80]}")
        if (i + 1) % 25 == 0:
            time.sleep(0.5)

    fixed_out = cfg.repo_path(args.fixed_out)
    audit_out.write_text(json.dumps(reviews, ensure_ascii=False, indent=2), encoding="utf-8")
    fixed_out.write_text(json.dumps(fixed_tcs, ensure_ascii=False, indent=2), encoding="utf-8")
    n_fix = sum(1 for r in reviews if r["review"].get("verdict") == "fix")
    n_amb = sum(1 for r in reviews if r["review"].get("verdict") == "ambiguous")
    print(f"\nReports: audit={audit_out} fixed={fixed_out}")
    print("Next: diff the fixed file against the input, review each suggested fix by hand, then replace.")
    print(f"SUMMARY audit: cases={len(tcs)} schema_issues={n_with_issues} reviewed={len(reviews)} "
          f"fix={n_fix} ambiguous={n_amb} ok={len(reviews) - n_fix - n_amb} | {cfg.METER.summary()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
