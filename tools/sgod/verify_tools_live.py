#!/usr/bin/env python3
"""[S-V4] Live check of every sgod_tools v1 tool, once per role, with a real JWT (reference infrastructure only).

S Việc 4 checkpoint: every tool in tools/sgod/sgod_tools.json has >= 1 real success:true call for a role that
tool_policy.json allows and >= 1 correct refusal for a role it does not allow. The script:

  * logs in once per role — company_admin = tier `enterprises` (required account), employee = tier
    `enterprise-users` (optional account; without it the employee rows are not run and the report says why) —
    and calls EVERY tool once per role, building each request from the tool's x_sgod block the way the executor
    does: id_params fill the {id} path segment (after the x_sgod.resolve step for asset_ref), every other function
    parameter is passed through as a query parameter of the same name (x_sgod has no rename table);
  * list tools: limit=--limit (5), plus one call per optional filter parameter (search = a word taken from the
    live list's first item; an enum = one of its values, preferring one seen in the data; a boolean = true) and,
    when the first page returns a next cursor, one call for page 2. Detail tools take their id / ref live from the
    matching list call (list_my_assets -> resolve GET /assets?search= -> get_asset / get_asset_histories;
    list_locations -> get_location; list_asset_transfers -> get_asset_transfer; list_maintenance_schedules ->
    get_maintenance_schedule and list_maintenance_tasks). When the source list is empty the route is called with a
    valid but non-existent ObjectId and classified "route OK, không có dữ liệu" (envelope success:false with a
    not-found message) vs "route MISSING" (gateway "Cannot GET");
  * records per (tool, role, call): method + path template, query KEYS (never values), HTTP status, body.success,
    body.statusCode, data shape, field names (of data, or of the first item of a list) and a note. It branches on
    body.success, never on the HTTP status (the gateway returns HTTP 200 for errors, spec §1/§4);
  * audits tool_policy.json offline (reusing validate_tools.py): no company/tenant/enterprise id parameter, every
    /sgod-chat tool owner-only, none of the removed / broken routes, read-only, refusal matrix Layer 1 + Layer 2;
  * writes a Vietnamese Markdown report (default docs/sgod/tools_v1_live_check.md).

READ-ONLY: every request is checked before it is sent — tool calls must be GET; the only POSTs allowed are login
(POST /sgod-auth/v1/<tier>/sessions) and session refresh (POST /sgod-auth/v1/sessions/refresh). Redirects are never
followed (urllib would resend x-api-key / Authorization to the host named by Location): a 30x is recorded as is.

Credentials come ONLY from the environment (names as .env.example); they are never printed or written:
  SGOD_BASE_URL, SGOD_AUTH_API_KEY, SGOD_ASSET_API_KEY, SGOD_CHAT_API_KEY      (required)
  SGOD_ENTERPRISE_EMAIL, SGOD_ENTERPRISE_PASSWORD                             (required: company_admin)
  SGOD_EUSER_EMAIL, SGOD_EUSER_PASSWORD                                       (optional: employee)
SGOD_BASE_URL must be http(s)://<host>[:port]; CR/LF left by a CRLF .env is stripped from every value.
Output guard, three layers: (1) the report and the API-derived console lines go through the capture_fixtures.py
Masker (known secrets — API keys, passwords, login e-mails, tokens — become <redacted>, the gateway address
<SGOD_GATEWAY>) and scrub_text (URLs, JWT pieces, host:port, internal host names, e-mails, IPv4, VN phones);
(2) during a live run sys.stdout / sys.stderr are line-filtered by scrub_text, and every transport or unexpected
exception is reported by type name and code location only, never by its message (it may hold the URL or a header
value); (3) Masker.leaks then refuses to write a report that still holds an e-mail, a phone number, a JWT, an IP or
the gateway (nothing is written, exit 2). Query values (search words, ids, cursors) stay in memory; only query keys
are recorded.

Usage:
  python tools/sgod/verify_tools_live.py --dry-run                 # plan + offline audit: no env, no network
  set -a; . ./.env; set +a                                          # reference infrastructure only
  python tools/sgod/verify_tools_live.py [--out docs/sgod/tools_v1_live_check.md] [--limit 5]

Exit: 0 = every call for an allowed role passed and the offline audit is clean; 1 = at least one failure (the
report is still written); 2 = refused to run or aborted (missing / malformed env, failed company_admin login,
read-only or leak guard, unexpected error); nothing is written.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture_fixtures as cf  # noqa: E402  gateway, login, JWT TTL and the secret / PII guard (Masker)
import validate_tools as vt  # noqa: E402  catalogue checks, spec §4 blocklist, tools_for_role (Layer 1)

DEFAULT_OUT = "docs/sgod/tools_v1_live_check.md"
DEVICE_ID = "chatsystem-tools-v1-verify"
NONEXISTENT_OID = "0" * 24  # valid ObjectId syntax that matches no document
REFRESH_PATH = "/sgod-auth/v1/sessions/refresh"
REQUIRED_ENV = ("SGOD_BASE_URL", "SGOD_AUTH_API_KEY", "SGOD_ASSET_API_KEY", "SGOD_CHAT_API_KEY",
                "SGOD_ENTERPRISE_EMAIL", "SGOD_ENTERPRISE_PASSWORD")
OPTIONAL_ENV = ("SGOD_EUSER_EMAIL", "SGOD_EUSER_PASSWORD")
# role, login tier (a key of roles.json "tiers"), e-mail env, password env, required account?
ACCOUNTS = (
    ("company_admin", "enterprises", "SGOD_ENTERPRISE_EMAIL", "SGOD_ENTERPRISE_PASSWORD", True),
    ("employee", "enterprise-users", "SGOD_EUSER_EMAIL", "SGOD_EUSER_PASSWORD", False),
)
# Detail / child tool -> (list tool called earlier for the same role, field of its FIRST item that feeds the call).
ID_SOURCES = {
    "get_asset": ("list_my_assets", "assetCode"),          # resolve GET /assets?search=<asset code> -> /assets/{id}
    "get_asset_histories": ("list_my_assets", "name"),     # resolve GET /assets?search=<asset name> -> .../histories
    "get_maintenance_schedule": ("list_maintenance_schedules", "id"),
    "list_maintenance_tasks": ("list_maintenance_schedules", "id"),  # -> query maintenanceScheduleId
    "get_asset_transfer": ("list_asset_transfers", "id"),
    "get_location": ("list_locations", "id"),
}
# Extra call that checks a description claim: get_location says its id may come from get_asset's result.
CHAIN_SOURCES = {"get_location": "get_asset"}
# Removed or broken routes (spec §4 + live calls 2026-10-14): a path equal to one of these, or below it, is refused.
REMOVED_ROUTES = ("/sgod-asset/v1/assets/suggest", "/sgod-asset/v1/dashboard/*", "/sgod-asset/v1/import-export/exports",
                  "/sgod-asset/v1/asset-offers", "/sgod-asset/v1/categories-offer")
LIST_KEYS = ("items", "users", "conversations")
PAGING_KEYS = {"meta", "nextCursor", "total", "page", "limit", "hasNextPage", "pagination"}

V_OK, V_WARN, V_NODATA, V_MISSING = "OK", "OK ⚠", "route OK, không có dữ liệu", "route MISSING"
V_FAIL, V_DENIED, V_SKIP, V_INFO = "LỖI", "CHẶN (policy)", "BỎ QUA", "tham khảo"
KIND_VI = {"not_found": "không tìm thấy", "route_missing": "route không tồn tại", "bad_request": "400 tham số",
           "unauthorized": "401", "forbidden": "403", "server_error": "lỗi server", "error": "lỗi"}


# Generic redaction under the Masker guard (same e-mail / IPv4 / phone / JWT patterns as Masker.leaks).
EMAIL_RE = re.compile(r"[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}")
IPV4_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
VN_PHONE_RE = re.compile(r"(?:\+84|\b0)[35789]\d{8}\b")
JWTISH_RE = re.compile(r"eyJ[\w-]{6,}(?:\.[\w-]*)*")  # a JWT or any piece of one (a truncated echo keeps no 2nd dot)
URL_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s'\"<>]*")
HOSTPORT_RE = re.compile(r"\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+:\d{2,5}\b")
INTERNAL_HOST_RE = re.compile(r"\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:internal|local|lan|corp|intra|svc|private)\b")


class ReadOnlyViolation(RuntimeError):
    """A request that is neither a GET nor an allowed login / refresh POST. It is never sent."""


def scrub_text(s: str, secrets=(), hosts=()) -> str:
    """Replace known secret values, the gateway address, URLs, JWT pieces, host:port pairs, internal host names,
    e-mails (except the @example.com fakes), IPv4 addresses (except the capture_fixtures "ip" fakes) and VN phones."""
    for sec in sorted({x for x in secrets if isinstance(x, str) and x}, key=len, reverse=True):
        s = s.replace(sec, "<redacted>")
    for h in sorted({x for x in hosts if isinstance(x, str) and x}, key=len, reverse=True):
        s = s.replace(h, "<SGOD_GATEWAY>")
    s = URL_RE.sub("<url>", s)
    s = JWTISH_RE.sub("<redacted-token>", s)
    s = EMAIL_RE.sub(lambda m: m.group(0) if m.group(0).endswith("@example.com") else "<email>", s)
    s = HOSTPORT_RE.sub("<host:port>", s)
    s = INTERNAL_HOST_RE.sub("<host>", s)
    s = IPV4_RE.sub(lambda m: m.group(0) if m.group(0).startswith("203.0.113.") else "<ip>", s)
    return VN_PHONE_RE.sub("<phone>", s)


class RedactingStream(io.TextIOBase):
    """Line-buffered stand-in for sys.stdout / sys.stderr during a live run: every line passes through `scrub`
    before it reaches the terminal, so print()s, warnings and tracebacks alike never show a secret or the gateway."""

    def __init__(self, inner, scrub) -> None:
        super().__init__()
        self._inner, self._scrub, self._buf = inner, scrub, ""

    @property
    def encoding(self):
        return getattr(self._inner, "encoding", "utf-8")

    def writable(self) -> bool:
        return True

    def isatty(self) -> bool:
        return self._inner.isatty()

    def write(self, s: str) -> int:
        self._buf += s
        *lines, self._buf = self._buf.split("\n")
        for line in lines:
            self._inner.write(self._scrub(line) + "\n")
        return len(s)

    def flush(self) -> None:  # a partial line stays buffered: a value is never split across two scrub calls
        self._inner.flush()

    def drain(self) -> None:
        if self._buf:
            self._inner.write(self._scrub(self._buf) + "\n")
            self._buf = ""
        self._inner.flush()


def valid_base_url(base: str) -> bool:
    try:
        u = urllib.parse.urlsplit(base)
        return (u.scheme in ("http", "https") and bool(u.hostname) and u.username is None
                and (u.port is None or u.port > 0) and not u.query and not u.fragment)
    except ValueError:  # e.g. a non-numeric port
        return False


def gateway_hosts(base: str) -> list[str]:
    """Every spelling of the gateway address that may show up in text (URL, host:port, bare host), longest first."""
    u = urllib.parse.urlsplit(base)
    hosts = {base, u.netloc, u.hostname or ""}
    if u.hostname and u.port:
        hosts.add(f"{u.hostname}:{u.port}")
    return sorted((h for h in hosts if h), key=len, reverse=True)


def where(e: BaseException) -> str:
    """Code location of an exception — innermost frame, plus the deepest frame in tools/sgod/ when that differs —
    never its message (it may hold a URL or a value). No "file:line" form: scrub_text would read it as host:port."""
    frames = traceback.extract_tb(e.__traceback__)
    if not frames:
        return "?"
    fmt = lambda f: f"{os.path.basename(f.filename)} dòng {f.lineno} ({f.name})"  # noqa: E731
    here = Path(__file__).resolve().parent
    own = [f for f in frames if Path(f.filename).resolve().parent == here]
    return fmt(frames[-1]) + (f" ← {fmt(own[-1])}" if own and own[-1] is not frames[-1] else "")


# ── catalogue helpers (shared by --dry-run and the live run) ──────────────────────────────────────────────
def authorize(policy: dict, role: str, tool: str) -> bool:
    """Layer 2 (authorize_tool_call): allowed iff role ∈ tool_policy.json[tool].roles; an unknown tool is denied."""
    entry = policy.get(tool)
    return isinstance(entry, dict) and role in (entry.get("roles") or [])


def require_get(name: str, x: dict) -> None:
    if x.get("method") != "GET" or x.get("writes") is not False:
        raise ReadOnlyViolation(f"tool {name}: x_sgod.method={x.get('method')!r} writes={x.get('writes')!r} "
                                f"— this script only calls read-only GET tools")


def parse_resolve(x: dict):
    """(method, path, query key, placeholder param) of x_sgod.resolve, or None (malformed -> None; validate_tools flags it)."""
    m = vt.RESOLVE_RE.match(x.get("resolve") or "")
    return m.groups() if m else None


def removed_route(path: str) -> str | None:
    for r in REMOVED_ROUTES:
        base = r[:-2] if r.endswith("/*") else r
        if path == base or path.startswith(base + "/"):
            return r
    return None


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class Step:
    kind: str                 # resolve | main | enum | bool | search | cursor | chain
    call: str                 # label shown in the plan / table
    path: str                 # path template
    query: dict               # query key -> description of the value (dry-run); live values stay in memory
    param: str | None = None
    id_desc: str = ""


def build_steps(t: dict, limit: int) -> list[Step]:
    """The calls made for one tool (per role). The live run executes exactly these steps."""
    fn, x = t["function"], t["x_sgod"]
    name = fn["name"]
    params = fn.get("parameters") or {}
    props = params.get("properties") or {}
    required = [p for p in (params.get("required") or []) if p in props]
    id_params = set(x.get("id_params") or [])
    src = ID_SOURCES.get(name)
    src_desc = f"mục đầu {src[0]}" if src else "nguồn chưa khai báo"
    base: dict = {}
    if "limit" in props:
        base["limit"] = str(limit)
    for p in required:
        if p not in id_params:
            base[p] = f"<id {src_desc}>"
    steps = []
    res = parse_resolve(x)
    if res:
        steps.append(Step("resolve", "resolve", res[1], {res[2]: f"<{src[1] if src else res[3]} của {src_desc}>"}))
    id_desc = ""
    if "{" in x["path"]:
        id_desc = "id = mục khớp của resolve" if res else f"id = {src_desc}"
    steps.append(Step("main", "chính", x["path"], dict(base), id_desc=id_desc))
    for p, sch in props.items():
        if p in ("limit", "cursor") or p in id_params or p in required or not isinstance(sch, dict):
            continue
        if sch.get("enum"):
            steps.append(Step("enum", f"{p}=<enum>", x["path"], {**base, p: "<giá trị enum thấy trong lượt chính, "
                                                                             "nếu không: giá trị đầu>"}, param=p))
        elif sch.get("type") == "boolean":
            steps.append(Step("bool", f"{p}=true", x["path"], {**base, p: "true"}, param=p))
        elif sch.get("type") == "string":
            steps.append(Step("search", p, x["path"], {**base, p: "<từ dài nhất trong mục đầu của lượt chính>"}, param=p))
    if "cursor" in props:
        steps.append(Step("cursor", "cursor", x["path"], {**base, "cursor": "<nextCursor của lượt chính, nếu có>"}))
    if name in CHAIN_SOURCES:
        steps.append(Step("chain", f"id từ {CHAIN_SOURCES[name]}", x["path"], {},
                          id_desc=f"id = phần tử đầu của asset.locations trong {CHAIN_SOURCES[name]}"))
    return steps


def needs_value(t: dict) -> bool:
    """True when the call needs an id / ref: a {param} path segment or a required non-path parameter."""
    fn, x = t["function"], t["x_sgod"]
    params = fn.get("parameters") or {}
    id_params = set(x.get("id_params") or [])
    return "{" in x["path"] or any(p not in id_params for p in (params.get("required") or []))


def exec_order(tools: list) -> list[int]:
    """Source lists first, then get_asset (it feeds get_location), then the rest — catalogue order otherwise."""
    sources = {s for s, _ in ID_SOURCES.values()}
    chains = set(CHAIN_SOURCES.values())

    def prio(i: int) -> int:
        n = tools[i]["function"]["name"]
        return 0 if n in sources else (1 if n in chains else 2)
    return sorted(range(len(tools)), key=lambda i: (prio(i), i))


# ── response helpers ──────────────────────────────────────────────────────────────────────────────────────
def unwrap_list(data):
    """(list key, items) when data is a list response ('' for a bare list), else (None, None)."""
    if isinstance(data, list):
        return "", data
    if not isinstance(data, dict):
        return None, None
    for k in LIST_KEYS:
        if isinstance(data.get(k), list):
            return k, data[k]
    if set(data) & PAGING_KEYS:
        lists = [k for k, v in data.items() if isinstance(v, list)]
        if len(lists) == 1:
            return lists[0], data[lists[0]]
    return None, None


def keys_of(d: dict) -> list[str]:
    """Sorted field names; ObjectId-looking keys (maps keyed by id) collapse into one '<ObjectId>×N' entry."""
    ks = [str(k) for k in d]
    out = sorted(k for k in ks if not cf.OID.match(k))
    n_oid = len(ks) - len(out)
    return out + ([f"<ObjectId>×{n_oid}"] if n_oid else [])


def fields_of(d: dict) -> list[str]:
    """Field names, one nesting level shown for object values: fullName{firstName,lastName}."""
    out = []
    for k in keys_of(d):
        v = d.get(k)
        out.append(f"{k}{{{','.join(keys_of(v))}}}" if isinstance(v, dict) and v else k)
    return out


def describe(data) -> tuple[str, list[str]]:
    """(shape, field names): object / list n=K / paginated <key> n=K + paging keys; fields of data or of item 0."""
    if data is None:
        return "null", []
    key, items = unwrap_list(data)
    if items is not None:
        first = items[0] if items else None
        fields = fields_of(first) if isinstance(first, dict) else []
        if key == "":
            return f"list n={len(items)}", fields
        extras = []
        for k in keys_of(data):
            if k == key:
                continue
            v = data.get(k)
            extras.append(f"{k}{{{','.join(keys_of(v))}}}" if isinstance(v, dict) else k)
        return f"paginated {key} n={len(items)}" + (f" + {', '.join(extras)}" if extras else ""), fields
    if isinstance(data, dict):
        if len(data) == 1:
            (k, v), = data.items()
            if isinstance(v, dict):
                return f"object (bọc trong {k})", fields_of(v)
        return "object", fields_of(data)
    return type(data).__name__, []


def item_ids(items) -> list[str]:
    return [str(it.get("id")) for it in (items or []) if isinstance(it, dict) and it.get("id")]


def next_cursor(data) -> str | None:
    if not isinstance(data, dict):
        return None
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    for c in (meta.get("nextCursor"), data.get("nextCursor")):
        if isinstance(c, str) and c:
            return c
    return None


def has_cursor_field(data) -> bool:
    return isinstance(data, dict) and ("nextCursor" in data or
                                       (isinstance(data.get("meta"), dict) and "nextCursor" in data["meta"]))


def all_strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from all_strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from all_strings(v)


def search_word(item) -> str | None:
    """The longest word (>= 3 chars) of the first item's name-like field. Kept in memory only."""
    if not isinstance(item, dict):
        return None
    for k in ("name", "title", "userName", "fullName", "assetCode"):
        v = item.get(k)
        if isinstance(v, dict):
            v = " ".join(s for s in v.values() if isinstance(s, str))
        words = [w for w in re.findall(r"\w[\w-]*", v) if len(w) >= 3 and not cf.OID.match(w)] if isinstance(v, str) else []
        if words:
            return max(words, key=len)
    return None


