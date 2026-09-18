#!/usr/bin/env python3
"""Machine gate for training rows — docs/contracts/training_row_format.md (contract 1).

CPU only, stdlib only, no model download. Run it before every fine-tune and in CI.

A row is valid when ALL of the following hold:
  * `messages` is exactly [system, user, assistant] with non-empty string contents;
  * messages[0].content == the preamble for the row's role (compared after .strip()) unless
    --no-preamble-check. Public rows: prompts/system_preamble_v0.txt verbatim (no slots). SGOD rows:
    prompts/system_preamble_v1.txt with its slots FILLED the same way datagen/build_parity_trainset.py
    (Preamble.render) and tools/sgod/validate_tools.py (GENERIC_CONTEXT) fill them — str.replace, in
    this order:
        {role}      -> the row's "role"
        {role_vi}   -> roles.json "role_names_vi"[role]   (--roles is REQUIRED when the file has slots)
        {full_name} -> "Người dùng"
        {user_id}   -> "usr-001"
    so an employee row must carry "- Vai trò: Nhân viên" and "- Mã người dùng: usr-001", never the
    literal "{role_vi}" — the three scripts must agree byte-for-byte or this gate rejects every row;
  * the assistant turn is one-or-more `<tool_call>{"name": str, "arguments": {..}}</tool_call>`
    blocks and NOTHING else, OR exactly REFUSAL_VI / DEFLECT_VI from prompts/fixed_replies.json;
  * `role` is in the role vocabulary (default {employee, company_admin, system_admin}; --roles);
  * optional `id` is a string and unique within the file;
  * if `replay_tools` is present, every entry is an OpenAI function object
    {"type": "function", "function": {"name", "description", "parameters": {"type": "object", ...}}}
    and every called tool name exists in replay_tools;
  * otherwise --tools is required and each call is checked against the catalogue: the name exists,
    every argument key is declared in parameters.properties, and (when tool_policy.json sits next
    to --tools) the tool is offered to the row's role — finetune_qlora.py renders only those tools.

Usage
  python training/validate_dataset.py data/public/xlam_2k.train.jsonl data/public/xlam_2k.val.jsonl
  python training/validate_dataset.py data/sgod/train.jsonl --tools tools/sgod/sgod_tools.json \
      --preamble prompts/system_preamble_v1.txt --roles tools/sgod/roles.json

Regression check of the slot rendering (must PASS): rows produced by the D-team renderer from a
tiny cases file, e.g. [{"id": "SN-0002", "user_role": "admin", "input": "Liệt kê các lịch bảo trì đang
hiệu lực.", "expected_tool": "list_maintenance_schedules", "expected_params": {"status": "active"},
"expected_permission": "allowed"}], validated with the same preamble/roles/tools files:
  python datagen/build_parity_trainset.py --sources /tmp/cases.json --out-dir /tmp/sgod \
      --train-name train.jsonl --val-ratio 0 --preamble prompts/system_preamble_v1.txt
  python training/validate_dataset.py /tmp/sgod/train.jsonl --preamble prompts/system_preamble_v1.txt \
      --tools tools/sgod/sgod_tools.json --roles tools/sgod/roles.json      # -> PASS, 0 errors
The rendered system turn of that row contains "- Vai trò: Quản trị viên doanh nghiệp",
"- Họ tên: Người dùng", "- Mã người dùng: usr-001".

Prints error counts by type and exits 1 on any error.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PREAMBLE = "prompts/system_preamble_v0.txt"
DEFAULT_FIXED_REPLIES = "prompts/fixed_replies.json"
DEFAULT_ROLES = {"employee", "company_admin", "system_admin"}
TOOL_POLICY_FILENAME = "tool_policy.json"
EXAMPLES_PER_TYPE = 5  # how many concrete rows to print per error type

# Preamble v1 slots. Names, generic values and the replace ORDER must equal
# datagen/build_parity_trainset.py (Preamble.render / config_sgod.GENERIC_CONTEXT) and
# tools/sgod/validate_tools.py (GENERIC_CONTEXT). {role_vi} comes from roles.json "role_names_vi".
PREAMBLE_SLOTS = ("role", "role_vi", "full_name", "user_id")
GENERIC_CONTEXT = {"full_name": "Người dùng", "user_id": "usr-001"}
_SLOT_RE = re.compile(r"\{([a-z_]+)\}")

# The whole assistant turn must be tool_call blocks separated by nothing but whitespace.
_TOOLCALL_BLOCKS = re.compile(r"(?:\s*<tool_call>.*?</tool_call>\s*)+", re.DOTALL)
_TOOLCALL_BODY = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)


def resolve_path(path):
    """Accept paths relative to the CWD or to the repo root (notebooks may run from either)."""
    if path and not os.path.exists(path):
        alt = os.path.join(REPO_ROOT, path)
        if os.path.exists(alt):
            return alt
    return path


# ── Reference inputs ──────────────────────────────────────────────────────────────────────────

def load_preamble(path):
    """Raw template text (stripped). Slots, if any, are filled per row by render_preamble()."""
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def preamble_slots(template):
    """Set of {slot} names found in the template; empty for the slot-less public preamble v0."""
    return set(_SLOT_RE.findall(template))


def render_preamble(template, role, role_names_vi):
    """Fill the slots for one role — the same str.replace sequence as build_parity_trainset.Preamble.render
    (str.replace, not str.format, so literal braces elsewhere in the text are left alone)."""
    txt = template.replace("{role}", role)
    txt = txt.replace("{role_vi}", role_names_vi.get(role, role))
    for slot, val in GENERIC_CONTEXT.items():
        txt = txt.replace("{" + slot + "}", val)
    return txt.strip()


def expected_preamble(ctx, role):
    """System text the row must carry: the template itself when it has no slots, else the template
    rendered for the row's role (cached per role). None when the role is invalid — role_invalid is
    already reported and the slots cannot be filled."""
    if not ctx["preamble_slots"]:
        return ctx["preamble"]
    if role not in ctx["roles"]:
        return None
    cache = ctx["preamble_cache"]
    if role not in cache:
        cache[role] = render_preamble(ctx["preamble"], role, ctx["role_names_vi"])
    return cache[role]


def preamble_diff_hint(expected, got):
    """Point at the first differing line so the reader sees WHAT differs, not only that it does."""
    exp_lines, got_lines = expected.splitlines(), got.splitlines()
    for i, (a, b) in enumerate(zip(exp_lines, got_lines), 1):
        if a != b:
            if a.strip() == b.strip():
                return f"system content differs from the rendered preamble at line {i} (whitespace only)"
            return (f"system content differs from the rendered preamble at line {i}: "
                    f"expected {a.strip()[:60]!r}, got {b.strip()[:60]!r}")
    return (f"system content differs from the rendered preamble: expected {len(exp_lines)} lines, "
            f"got {len(got_lines)}")


def load_fixed_replies(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    missing = [k for k in ("REFUSAL_VI", "DEFLECT_VI") if k not in d]
    if missing:
        sys.exit(f"ERROR: {path} lacks {missing}")
    return {d["REFUSAL_VI"], d["DEFLECT_VI"]}


def _find_string_lists(obj, key):
    """Yield every list of strings stored under `key` anywhere in a JSON object."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, list) and all(isinstance(x, str) for x in v):
                yield v
            else:
                yield from _find_string_lists(v, key)
    elif isinstance(obj, list):
        for v in obj:
            yield from _find_string_lists(v, key)


