#!/usr/bin/env python3
"""
tools/sgod/extract_openapi.py

Script tự động trích xuất, khử bí mật (sanitization) và lập bảng query parameters
từ Swagger UI Gateway nội bộ của SGOD.

Cách cấu hình địa chỉ Gateway (chọn 1 trong 2 cách):
  1. Biến môi trường:
       export SGOD_GATEWAY="http://<SGOD_IP>:5000"
       python tools/sgod/extract_openapi.py
  2. Tham số dòng lệnh:
       python tools/sgod/extract_openapi.py --gateway "http://<SGOD_IP>:5000"

Đầu ra:
  - docs/sgod/openapi-auth.json
  - docs/sgod/openapi-asset.json
  - docs/sgod/openapi-chat.json
  - docs/sgod/query_params.md
"""

import argparse
import json
import os
import re
import sys
import urllib.request

# Đường dẫn tương đối tới các tệp khởi tạo Swagger của từng service
SERVICE_PATHS = {
    "auth": "/swagger/v1/auth-service/swagger-ui-init.js",
    "asset": "/swagger/v1/asset-service/swagger-ui-init.js",
    "chat": "/swagger/v1/chat-service/swagger-ui-init.js",
}

# Danh sách các read-only endpoints (GET) trọng tâm cần xây dựng bảng tham số
TARGET_ENDPOINTS = [
    ("asset", "/sgod-asset/v1/assets"),
    ("asset", "/sgod-asset/v1/assets/{id}"),
    ("asset", "/sgod-asset/v1/assets/suggest"),
    ("asset", "/sgod-asset/v1/assets/{id}/histories"),
    ("asset", "/sgod-asset/v1/asset-statuses/history/{assetId}"),
    ("asset", "/sgod-asset/v1/asset-statuses/by-asset/{assetId}"),
    ("asset", "/sgod-asset/v1/maintenance/schedules"),
    ("asset", "/sgod-asset/v1/maintenance/schedules/{id}"),
    ("asset", "/sgod-asset/v1/maintenance/records"),
    ("asset", "/sgod-asset/v1/maintenance/tasks"),
    ("asset", "/sgod-asset/v1/asset-transfers"),
    ("asset", "/sgod-asset/v1/asset-transfers/{id}"),
    ("asset", "/sgod-asset/v1/request-staff"),
    ("asset", "/sgod-asset/v1/locations"),
    ("auth", "/sgod-auth/v1/users/myself"),
    ("auth", "/sgod-auth/v1/departments/tree"),
    ("auth", "/sgod-auth/v1/enterprises/profile"),
    ("auth", "/sgod-auth/v1/roles"),
    ("auth", "/sgod-auth/v1/enterprise-users"),
]


def strip_secrets(obj, gateway_host: str = ""):
    """Khử địa chỉ IP, emails, secrets và thông tin server nội bộ."""
    if isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
            if k in ["servers", "security", "securityDefinitions"]:
                continue
            if isinstance(v, str):
                v_clean = v
                if gateway_host:
                    v_clean = v_clean.replace(gateway_host, "<SGOD_GATEWAY_HOST>")
                # Mask mọi IP dải private 10.x.x.x
                v_clean = re.sub(r"10\.\d+\.\d+\.\d+(:\d+)?", "<SGOD_GATEWAY_HOST>", v_clean)
                # Mask emails
                v_clean = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "<redacted-email>", v_clean)
                res[k] = v_clean
            else:
                res[k] = strip_secrets(v, gateway_host)
        return res
    elif isinstance(obj, list):
        return [strip_secrets(item, gateway_host) for item in obj]
    elif isinstance(obj, str):
        v_clean = obj
        if gateway_host:
            v_clean = v_clean.replace(gateway_host, "<SGOD_GATEWAY_HOST>")
        v_clean = re.sub(r"10\.\d+\.\d+\.\d+(:\d+)?", "<SGOD_GATEWAY_HOST>", v_clean)
        v_clean = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "<redacted-email>", v_clean)
        return v_clean
    else:
        return obj


def fetch_spec(url: str, gateway_host: str = "") -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "SGOD-Extractor/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read().decode("utf-8")

    m = re.search(r'"swaggerDoc":\s*(\{.*\}),\s*"customOptions"', content, re.DOTALL)
    if not m:
        m = re.search(r'"swaggerDoc":\s*(\{.*\}),', content, re.DOTALL)
    if not m:
        raise ValueError(f"Không tìm thấy swaggerDoc JSON trong {url}")

    raw_doc = json.loads(m.group(1))
    return strip_secrets(raw_doc, gateway_host)