def pick_enum(enum: list, items, param: str):
    seen = {it.get(param) for it in (items or []) if isinstance(it, dict)}
    return next((v for v in enum if v in seen), enum[0])


def pick_match(items, ref: str):
    """Item of a resolve response that matches ref exactly (assetCode / name / id), plus a note without values."""
    r = ref.strip().lower()
    exact = [it for it in items if isinstance(it, dict) and r in {str(it.get("assetCode", "")).lower(),
                                                                   str(it.get("name", "")).strip().lower(),
                                                                   str(it.get("id", "")).lower()}]
    if exact:
        extra = " (trùng tên — lấy mục đầu)" if len(exact) > 1 else ""
        return exact[0], f"resolve: {len(items)} kết quả, {len(exact)} khớp chính xác{extra}"
    if len(items) == 1:
        return items[0], "resolve: 1 kết quả, không khớp chính xác — lấy mục đó"
    return None, f"resolve: {len(items)} kết quả, không mục nào khớp chính xác"


def api_text(body: dict) -> str:
    """error / message of an envelope on one line, without query strings, ObjectIds, URLs, host names, e-mails, IPs,
    phones or JWT pieces (scrubbed BEFORE the cut, so a truncated value cannot slip through), at most 140 chars."""
    parts = []
    for k in ("error", "message"):
        v = body.get(k)
        if isinstance(v, (list, dict)):
            v = "; ".join(str(s) for s in (v if isinstance(v, list) else v.values()))
        if v:
            parts.append(str(v))
    s = " | ".join(dict.fromkeys(parts))
    s = re.sub(r"\?\S*", "", s)
    s = re.sub(r"\b[0-9a-f]{24}\b", "<id>", s)
    return " ".join(scrub_text(s).split())[:140]