def load_roles(path):
    """Return (roles, role_names_vi). tools/sgod/roles.json = {"tiers": {...}, "roles": [...],
    "role_names_vi": {role: "tên tiếng Việt"}}; any string list under a "roles" key is accepted, as is
    a bare JSON list of strings (then role_names_vi is empty and {role_vi} falls back to the role key)."""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, list) and all(isinstance(x, str) for x in d):
        return set(d), {}
    roles = set()
    for lst in _find_string_lists(d, "roles"):
        roles.update(lst)
    if not roles:
        sys.exit(f"ERROR: no list of role names found under a 'roles' key in {path}")
    names = d.get("role_names_vi") if isinstance(d, dict) else None
    role_names_vi = {str(k): str(v) for k, v in names.items()} if isinstance(names, dict) else {}
    return roles, role_names_vi


def load_catalogue(path):
    """Return (catalogue {name: properties-set}, policy {name: roles} or None)."""
    with open(path, encoding="utf-8") as f:
        tools = json.load(f)
    if isinstance(tools, dict) and "tools" in tools:
        tools = tools["tools"]
    catalogue = {}
    for t in tools:
        fn = t.get("function", t)
        props = (fn.get("parameters") or {}).get("properties") or {}
        catalogue[fn["name"]] = set(props)
    policy = None
    policy_path = os.path.join(os.path.dirname(os.path.abspath(path)), TOOL_POLICY_FILENAME)
    if os.path.exists(policy_path):
        with open(policy_path, encoding="utf-8") as f:
            raw = json.load(f)
        policy = {name: set(e.get("roles", []) if isinstance(e, dict) else e) for name, e in raw.items()}
    return catalogue, policy


