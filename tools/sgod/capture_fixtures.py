#!/usr/bin/env python3
"""[S-V2] Capture REAL SGOD response fixtures (run only on the reference infrastructure).

Replaces tools/sgod/generate_fixtures.py (which hard-codes invented responses). Every file this script
writes is the full HTTP response body returned by the live gateway (envelope included), with PII masked
by consistent fakes. Nothing is invented: when a call fails or returns no data, the manifest says so and
no fixture is written for it.

Credentials come ONLY from the environment (names follow .env.example); they are never printed, never
passed on the command line and never written to disk:
  SGOD_BASE_URL, SGOD_AUTH_API_KEY, SGOD_ASSET_API_KEY, SGOD_CHAT_API_KEY      (required)
  SGOD_ENTERPRISE_EMAIL, SGOD_ENTERPRISE_PASSWORD                             (required: enterprise owner)
  SGOD_EUSER_EMAIL, SGOD_EUSER_PASSWORD                                       (optional: negative #4 and
                                                                               employee-scope samples)

Usage:
  python tools/sgod/capture_fixtures.py capture --out fixtures/sgod [--max-wait-expiry 1800] [--employee-samples]
  python tools/sgod/capture_fixtures.py capture --dry-run            # print the plan, no network
  python tools/sgod/capture_fixtures.py inventory --fixtures fixtures/sgod [--openapi-enums enums.json]

Outputs:
  fixtures/sgod/<service>/<METHOD>_<slug>.json   full body, masked (slug: path after /v1/, '-'->'_', '{x}'->'x')
  fixtures/sgod/negative/*.json                   the 4 negative cases (flow file = list of real steps)
  fixtures/sgod/manifest.tsv                      file, method, path, query, tier, http_status, captured_at, sha8
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

DEVICE_ID = "chatsystem-fixture-capture"
LIST_LIMIT = 10

# (service_dir, path_template, query, needs) — needs = name of an id resolved from an earlier response.
PLAN = [
    ("auth", "/sgod-auth/v1/users/myself", {}, None),
    ("auth", "/sgod-auth/v1/session/context", {}, None),
    ("auth", "/sgod-auth/v1/enterprises/profile", {}, None),
    ("auth", "/sgod-auth/v1/enterprise-users", {"limit": LIST_LIMIT}, None),
    ("auth", "/sgod-auth/v1/roles", {}, None),
    ("auth", "/sgod-auth/v1/departments/tree", {}, None),
    ("asset", "/sgod-asset/v1/assets", {"limit": LIST_LIMIT}, None),
    ("asset", "/sgod-asset/v1/assets/{id}", {}, "asset_id"),
    ("asset", "/sgod-asset/v1/assets/suggest", {"q": "{asset_q}"}, "asset_q"),
    ("asset", "/sgod-asset/v1/assets/{id}/histories", {"limit": LIST_LIMIT}, "asset_id"),
    ("asset", "/sgod-asset/v1/asset-statuses/by-asset/{assetId}", {"limit": LIST_LIMIT}, "asset_id"),
    ("asset", "/sgod-asset/v1/asset-statuses/history/{assetId}", {"limit": LIST_LIMIT}, "asset_id"),
    ("asset", "/sgod-asset/v1/categories", {"limit": 20}, None),
    ("asset", "/sgod-asset/v1/locations", {"limit": 20}, None),
    ("asset", "/sgod-asset/v1/locations/{id}", {}, "location_id"),
    ("asset", "/sgod-asset/v1/maintenance/schedules", {"limit": LIST_LIMIT}, None),
    ("asset", "/sgod-asset/v1/maintenance/schedules/{id}", {}, "schedule_id"),
    ("asset", "/sgod-asset/v1/maintenance/tasks", {"maintenanceScheduleId": "{schedule_id}", "limit": LIST_LIMIT}, "schedule_id"),
    ("asset", "/sgod-asset/v1/maintenance/records", {"limit": LIST_LIMIT}, None),
    ("asset", "/sgod-asset/v1/asset-transfers", {"limit": LIST_LIMIT}, None),
    ("asset", "/sgod-asset/v1/asset-transfers/{id}", {}, "transfer_id"),
    ("asset", "/sgod-asset/v1/asset-transfers/summary", {}, None),
    ("asset", "/sgod-asset/v1/request-staff", {"limit": LIST_LIMIT}, None),
    ("asset", "/sgod-asset/v1/request-staff/summary", {}, None),
    ("asset", "/sgod-asset/v1/dashboard/statistics-asset", {}, None),
    ("chat", "/sgod-chat/v1/conversations", {"limit": LIST_LIMIT}, None),
    ("chat", "/sgod-chat/v1/conversations/unread-counts", {}, None),
    ("chat", "/sgod-chat/v1/messages", {"conversationId": "{conversation_id}", "limit": LIST_LIMIT}, "conversation_id"),
]
# Which list response feeds which id (path in the response is found generically: first 24-hex 'id').
ID_SOURCES = {
    "/sgod-asset/v1/assets": "asset_id",
    "/sgod-asset/v1/locations": "location_id",
    "/sgod-asset/v1/maintenance/schedules": "schedule_id",
    "/sgod-asset/v1/asset-transfers": "transfer_id",
    "/sgod-chat/v1/conversations": "conversation_id",
}
# Spec §4 documents these as returning HTTP 200 with success:false; the first one that still does is used.
HTTP200_ERROR_CANDIDATES = [
    "/sgod-asset/v1/maintenance/schedules/count-by-tab",
    "/sgod-asset/v1/import-export/exports",
    "/sgod-asset/v1/dashboard/summary",
]
OID = re.compile(r"^[0-9a-f]{24}$")


def slug(path: str) -> str:
    rest = path.split("/v1/", 1)[1]
    return "_".join(p.strip("{}").replace("-", "_") for p in rest.split("/"))


def env(name: str, required: bool = True) -> str | None:
    v = os.environ.get(name)
    if required and not v:
        sys.exit(f"missing environment variable {name} (see .env.example); refusing to run")
    return v


class Gateway:
    device_id = DEVICE_ID  # x-device-id header; a subclass may override it (tools/sgod/verify_tools_live.py)

    def __init__(self) -> None:
        self.base = env("SGOD_BASE_URL").rstrip("/")
        self.keys = {"auth": env("SGOD_AUTH_API_KEY"), "asset": env("SGOD_ASSET_API_KEY"), "chat": env("SGOD_CHAT_API_KEY")}

    def key_for(self, path: str) -> str:
        return self.keys[path.split("/")[1].replace("sgod-", "")]

    def call(self, method: str, path: str, query: dict | None = None, token: str | None = None, body: dict | None = None):
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
            with urllib.request.urlopen(req, timeout=30) as r:
                status, raw = r.status, r.read()
        except urllib.error.HTTPError as e:  # 4xx/5xx still carry the gateway envelope
            status, raw = e.code, e.read()
        except (urllib.error.URLError, TimeoutError) as e:
            return None, None, f"network error: {type(e).__name__}"
        try:
            return status, json.loads(raw.decode("utf-8")), None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return status, None, f"non-JSON body ({len(raw)} B)"

    def try_login(self, tier: str, email: str, password: str):
        """(accessToken, refreshToken, None) on success, else (None, None, reason); the reason never holds a secret."""
        status, body, err = self.call("POST", f"/sgod-auth/v1/{tier}/sessions", body={"credential": email, "password": password})
        data = (body or {}).get("data") or {}
        if status != 200 or not (body or {}).get("success") or "accessToken" not in data:
            return None, None, f"login failed for tier {tier}: http={status} {err or ''} success={(body or {}).get('success')}"
        return data["accessToken"], data.get("refreshToken"), None

    def login(self, tier: str, email: str, password: str):
        access, refresh, why = self.try_login(tier, email, password)
        if why:
            sys.exit(why)
        return access, refresh


class Masker:
    """Consistent fakes: the same real value maps to the same fake in every file. ObjectIds and enums are kept."""

    KEY_KIND = {
        "email": "email", "phone": "phone", "phonenumber": "phone", "mobile": "phone",
        "firstname": "first", "lastname": "last", "fullname": "fullname", "username": "username",
        "displayname": "fullname", "nickname": "fullname", "lastnameusersent": "fullname", "sendername": "fullname",
        "creatorname": "fullname", "enterprisename": "enterprise", "companyname": "enterprise",
        "address": "address", "addressdetail": "address", "street": "address",
        "avatarurl": "url", "logourl": "url", "avatar": "url", "logo": "url", "ipaddress": "ip", "ip": "ip",
        "accesstoken": "secret", "refreshtoken": "secret", "interimtoken": "secret", "token": "secret",
    }
    FAKE = {
        "email": lambda n: f"user{n:02d}@example.com",
        "phone": lambda n: f"+840000{n:05d}",  # "+84" then "0": never matches a real VN mobile
        "first": lambda n: f"Test{n:02d}",
        "last": lambda n: "Nguyễn",
        "fullname": lambda n: f"Người dùng {n:02d}",
        "username": lambda n: f"user{n:02d}",
        "enterprise": lambda n: f"Doanh nghiệp Demo {n:02d}",
        "address": lambda n: f"Địa chỉ mẫu {n:02d}",
        "url": lambda n: f"https://example.com/media/{n:02d}.png",
        "ip": lambda n: f"203.0.113.{n}",
        "secret": lambda n: "<redacted-token>",
    }

    def __init__(self, secrets: list[str], gateway_host: str) -> None:
        self.maps: dict[str, dict[str, str]] = defaultdict(dict)
        self.secrets = [s for s in secrets if s]
        self.gateway_host = gateway_host
        self.hosts = [h for h in {gateway_host, gateway_host.split(":")[0]} if h]

    @staticmethod
    def _word(real: str) -> re.Pattern:
        return re.compile(r"(?<!\w)" + re.escape(real) + r"(?!\w)")

    def fake(self, kind: str, real: str) -> str:
        m = self.maps[kind]
        if real not in m:
            m[real] = self.FAKE[kind](len(m) + 1)
        return m[real]

    def _walk(self, x, key: str | None = None):
        if isinstance(x, dict):
            return {k: self._walk(v, k) for k, v in x.items()}
        if isinstance(x, list):
            return [self._walk(v, key) for v in x]
        nkey = re.sub(r"[_\-]", "", key).lower() if key is not None else None
        if isinstance(x, str) and x and nkey is not None:
            kind = self.KEY_KIND.get(nkey) or ("address" if nkey == "detail" else None)  # location.detail = street address
            if kind and not OID.match(x):
                return self.fake(kind, x)
        if isinstance(x, float) and nkey in ("latitude", "longitude", "lat", "lng", "lon"):
            return round(x, 2)  # ~1 km: keeps the shape, does not pinpoint a real address
        return x

    def _scrub_strings(self, x):
        if isinstance(x, dict):
            return {k: self._scrub_strings(v) for k, v in x.items()}
        if isinstance(x, list):
            return [self._scrub_strings(v) for v in x]
        if isinstance(x, str):
            s = x
            for kind, m in self.maps.items():  # real values echoed in free text (searchText, snippets, content)
                for real, fake in sorted(m.items(), key=lambda kv: -len(kv[0])):
                    if len(real) >= 3 and real in s:
                        s = self._word(real).sub(fake, s)
            s = re.sub(r"eyJ[\w-]+\.[\w-]+\.[\w-]+", "<redacted-token>", s)
            for sec in self.secrets:
                s = s.replace(sec, "<redacted>")
            for h in self.hosts:
                s = s.replace(h, "<SGOD_GATEWAY>")
            return s
        return x

    def mask(self, body):
        return self._scrub_strings(self._walk(body))

    def leaks(self, body) -> list[str]:
        """Return names of failed checks (never the matched values)."""
        s = json.dumps(body, ensure_ascii=False)
        fails = []
        if any(not e.endswith("@example.com") for e in re.findall(r"[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}", s)):
            fails.append("email")
        if re.search(r"(\+84|\b0)[35789]\d{8}\b", s):
            fails.append("vn-phone")
        if re.search(r"eyJ[\w-]+\.[\w-]+\.", s):  # JWT = 3 dot-separated parts; base64-JSON cursors (no dots) are kept
            fails.append("jwt")
        if any(h in s for h in self.hosts):
            fails.append("gateway-host")
        if any(not ip.startswith("203.0.113.") for ip in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", s)):
            fails.append("ipv4")
        if any(sec in s for sec in self.secrets):
            fails.append("secret-value")
        for kind in ("fullname", "first", "username", "enterprise", "address"):
            if any(len(real) >= 3 and self._word(real).search(s) for real in self.maps.get(kind, {})):
                fails.append(f"unmasked-{kind}")
        return fails


def first_id(body) -> str | None:
    """First 24-hex 'id' inside data (list endpoints: items / conversations / tree roots)."""
    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("id"), str) and OID.match(x["id"]):
                return x["id"]
            for v in x.values():
                r = walk(v)
                if r:
                    return r
        elif isinstance(x, list):
            for v in x:
                r = walk(v)
                if r:
                    return r
        return None
    return walk((body or {}).get("data"))


def first_name(body) -> str | None:
    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("name"), str) and x["name"].strip():
                return x["name"]
            for v in x.values():
                r = walk(v)
                if r:
                    return r
        elif isinstance(x, list):
            for v in x:
                r = walk(v)
                if r:
                    return r
        return None
    return walk((body or {}).get("data"))


def jwt_ttl(token: str) -> tuple[int | None, int | None]:
    try:
        payload = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return claims.get("exp"), claims.get("iat")
    except Exception:  # noqa: BLE001 — opaque token: no TTL known
        return None, None


class Writer:
    def __init__(self, out: str, masker: Masker) -> None:
        self.out, self.masker, self.rows = out, masker, []

    def save(self, rel: str, body, method: str, path: str, query: dict, tier: str, status) -> bool:
        masked = self.masker.mask(body)
        if not isinstance(masked, dict) or "success" not in masked:
            self.rows.append((rel, method, path, json.dumps(query, ensure_ascii=False), tier, status, "SKIPPED: no success field"))
            print(f"  skip {rel}: body has no 'success' field (not written)")
            return False
        fails = self.masker.leaks(masked)
        if fails:
            sys.exit(f"ABORT: masking check failed for {rel}: {fails} (nothing written for this file)")
        text = json.dumps(masked, ensure_ascii=False, indent=2) + "\n"
        full = os.path.join(self.out, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)
        sha8 = hashlib.sha256(text.encode()).hexdigest()[:8]
        now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.rows.append((rel, method, path, json.dumps(query, ensure_ascii=False), tier, status, f"{now} sha256:{sha8}"))
        print(f"  {method} {path} -> http {status} -> {rel} ({len(text)} B)")
        return True

    def note(self, rel: str, method: str, path: str, query: dict, tier: str, status, why: str) -> None:
        self.rows.append((rel, method, path, json.dumps(query, ensure_ascii=False), tier, status, why))
        print(f"  {method} {path} -> {why}")

    def write_manifest(self) -> None:
        with open(os.path.join(self.out, "manifest.tsv"), "w", encoding="utf-8") as f:
            f.write("file\tmethod\tpath\tquery\ttier\thttp_status\tcaptured_at / note\n")
            for r in self.rows:
                f.write("\t".join(str(c) for c in r) + "\n")


def capture(args) -> None:
    if args.dry_run:
        for svc, path, query, needs in PLAN:
            print(f"GET {path} {query or ''} -> {svc}/GET_{slug(path)}.json" + (f"   (needs {needs})" if needs else ""))
        print("negatives: HTTP200 success:false from", HTTP200_ERROR_CANDIDATES, "| 401 expired | 401->refresh->retry | chat as enterprise-user")
        return
    gw = Gateway()
    host = urllib.parse.urlparse(gw.base).netloc
    secrets = [gw.keys[k] for k in gw.keys] + [env("SGOD_ENTERPRISE_PASSWORD"), env("SGOD_EUSER_PASSWORD", False)]
    masker = Masker(secrets, host)
    w = Writer(args.out, masker)

    token, refresh = gw.login("enterprises", env("SGOD_ENTERPRISE_EMAIL"), env("SGOD_ENTERPRISE_PASSWORD"))
    ids: dict[str, str] = {}
    print("enterprise login ok (token not shown)")
    for svc, path, query, needs in PLAN:
        if needs and needs not in ids:
            w.note(f"{svc}/GET_{slug(path)}.json", "GET", path, query, "enterprise", "-", f"SKIPPED: no {needs} (upstream list empty or failed)")
            continue
        real_path = path.replace("{id}", ids.get({"/sgod-asset/v1/locations/{id}": "location_id",
                                                   "/sgod-asset/v1/maintenance/schedules/{id}": "schedule_id",
                                                   "/sgod-asset/v1/asset-transfers/{id}": "transfer_id"}.get(path, "asset_id"), "")
                                 ).replace("{assetId}", ids.get("asset_id", ""))
        real_query = {k: (v.format(**ids) if isinstance(v, str) else v) for k, v in query.items()}
        status, body, err = gw.call("GET", real_path, real_query, token)
        if status == 401:  # access token expired mid-run: log in again once, then retry
            token, refresh = gw.login("enterprises", env("SGOD_ENTERPRISE_EMAIL"), env("SGOD_ENTERPRISE_PASSWORD"))
            status, body, err = gw.call("GET", real_path, real_query, token)
        rel = f"{svc}/GET_{slug(path)}.json"
        if body is None:
            w.note(rel, "GET", real_path, real_query, "enterprise", status, f"NOT WRITTEN: {err}")
            continue
        if not (status == 200 and body.get("success") is True):
            # A real error is still evidence (e.g. endpoint removed since the spec): keep it, but never under a success name.
            rel = f"negative/GET_{slug(path)}__HTTP{status}.json"
        w.save(rel, body, "GET", real_path, real_query, "enterprise", status)
        if path in ID_SOURCES and body.get("success"):
            oid = first_id(body)
            if oid:
                ids[ID_SOURCES[path]] = oid
            if path == "/sgod-asset/v1/assets":
                name = first_name(body)
                if name:
                    ids["asset_q"] = name.split()[0]

    # --- negative 1: HTTP 200 with success:false (spec §4 error masking) ---
    for p in HTTP200_ERROR_CANDIDATES:
        status, body, err = gw.call("GET", p, {}, token)
        if status == 200 and isinstance(body, dict) and body.get("success") is False:
            w.save("negative/HTTP200_success_false.json", body, "GET", p, {}, "enterprise", status)
            break
        w.note("negative/HTTP200_success_false.json", "GET", p, {}, "enterprise", status, "candidate did not reproduce HTTP 200 + success:false")

    # --- negative 2 + 3: 401 with an expired token, then refresh and retry ---
    probe = "/sgod-auth/v1/users/myself"
    exp, _ = jwt_ttl(token)
    wait = (exp - time.time() + 5) if exp else None
    if wait is not None and wait <= args.max_wait_expiry:
        print(f"  waiting {int(max(wait, 0))} s for the access token to expire ...")
        time.sleep(max(wait, 0))
        stale, label = token, "HTTP401_expired_token.json"
    else:
        head, payload, sig = token.split(".") if token.count(".") == 2 else (token, "", "")
        stale, label = f"{head}.{payload}.{sig[::-1]}", "HTTP401_invalid_token.json"
        print(f"  token TTL unknown or > {args.max_wait_expiry} s: using a token with a broken signature (file named {label})")
    s1, b1, e1 = gw.call("GET", probe, {}, stale)
    if b1 is not None:
        w.save(f"negative/{label}", b1, "GET", probe, {}, "enterprise (stale token)", s1)
    if refresh:
        s2, b2, e2 = gw.call("POST", "/sgod-auth/v1/sessions/refresh", body={"refreshToken": refresh})
        new_token = ((b2 or {}).get("data") or {}).get("accessToken")
        s3, b3, e3 = (gw.call("GET", probe, {}, new_token) if new_token else (None, None, "refresh returned no accessToken"))
        flow = {
            "success": bool((b3 or {}).get("success")),
            "flow": "401 -> POST /sgod-auth/v1/sessions/refresh -> retry (each step is a real response; tokens masked)",
            "steps": [
                {"request": f"GET {probe} (stale token)", "http_status": s1, "body": b1},
                {"request": "POST /sgod-auth/v1/sessions/refresh", "http_status": s2, "body": b2},
                {"request": f"GET {probe} (refreshed token)", "http_status": s3, "body": b3},
            ],
        }
        w.save("negative/FLOW_401_refresh_retry_success.json", flow, "FLOW", probe, {}, "enterprise", f"{s1}->{s2}->{s3}")
    else:
        w.note("negative/FLOW_401_refresh_retry_success.json", "FLOW", probe, {}, "enterprise", "-", "NOT WRITTEN: login returned no refreshToken")

    # --- negative 4: chat with an enterprise-user token (spec §4: HTTP 500) + optional employee-scope samples ---
    if env("SGOD_EUSER_EMAIL", False) and env("SGOD_EUSER_PASSWORD", False):
        etoken, _ = gw.login("enterprise-users", env("SGOD_EUSER_EMAIL"), env("SGOD_EUSER_PASSWORD"))
        p = "/sgod-chat/v1/conversations"
        s4, b4, e4 = gw.call("GET", p, {"limit": LIST_LIMIT}, etoken)
        name = f"negative/HTTP{s4}_chat_conversations_enterprise_user.json"
        if b4 is not None:
            w.save(name, b4, "GET", p, {"limit": LIST_LIMIT}, "enterprise-user", s4)
        if args.employee_samples:
            for svc, path in [("asset", "/sgod-asset/v1/assets"), ("auth", "/sgod-auth/v1/users/myself"),
                              ("auth", "/sgod-auth/v1/enterprises/profile"), ("auth", "/sgod-auth/v1/enterprise-users"),
                              ("auth", "/sgod-auth/v1/departments/tree")]:
                s, b, e = gw.call("GET", path, {}, etoken)
                if b is not None:
                    w.save(f"{svc}/GET_{slug(path)}__as_enterprise_user.json", b, "GET", path, {}, "enterprise-user", s)
    else:
        w.note("negative/HTTP500_chat_conversations_enterprise_user.json", "GET", "/sgod-chat/v1/conversations", {}, "enterprise-user", "-",
               "NOT CAPTURED: SGOD_EUSER_EMAIL/SGOD_EUSER_PASSWORD not set (no enterprise-user account in the spec)")
    w.write_manifest()
    print(f"done: {sum(1 for r in w.rows if 'sha256:' in str(r[-1]))} files written; manifest at {os.path.join(args.out, 'manifest.tsv')}")


ENUM_KEYS = {"status", "assetType", "unit", "importanceLevel", "typeRequest", "statusRequest", "userType", "belongTo",
             "type", "messageType", "role", "maintenanceType", "locationAsset", "gender", "layer", "role_type",
             "source_type", "senderBelongTo", "statusChange", "action", "statusTransfer", "typeTransfer",
             "workflowPhase", "statusAsset", "statusOrigin", "subjectKind", "belong"}


def norm(k: str) -> str:
    return re.sub(r"[_\-]", "", k).lower()


NORM_ENUM_KEYS = {norm(k) for k in ENUM_KEYS}


def inventory(args) -> None:
    seen: dict[tuple[str, str], set[str]] = defaultdict(set)
    for root, _, files in os.walk(args.fixtures):
        for fn in sorted(files):
            if not fn.endswith(".json"):
                continue
            rel = os.path.relpath(os.path.join(root, fn), args.fixtures)
            def walk(x, key=None):
                if isinstance(x, dict):
                    for k, v in x.items():
                        walk(v, k)
                elif isinstance(x, list):
                    for v in x:
                        walk(v, key)
                elif (key and not key.startswith("_") and norm(key) in NORM_ENUM_KEYS and isinstance(x, str) and x
                      and not OID.match(x)):
                    seen[(key, x)].add(rel)
            walk(json.load(open(os.path.join(root, fn), encoding="utf-8")))
    enums = json.load(open(args.openapi_enums, encoding="utf-8"))["enums"] if args.openapi_enums else []
    print("| field | value | source file(s) | declared in live OpenAPI enum |")
    print("|---|---|---|---|")
    for (k, v), files in sorted(seen.items()):
        hits = sorted({e["where"] for e in enums if norm(e["field"]) == norm(k) and v in e["values"]})
        shown = "; ".join(hits[:2]) + (f" (+{len(hits) - 2})" if len(hits) > 2 else "") if hits else "—"
        print(f"| `{k}` | `{v}` | {', '.join(f'`{f}`' for f in sorted(files))} | {shown} |")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture")
    c.add_argument("--out", default="fixtures/sgod")
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--max-wait-expiry", type=int, default=1800, help="seconds to wait for a real token expiry (else broken-signature 401)")
    c.add_argument("--employee-samples", action="store_true", help="also save a few GETs made with the enterprise-user token")
    i = sub.add_parser("inventory")
    i.add_argument("--fixtures", default="fixtures/sgod")
    i.add_argument("--openapi-enums", default=None, help="JSON {enums: [{field, values, where}]} extracted from the live Swagger")
    a = ap.parse_args()
    capture(a) if a.cmd == "capture" else inventory(a)


if __name__ == "__main__":
    main()