def classify(status, body, err) -> tuple[str, str]:
    """ok | not_found | route_missing | bad_request | unauthorized | forbidden | server_error | error (+ API text).

    Decides on body.success, never on the HTTP status: the gateway returns HTTP 200 for errors (spec §1, §4).
    """
    if body is None:
        return "error", err or "không có body"
    if not isinstance(body, dict) or "success" not in body:
        return "error", "body không có trường success"
    if body.get("success") is True:
        return "ok", ""
    text = api_text(body)
    sc = body.get("statusCode")
    if "Cannot GET" in text:  # Express / Nest default 404: no route at all
        return "route_missing", text
    if sc == 404 or "not found" in text.lower() or "NOT_FOUND" in text:
        return "not_found", text
    for code, kind in ((401, "unauthorized"), (403, "forbidden"), (400, "bad_request")):
        if sc == code or status == code:
            return kind, text
    if (isinstance(sc, int) and sc >= 500) or (isinstance(status, int) and status >= 500):
        return "server_error", text
    return "error", text


def qv(v):
    """Query value as the API expects it: booleans as lowercase strings (urlencode(True) would send 'True')."""
    return ("true" if v else "false") if isinstance(v, bool) else v


# ── live run ──────────────────────────────────────────────────────────────────────────────────────────────
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Hand a 30x back as the response instead of following it: urllib would resend x-api-key and Authorization to
    whatever host the Location header names."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ReadOnlyGateway(cf.Gateway):
    """capture_fixtures.Gateway hardened for a run whose output is published: refuses, before sending, anything but
    GET and the login / refresh POSTs; never follows a redirect; strips CR/LF and blanks around SGOD_BASE_URL and the
    API keys (a CRLF .env would make http.client raise an error whose message holds the header value); reduces every
    transport exception to its type name (a message may hold the URL or a header value)."""
    device_id = DEVICE_ID

    def __init__(self, tiers) -> None:
        super().__init__()
        self.base = self.base.strip().rstrip("/")
        self.keys = {k: v.strip() for k, v in self.keys.items()}
        self.allowed_posts = {f"/sgod-auth/v1/{t}/sessions" for t in tiers} | {REFRESH_PATH}
        self.counts = {"GET": 0, "login": 0, "refresh": 0}
        self._opener = urllib.request.build_opener(_NoRedirect())

    def call(self, method, path, query=None, token=None, body=None):
        if method == "GET" and body is None:
            self.counts["GET"] += 1
        elif method == "POST" and path in self.allowed_posts:
            self.counts["refresh" if path == REFRESH_PATH else "login"] += 1
        else:
            raise ReadOnlyViolation(f"{method} {path}: only GET tool calls and the login / session-refresh POSTs "
                                    f"are allowed")
        try:
            return self._send(method, path, query, token, body)
        except Exception as e:  # noqa: BLE001 — type name only, never str(e)
            return None, None, f"network error: {type(e).__name__}"

    def _send(self, method, path, query, token, body):
        """capture_fixtures.Gateway.call, through this gateway's own opener (no redirect handling)."""
        url = self.base + path + (("?" + urllib.parse.urlencode(query)) if query else "")
        headers = {"Accept": "application/json", "x-api-key": self.key_for(path), "x-device-id": self.device_id}
        if token:
            headers["Authorization"] = "Bearer " + token
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=30) as r:
                status, raw = r.status, r.read()
        except urllib.error.HTTPError as e:  # 4xx / 5xx still carry the gateway envelope; a 30x lands here too
            status, raw = e.code, e.read()
        if 300 <= status < 400:
            return status, None, f"HTTP {status} redirect (not followed)"
        try:
            return status, json.loads(raw.decode("utf-8")), None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return status, None, f"non-JSON body ({len(raw)} B)"


def safe_print(masker, line: str) -> None:
    """Console output through the capture_fixtures guard (a line that fails is replaced, never printed)."""
    if [f for f in masker.leaks(line) if not f.startswith("unmasked-")]:
        line = "  (dòng log bị ẩn: không qua được kiểm tra rò rỉ)"
    print(line, flush=True)


class Session:
    """One role's JWT: login, silent renewal near expiry (refresh, else a new login), GET with one retry on 401."""

    def __init__(self, gw: ReadOnlyGateway, masker, role: str, tier: str, email: str, password: str) -> None:
        self.gw, self.masker, self.role, self.tier = gw, masker, role, tier
        self._email, self._password = email, password
        self.token = self.refresh_token = None

    def login(self) -> str | None:
        access, refresh, why = self.gw.try_login(self.tier, self._email, self._password)
        if why:
            return why
        self.token, self.refresh_token = access, refresh
        self.masker.secrets += [s for s in (access, refresh) if isinstance(s, str) and s]
        return None

    def _near_expiry(self) -> bool:
        exp, _ = cf.jwt_ttl(self.token or "")
        return exp is None or exp - time.time() < 60

    def _renew(self) -> bool:
        if self.refresh_token:
            _, body, _ = self.gw.call("POST", REFRESH_PATH, body={"refreshToken": self.refresh_token})
            data = (body.get("data") or {}) if isinstance(body, dict) else {}
            if isinstance(body, dict) and body.get("success") and isinstance(data, dict) and data.get("accessToken"):
                self.token = data["accessToken"]
                self.refresh_token = data.get("refreshToken") or self.refresh_token
                self.masker.secrets += [s for s in (self.token, self.refresh_token) if isinstance(s, str) and s]
                return True
        return self.login() is None

    def get(self, path: str, query: dict):
        exp, _ = cf.jwt_ttl(self.token or "")
        if exp is not None and exp - time.time() < 60:
            self._renew()
        status, body, err = self.gw.call("GET", path, query or None, self.token)
        unauthorized = status == 401 or (isinstance(body, dict) and body.get("success") is False
                                          and body.get("statusCode") == 401)
        if unauthorized and self._near_expiry() and self._renew():  # expired token: renew once and retry
            status, body, err = self.gw.call("GET", path, query or None, self.token)
        return status, body, err