# ── Per-row checks ────────────────────────────────────────────────────────────────────────────

def check_tool_object(tool):
    """Shape of one replay_tools entry; returns a reason string or None."""
    if not isinstance(tool, dict) or tool.get("type") != "function":
        return "entry is not {type: 'function', ...}"
    fn = tool.get("function")
    if not isinstance(fn, dict):
        return "missing 'function' object"
    if not isinstance(fn.get("name"), str) or not fn["name"]:
        return "function.name is not a non-empty string"
    if not isinstance(fn.get("description"), str):
        return f"function.description missing for '{fn.get('name')}'"
    params = fn.get("parameters")
    if not isinstance(params, dict) or params.get("type") != "object":
        return f"function.parameters of '{fn['name']}' is not a JSON schema with type 'object'"
    if "properties" in params and not isinstance(params["properties"], dict):
        return f"function.parameters.properties of '{fn['name']}' is not an object"
    return None


def parse_tool_calls(content):
    """Return (calls, reason). calls = [{"name", "arguments"}] when the assistant turn is tool-call
    only; reason explains the first structural problem otherwise."""
    if not _TOOLCALL_BLOCKS.fullmatch(content):
        if "<tool_call>" in content:
            return None, "assistant turn has text outside <tool_call>...</tool_call> blocks"
        return None, "assistant turn is neither <tool_call> blocks nor REFUSAL_VI/DEFLECT_VI"
    calls = []
    for body in _TOOLCALL_BODY.findall(content):
        try:
            call = json.loads(body)
        except json.JSONDecodeError as e:
            return None, f"<tool_call> body is not valid JSON ({e.msg})"
        if not isinstance(call, dict):
            return None, "<tool_call> body is not a JSON object"
        if not isinstance(call.get("name"), str) or not call["name"]:
            return None, "<tool_call> lacks a string 'name'"
        if not isinstance(call.get("arguments"), dict):
            return None, f"<tool_call> '{call['name']}' lacks an object 'arguments'"
        extra = set(call) - {"name", "arguments"}
        if extra:
            return None, f"<tool_call> '{call['name']}' has unexpected keys {sorted(extra)}"
        calls.append(call)
    return calls, None


