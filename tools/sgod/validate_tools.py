#!/usr/bin/env python3
"""Validate the SGOD tool catalogue (contract 4) and its token budget.

Checks, in order (every failure is printed; exit code 1 if any):
  * file shape: list of {"type":"function","function":{name,description,parameters},"x_sgod":{...}}
  * unique snake_case names; function.parameters.type == "object"; required ⊂ properties
  * tool_policy.json keys == tool names; policy.roles == x_sgod.allowed_roles; policy.writes == x_sgod.writes
  * every role ⊂ roles.json["roles"]
  * forbidden parameter names matching (company|tenant|enterprise)_?id — the JWT scopes the tenant (spec §1)
  * x_sgod.method GET <=> writes false; v1 rule: every tool has writes == false
  * x_sgod.method + x_sgod.path appear in a docs/sgod-api-reference.md table ({param} segments normalised);
    x_sgod.service matches the path prefix
  * blocklist: the broken GETs of spec §4, and any /sgod-chat/v1 path offered to a non-owner role
  * x_sgod.resolve (optional) has the form "GET /sgod-<svc>/v1/...?<key>={<param>}" with <param> in id_params
  * token budget (Qwen2.5 tokenizer, no torch model): preamble ≤ --max-preamble-tokens and the rendered
    system turn (preamble + that role's tools) ≤ --max-system-tokens for EVERY role; the summary names the
    single role whose system turn has the most tokens
  * preamble slots {role}/{role_vi}/{full_name}/{user_id} are filled with slot-by-slot str.replace — the
    SAME renderer as datagen/build_parity_trainset.py — so a literal JSON example may live in the preamble;
    a fixture self-test of that renderer runs on every invocation

Usage (see docs/contracts/cli.md):
  python tools/sgod/validate_tools.py [--tools ...] [--policy ...] [--roles ...] [--spec ...] [--preamble ...]
                                      [--max-preamble-tokens 1000] [--max-system-tokens 3400]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOKENIZER_ID = "Qwen/Qwen2.5-0.5B-Instruct"

SERVICES = {"auth": "/sgod-auth/v1/", "asset": "/sgod-asset/v1/", "chat": "/sgod-chat/v1/"}
HTTP_METHODS = {"GET", "POST", "PATCH", "PUT", "DELETE"}
SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")
FORBIDDEN_PARAM = re.compile(r"(company|tenant|enterprise)_?id", re.IGNORECASE)
X_SGOD_REQUIRED = {"service", "method", "path", "jwt_scoped", "allowed_roles", "writes", "id_params"}
X_SGOD_OPTIONAL = {"resolve", "notes"}
RESOLVE_RE = re.compile(r"^(GET) (/sgod-[a-z]+/v1/[^?\s{}]+)\?([A-Za-z_][A-Za-z0-9_]*)=\{([a-z][a-z0-9_]*)\}$")

# Preamble slot contract — MUST stay identical to datagen/build_parity_trainset.py (PLACEHOLDER_RE, KNOWN_SLOTS)
# and datagen/config_sgod.py (GENERIC_CONTEXT): the token budget below is measured on the very text the
# training rows carry. Slots are filled with str.replace, slot by slot, NOT str.format, so a literal JSON
# example such as <tool_call>{"name": ...}</tool_call> may appear in the preamble without breaking anything.
PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")        # bare-word {slot}; JSON braces / "{}" never match
KNOWN_SLOTS = {"role", "role_vi", "full_name", "user_id"}
GENERIC_CONTEXT = {"full_name": "Người dùng", "user_id": "usr-001"}  # {role} / {role_vi} filled per role

# Spec §4 broken GETs. The list is ALSO parsed from the spec at run time; this constant is a floor so
# the blocklist can never silently shrink if the spec is edited.
KNOWN_BROKEN_GETS = {
    ("GET", "/sgod-asset/v1/dashboard/summary"),
    ("GET", "/sgod-asset/v1/maintenance/schedules/count-by-tab"),
    ("GET", "/sgod-asset/v1/import-export/exports"),
    ("GET", "/sgod-asset/v1/asset-offers"),
    ("GET", "/sgod-asset/v1/categories-offer"),
}


# ── path helpers ─────────────────────────────────────────────────────────────
def resolve_path(p: str | Path) -> Path:
    """Accept a path relative to the cwd or to the repo root (so the script works from anywhere)."""
    p = Path(p)
    if p.exists():
        return p
    alt = REPO / p
    return alt if alt.exists() else p


def normalise_path(path: str) -> str:
    """Replace every {param} segment with {} so /assets/{id} and /assets/{assetId} compare equal."""
    return re.sub(r"\{[^/{}]+\}", "{}", path.strip())


# ── spec parsing (shared with gen_tool_api_mapping.py) ───────────────────────
_TABLE_ROW = re.compile(r"^\|\s*`?(GET|POST|PATCH|PUT|DELETE)`?\s*\|\s*`([^`]+)`\s*\|(.*)$")
_INLINE_CALL = re.compile(r"`(GET|POST|PATCH|PUT|DELETE) (/sgod-[a-z]+/v1/[^\s`?]+)")


def parse_spec_endpoints(spec_text: str) -> dict[tuple[str, str], str]:
    """Return {(METHOD, normalised_path): summary} for every endpoint row in the spec's markdown tables.

    Handles both table styles used in docs/sgod-api-reference.md (`GET` in backticks in §2, bare in §5)
    plus the inline "`GET /sgod-.../v1/...`" cells of the §3 intent table.
    """
    out: dict[tuple[str, str], str] = {}
    for line in spec_text.splitlines():
        m = _TABLE_ROW.match(line.strip())
        if m:
            method, path, rest = m.group(1), m.group(2).strip(), m.group(3)
            if path.startswith("/"):
                summary = rest.strip().strip("|").strip()
                out.setdefault((method, normalise_path(path)), summary)
            continue
        for method, path in _INLINE_CALL.findall(line):
            out.setdefault((method, normalise_path(path)), "")
    return out


def _section(spec_text: str, heading_prefix: str) -> str:
    """Text of the '## N.' section whose heading starts with heading_prefix (until the next '## ')."""
    lines = spec_text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(heading_prefix)), None)
    if start is None:
        return ""
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def parse_spec_blocklist(spec_text: str) -> dict[tuple[str, str], str]:
    """Broken GET endpoints from the spec §4 table → {(METHOD, path): quoted symptom}.

    Rows look like `| Med | asset | `GET /dashboard/summary` | <symptom> |`; the path is relative to the
    service prefix. Rows with several endpoints in one cell (`GET /asset-offers`, `GET /categories-offer`)
    yield one entry each. KNOWN_BROKEN_GETS is unioned in as a floor.
    """
    out: dict[tuple[str, str], str] = {}
    sec = _section(spec_text, "## 4.")
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] in ("Sev", "---"):
            continue
        sev, service, endpoint_cell, symptom = cells[0], cells[1].lower(), cells[2], cells[3]
        prefix = SERVICES.get(service)
        if not prefix:
            continue
        for method, rel in re.findall(r"`(GET|POST|PATCH|PUT|DELETE) (/[^`\s]+)`", endpoint_cell):
            out[(method, prefix.rstrip("/") + rel)] = symptom
    for key in KNOWN_BROKEN_GETS:
        out.setdefault(key, "spec §4 (hardcoded floor — row not found while parsing)")
    return out


def chat_owner_symptom(spec_text: str) -> str:
    """The §4 symptom text for 'all endpoints for non-owner' (chat), or a default sentence."""
    sec = _section(spec_text, "## 4.")
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[1].lower() == "chat" and "non-owner" in cells[2]:
            return cells[3]
    return "`500` for Enterprise-User & Sub-Enterprise tokens; only the Enterprise owner works."


# ── loading ──────────────────────────────────────────────────────────────────
def load_json(path: Path, what: str, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{what}: file not found: {path}")
    except json.JSONDecodeError as e:
        errors.append(f"{what}: invalid JSON in {path}: {e}")
    return None


def tools_for_role(tools: list, policy: dict, role: str) -> list:
    """The function objects offered to `role` (what apply_chat_template(tools=) renders at serve time)."""
    return [t for t in tools if role in (policy.get(t["function"]["name"], {}).get("roles") or [])]


# ── structural checks ────────────────────────────────────────────────────────
def _walk_property_names(schema, prefix=""):
    """Yield every property name in a JSON Schema, descending into nested objects/arrays."""
    if not isinstance(schema, dict):
        return
    for name, sub in (schema.get("properties") or {}).items():
        yield prefix + name
        yield from _walk_property_names(sub, prefix + name + ".")
    if "items" in schema:
        yield from _walk_property_names(schema["items"], prefix + "[].")


def check_tools(tools, policy, roles_doc, spec_text, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(tools, list) or not tools:
        errors.append("sgod_tools.json must be a non-empty JSON list of tool objects")
        return
    if not isinstance(policy, dict):
        errors.append("tool_policy.json must be a JSON object {tool: {writes, roles}}")
        policy = {}
    valid_roles = set(roles_doc.get("roles") or []) if isinstance(roles_doc, dict) else set()
    if not valid_roles:
        errors.append('roles.json must define a non-empty "roles" list')
    owner_role = (roles_doc.get("tiers") or {}).get("enterprises") if isinstance(roles_doc, dict) else None
    if not owner_role:
        errors.append('roles.json must map tiers["enterprises"] to the owner role (e.g. company_admin)')

    spec_endpoints = parse_spec_endpoints(spec_text)
    if len(spec_endpoints) < 50:
        errors.append(f"spec parse found only {len(spec_endpoints)} endpoints — is --spec the right file?")
    blocklist = parse_spec_blocklist(spec_text)

    names: list[str] = []
    for i, tool in enumerate(tools):
        where = f"tools[{i}]"
        if not isinstance(tool, dict) or tool.get("type") != "function" or not isinstance(tool.get("function"), dict):
            errors.append(f'{where}: must be {{"type":"function","function":{{...}},"x_sgod":{{...}}}}')
            continue
        fn = tool["function"]
        name = fn.get("name")
        if not isinstance(name, str) or not SNAKE_CASE.match(name):
            errors.append(f"{where}: function.name {name!r} is not snake_case")
            name = str(name)
        elif name in names:
            errors.append(f"{where}: duplicate tool name {name!r}")
        names.append(name)
        where = f"tool {name!r}"

        desc = fn.get("description")
        if not isinstance(desc, str) or not desc.strip():
            errors.append(f"{where}: function.description must be a non-empty Vietnamese string")
        elif desc.isascii():
            warnings.append(f"{where}: description has no Vietnamese diacritics — is it really Vietnamese?")

        params = fn.get("parameters")
        if not isinstance(params, dict) or params.get("type") != "object":
            errors.append(f'{where}: function.parameters.type must be "object"')
            params = {"properties": {}, "required": []}
        props = params.get("properties")
        if not isinstance(props, dict):
            errors.append(f"{where}: function.parameters.properties must be an object")
            props = {}
        required = params.get("required", [])
        if not isinstance(required, list):
            errors.append(f"{where}: function.parameters.required must be a list")
            required = []
        for r in required:
            if r not in props:
                errors.append(f"{where}: required parameter {r!r} is not declared in properties")
        for pname in _walk_property_names(params):
            if FORBIDDEN_PARAM.search(pname.split(".")[-1]):
                errors.append(f"{where}: forbidden parameter name {pname!r} — the JWT scopes the tenant (spec §1)")
        for pname, schema in props.items():
            if isinstance(schema, dict) and "enum" in schema:
                enum = schema["enum"]
                if not isinstance(enum, list) or not enum or len(set(map(str, enum))) != len(enum):
                    errors.append(f"{where}: parameter {pname!r} enum must be a non-empty list of unique values")

        # ── x_sgod ──
        x = tool.get("x_sgod")
        if not isinstance(x, dict):
            errors.append(f"{where}: missing x_sgod block")
            continue
        missing = X_SGOD_REQUIRED - set(x)
        extra = set(x) - X_SGOD_REQUIRED - X_SGOD_OPTIONAL
        if missing:
            errors.append(f"{where}: x_sgod missing keys {sorted(missing)}")
        if extra:
            errors.append(f"{where}: x_sgod has unknown keys {sorted(extra)} (allowed extras: {sorted(X_SGOD_OPTIONAL)})")
        service, method, path = x.get("service"), x.get("method"), x.get("path")
        writes, jwt_scoped = x.get("writes"), x.get("jwt_scoped")
        allowed = x.get("allowed_roles")
        id_params = x.get("id_params")

        if service not in SERVICES:
            errors.append(f"{where}: x_sgod.service {service!r} must be one of {sorted(SERVICES)}")
        if method not in HTTP_METHODS:
            errors.append(f"{where}: x_sgod.method {method!r} must be one of {sorted(HTTP_METHODS)}")
        if not isinstance(path, str) or not path.startswith("/"):
            errors.append(f"{where}: x_sgod.path must be an absolute path string")
            path = ""
        elif service in SERVICES and not path.startswith(SERVICES[service]):
            errors.append(f"{where}: x_sgod.path {path!r} does not start with {SERVICES[service]!r} (service={service})")
        if "?" in path:
            errors.append(f"{where}: x_sgod.path must not contain a query string (query params are function parameters)")
        if not isinstance(jwt_scoped, bool):
            errors.append(f"{where}: x_sgod.jwt_scoped must be true/false")
        if not isinstance(writes, bool):
            errors.append(f"{where}: x_sgod.writes must be true/false")
        else:
            if method == "GET" and writes:
                errors.append(f"{where}: method GET but writes=true")
            if method in HTTP_METHODS and method != "GET" and not writes:
                errors.append(f"{where}: method {method} but writes=false")
            if writes:
                errors.append(f"{where}: v1 rule — every tool must be read-only (writes=false); got method {method}")
        if not isinstance(allowed, list) or not allowed:
            errors.append(f"{where}: x_sgod.allowed_roles must be a non-empty list")
            allowed = []
        for r in allowed:
            if r not in valid_roles:
                errors.append(f"{where}: allowed_roles contains {r!r}, not in roles.json {sorted(valid_roles)}")
        if not isinstance(id_params, list):
            errors.append(f"{where}: x_sgod.id_params must be a list")
            id_params = []
        for p in id_params:
            if p not in props:
                errors.append(f"{where}: id_params entry {p!r} is not a declared parameter")
            elif p not in required:
                errors.append(f"{where}: id_params entry {p!r} must be in parameters.required")
        if path and "{" in path and not id_params:
            errors.append(f"{where}: path {path!r} has a {{param}} segment but id_params is empty")
        notes = x.get("notes")
        if notes is not None and not (isinstance(notes, str) or
                                      (isinstance(notes, list) and all(isinstance(n, str) for n in notes))):
            errors.append(f"{where}: x_sgod.notes must be a string or a list of strings")

        # ── spec membership + blocklist ──
        if method in HTTP_METHODS and path:
            key = (method, normalise_path(path))
            if key not in spec_endpoints:
                errors.append(f"{where}: {method} {path} is not an endpoint row in the spec tables")
            if key in blocklist:
                errors.append(f"{where}: {method} {path} is blocklisted by spec §4: {blocklist[key]}")
            if path.startswith(SERVICES["chat"]) and owner_role:
                bad = [r for r in allowed if r != owner_role]
                if bad:
                    errors.append(f"{where}: /sgod-chat/v1 tools are owner-only ({owner_role}); "
                                  f"spec §4: chat returns 500 for non-owner tokens; offending roles {bad}")

        # ── resolve ──
        resolve = x.get("resolve")
        if resolve is not None:
            m = RESOLVE_RE.match(resolve) if isinstance(resolve, str) else None
            if not m:
                errors.append(f"{where}: x_sgod.resolve must look like "
                              f"'GET /sgod-<svc>/v1/<path>?<key>={{<param>}}', got {resolve!r}")
            else:
                r_method, r_path, _key, r_param = m.groups()
                if (r_method, normalise_path(r_path)) not in spec_endpoints:
                    errors.append(f"{where}: resolve endpoint {r_method} {r_path} is not in the spec tables")
                if r_param not in id_params:
                    errors.append(f"{where}: resolve placeholder {{{r_param}}} must be listed in id_params")
                if r_param not in props:
                    errors.append(f"{where}: resolve placeholder {{{r_param}}} is not a declared parameter")

        # ── policy sidecar ──
        pol = policy.get(name)
        if pol is None:
            errors.append(f"{where}: no entry in tool_policy.json")
        else:
            if not isinstance(pol, dict) or set(pol) != {"writes", "roles"}:
                errors.append(f"{where}: tool_policy entry must be exactly {{\"writes\": bool, \"roles\": [...]}}")
            else:
                if pol["writes"] != writes:
                    errors.append(f"{where}: tool_policy.writes={pol['writes']} differs from x_sgod.writes={writes}")
                if not isinstance(pol["roles"], list) or sorted(pol["roles"]) != sorted(allowed):
                    errors.append(f"{where}: tool_policy.roles={pol.get('roles')} differs from "
                                  f"x_sgod.allowed_roles={allowed}")

    for orphan in sorted(set(policy) - set(names)):
        errors.append(f"tool_policy.json: entry {orphan!r} has no tool in sgod_tools.json")


# ── token budget ─────────────────────────────────────────────────────────────
def _n_tokens(encoded) -> int:
    """Length of the token id sequence, robust to transformers versions.

    transformers ≥ 4.4x/5.x returns a BatchEncoding (dict with input_ids) from apply_chat_template(tokenize=True);
    older versions return a plain list of ints.
    """
    if hasattr(encoded, "keys") or isinstance(encoded, dict):
        ids = encoded["input_ids"]
    else:
        ids = encoded
    if ids and isinstance(ids[0], (list, tuple)):
        ids = ids[0]
    return len(ids)


def preamble_placeholders(text: str) -> set[str]:
    """Bare-word {slot} names in a preamble (same regex as datagen/build_parity_trainset.py PLACEHOLDER_RE)."""
    return set(PLACEHOLDER_RE.findall(text))


def render_preamble(template: str, role: str, role_names_vi: dict[str, str] | None = None) -> str:
    """Fill the preamble slots for `role` exactly like datagen/build_parity_trainset.py Preamble.render.

    Sequential str.replace — {role}, {role_vi}, then GENERIC_CONTEXT — so every other brace in the template
    (a literal JSON example, "{}") passes through untouched. The result is .strip()ped like a training row.
    """
    names = role_names_vi or {}
    txt = template.replace("{role}", role)
    txt = txt.replace("{role_vi}", names.get(role, role))
    for slot, val in GENERIC_CONTEXT.items():
        txt = txt.replace("{" + slot + "}", val)
    return txt.strip()


_SELF_TEST_FIXTURE = (
    "Vai trò: {role_vi} ({role}) — {full_name} / {user_id}\n"
    'Ví dụ: <tool_call>{"name": "get_asset", "arguments": {"asset_ref": "Laptop QA"}}</tool_call>\n'
    'Rỗng: {} và { "k": 1 }\n'
)


def render_self_test() -> None:
    """Fixture check of the renderer: slots filled, literal JSON braces preserved, no slot left over.

    Runs at the start of every validate_tools invocation (pure string ops, no tokenizer) and raises
    AssertionError if the renderer ever diverges from the datagen contract described at the top.
    """
    assert preamble_placeholders(_SELF_TEST_FIXTURE) == KNOWN_SLOTS, "fixture: slot detection"
    out = render_preamble(_SELF_TEST_FIXTURE, "employee", {"employee": "Nhân viên"})
    first = out.splitlines()[0]
    assert first == "Vai trò: Nhân viên (employee) — Người dùng / usr-001", f"slots not filled: {first!r}"
    assert '<tool_call>{"name": "get_asset", "arguments": {"asset_ref": "Laptop QA"}}</tool_call>' in out, \
        "literal JSON example was altered by rendering"
    assert 'Rỗng: {} và { "k": 1 }' in out, "literal braces were altered by rendering"
    assert not (preamble_placeholders(out) & KNOWN_SLOTS), "a slot survived rendering"
    assert preamble_placeholders("x {foo} y {}") == {"foo"}, "unknown-slot detection"
    try:  # the bug this guards against: str.format cannot render a preamble that holds a JSON example
        _SELF_TEST_FIXTURE.format(role="e", role_vi="e", full_name="e", user_id="e")
    except (KeyError, ValueError, IndexError):
        pass
    else:
        raise AssertionError("fixture lost the literal brace that must break str.format")


def check_tokens(tools, policy, roles_doc, preamble_path: Path, max_preamble: int, max_system: int,
                 errors: list[str]) -> dict:
    """Count preamble tokens and the rendered system turn per role. Returns the counts for the summary."""
    counts: dict = {}
    try:
        preamble = preamble_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"preamble: file not found: {preamble_path}")
        return counts
    unknown = preamble_placeholders(preamble) - KNOWN_SLOTS
    if unknown:
        errors.append(f"preamble: unexpected placeholders {sorted(unknown)} (allowed: {sorted(KNOWN_SLOTS)}); "
                      f"datagen would leave them literal in every training row")
    if FORBIDDEN_PARAM.search(preamble):
        errors.append("preamble: mentions a company/tenant/enterprise id — the JWT scopes it, remove the reference")
    if unknown or FORBIDDEN_PARAM.search(preamble):
        return counts  # the text is invalid; token counts of an invalid preamble are meaningless

    try:
        from transformers import AutoTokenizer  # lazy: keep the structural checks torch/transformers-free
        tok = AutoTokenizer.from_pretrained(TOKENIZER_ID)
    except Exception as e:  # noqa: BLE001 — any load failure is a hard failure of the budget check
        errors.append(f"tokenizer: could not load {TOKENIZER_ID} ({type(e).__name__}: {e})")
        return counts

    counts["preamble_raw"] = len(tok(preamble.strip(), add_special_tokens=False)["input_ids"])  # template as datagen loads it
    if counts["preamble_raw"] > max_preamble:
        errors.append(f"preamble: {counts['preamble_raw']} tokens > --max-preamble-tokens {max_preamble}")

    role_names_vi = (roles_doc.get("role_names_vi") or {}) if isinstance(roles_doc, dict) else {}
    roles = list(roles_doc.get("roles") or []) if isinstance(roles_doc, dict) else []
    per_role: dict[str, tuple[int, int]] = {}
    for role in roles:
        offered = tools_for_role(tools, policy, role)
        content = render_preamble(preamble, role, role_names_vi)
        leftover = preamble_placeholders(content) & KNOWN_SLOTS
        if leftover:
            errors.append(f"preamble: slots {sorted(leftover)} still present after rendering for role {role!r}")
        msgs = [{"role": "system", "content": content}, {"role": "user", "content": "x"}]
        rendered = tok.apply_chat_template(msgs, tools=[{"type": "function", "function": t["function"]} for t in offered]
                                           or None, tokenize=True)
        per_role[role] = (len(offered), _n_tokens(rendered))
    counts["per_role"] = per_role
    if per_role:  # the single role reported in the summary = the one whose system turn has the most tokens
        worst_role, (worst_tools, worst) = max(per_role.items(), key=lambda kv: kv[1][1])
        counts["system_max"] = (worst_role, worst_tools, worst)
        if worst > max_system:
            errors.append(f"system turn for role {worst_role!r}: {worst} tokens > --max-system-tokens {max_system}")
    return counts


# ── main ─────────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tools", default="tools/sgod/sgod_tools.json")
    ap.add_argument("--policy", default="tools/sgod/tool_policy.json")
    ap.add_argument("--roles", default="tools/sgod/roles.json")
    ap.add_argument("--spec", default="docs/sgod-api-reference.md")
    ap.add_argument("--preamble", default="prompts/system_preamble_v1.txt")
    ap.add_argument("--max-preamble-tokens", type=int, default=1000)
    ap.add_argument("--max-system-tokens", type=int, default=3400)
    args = ap.parse_args(argv)

    try:
        render_self_test()
    except AssertionError as e:
        print(f"ERROR self-test: preamble renderer diverged from the datagen contract — {e}")
        print("validate_tools: FAIL — renderer self-test failed, 0 checks run")
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    tools = load_json(resolve_path(args.tools), "tools", errors)
    policy = load_json(resolve_path(args.policy), "policy", errors)
    roles_doc = load_json(resolve_path(args.roles), "roles", errors)
    spec_path = resolve_path(args.spec)
    try:
        spec_text = spec_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"spec: file not found: {spec_path}")
        spec_text = ""

    counts: dict = {}
    if tools is not None and policy is not None and roles_doc is not None:
        check_tools(tools, policy, roles_doc, spec_text, errors, warnings)
        if not errors:  # only spend the tokenizer load on a structurally valid catalogue
            counts = check_tokens(tools, policy, roles_doc, resolve_path(args.preamble),
                                  args.max_preamble_tokens, args.max_system_tokens, errors)

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    if counts:
        print(f"tokens: preamble={counts.get('preamble_raw')} (limit {args.max_preamble_tokens})")
        for role, (n_tools, n_tok) in counts.get("per_role", {}).items():
            print(f"tokens: system turn role={role} tools={n_tools} -> {n_tok} (limit {args.max_system_tokens})")

    n_tools = len(tools) if isinstance(tools, list) else 0
    if errors:
        print(f"validate_tools: FAIL — {len(errors)} error(s), {n_tools} tool(s)")
        return 1
    max_role, max_role_tools, max_tok = counts.get("system_max", ("?", 0, 0))
    print(f"validate_tools: OK — {n_tools} tools, 0 errors, preamble {counts.get('preamble_raw')} tok "
          f"≤ {args.max_preamble_tokens}, system turn max {max_tok} tok (role {max_role}, {max_role_tools} tools) "
          f"≤ {args.max_system_tokens}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