@dataclass
class Row:
    idx: int
    tool: str
    role: str
    allowed: bool
    call: str
    path: str
    query_keys: list
    seq: int = 0
    http: object = None
    success: object = None
    status_code: object = None
    shape: str = "—"
    fields: list = field(default_factory=list)
    verdict: str = ""
    note: str = ""           # this script's own words (static vocabulary, counts, enum values)
    api_note: str = ""       # text that came from the API (masked; also checked by the name guard)
    fail: bool = False
    warn: bool = False
    real_success: bool = False


class Runner:
    def __init__(self, sess: Session, tools: list, policy: dict, limit: int) -> None:
        self.sess, self.tools, self.policy, self.limit = sess, tools, policy, limit
        self.rows: list[Row] = []
        self.cache: dict[str, dict] = {}  # tool -> {"ok", "first", "items", "ids", "data"} of its main call

    def _row(self, idx: int, name: str, allowed: bool, step: Step, path: str, keys: list) -> Row:
        row = Row(idx, name, self.sess.role, allowed, step.call, path, keys, seq=len(self.rows))
        self.rows.append(row)
        return row

    def _get(self, row: Row, real_path: str, query: dict):
        status, body, err = self.sess.get(real_path, {k: qv(v) for k, v in query.items()})
        masked = self.sess.masker.mask(body) if body is not None else None  # also teaches the masker every PII value
        kind, text = classify(status, masked, err)
        row.http = status
        if isinstance(body, dict):  # only a bool / a 3-digit code is echoed: these land in the report and the console
            s, sc = body.get("success"), body.get("statusCode")
            row.success = s if s is None or isinstance(s, bool) else "?"
            row.status_code = int(sc) if re.fullmatch(r"\d{3}", str(sc)) else (None if sc is None else "?")
        data = body.get("data") if isinstance(body, dict) else None
        if kind == "ok":
            row.shape, row.fields = describe(data)
        elif text:
            row.api_note = text
        safe_print(self.sess.masker, f"  [{self.sess.role}] {row.tool} · {row.call}: GET {row.path} "
                                     f"keys={','.join(row.query_keys) or '—'} -> http {status} success={row.success} "
                                     f"statusCode={row.status_code} {row.shape}")
        return kind, data

    def run(self) -> None:
        for idx in exec_order(self.tools):
            try:
                self.run_tool(idx)
            except ReadOnlyViolation:
                raise
            except Exception as e:  # noqa: BLE001 — one tool's unexpected data must not end the run; never str(e)
                name = self.tools[idx]["function"]["name"]
                row = Row(idx, name, self.sess.role, authorize(self.policy, self.sess.role, name), "—",
                          str(self.tools[idx]["x_sgod"].get("path", "")), [], seq=len(self.rows))
                row.verdict, row.fail = V_FAIL, True
                row.note = f"lỗi trong script: {type(e).__name__} tại {where(e)}"
                self.rows.append(row)
                print(f"  [{self.sess.role}] {name}: {row.note}", flush=True)

    def run_tool(self, idx: int) -> None:  # noqa: C901 — one linear script per tool reads best here
        t = self.tools[idx]
        fn, x = t["function"], t["x_sgod"]
        name = fn["name"]
        require_get(name, x)
        allowed = authorize(self.policy, self.sess.role, name)
        props = (fn.get("parameters") or {}).get("properties") or {}
        id_params = set(x.get("id_params") or [])
        req_query = [p for p in ((fn.get("parameters") or {}).get("required") or []) if p not in id_params]
        src = ID_SOURCES.get(name)
        ref, probe, src_note = None, False, ""
        if needs_value(t):
            src_entry = self.cache.get(src[0]) if src else None
            first = (src_entry or {}).get("first")
            if isinstance(first, dict):
                v = first.get(src[1]) or (first.get("name") if src[1] == "assetCode" else None)
                ref = v if isinstance(v, str) and v.strip() else None
            if ref is None:
                probe = True
                if not src:
                    src_note = "chưa khai báo nguồn id → gọi bằng ObjectId không tồn tại"
                elif (src_entry or {}).get("ok"):
                    src_note = (f"mục đầu {src[0]} thiếu trường `{src[1]}`" if isinstance(first, dict)
                                else f"nguồn rỗng ({src[0]} không có mục)") + " → gọi bằng ObjectId hợp lệ không tồn tại"
                else:
                    src_note = f"nguồn không dùng được ({src[0]} lỗi) → gọi bằng ObjectId hợp lệ không tồn tại"
            else:
                src_note = f"{'ref' if x.get('resolve') else 'id'} lấy từ mục đầu {src[0]}" + (
                    f" ({src[1]})" if src[1] != "id" else "")
        target_id = NONEXISTENT_OID if probe else (ref if not x.get("resolve") else None)
        base_q = {"limit": self.limit} if "limit" in props else {}
        for p in req_query:  # e.g. maintenanceScheduleId: the source id, or the non-existent ObjectId
            base_q[p] = NONEXISTENT_OID if probe else ref
        main = {"ok": False, "items": None, "ids": [], "data": None}

        for step in build_steps(t, self.limit):
            if not allowed and step.kind not in ("resolve", "main"):
                continue  # a refused role gets the main call only: evidence of what SGOD itself returns
            if step.kind == "resolve":
                if probe:
                    continue  # nothing to resolve: the main call goes straight to the non-existent id
                key = next(iter(step.query))
                row = self._row(idx, name, allowed, step, step.path, [key])
                kind, data = self._get(row, step.path, {key: ref})
                if kind != "ok":
                    row.verdict, row.fail = V_FAIL, allowed
                    row.note = f"resolve lỗi ({KIND_VI.get(kind, kind)})"
                    continue
                _, items = unwrap_list(data)
                hit, how = pick_match(items or [], ref)
                row.note = how
                if hit is None or not cf.OID.match(str(hit.get("id", ""))):
                    row.verdict, row.fail = V_FAIL, allowed
                else:
                    row.verdict, target_id = V_OK, str(hit["id"])
                continue

            if step.kind == "main":
                keys = list(step.query)
                row = self._row(idx, name, allowed, step, step.path, keys)
                if "{" in step.path and target_id is None:
                    row.verdict, row.fail, row.note = V_SKIP, allowed, "không có id (resolve không ra id)"
                    continue
                real_path = (re.sub(r"\{[^/{}]+\}", urllib.parse.quote(target_id, safe=""), step.path)
                             if "{" in step.path else step.path)
                kind, data = self._get(row, real_path, dict(base_q))
                notes = [src_note] if src_note else []
                if not allowed:
                    row.verdict = V_DENIED
                    notes.append("SGOD trả success:true — chỉ policy của chat chặn" if kind == "ok"
                                 else f"SGOD cũng từ chối ({KIND_VI.get(kind, kind)})")
                elif probe:
                    if kind == "route_missing":
                        row.verdict, row.fail = V_MISSING, True
                    elif kind in ("not_found", "ok"):
                        row.verdict = V_NODATA
                        if kind == "ok":
                            notes.append("success:true với id không tồn tại")
                    else:  # 400 / 401 / 403 / 5xx / no envelope: the route answered, but not with "not found"
                        row.verdict, row.fail = V_FAIL, True
                        notes.append(f"id không tồn tại nhưng API không trả 'không tìm thấy' ({KIND_VI.get(kind, kind)})")
                elif kind == "ok":
                    row.verdict, row.real_success = V_OK, True
                elif kind == "route_missing":
                    row.verdict, row.fail = V_MISSING, True
                else:
                    row.verdict, row.fail = V_FAIL, True
                if kind == "ok":
                    _, items = unwrap_list(data)
                    main.update(ok=True, data=data, items=items, ids=item_ids(items))
                    if allowed and not probe and items is not None and "limit" in props and len(items) > self.limit:
                        row.warn = True
                        notes.append(f"n > limit={self.limit} → nghi API bỏ qua `limit`")
                    if allowed and not probe and "cursor" in props and items is not None and not next_cursor(data):
                        if has_cursor_field(data):
                            notes.append("hết trang (nextCursor rỗng) — không gọi trang 2")
                        else:
                            row.warn = True
                            notes.append("phản hồi không có nextCursor → tham số `cursor` không lấy được từ kết quả")
                    if allowed and name == "get_my_permissions" and isinstance(data, dict) and not data.get("id"):
                        row.verdict, row.fail, row.real_success = V_FAIL, True, False
                        notes.append("data.id rỗng — JWT không được nhận (endpoint trả 200 + id rỗng khi thiếu JWT)")
                    for k in ("userType", "belong"):
                        v = data.get(k) if isinstance(data, dict) else None
                        if isinstance(v, str) and re.fullmatch(r"[A-Za-z_]{2,32}", v):
                            row.api_note = (row.api_note + "; " if row.api_note else "") + f"{k}={v}"
                if allowed and row.verdict == V_OK and row.warn:
                    row.verdict = V_WARN
                row.note = "; ".join(n for n in notes if n)
                self.cache[name] = {"ok": kind == "ok" and not probe, "items": main["items"], "data": main["data"],
                                    "ids": main["ids"],
                                    "first": (main["items"] or [None])[0] if isinstance(main["items"], list) else None}
                continue

            if not main["ok"] or probe:
                continue  # filters / paging only make sense on a successful call over real data
            if step.kind in ("enum", "bool", "search"):
                p = step.param
                if step.kind == "search":
                    value = search_word((main["items"] or [None])[0] if main["items"] else None)
                    if value is None:
                        continue  # no item to take a word from (empty list)
                    label = f"{p}=<từ khoá>"
                elif step.kind == "enum":
                    value = pick_enum(props[p]["enum"], main["items"], p)
                    label = f"{p}={value}"
                else:
                    value, label = True, f"{p}=true"
                step = Step(step.kind, label, step.path, step.query, p)
                q = {**base_q, p: value}
                row = self._row(idx, name, allowed, step, step.path, list(q))
                kind, data = self._get(row, step.path, q)
                if kind != "ok":
                    row.verdict, row.fail = V_FAIL, True
                    row.note = f"giá trị bị từ chối ({KIND_VI.get(kind, kind)})"
                    continue
                _, items = unwrap_list(data)
                row.warn, row.note = filter_note(step.kind, p, value, items, main["ids"])
                row.verdict = V_WARN if row.warn else V_OK
                continue

            if step.kind == "cursor":
                cur = next_cursor(main["data"])
                if not cur:
                    continue
                q = {**base_q, "cursor": cur}
                row = self._row(idx, name, allowed, step, step.path, list(q))
                kind, data = self._get(row, step.path, q)
                if kind != "ok":
                    row.verdict, row.fail, row.note = V_FAIL, True, f"trang 2 lỗi ({KIND_VI.get(kind, kind)})"
                    continue
                _, items = unwrap_list(data)
                ids2 = item_ids(items)
                overlap = len(set(ids2) & set(main["ids"]))
                if ids2 and overlap == len(ids2):
                    row.verdict, row.warn = V_WARN, True
                    row.note = f"trang 2 trùng hoàn toàn trang 1 ({overlap} mục) → nghi API bỏ qua `cursor`"
                else:
                    row.verdict = V_OK
                    row.note = f"trang 2: {len(ids2)} mục, trùng trang 1: {overlap}"
                continue

            if step.kind == "chain":
                src_data = (self.cache.get(CHAIN_SOURCES[name]) or {}).get("data")
                asset = src_data.get("asset") if isinstance(src_data, dict) else None
                locs = asset.get("locations") if isinstance(asset, dict) else None
                loc = locs[0] if isinstance(locs, list) and locs else None
                loc = loc.get("id") if isinstance(loc, dict) else loc
                if not (isinstance(loc, str) and cf.OID.match(loc)):
                    continue
                row = self._row(idx, name, allowed, step, step.path, [])
                kind, data = self._get(row, re.sub(r"\{[^/{}]+\}", loc, step.path), {})
                if kind == "ok":
                    row.verdict, row.note = V_OK, "id trong asset.locations của get_asset tra được bằng get_location"
                else:
                    row.verdict = V_INFO
                    row.note = (f"id trong asset.locations của get_asset KHÔNG tra được bằng get_location "
                                f"({KIND_VI.get(kind, kind)}) — mô tả get_location không được gợi ý lấy id từ get_asset")