def validate_row(row, ctx):
    """Return a list of (error_type, detail) for one parsed row. ctx = dict of reference inputs."""
    errors = []
    if not isinstance(row, dict):
        return [("json_invalid", "row is not a JSON object")]

    rid = row.get("id")
    if rid is not None and not isinstance(rid, str):
        errors.append(("id_type", f"'id' must be a string, got {type(rid).__name__}"))

    role = row.get("role")
    if role not in ctx["roles"]:
        errors.append(("role_invalid", f"role={role!r} not in {sorted(ctx['roles'])}"))

    if "replay" in row and not isinstance(row["replay"], bool):
        errors.append(("replay_flag", "'replay' must be a boolean when present"))

    msgs = row.get("messages")
    if not isinstance(msgs, list) or len(msgs) != 3 or not all(isinstance(m, dict) for m in msgs):
        n = len(msgs) if isinstance(msgs, list) else "none"
        errors.append(("messages_shape", f"messages must be a list of exactly 3 objects, got {n}"))
        return errors  # nothing below is meaningful without the 3 turns

    expected_roles = ["system", "user", "assistant"]
    got_roles = [m.get("role") for m in msgs]
    if got_roles != expected_roles:
        errors.append(("roles_order", f"message roles {got_roles} != {expected_roles}"))
        return errors
    for m in msgs:
        c = m.get("content")
        if not isinstance(c, str) or not c.strip():
            errors.append(("content_type", f"{m['role']} content must be a non-empty string"))
    if any(e[0] == "content_type" for e in errors):
        return errors

    if ctx["preamble"] is not None:
        expected = expected_preamble(ctx, role)
        if expected is not None and msgs[0]["content"].strip() != expected:
            errors.append(("preamble_mismatch", preamble_diff_hint(expected, msgs[0]["content"].strip())))

    # Assistant turn: tool calls XOR a fixed reply
    content = msgs[2]["content"]
    calls = []
    if content in ctx["fixed_replies"]:
        pass
    elif content.strip() in ctx["fixed_replies"]:
        errors.append(("assistant_format", "fixed reply has surrounding whitespace; must match exactly"))
    else:
        calls, reason = parse_tool_calls(content)
        if reason:
            errors.append(("assistant_format", reason))
            calls = []

    # Tools: the row's own replay_tools, else the catalogue
    replay_tools = row.get("replay_tools")
    if replay_tools is not None:
        if not isinstance(replay_tools, list) or not replay_tools:
            errors.append(("replay_tools_shape", "'replay_tools' must be a non-empty list"))
        else:
            for i, t in enumerate(replay_tools):
                reason = check_tool_object(t)
                if reason:
                    errors.append(("replay_tools_shape", f"replay_tools[{i}]: {reason}"))
            names = {t["function"]["name"] for t in replay_tools
                     if isinstance(t, dict) and isinstance(t.get("function"), dict) and "name" in t["function"]}
            for call in calls:
                if call["name"] not in names:
                    errors.append(("tool_unknown", f"called '{call['name']}' not in replay_tools {sorted(names)}"))
    elif calls:
        catalogue, policy = ctx["catalogue"], ctx["policy"]
        if catalogue is None:
            errors.append(("tools_required", "row has no replay_tools and --tools was not given"))
        else:
            for call in calls:
                name = call["name"]
                if name not in catalogue:
                    errors.append(("tool_unknown", f"called '{name}' is not in the --tools catalogue"))
                    continue
                unknown_args = set(call["arguments"]) - catalogue[name]
                if unknown_args:
                    errors.append(("arg_unknown", f"'{name}' arguments {sorted(unknown_args)} not in schema "
                                                  f"properties {sorted(catalogue[name])}"))
                if policy is not None and role in ctx["roles"] and role not in policy.get(name, set()):
                    errors.append(("tool_not_offered_to_role",
                                   f"'{name}' is not offered to role '{role}' by {TOOL_POLICY_FILENAME}"))
    return errors


# ── File loop ─────────────────────────────────────────────────────────────────────────────────