def generate_query_params_table(specs: dict, out_file: str):
    lines = [
        "# Bảng tham số truy vấn SGOD (Query Parameters Table)",
        "",
        "> Sinh tự động từ `openapi-auth.json`, `openapi-asset.json`, `openapi-chat.json` phục vụ nhóm Data (D Việc 1) xây dựng Entity Pools và Param Sampler.",
        "",
        "| # | Dịch vụ | Phương thức | Đường dẫn API (Path) | Tham số truy vấn (Query / Path / Header) | Kiểu dữ liệu | Giá trị Enum / Ràng buộc | Mục đích & Ý nghĩa |",
        "|---|---|---|---|---|---|---|---|",
    ]

    idx = 1
    for svc, path in TARGET_ENDPOINTS:
        spec = specs.get(svc, {})
        p_data = spec.get("paths", {}).get(path, {})
        get_data = p_data.get("get", {})
        summary = get_data.get("summary", get_data.get("description", ""))
        parameters = get_data.get("parameters", [])

        if not parameters:
            lines.append(f"| {idx} | `{svc}` | `GET` | `{path}` | — | — | — | {summary} |")
            idx += 1
        else:
            param_strs = []
            type_strs = []
            enum_strs = []
            for param in parameters:
                p_in = param.get("in")
                p_name = param.get("name")
                p_type = param.get("type", param.get("schema", {}).get("type", "string"))
                p_enum = param.get("enum", param.get("schema", {}).get("enum", []))
                p_desc = param.get("description", "")

                p_display = f"`{p_name}` ({p_in})"
                param_strs.append(p_display)
                type_strs.append(p_type)
                if p_enum:
                    enum_strs.append(f"`{p_name}`: " + str(p_enum))
                elif p_desc:
                    enum_strs.append(f"`{p_name}`: {p_desc}")
                else:
                    enum_strs.append("—")

            lines.append(
                f"| {idx} | `{svc}` | `GET` | `{path}` | {'<br>'.join(param_strs)} | {'<br>'.join(type_strs)} | {'<br>'.join(enum_strs)} | {summary} |"
            )
            idx += 1

    lines.extend([
        "",
        "## Các Endpoint bị hỏng (Broken Endpoints — Mục 4 trong Spec)",
        "",
        "> **CẢNH BÁO**: Tuyệt đối KHÔNG biến các endpoint này thành Tool (Broken — Not a tool):",
        "",
        "| Dịch vụ | Phương thức | Đường dẫn API | Mã lỗi / Hiện tượng | Lý do loại trừ |",
        "|---|---|---|---|---|",
        "| `asset` | `GET` | `/sgod-asset/v1/maintenance/schedules/count-by-tab` | HTTP 500 | Lỗi server nội bộ, không gọi được |",
        "| `asset` | `GET` | `/sgod-asset/v1/inventory/overview` | HTTP 500 / Timeout | Endpoint chưa hoàn thiện |",
        "| `chat` | `GET` | `/sgod-chat/v1/conversations` (non-owner) | HTTP 500 | Token non-owner bị lỗi 500, chỉ admin mới dùng được |",
    ])

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Trích xuất OpenAPI specs từ Swagger Gateway và tạo query_params.md")
    parser.add_argument(
        "--gateway",
        default=os.environ.get("SGOD_GATEWAY", ""),
        help="Địa chỉ base của SGOD Gateway (hoặc đặt biến SGOD_GATEWAY)",
    )
    parser.add_argument("--out-dir", default="docs/sgod", help="Thư mục xuất kết quả")
    args = parser.parse_args()

    gateway = args.gateway.rstrip("/")
    if not gateway:
        print("[!] Lỗi: Chưa cung cấp địa chỉ Gateway.")
        print("    Vui lòng dùng: export SGOD_GATEWAY=\"http://<IP_GATEWAY>:5000\" hoặc thêm cờ --gateway")
        sys.exit(1)

    os.makedirs(args.out_dir, exist_ok=True)
    specs = {}

    for svc, rel_path in SERVICE_PATHS.items():
        url = gateway + rel_path
        print(f"[*] Đang tải {svc} từ endpoint...")
        try:
            doc = fetch_spec(url, gateway_host=gateway)
            specs[svc] = doc
            out_json = os.path.join(args.out_dir, f"openapi-{svc}.json")
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2, ensure_ascii=False)
            print(f"  -> Đã lưu {out_json} ({len(doc.get('paths', {}))} paths)")
        except Exception as e:
            print(f"  -> Lỗi khi tải {svc}: {e}")

    out_table = os.path.join(args.out_dir, "query_params.md")
    print(f"[*] Đang tạo bảng tham số: {out_table}...")
    generate_query_params_table(specs, out_table)
    print("  -> Hoàn tất tạo query_params.md")


if __name__ == "__main__":
    main()