def filter_note(kind: str, param: str, value, items, base_ids: list) -> tuple[bool, str]:
    """(warn, note): does the optional filter look honoured? Only enum values are ever named."""
    if items is None:
        return True, "phản hồi không phải danh sách"
    n = len(items)
    same = bool(base_ids) and item_ids(items) == base_ids
    if kind == "search":
        term = str(value).lower()
        hit = sum(1 for it in items if any(term in s.lower() for s in all_strings(it)))
        if n == 0:
            return True, "0 mục với từ khoá lấy từ chính danh sách → nghi `search` không khớp trường đó"
        if hit == n:
            return False, f"lọc đúng: {hit}/{n} mục chứa từ khoá"
        if same:
            return True, f"{hit}/{n} mục chứa từ khoá, kết quả trùng lượt chính → nghi API bỏ qua `{param}`"
        return False, f"{hit}/{n} mục chứa nguyên văn từ khoá (phần còn lại khớp mờ)"
    if kind == "enum":
        vals = [it.get(param) for it in items if isinstance(it, dict)]
        if n == 0:
            return False, f"0 mục có `{param}={value}` (giá trị được API chấp nhận)"
        if all(v is None for v in vals):
            return False, f"mục không có trường `{param}` — không kiểm được tác dụng lọc"
        hit = sum(1 for v in vals if v == value)
        if hit == n:
            return False, f"lọc đúng: {n}/{n} mục có `{param}={value}`"
        return True, f"{hit}/{n} mục có `{param}={value}`" + (" — trùng lượt chính → nghi API bỏ qua" if same else "")
    return False, f"n={n} (lượt chính n={len(base_ids)}); boolean gửi dạng chuỗi `true`"


# ── offline audit (no network) ────────────────────────────────────────────────────────────────────────────
def offline_audit(tools: list, policy: dict, roles_doc: dict, spec_text: str) -> dict:
    names = [t["function"]["name"] for t in tools]
    errors: list[str] = []
    warnings: list[str] = []
    vt.check_tools(tools, policy, roles_doc, spec_text, errors, warnings)

    n_names, forbidden = 0, []
    for t in tools:
        fn = t["function"]
        for pname in vt._walk_property_names(fn.get("parameters") or {}):
            n_names += 1
            if vt.FORBIDDEN_PARAM.search(pname.split(".")[-1]):
                forbidden.append(f"{fn['name']}.{pname}")
        res = parse_resolve(t["x_sgod"])
        if res:
            n_names += 1
            if vt.FORBIDDEN_PARAM.search(res[2]):
                forbidden.append(f"{fn['name']} resolve ?{res[2]}")

    owner = (roles_doc.get("tiers") or {}).get("enterprises")
    chat = []
    for t in tools:
        x, name = t["x_sgod"], t["function"]["name"]
        if str(x.get("path", "")).startswith(vt.SERVICES["chat"]):
            roles = (policy.get(name) or {}).get("roles")
            chat.append((name, roles, roles == [owner] and x.get("allowed_roles") == [owner]))

    blocklist = vt.parse_spec_blocklist(spec_text)
    blocked = sorted({p for _, p in blocklist} | set(REMOVED_ROUTES))
    used = []
    for t in tools:
        x, name = t["x_sgod"], t["function"]["name"]
        targets = [(x.get("method"), str(x.get("path", "")), "path")]
        res = parse_resolve(x)
        if res:
            targets.append((res[0], res[1], "resolve"))
        for method, p, where in targets:
            hit = blocklist.get((method, vt.normalise_path(p))) or removed_route(p)
            if hit:
                used.append(f"{name} ({where}: {method} {p})")

    read_only = [(t["function"]["name"], t["x_sgod"].get("method"), t["x_sgod"].get("writes"),
                  (policy.get(t["function"]["name"]) or {}).get("writes")) for t in tools]
    ro_bad = [r for r in read_only if (r[1], r[2], r[3]) != ("GET", False, False)]

    tiers = roles_doc.get("tiers") or {}
    matrix, consistent = {}, True
    for role in roles_doc.get("roles") or []:
        offered = {t["function"]["name"] for t in vt.tools_for_role(tools, policy, role)}  # Layer 1
        for t in tools:
            n = t["function"]["name"]
            l1, l2, decl = n in offered, authorize(policy, role, n), role in (t["x_sgod"].get("allowed_roles") or [])
            consistent &= (l1 == l2 == decl)
        matrix[role] = {"tiers": [k for k, v in tiers.items() if v == role], "offered": [n for n in names if n in offered],
                        "denied": [n for n in names if not authorize(policy, role, n)]}
    denied_roles = {n: [r for r in (roles_doc.get("roles") or []) if not authorize(policy, r, n)] for n in names}
    ok = not errors and not forbidden and all(c[2] for c in chat) and not used and not ro_bad and consistent
    return {"errors": errors, "warnings": warnings, "n_names": n_names, "forbidden": forbidden, "owner": owner,
            "chat": chat, "blocked": blocked, "used": used, "ro_bad": ro_bad, "matrix": matrix,
            "consistent": consistent, "denied_roles": denied_roles, "ok": ok}