def validate_file(path, ctx, max_rows=None):
    """Validate one JSONL file. Returns (n_rows, Counter(error_type), examples{type: [msg]})."""
    counts, examples, seen_ids = Counter(), defaultdict(list), {}
    n_rows = 0

    def record(kind, line_no, rid, detail):
        counts[kind] += 1
        if len(examples[kind]) < EXAMPLES_PER_TYPE:
            examples[kind].append(f"line {line_no} id={rid}: {detail}")

    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            n_rows += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                record("json_invalid", line_no, None, f"invalid JSON: {e.msg}")
                continue
            rid = row.get("id") if isinstance(row, dict) else None
            if isinstance(rid, str):
                if rid in seen_ids:
                    record("id_duplicate", line_no, rid, f"already used at line {seen_ids[rid]}")
                else:
                    seen_ids[rid] = line_no
            for kind, detail in validate_row(row, ctx):
                record(kind, line_no, rid, detail)
            if max_rows is not None and n_rows >= max_rows:
                break
    return n_rows, counts, examples


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Validate training rows against docs/contracts/training_row_format.md "
                    "(exit 1 on any error).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("files", nargs="+", help="one or more JSONL files of training rows")
    p.add_argument("--preamble", default=DEFAULT_PREAMBLE,
                   help="messages[0].content must equal this file (after strip); {role}/{role_vi}/"
                        "{full_name}/{user_id} slots are filled per row the way build_parity_trainset.py does")
    p.add_argument("--no-preamble-check", action="store_true", help="skip the preamble comparison")
    p.add_argument("--tools", default=None,
                   help="tool catalogue JSON; REQUIRED for rows without replay_tools "
                        "(names + argument keys are checked; tool_policy.json beside it adds a role check)")
    p.add_argument("--roles", default=None,
                   help="roles.json with the valid 'role' values (+ 'role_names_vi' for the {role_vi} slot); "
                        "REQUIRED when --preamble has slots; default "
                        + "{" + ", ".join(sorted(DEFAULT_ROLES)) + "}")
    p.add_argument("--fixed-replies", default=DEFAULT_FIXED_REPLIES,
                   help="JSON with REFUSAL_VI and DEFLECT_VI")
    p.add_argument("--max-rows", type=int, default=None, help="check only the first N rows of each file")
    args = p.parse_args(argv)

    fixed_path = resolve_path(args.fixed_replies)
    if not os.path.exists(fixed_path):
        sys.exit(f"ERROR: fixed replies file not found: {args.fixed_replies}")
    roles, role_names_vi = DEFAULT_ROLES, {}
    if args.roles:
        roles_path = resolve_path(args.roles)
        if not os.path.exists(roles_path):
            sys.exit(f"ERROR: roles file not found: {args.roles}")
        roles, role_names_vi = load_roles(roles_path)
    preamble, slots = None, set()
    if not args.no_preamble_check:
        preamble_path = resolve_path(args.preamble)
        if not os.path.exists(preamble_path):
            sys.exit(f"ERROR: preamble file not found: {args.preamble} (or pass --no-preamble-check)")
        preamble = load_preamble(preamble_path)
        slots = preamble_slots(preamble)
        unknown = slots - set(PREAMBLE_SLOTS)
        if unknown:
            sys.exit(f"ERROR: preamble {args.preamble} has unknown slot(s) {sorted(unknown)}; known slots are "
                     f"{list(PREAMBLE_SLOTS)} — no row could ever match it (fix the preamble file)")
        if slots and not args.roles:
            sys.exit(f"ERROR: preamble {args.preamble} has slots {sorted(slots)}; pass --roles tools/sgod/roles.json "
                     "(its 'role_names_vi' fills {role_vi}) so the expected system turn can be rendered per role")
        if slots:
            missing = sorted(r for r in roles if r not in role_names_vi)
            if "role_vi" in slots and missing:
                print(f"WARNING: {args.roles} has no role_names_vi for {missing}; {{role_vi}} falls back to the "
                      "role key (same as build_parity_trainset.py)", file=sys.stderr)
            print(f"preamble {args.preamble}: slots {sorted(slots)} rendered per role with "
                  f"role_names_vi={json.dumps(role_names_vi, ensure_ascii=False)} "
                  f"generic={json.dumps(GENERIC_CONTEXT, ensure_ascii=False)}")
    catalogue = policy = None
    if args.tools:
        tools_path = resolve_path(args.tools)
        if not os.path.exists(tools_path):
            sys.exit(f"ERROR: --tools file not found: {args.tools}")
        catalogue, policy = load_catalogue(tools_path)
    ctx = {"preamble": preamble, "preamble_slots": slots, "role_names_vi": role_names_vi, "preamble_cache": {},
           "fixed_replies": load_fixed_replies(fixed_path), "roles": roles, "catalogue": catalogue, "policy": policy}

    total_rows, total_errors, grand = 0, 0, Counter()
    for path in args.files:
        if not os.path.exists(path):
            print(f"[{path}] ERROR: file not found")
            total_errors += 1
            grand["file_missing"] += 1
            continue
        n_rows, counts, examples = validate_file(path, ctx, args.max_rows)
        n_err = sum(counts.values())
        total_rows += n_rows
        total_errors += n_err
        grand.update(counts)
        print(f"[{path}] rows={n_rows} errors={n_err}")
        for kind, c in counts.most_common():
            print(f"    {kind}: {c}")
            for ex in examples[kind]:
                print(f"        - {ex}")

    if grand:
        print("errors by type (all files): " + ", ".join(f"{k}={v}" for k, v in grand.most_common()))
    status = "PASS" if total_errors == 0 else "FAIL"
    print(f"validate_dataset: {status} files={len(args.files)} rows={total_rows} errors={total_errors}")
    sys.exit(0 if total_errors == 0 else 1)


if __name__ == "__main__":
    main()
