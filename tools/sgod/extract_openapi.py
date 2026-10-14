#!/usr/bin/env python3
"""
tools/sgod/extract_openapi.py — S Việc 1.

Trích OpenAPI JSON (khối `swaggerDoc` trong `swagger-ui-init.js`) của ba service SGOD (auth, asset,
chat), khử bí mật và sinh bảng tham số truy vấn `docs/sgod/query_params.md`.

Tải lại spec (chạy trên hạ tầng tham chiếu; GET Swagger không cần đăng nhập):
    export SGOD_BASE_URL="http://<SGOD_GATEWAY>"        # cùng tên biến với .env.example
    python tools/sgod/extract_openapi.py
    # hoặc: python tools/sgod/extract_openapi.py --gateway "http://<SGOD_GATEWAY>"

Chỉ sinh lại bảng từ các spec đã commit (offline, không cần bí mật):
    python tools/sgod/extract_openapi.py --offline [--out-dir docs/sgod]

Đầu ra:
  - docs/sgod/openapi-{auth,asset,chat}.json  (pretty-print, indent 2, có `x-sgod-capture`)
  - docs/sgod/query_params.md

Khử bí mật: bỏ `servers`; thay địa chỉ gateway và mọi IP nội bộ (RFC 1918, loopback) bằng
`<SGOD_GATEWAY>`; che email thật (giữ tên miền ví dụ RFC 2606); che JWT đầy đủ; che giá trị của mọi
biến môi trường `SGOD_*KEY|*PASSWORD|*TOKEN|*SECRET|*EMAIL` nếu có. Sau khi khử, script quét lại toàn
bộ đầu ra và DỪNG (exit 2, không ghi tệp) nếu còn sót. `security` (chỉ là tên scheme) được giữ để biết
endpoint nào cần JWT.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request

SERVICE_PATHS = {
    "auth": "/swagger/v1/auth-service/swagger-ui-init.js",
    "asset": "/swagger/v1/asset-service/swagger-ui-init.js",
    "chat": "/swagger/v1/chat-service/swagger-ui-init.js",
}

# GET cần có trong query_params.md. Nguồn: §2 = bảng "Key endpoints", §3 = bảng intent
# "Natural-language intent → API call" của docs/sgod-api-reference.md; D-V1 = danh mục tool v1
# (tools/sgod/sgod_tools.json); cand#n = docs/sgod/candidate_tools.md.
TARGET_ENDPOINTS = [
    # asset-service
    ("asset", "/sgod-asset/v1/assets", "§2 · §3 · D-V1"),
    ("asset", "/sgod-asset/v1/assets/{id}", "§2 · §3 · D-V1"),
    ("asset", "/sgod-asset/v1/assets/suggest", "§2"),
    ("asset", "/sgod-asset/v1/assets/{id}/histories", "D-V1"),
    ("asset", "/sgod-asset/v1/asset-statuses/history/{assetId}", "cand#5"),
    ("asset", "/sgod-asset/v1/asset-statuses/by-asset/{assetId}", "cand#6"),
    ("asset", "/sgod-asset/v1/categories", "§2 · D-V1"),
    ("asset", "/sgod-asset/v1/locations", "§2 · D-V1"),
    ("asset", "/sgod-asset/v1/locations/{id}", "§3 · D-V1"),
    ("asset", "/sgod-asset/v1/asset-transfers", "§2 · §3 · D-V1"),
    ("asset", "/sgod-asset/v1/asset-transfers/{id}", "D-V1"),
    ("asset", "/sgod-asset/v1/asset-transfers/summary", "D-V1"),
    ("asset", "/sgod-asset/v1/maintenance/schedules", "§2 · §3 · D-V1"),
    ("asset", "/sgod-asset/v1/maintenance/schedules/{id}", "D-V1"),
    ("asset", "/sgod-asset/v1/maintenance/records", "D-V1"),
    ("asset", "/sgod-asset/v1/maintenance/tasks", "cand#10 · D-V1"),
    ("asset", "/sgod-asset/v1/request-staff", "§2 · D-V1"),
    ("asset", "/sgod-asset/v1/request-staff/summary", "D-V1"),
    ("asset", "/sgod-asset/v1/dashboard/statistics-asset", "§2"),
    ("asset", "/sgod-asset/v1/assets/summary", "§2 · §3 · D-V1"),
    # auth-service
    ("auth", "/sgod-auth/v1/users/myself", "§2 · §3 · D-V1"),
    ("auth", "/sgod-auth/v1/session/context", "§2 · §3 · D-V1"),
    ("auth", "/sgod-auth/v1/enterprises/profile", "§2 · D-V1"),
    ("auth", "/sgod-auth/v1/enterprise-users", "§2 · cand#25 · D-V1"),
    ("auth", "/sgod-auth/v1/roles", "§2"),
    ("auth", "/sgod-auth/v1/permissions", "§2"),
    ("auth", "/sgod-auth/v1/departments/tree", "§2 · cand#26"),
    # chat-service — spec §4: chỉ token Enterprise owner dùng được (enterprise-user / sub-enterprise nhận 500)
    ("chat", "/sgod-chat/v1/conversations", "§2 · §3 · D-V1"),
    ("chat", "/sgod-chat/v1/conversations/unread-counts", "§2 · §3 · D-V1"),
    ("chat", "/sgod-chat/v1/messages", "§2"),
    ("chat", "/sgod-chat/v1/settings/current", "§2"),
]

# docs/sgod-api-reference.md §4 "Known issues & maturity" — KHÔNG làm tool.
BROKEN_ENDPOINTS = [
    ("asset", "/sgod-asset/v1/dashboard/summary", "`this.assetRepo.countSummary is not a function` (500)"),
    ("asset", "/sgod-asset/v1/maintenance/schedules/count-by-tab", "gRPC `CountMaintenanceScheduleTabs not found`"),
    ("asset", "/sgod-asset/v1/import-export/exports", "gRPC `ListAssetExports not found`"),
    ("asset", "/sgod-asset/v1/asset-offers", "`No handler found` (CQRS query chưa đăng ký)"),
    ("asset", "/sgod-asset/v1/categories-offer", "`No handler found` (CQRS query chưa đăng ký)"),
    ("asset", "/sgod-asset/v1/assets/suggest", "2026-10-14: gọi thật → `success:false`, `statusCode` 404 (route đã bỏ); dùng `GET /assets?search=`"),
    ("asset", "/sgod-asset/v1/dashboard/statistics-asset", "2026-10-14: gọi thật → HTTP 404 (`/dashboard/*` đã bỏ); dùng `GET /assets/summary`"),
]

PRIVATE_IP = re.compile(
    r"(?<![\d.])(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168|127\.\d{1,3})\.\d{1,3}\.\d{1,3}(?::\d{1,5})?(?![\d.])"
)
EMAIL = re.compile(r"[A-Za-z0-9_.+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
EXAMPLE_DOMAIN = re.compile(r"(?:^|\.)(?:example\.(?:com|net|org)|example|test|invalid|localhost)$", re.I)
JWT = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
SECRET_ENV = re.compile(r"^SGOD_.*(KEY|PASSWORD|TOKEN|SECRET|EMAIL)$")


def secret_values(gateway: str) -> list:
    """(giá trị, placeholder) cần che: địa chỉ gateway + giá trị các biến SGOD_* bí mật trong môi trường."""
    pairs = {v: "<redacted>" for k, v in os.environ.items() if SECRET_ENV.match(k) and len(v) >= 6}
    if gateway:
        hostport = re.sub(r"^https?://", "", gateway).rstrip("/")
        for v in (gateway, hostport, hostport.split(":")[0]):
            pairs[v] = "<SGOD_GATEWAY>"
    return sorted(pairs.items(), key=lambda kv: len(kv[0]), reverse=True)


def clean_str(s: str, secrets: list) -> str:
    for v, placeholder in secrets:
        s = s.replace(v, placeholder)
    s = PRIVATE_IP.sub("<SGOD_GATEWAY>", s)
    s = EMAIL.sub(lambda m: m.group(0) if EXAMPLE_DOMAIN.search(m.group(1)) else "<redacted-email>", s)
    return JWT.sub("<redacted-jwt>", s)


def is_server_list(v) -> bool:
    return isinstance(v, list) and all(isinstance(x, dict) and "url" in x for x in v)


def strip_secrets(obj, secrets: list):
    """Khử bí mật đệ quy; chỉ bỏ `servers` khi đúng là danh sách Server Object (không xoá thuộc tính schema trùng tên)."""
    if isinstance(obj, dict):
        return {
            clean_str(k, secrets): strip_secrets(v, secrets)
            for k, v in obj.items()
            if not (k == "servers" and is_server_list(v))
        }
    if isinstance(obj, list):
        return [strip_secrets(x, secrets) for x in obj]
    if isinstance(obj, str):
        return clean_str(obj, secrets)
    return obj


def leak_report(doc, secrets: list) -> dict:
    text = json.dumps(doc, ensure_ascii=False)
    found = {"private_ip": len(PRIVATE_IP.findall(text)), "jwt": len(JWT.findall(text)),
             "secret_values": sum(text.count(v) for v, _ in secrets)}
    return {k: n for k, n in found.items() if n}


def fetch_swagger_doc(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "sgod-openapi-extractor/1.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode("utf-8")
    m = re.search(r'"swaggerDoc"\s*:\s*', content)
    if not m:
        raise ValueError("không tìm thấy khối swaggerDoc")
    doc, _ = json.JSONDecoder().raw_decode(content, m.end())  # đọc đúng một object JSON (không dùng regex tham lam)
    return doc


def md_cell(s) -> str:
    return " ".join(str(s).split()).replace("|", "\\|")


def schema_type(sch: dict) -> str:
    t = sch.get("type") or ("$ref " + sch["$ref"].split("/")[-1] if "$ref" in sch else "?")
    if t == "array":
        t = f"array<{schema_type(sch.get('items', {}))}>"
    return t


def constraints(sch: dict) -> str:
    enum = sch.get("enum") or sch.get("items", {}).get("enum")
    parts = ["enum: " + " · ".join(f"`{e}`" for e in enum)] if enum else []
    for k in ("default", "minimum", "maximum", "minLength", "maxLength", "format", "pattern"):
        if k in sch:
            parts.append(f"{k}={sch[k]}")
    return "; ".join(parts)


def generate_query_params_table(specs: dict, out_file: str):
    cap = {s: d.get("x-sgod-capture", {}).get("date", "?") for s, d in specs.items()}
    lines = [
        "# Bảng tham số truy vấn SGOD (S Việc 1)",
        "",
        "> Sinh tự động bằng `python tools/sgod/extract_openapi.py --offline` từ `openapi-auth.json`, "
        "`openapi-asset.json`, `openapi-chat.json` — **không sửa tay**. Spec lấy từ `swagger-ui-init.js` qua "
        "`<SGOD_GATEWAY>` trên hạ tầng tham chiếu, ngày chụp: "
        + ", ".join(f"{s} {d}" for s, d in cap.items()) + ".",
        "> Nguồn: §2/§3 = `docs/sgod-api-reference.md`; D-V1 = `tools/sgod/sgod_tools.json`; "
        "cand#n = `docs/sgod/candidate_tools.md`. Swagger có thể lệch API thật — S Việc 4 xác minh bằng JWT thật.",
        "> Chat (§4): mọi endpoint `/sgod-chat/v1` chỉ chạy với token Enterprise owner (enterprise-user và "
        "sub-enterprise nhận 500) → tool chat chỉ mở cho `company_admin`.",
        "",
        "| # | Dịch vụ | Phương thức | Đường dẫn | Tham số (vị trí) | Kiểu | Bắt buộc | Enum / ràng buộc | Mô tả tham số | Mục đích endpoint | Nguồn |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    missing, intent = [], 0
    for i, (svc, path, src) in enumerate(TARGET_ENDPOINTS, 1):
        intent += "§3" in src
        op = specs[svc].get("paths", {}).get(path, {}).get("get")
        if op is None:
            missing.append(path)
            lines.append(f"| {i} | `{svc}` | `GET` | `{path}` | — | — | — | — | — | "
                         f"**không có trong Swagger live (chụp {cap[svc]})** — không làm tool cho tới khi S Việc 4 xác minh | {src} |")
            continue
        params = specs[svc]["paths"][path].get("parameters", []) + op.get("parameters", [])
        summary = md_cell(op.get("summary") or op.get("description", ""))
        if not params:
            lines.append(f"| {i} | `{svc}` | `GET` | `{path}` | — | — | — | — | — | {summary} | {src} |")
            continue
        cols = [[], [], [], [], []]
        for p in params:
            sch = p.get("schema", {})
            cols[0].append(f"`{p.get('name')}` ({p.get('in')})")
            cols[1].append(schema_type(sch))
            cols[2].append("có" if p.get("required") else "không")
            cols[3].append(md_cell(constraints(sch)) or "—")
            cols[4].append(md_cell(p.get("description", "")) or "—")
        lines.append(f"| {i} | `{svc}` | `GET` | `{path}` | " + " | ".join("<br>".join(c) for c in cols)
                     + f" | {summary} | {src} |")

    lines += [
        "",
        f"Tổng: {len(TARGET_ENDPOINTS)} GET; bảng intent §3 có {intent} GET khác nhau — tất cả đều có dòng ở trên"
        + (f"; {len(missing)} GET không còn trong Swagger live: " + ", ".join(f"`{m}`" for m in missing) if missing else "")
        + ".",
        "",
        "## Endpoint hỏng — broken, not a tool (spec §4)",
        "",
        "| Dịch vụ | Phương thức | Đường dẫn | Hiện tượng (spec §4) | Trong Swagger live? |",
        "|---|---|---|---|---|",
    ]
    for svc, path, symptom in BROKEN_ENDPOINTS:
        live = "có" if "get" in specs[svc].get("paths", {}).get(path, {}) else f"không (chụp {cap[svc]})"
        lines.append(f"| `{svc}` | `GET` | `{path}` | {symptom} | {live} |")
    lines += [
        "| `chat` | mọi | `/sgod-chat/v1/*` với token enterprise-user / sub-enterprise | 500 (tái hiện 8/8); "
        "lỗi JWKS `16 UNAUTHENTICATED` không ổn định | có — chỉ dùng với token Enterprise owner |",
        "",
        "Lỗi SGOD thường trả HTTP 200 kèm `body.success=false` và `body.statusCode` là mã thật (spec §1, §4).",
    ]
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Trích OpenAPI SGOD từ swagger-ui-init.js và sinh query_params.md")
    ap.add_argument("--gateway", default=os.environ.get("SGOD_BASE_URL") or os.environ.get("SGOD_GATEWAY", ""),
                    help="base URL của gateway (mặc định: biến SGOD_BASE_URL như .env.example)")
    ap.add_argument("--offline", action="store_true", help="không tải; chỉ sinh lại bảng từ spec trong --out-dir")
    ap.add_argument("--out-dir", default="docs/sgod", help="thư mục đọc/ghi spec và bảng")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    gateway = "" if args.offline else args.gateway.rstrip("/")
    specs = {}
    if gateway:
        secrets = secret_values(gateway)
        today = dt.date.today().isoformat()
        for svc, rel in SERVICE_PATHS.items():
            print(f"[*] tải {svc}-service ...", flush=True)
            try:
                raw = fetch_swagger_doc(gateway + rel)
            except Exception as e:  # noqa: BLE001 — báo lỗi rồi dừng, không ghi bảng thiếu
                print(f"[!] lỗi khi tải {svc}: {type(e).__name__}: {clean_str(str(e), secrets)}", file=sys.stderr)
                return 1
            doc = strip_secrets(raw, secrets)
            leaks = leak_report(doc, secrets)
            if leaks:
                print(f"[!] {svc}: còn chuỗi giống bí mật sau khi khử {leaks} — không ghi tệp", file=sys.stderr)
                return 2
            doc["x-sgod-capture"] = {"date": today, "source": f"<SGOD_GATEWAY>{rel}",
                                     "tool": "tools/sgod/extract_openapi.py"}
            specs[svc] = doc
        for svc, doc in specs.items():
            out_json = os.path.join(args.out_dir, f"openapi-{svc}.json")
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2, ensure_ascii=False)
                f.write("\n")
            n_ops = sum(1 for it in doc["paths"].values() for m in it if m in ("get", "post", "put", "patch", "delete"))
            print(f"  -> {out_json}: {len(doc['paths'])} paths, {n_ops} operations")
    else:
        print("[*] offline: đọc spec đã commit")
        for svc in SERVICE_PATHS:
            spec_file = os.path.join(args.out_dir, f"openapi-{svc}.json")
            if not os.path.exists(spec_file):
                print(f"[!] thiếu {spec_file}; chạy lại với --gateway trên hạ tầng tham chiếu", file=sys.stderr)
                return 1
            with open(spec_file, encoding="utf-8") as fp:
                specs[svc] = json.load(fp)
    out_table = os.path.join(args.out_dir, "query_params.md")
    generate_query_params_table(specs, out_table)
    print(f"[*] đã ghi {out_table}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