def audit_lines(a: dict, n_tools: int) -> list[str]:
    """Plain-text audit summary for the console (--dry-run and live)."""
    mark = lambda b: "✓" if b else "✗"  # noqa: E731
    out = [f"{mark(not a['errors'])} validate_tools.check_tools: {len(a['errors'])} lỗi, {len(a['warnings'])} cảnh báo"]
    out += [f"    {e}" for e in a["errors"]]
    out.append(f"{mark(not a['forbidden'])} tham số company/tenant/enterprise id: {len(a['forbidden'])} "
               f"(đã quét {a['n_names']} tên: tham số của tool và khoá query của resolve)")
    out += [f"    {f}" for f in a["forbidden"]]
    out.append(f"{mark(all(c[2] for c in a['chat']))} tool /sgod-chat chỉ cho {a['owner']}: "
               + ", ".join(f"{n}={r}" for n, r, _ in a["chat"]))
    out.append(f"{mark(not a['used'])} route đã bỏ / hỏng: {len(a['used'])} tool dùng (danh sách chặn {len(a['blocked'])} route)")
    out += [f"    {u}" for u in a["used"]]
    out.append(f"{mark(not a['ro_bad'])} chỉ đọc: {n_tools - len(a['ro_bad'])}/{n_tools} tool GET + writes=false (x_sgod và policy)")
    out.append(f"{mark(a['consistent'])} Layer 1 (tools_for_role) ≡ Layer 2 (authorize) ≡ x_sgod.allowed_roles: "
               + "; ".join(f"{r}: mở {len(m['offered'])}, chặn {len(m['denied'])}" for r, m in a["matrix"].items()))
    return out


# ── report ────────────────────────────────────────────────────────────────────────────────────────────────
def md(s) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def render_report(ctx: dict) -> tuple[str, list[str]]:
    """The Markdown report + every API-derived string embedded in it (for the name guard)."""
    masker, tools, a = ctx["masker"], ctx["tools"], ctx["audit"]
    rows = sorted(ctx["rows"], key=lambda r: (r.idx, ctx["role_order"].index(r.role), r.seq))
    api_texts: list[str] = []
    n = len(tools)
    L = [f"# Kiểm tra {n} tool `sgod_tools` v1 trên API thật theo vai trò (S Việc 4)", "",
         "> Sinh bằng `python tools/sgod/verify_tools_live.py` trên hạ tầng tham chiếu — **không sửa tay**; chạy lại "
         "để cập nhật. Mỗi lượt gọi tool là `GET` (script kiểm tra trước khi gửi); `POST` duy nhất là đăng nhập và làm "
         "mới phiên. Kết luận rẽ nhánh theo `body.success`, không theo mã HTTP (gateway có khi trả HTTP 200 cho lỗi — "
         "spec §1, §4). Chỉ ghi **tên** khoá query, không ghi giá trị (từ khoá, id, cursor); token, khoá API, mật khẩu, "
         "email và địa chỉ gateway bị chặn bởi bộ kiểm tra rò rỉ của `tools/sgod/capture_fixtures.py`.", "",
         "| Mục | Giá trị |", "|---|---|",
         f"| Thời điểm chạy (UTC) | {ctx['run_at']} |",
         "| Gateway | `<SGOD_GATEWAY>` |",
         f"| Commit | `{ctx['git_sha']}`" + (" (có thay đổi chưa commit trong `tools/sgod/`)" if ctx["git_dirty"] else "") + " |",
         f"| sha256 `tools/sgod/sgod_tools.json` | `{ctx['sha_tools']}` |",
         f"| sha256 `tools/sgod/tool_policy.json` | `{ctx['sha_policy']}` |"]
    for role, tier, login_ep, state in ctx["accounts"]:
        L.append(f"| Tầng đăng nhập — `{role}` | `{tier}` (`{login_ep}`) — {state} |")
    c = ctx["counts"]
    L += [f"| Số lượt gọi | {c['GET']} `GET` · {c['login']} `POST` đăng nhập · {c['refresh']} `POST` làm mới phiên |",
          f"| `limit` cho tool danh sách | {ctx['limit']} |", ""]

    L += ["## 1. Kết quả theo tool × vai trò", "",
          "| Tool | Vai trò | Policy | Lượt gọi | Endpoint | Query keys | HTTP | success | statusCode | Dạng data "
          "| Trường | Kết luận | Ghi chú |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    first_seen: dict = {}  # (role, endpoint, fields) -> label of the first row that listed those fields
    for r in rows:
        shape = masker.mask(r.shape)
        fields = masker.mask(", ".join(r.fields)) if r.fields else ""
        api = masker.mask(r.api_note) if r.api_note else ""
        api_texts += [shape, fields, api]
        note = "; ".join(s for s in (r.note, f"API: {api}" if api else "") if s)
        seen_key = (r.role, r.path, fields)
        if not fields:
            fields_cell = "—"
        elif seen_key in first_seen:
            fields_cell = f"như dòng {first_seen[seen_key]}"  # same endpoint, same fields: do not repeat the list
        else:
            first_seen[seen_key] = f"`{r.tool}` · {md(r.call)}"
            fields_cell = f"`{md(fields)}`"
        L.append(f"| `{r.tool}` | {r.role} | {'được phép' if r.allowed else 'bị chặn'} | {md(r.call)} | "
                 f"`GET {r.path}` | {md(', '.join(r.query_keys)) or '—'} | {r.http if r.http is not None else '—'} | "
                 f"{'—' if r.success is None else str(r.success).lower()} | "
                 f"{r.status_code if r.status_code is not None else '—'} | {md(shape)} | "
                 f"{fields_cell} | {r.verdict} | {md(note) or '—'} |")
    L += ["", "Lượt gọi: **chính** = gọi đúng như executor gọi tool (tool danh sách: `limit`); **resolve** = bước tra "
          "ref → id của `x_sgod.resolve`; **<tham số>=…** = một tham số lọc tuỳ chọn của tool (từ khoá tìm lấy từ mục "
          "đầu của lượt chính, giá trị enum ưu tiên giá trị có trong dữ liệu); **cursor** = trang 2 bằng `nextCursor` "
          "của lượt chính; **id từ get_asset** = kiểm tra thêm: id trong `asset.locations` có dùng được cho `get_location` không.",
          "",
          f"Kết luận: **{V_OK}** = `success:true` trên dữ liệu thật · **{V_WARN}** = `success:true` nhưng có dấu hiệu "
          f"API bỏ qua tham số hoặc thiếu cursor (xem ghi chú) · **{V_NODATA}** = nguồn rỗng nên gọi bằng ObjectId hợp "
          f"lệ không tồn tại; route có (phong bì không tìm thấy) · **{V_MISSING}** = gateway trả `Cannot GET` · "
          f"**{V_FAIL}** / **{V_SKIP}** = thất bại ở vai trò được phép · **{V_DENIED}** = vai trò không có trong "
          f"`tool_policy.json` của tool: chat từ chối (Layer 1 + Layer 2, §3.6); lượt gọi chỉ để ghi lại SGOD tự trả gì "
          f"· **{V_INFO}** = kiểm tra thêm, không tính vào kết luận của tool.", ""]

    L += ["## 2. Tóm tắt", ""]
    for role in ctx["role_order"]:
        rr = [r for r in rows if r.role == role]
        if not rr:
            continue
        cnt = {v: sum(1 for r in rr if r.verdict == v) for v in (V_OK, V_WARN, V_NODATA, V_FAIL, V_SKIP, V_MISSING,
                                                                   V_DENIED, V_INFO)}
        L.append(f"- `{role}`: {len({r.tool for r in rr})} tool · {len(rr)} lượt gọi — "
                 + " · ".join(f"{k} {v}" for k, v in cnt.items() if v or k in (V_OK, V_FAIL)))
    if ctx["employee_absent"]:
        L.append(f"- `employee`: **không gọi API thật** — {ctx['employee_absent']}")
    L += ["", "**Checkpoint S Việc 4** (mỗi tool: ≥ 1 lượt `success:true` thật cho vai trò được phép; ≥ 1 vai trò bị "
          "từ chối đúng):", "",
          "| Tool | `success:true` thật (vai trò được phép) | Từ chối đúng (vai trò bị chặn) |", "|---|---|---|"]
    n_real = 0
    for t in tools:
        name = t["function"]["name"]
        real = sorted({r.role for r in rows if r.tool == name and r.real_success}, key=ctx["role_order"].index)
        n_real += bool(real)
        if real:
            c2 = "✓ " + ", ".join(real)
        else:
            why = sorted({r.verdict for r in rows if r.tool == name and r.allowed and r.call == "chính"})
            c2 = "✗ — " + (", ".join(why) if why else "chưa gọi")
        parts = []
        for role in a["denied_roles"].get(name, []):
            tiers = a["matrix"].get(role, {}).get("tiers") or []
            live = [r for r in rows if r.tool == name and r.role == role and r.call == "chính"]
            if live:
                lr = live[0]
                code = lr.status_code if lr.status_code is not None else f"HTTP {lr.http}"
                sgod = "SGOD trả success:true — chỉ policy chặn" if lr.success is True else f"SGOD cũng từ chối ({code})"
                parts.append(f"✓ {role} (Layer 1 + Layer 2; gọi thật: {sgod})")
            elif not tiers:
                parts.append(f"✓ {role} (Layer 1 + Layer 2; không có tầng đăng nhập SGOD)")
            else:
                parts.append(f"✓ {role} (Layer 1 + Layer 2; chưa gọi thật)")
        L.append(f"| `{name}` | {c2} | {'<br>'.join(parts) if parts else '✗ — không vai trò nào bị chặn'} |")
    n_refusal = sum(1 for t in tools if a["denied_roles"].get(t["function"]["name"]))
    L += ["", f"Kết quả checkpoint: **{n_real}/{n}** tool có `success:true` thật cho vai trò được phép; **{n_refusal}/{n}** "
          f"tool có ≥ 1 vai trò bị từ chối đúng theo `tool_policy.json` (Layer 1 + Layer 2).", ""]

    L += ["## 3. Kiểm tra offline `tool_policy.json` (không gọi mạng)", "",
          "### 3.1 `validate_tools.check_tools` (cấu trúc, spec, danh sách chặn, chat, resolve, policy)", "",
          f"{len(a['errors'])} lỗi, {len(a['warnings'])} cảnh báo trên {n} tool." + (
              "" if not a["errors"] else " Lỗi: " + "; ".join(f"`{md(e)}`" for e in a["errors"])), "",
          "### 3.2 Không tham số company / tenant / enterprise id", "",
          f"Đã quét {a['n_names']} tên tham số (kể cả lồng nhau) và khoá query của bước resolve theo mẫu "
          f"`(company|tenant|enterprise)_?id`: **{len(a['forbidden'])}** khớp" + (
              "." if not a["forbidden"] else ": " + ", ".join(f"`{f}`" for f in a["forbidden"]) + "."),
          "JWT quyết định tenant (spec §1).", "",
          f"### 3.3 Tool `/sgod-chat` chỉ mở cho `{a['owner']}`", "",
          "| Tool | `roles` trong policy | Đạt |", "|---|---|---|"]
    L += [f"| `{nm}` | {', '.join(rl or [])} | {'✓' if ok else '✗'} |" for nm, rl, ok in a["chat"]]
    L += ["", "Spec §4: chat-service trả 500 cho token enterprise-user / sub-enterprise.", "",
          "### 3.4 Không dùng route đã bỏ / hỏng", "",
          "Danh sách chặn (spec §4 qua `validate_tools.parse_spec_blocklist` + route đã bỏ khi gọi thật 2026-10-14): "
          + ", ".join(f"`{p}`" for p in a["blocked"]) + ".",
          f"Số tool dùng các route này (đường dẫn hoặc bước resolve): **{len(a['used'])}**" + (
              "." if not a["used"] else ": " + "; ".join(a["used"]) + "."), "",
          "### 3.5 Chỉ đọc", "",
          f"{n - len(a['ro_bad'])}/{n} tool có `x_sgod.method = GET`, `x_sgod.writes = false` và policy `writes = false`.",
          "", "### 3.6 Ma trận từ chối — Layer 1 + Layer 2", "",
          "Layer 1: model chỉ thấy tool có vai trò trong `tool_policy.json` (`validate_tools.tools_for_role`, cùng bộ "
          "lọc mà `finetune_qlora.py` / `predict_toolcall.py` dùng khi render `tools=`). Layer 2: executor gọi "
          "`authorize_tool_call` — vai trò ∉ `tool_policy.json[tool].roles` → *denied*, trả `REFUSAL_VI` và không gọi "
          "SGOD (hợp đồng 3 §6). Quyền do mã quyết định, không do model.", "",
          "| Vai trò | Tầng đăng nhập SGOD | Số tool mở (Layer 1) | Tool bị từ chối (Layer 2) |", "|---|---|---|---|"]
    for role, m in a["matrix"].items():
        L.append(f"| `{role}` | {', '.join(f'`{x}`' for x in m['tiers']) or 'không có (không hỗ trợ)'} | "
                 f"{len(m['offered'])} | {', '.join(f'`{d}`' for d in m['denied']) or '—'} |")
    L += ["", f"Layer 1 ≡ Layer 2 ≡ `x_sgod.allowed_roles` cho mọi cặp (vai trò, tool): **{'✓' if a['consistent'] else '✗'}**.",
          f"Kết luận kiểm tra offline: **{'đạt' if a['ok'] else 'KHÔNG đạt'}**.", ""]

    L += ["## 4. Phạm vi dữ liệu `employee` so với `company_admin`", ""]
    scope = ctx["scope"]
    if scope:
        L += [f"Lượt chính của tool danh sách mở cho cả hai vai trò (`limit={ctx['limit']}`, chỉ đếm id):", "",
              "| Tool | `company_admin` n | `employee` n | id chung |", "|---|---|---|---|"]
        L += [f"| `{nm}` | {na} | {ne} | {both} |" for nm, na, ne, both in scope]
        L.append("")
    else:
        L += ["Chưa so sánh được (cần lượt chính thành công của cả hai vai trò).", ""]

    L += ["## 5. Chạy lại", "", "```bash",
          "# Chỉ trên hạ tầng tham chiếu. Biến lấy từ .env (mẫu: .env.example); không bao giờ commit .env.",
          "set -a; . ./.env; set +a",
          "python tools/sgod/verify_tools_live.py --dry-run     # kế hoạch + kiểm tra offline, không gọi mạng",
          "python tools/sgod/verify_tools_live.py --out docs/sgod/tools_v1_live_check.md", "```", ""]
    return "\n".join(L), [s for s in api_texts if s]


def guard(masker, text: str, api_texts: list[str]) -> list[str]:
    """capture_fixtures guard: secrets / e-mail / phone / JWT / IP / gateway on the whole text; unmasked names on the
    API-derived parts only (this script's own vocabulary — role names, field names — must not trip the name check)."""
    fails = [f for f in masker.leaks(text) if not f.startswith("unmasked-")]
    fails += [f for f in masker.leaks("\n".join(api_texts)) if f.startswith("unmasked-")]
    return sorted(set(fails))


def git_info() -> tuple[str, bool]:
    try:
        sha = subprocess.run(["git", "-C", str(vt.REPO), "rev-parse", "--short=7", "HEAD"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(vt.REPO), "status", "--porcelain", "--", "tools/sgod"],
                               capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown", False
    return sha or "unknown", bool(dirty)


# ── entry points ──────────────────────────────────────────────────────────────────────────────────────────
def print_plan(tools: list, policy: dict, roles_doc: dict, a: dict, limit: int, paths: dict) -> int:
    print("verify_tools_live --dry-run — không đọc giá trị biến môi trường nào, không gọi mạng")
    print(f"sgod_tools.json  sha256 {sha256_of(paths['tools'])}")
    print(f"tool_policy.json sha256 {sha256_of(paths['policy'])}")
    login = roles_doc.get("login_endpoints") or {}
    print("Vai trò → tầng đăng nhập:")
    for role, tier, e_env, p_env, required in ACCOUNTS:
        print(f"  {role} → {tier} ({login.get(tier, '?')}) — {'bắt buộc' if required else 'tùy chọn'}: {e_env}, {p_env}")
    present = lambda n: "có" if os.environ.get(n) else "thiếu"  # noqa: E731  presence only, value never read out
    print("Biến môi trường (chỉ kiểm tra có/không): "
          + ", ".join(f"{n}={present(n)}" for n in REQUIRED_ENV + OPTIONAL_ENV))
    print(f"Kế hoạch — mọi lượt là GET; tool danh sách limit={limit}; vai trò bị policy chặn chỉ chạy lượt chính "
          f"(+ resolve) để ghi lại SGOD tự trả gì:")
    per_role = {role: 0 for role, *_ in ACCOUNTS}
    for i, t in enumerate(tools, 1):
        fn, x = t["function"], t["x_sgod"]
        name = fn["name"]
        roles = (policy.get(name) or {}).get("roles") or []
        denied = a["denied_roles"].get(name, [])
        print(f"  [{i:2d}] {name} — policy: {', '.join(roles)}; bị chặn: {', '.join(denied) or '—'}")
        try:
            require_get(name, x)
        except ReadOnlyViolation as e:
            print(f"       ✗ KHÔNG GỌI — {e}")
            continue
        for step in build_steps(t, limit):
            q = "&".join(f"{k}={v}" for k, v in step.query.items())
            extra = f"   ({step.id_desc})" if step.id_desc else ""
            if step.kind == "main" and name in ID_SOURCES and needs_value(t):
                extra += f"   [nguồn rỗng → ObjectId không tồn tại {NONEXISTENT_OID}]"
            print(f"       {step.call:<24} GET {step.path}{'?' + q if q else ''}{extra}")
            for role in per_role:
                if authorize(policy, role, name) or step.kind in ("main", "resolve"):
                    per_role[role] += 1
    print("Kiểm tra offline:")
    for line in audit_lines(a, len(tools)):
        print("  " + line)
    print(f"verify_tools_live --dry-run: {'OK' if a['ok'] else 'FAIL'} — {len(tools)} tool, tối đa "
          + ", ".join(f"{n} GET cho {r}" for r, n in per_role.items())
          + f", kiểm tra offline {len(a['errors']) + len(a['forbidden']) + len(a['used']) + len(a['ro_bad'])} lỗi")
    return 0 if a["ok"] else 1


def run_live(args, tools: list, policy: dict, roles_doc: dict, a: dict, paths: dict) -> int:
    """Checks the environment, then runs _run_live behind the output guard: sys.stdout / sys.stderr are line-filtered
    by scrub_text, and an unexpected exception is reported by type and code location only (exit 2)."""
    missing = [n for n in REQUIRED_ENV if not (os.environ.get(n) or "").strip()]
    if missing:
        print(f"verify_tools_live: thiếu biến môi trường {', '.join(missing)} (xem .env.example) — không chạy")
        return 2
    base = os.environ["SGOD_BASE_URL"].strip().rstrip("/")
    if not valid_base_url(base):
        print("verify_tools_live: SGOD_BASE_URL phải có dạng http(s)://<host>[:port] (giá trị không in ra) — không chạy")
        return 2
    raw = [os.environ.get(n) or "" for n in REQUIRED_ENV[1:] + OPTIONAL_ENV]  # API keys, e-mails, passwords
    masker = cf.Masker(raw + [v.strip() for v in raw], "")  # login tokens are appended to masker.secrets later
    masker.hosts = gateway_hosts(base)  # longest first: "host:port" before the bare host (no stray ":port" left)
    real_out, real_err = sys.stdout, sys.stderr
    scrub = lambda t: scrub_text(t, masker.secrets, masker.hosts)  # noqa: E731 — reads the live lists
    sys.stdout, sys.stderr = RedactingStream(real_out, scrub), RedactingStream(real_err, scrub)
    try:
        return _run_live(args, tools, policy, roles_doc, a, paths, masker)
    except KeyboardInterrupt:
        print("verify_tools_live: dừng (Ctrl-C)", file=sys.stderr)
        return 130
    except BaseException as e:  # noqa: BLE001 — type + code location only: the message may hold a URL or a value
        print(f"verify_tools_live: ABORT — lỗi {type(e).__name__} tại {where(e)} (thông điệp lỗi không in ra)",
              file=sys.stderr)
        return 2
    finally:
        for s in (sys.stdout, sys.stderr):
            if isinstance(s, RedactingStream):
                s.drain()
        sys.stdout, sys.stderr = real_out, real_err


def _run_live(args, tools: list, policy: dict, roles_doc: dict, a: dict, paths: dict, masker) -> int:
    try:
        for t in tools:
            require_get(t["function"]["name"], t["x_sgod"])
    except ReadOnlyViolation as e:
        print(f"verify_tools_live: REFUSED — {e}")
        return 2
    tiers = list((roles_doc.get("tiers") or {}).keys())
    login_eps = roles_doc.get("login_endpoints") or {}
    gw = ReadOnlyGateway(tiers)

    rows, caches, accounts, role_order = [], {}, [], []
    employee_absent, exit_code = "", 0
    for role, tier, e_env, p_env, required in ACCOUNTS:
        if (roles_doc.get("tiers") or {}).get(tier) != role:
            print(f"verify_tools_live: roles.json tiers[{tier!r}] != {role!r} — không chạy")
            return 2
        ep = login_eps.get(tier, f"POST /sgod-auth/v1/{tier}/sessions")
        # a CRLF .env leaves "\r" on every value; a password keeps any other blank it may have on purpose
        email, password = (os.environ.get(e_env) or "").strip(), (os.environ.get(p_env) or "").strip("\r\n")
        if not (email and password):
            employee_absent = (f"hạ tầng tham chiếu chưa có tài khoản thử tầng `{tier}` (`{e_env}` / `{p_env}` không "
                               f"đặt). Từ chối cho `{role}` do `tool_policy.json` bảo đảm bằng mã: Layer 1 — danh sách "
                               f"tool render cho `{role}` không chứa tool chỉ dành cho `company_admin`; Layer 2 — "
                               f"`authorize_tool_call` trả *denied* (§3.6).")
            accounts.append((role, tier, ep, "**không chạy** — chưa có tài khoản thử tầng này"))
            continue
        sess = Session(gw, masker, role, tier, email, password)
        try:
            why = sess.login()
        except ReadOnlyViolation as e:
            print(f"verify_tools_live: REFUSED — {e}")
            return 2
        if why:
            safe_print(masker, f"verify_tools_live: {role}: {why}")
            if required:
                return 2
            accounts.append((role, tier, ep, f"**đăng nhập thất bại** ({md(why)})"))
            employee_absent = (f"đăng nhập tầng `{tier}` thất bại ({md(why)}). Từ chối cho `{role}` vẫn do "
                               f"`tool_policy.json` bảo đảm bằng mã (Layer 1 + Layer 2, §3.6).")
            exit_code = 1
            continue
        print(f"{role}: đăng nhập tầng {tier} ok (token không in ra)", flush=True)
        accounts.append((role, tier, ep, "đã chạy"))
        runner = Runner(sess, tools, policy, args.limit)
        try:
            runner.run()
        except ReadOnlyViolation as e:
            print(f"verify_tools_live: REFUSED — {e}")
            return 2
        rows += runner.rows
        caches[role] = runner.cache
        role_order.append(role)
    role_order += [r for r, *_ in ACCOUNTS if r not in role_order]

    scope = []  # list tools open to both roles: does an employee see the same page 1 as the owner?
    if "company_admin" in caches and "employee" in caches:
        for t in tools:
            nm = t["function"]["name"]
            props = (t["function"].get("parameters") or {}).get("properties") or {}
            if "limit" not in props or not all(authorize(policy, r, nm) for r in ("company_admin", "employee")):
                continue
            ca, ce = caches["company_admin"].get(nm) or {}, caches["employee"].get(nm) or {}
            if ca.get("ok") and ce.get("ok") and isinstance(ca.get("items"), list) and isinstance(ce.get("items"), list):
                scope.append((nm, len(ca["items"]), len(ce["items"]), len(set(ca["ids"]) & set(ce["ids"]))))

    git_sha, git_dirty = git_info()
    ctx = {"masker": masker, "tools": tools, "audit": a, "rows": rows, "role_order": role_order,
           "run_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), "git_sha": git_sha,
           "git_dirty": git_dirty, "sha_tools": sha256_of(paths["tools"]), "sha_policy": sha256_of(paths["policy"]),
           "accounts": accounts, "counts": gw.counts, "limit": args.limit, "employee_absent": employee_absent,
           "scope": scope}
    text, api_texts = render_report(ctx)
    text = scrub_text(text, masker.secrets, masker.hosts)  # placeholders for anything the per-field masking missed
    fails = guard(masker, text, api_texts)
    if fails:
        print(f"verify_tools_live: ABORT — kiểm tra rò rỉ thất bại {fails}; không ghi báo cáo")
        return 2
    out = Path(args.out)
    if not out.is_absolute() and not out.parent.exists():
        out = vt.REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")

    for line in audit_lines(a, len(tools)):
        print("  " + line)
    fails_live = [r for r in rows if r.fail]
    n_real = len({r.tool for r in rows if r.real_success})
    if fails_live or not a["ok"]:
        exit_code = 1
    n_warn = sum(1 for r in rows if r.warn)
    print(f"verify_tools_live: {'OK' if exit_code == 0 else 'FAIL'} — {len(tools)} tool, {len(rows)} lượt gọi "
          f"({gw.counts['GET']} GET), {len(fails_live)} lỗi ở vai trò được phép, {n_warn} cảnh báo ⚠, "
          f"{n_real}/{len(tools)} tool có success:true thật, kiểm tra offline {'đạt' if a['ok'] else 'KHÔNG đạt'}; "
          f"báo cáo {out}")
    return exit_code


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tools", default="tools/sgod/sgod_tools.json")
    ap.add_argument("--policy", default="tools/sgod/tool_policy.json")
    ap.add_argument("--roles", default="tools/sgod/roles.json")
    ap.add_argument("--spec", default="docs/sgod-api-reference.md", help="spec whose §4 feeds the blocklist")
    ap.add_argument("--out", default=DEFAULT_OUT, help=f"Markdown report (default {DEFAULT_OUT})")
    ap.add_argument("--limit", type=int, default=5, help="limit for list tools (default 5)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and the offline audit; no env, no network")
    args = ap.parse_args(argv)
    if args.limit < 1:
        ap.error("--limit must be >= 1")

    errors: list[str] = []
    paths = {"tools": vt.resolve_path(args.tools), "policy": vt.resolve_path(args.policy),
             "roles": vt.resolve_path(args.roles), "spec": vt.resolve_path(args.spec)}
    tools = vt.load_json(paths["tools"], "tools", errors)
    policy = vt.load_json(paths["policy"], "policy", errors)
    roles_doc = vt.load_json(paths["roles"], "roles", errors)
    try:
        spec_text = paths["spec"].read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"spec: file not found: {paths['spec']}")
    if not errors and not (isinstance(tools, list) and isinstance(policy, dict) and isinstance(roles_doc, dict)):
        errors.append("tools must be a JSON list, policy and roles JSON objects")
    if errors:
        for e in errors:
            print(f"ERROR {e}")
        print(f"verify_tools_live: FAIL — {len(errors)} input error(s)")
        return 2
    audit = offline_audit(tools, policy, roles_doc, spec_text)
    if args.dry_run:
        return print_plan(tools, policy, roles_doc, audit, args.limit, paths)
    return run_live(args, tools, policy, roles_doc, audit, paths)


if __name__ == "__main__":
    sys.exit(main())
