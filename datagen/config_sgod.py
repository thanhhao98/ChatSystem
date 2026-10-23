"""Single config for the SGOD data-generation pipeline — edit THIS (and prompts/) to retarget.

Ported from the reference system (POC v1) datagen config. The pipeline
itself is app-agnostic; everything that knows about the SGOD domain lives here or in
`datagen/prompts/`. The retarget checklist (kept from the POC v1 docstring, adapted):

  1. TOOL_DEFS_PATH  -> tools/sgod/sgod_tools.json  (list of {"type","function","x_sgod"}).
  2. POLICY_PATH     -> tools/sgod/tool_policy.json ({tool: {"writes": bool, "roles": [...]}}).
     Permissions are derived from that file ONLY (see audit_test_cases.load_permissions).
  3. ROLES_PATH      -> tools/sgod/roles.json (chat-role vocabulary + aliases) -> ROLE_MAP.
  4. DOMAIN_SYSTEM   -> generation system prompt (domain + language + example entities).
  5. CATEGORY_HINTS  -> scenario taxonomy (bucket -> one-line hint). NO multi-turn / multi_step.
  6. ENTITY_POOLS / PARAM_SAMPLER / BUCKET_PLAN / TRACKB_BUCKET_PLAN -> entity + tool coverage.
Everything else (anti-leakage, batched generation, multi-LLM consensus, schema validation,
parity row formatting) carries over unchanged.

Every block marked TODO(D-Việc-3) is a STUB with 1-2 worked entries. The Data interns fill them
in from `tools/sgod/sgod_tools.json`, `fixtures/sgod/` and `docs/personas_sgod.md`. POC v1 values
are kept in comments as examples of the expected density.

Nothing here imports from the reference system (POC v1). No secrets: OPENAI_API_KEY / OPENAI_BASE_URL are
read from the environment at call time only (see `require_openai_client`).
"""
import json
import os
import random
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def repo_path(p) -> Path:
    """Resolve a CLI/config path: absolute paths are kept, relative ones are repo-rooted."""
    p = Path(p)
    return p if p.is_absolute() else REPO / p


# ───────────────────────────────────────────────────────────────────────────
# 0. FILE LOCATIONS (contract 4: tool catalogue shape; contract 3: roles)
# ───────────────────────────────────────────────────────────────────────────
TOOL_DEFS_PATH = os.environ.get("TOOL_DEFS_PATH", "tools/sgod/sgod_tools.json")
POLICY_PATH = os.environ.get("TOOL_POLICY_PATH", "tools/sgod/tool_policy.json")
ROLES_PATH = os.environ.get("ROLES_PATH", "tools/sgod/roles.json")

PREAMBLE_V1_PATH = "prompts/system_preamble_v1.txt"   # SGOD rows: {role_vi}/{full_name}/{user_id}
#   (+ optional {role}) filled from GENERIC_CONTEXT / role_names_vi
PREAMBLE_V0_PATH = "prompts/system_preamble_v0.txt"   # public/replay rows (neutral)
FIXED_REPLIES_PATH = "prompts/fixed_replies.json"     # REFUSAL_VI / DEFLECT_VI
PROMPT_DIR = "datagen/prompts"                        # training-data prompts (interns edit)
PROMPT_DIR_EVAL = "datagen/prompts_eval"              # eval-augmentation prompts (DISJOINT set)
DATA_DIR = "data/sgod"                                # every stage output lands here

# ───────────────────────────────────────────────────────────────────────────
# 1. LLM MODEL PLACEHOLDERS — models are switched in ONE place.
#    Scripts read these as their --model defaults. The values are placeholder names; the real
#    served name depends on the OPENAI_BASE_URL gateway of the reference infrastructure, so the
#    operator sets it through the environment (GEN_MODEL, LABEL_MODELS = space-separated list,
#    ARBITER_MODEL) — the same names run_pipeline.sh reads. Never commit a gateway-specific id here;
#    files written under data/sgod/ only carry model_alias() (the part after the last "/").
# ───────────────────────────────────────────────────────────────────────────
GEN_MODEL = os.environ.get("GEN_MODEL") or "gpt-4o"           # generate_scenarios / generate_irrelevance
LABEL_MODELS = (os.environ.get("LABEL_MODELS") or "").split() or ["gpt-4o", "gpt-4o-mini"]
#                                                             # label_scenarios + verify_trainset stage C (consensus)
ARBITER_MODEL = os.environ.get("ARBITER_MODEL") or "gpt-4o"   # polish_scenarios / audit_test_cases pass 2
#                                  (for eval_v1 augmentation MUST differ from the GPT under test: SCORED_MODEL)

# ───────────────────────────────────────────────────────────────────────────
# 2. ROLES — chat roles come from tools/sgod/roles.json (contract 3). ROLE_MAP maps the labels
#    used in case files ("admin", "employee") to the chat-role vocabulary the policy uses.
#    Never key on SGOD role ObjectIds.
# ───────────────────────────────────────────────────────────────────────────
_ROLE_MAP_FALLBACK = {"admin": "company_admin", "employee": "employee"}
_CHAT_ROLES_FALLBACK = ["employee", "company_admin", "system_admin"]

_ROLE_NAMES_VI_FALLBACK = {
    "employee": "Nhân viên",
    "company_admin": "Quản trị viên doanh nghiệp",
    "system_admin": "Quản trị hệ thống",
}

# Generic per-user context for the {full_name} / {user_id} preamble slots. Training rows carry
# GENERIC values (the model learns structure, not ids); serve fills the real user. MUST equal
# tools/sgod/validate_tools.py GENERIC_CONTEXT so token budgets are measured on the same text.
GENERIC_CONTEXT = {"full_name": "Người dùng", "user_id": "usr-001"}


def load_role_names_vi(path=None):
    """Vietnamese role labels for the {role_vi} slot: roles.json "role_names_vi" when present."""
    p = repo_path(path or ROLES_PATH)
    names = dict(_ROLE_NAMES_VI_FALLBACK)
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(d, dict) and isinstance(d.get("role_names_vi"), dict):
                names.update({str(k): str(v) for k, v in d["role_names_vi"].items()})
        except json.JSONDecodeError:
            pass
    return names


ROLE_NAMES_VI = load_role_names_vi()


def load_roles(path=None):
    """Return (chat_roles: list[str], role_map: dict) from roles.json, tolerant to its shape.

    Accepted shapes (the S-team owns the file; the first matching rule wins):
      {"roles": [..], "aliases": {"admin": "company_admin"}, "tier_to_role": {...}}
      {"roles": {"company_admin": {...}, "employee": {...}}, ...}
      ["employee", "company_admin", "system_admin"]
      {"company_admin": {...}, "employee": {...}}          # role -> anything
    Missing file -> fallback vocabulary + {"admin": "company_admin", "employee": "employee"}.
    """
    p = repo_path(path or ROLES_PATH)
    roles, aliases = list(_CHAT_ROLES_FALLBACK), {}
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"WARNING: {p} is not valid JSON ({exc}); using fallback roles", file=sys.stderr)
            d = None
        if isinstance(d, list):
            roles = [str(r) for r in d]
        elif isinstance(d, dict):
            r = d.get("roles") or d.get("chat_roles")
            if isinstance(r, list):
                roles = [str(x) for x in r]
            elif isinstance(r, dict):
                roles = list(r.keys())
            elif "tiers" in d or "tier_to_role" in d or "aliases" in d or "role_map" in d:
                tiers = d.get("tiers") or d.get("tier_to_role") or {}
                roles = sorted(set(tiers.values()) | set(_CHAT_ROLES_FALLBACK))
            else:
                roles = list(d.keys())
            aliases = dict(d.get("aliases") or d.get("role_map") or {})
    role_map = dict(_ROLE_MAP_FALLBACK)
    role_map.update({str(k): str(v) for k, v in aliases.items()})
    for r in roles:
        role_map.setdefault(r, r)
    return roles, role_map


CHAT_ROLES, ROLE_MAP = load_roles()
CASE_ROLES = ["employee", "admin"]   # labels used in case files / bucket plans (mapped via ROLE_MAP)

# ───────────────────────────────────────────────────────────────────────────
# 3. DOMAIN SYSTEM PROMPT for net-new query generation.
#    TODO(D-Việc-3): rewrite for SGOD (entities: assetCode "000000001", asset names, locations,
#    categories, maintenance schedule status ...) from fixtures/sgod/ and docs/personas_sgod.md.
#    A file datagen/prompts/domain_system.md, when present, OVERRIDES this string.
# ───────────────────────────────────────────────────────────────────────────
DOMAIN_SYSTEM = """Bạn tạo dữ liệu kiểm thử cho một chatbot quản lý tài sản doanh nghiệp tiếng Việt (nền tảng SGOD).
Tạo các câu truy vấn NGƯỜI DÙNG THẬT sẽ gõ — KHÔNG phải diễn giải lại của nhau, mà là các TÌNH HUỐNG KHÁC NHAU.
Đa dạng hoá: tên tài sản (vd "Laptop Dell Latitude", "Máy in Canon tầng 3"), mã tài sản (vd 000000012),
vị trí/kho, danh mục, trạng thái, lịch bảo trì, số lượng, mốc thời gian.
Trộn văn phong: trang trọng, thân mật, viết tắt, có lỗi chính tả nhẹ, dùng "ạ/nhé/giùm".
Chỉ trả về MỘT mảng JSON các chuỗi câu truy vấn tiếng Việt. KHÔNG giải thích, KHÔNG nêu tên công cụ."""
# POC v1 example (for density): mentioned asset codes AS-021/AS-117, offices Hà Nội/Đà Nẵng/Sài Gòn,
# statuses available/assigned/maintenance/retired/lost, conditions new/good/fair/poor.

# ───────────────────────────────────────────────────────────────────────────
# 4. CATEGORY HINTS — scenario taxonomy: category -> one-line generation hint.
#    Single-turn only. The POC v1 "multi_step" category is REMOVED on purpose (phase 2 = single turn).
#    TODO(D-Việc-3): extend to cover every tool in sgod_tools.json (~20 read-only tools).
#    A file datagen/prompts/category_<name>.md, when present, OVERRIDES that category's hint.
# ───────────────────────────────────────────────────────────────────────────
CATEGORY_HINTS = {
    "my_assets": "NGƯỜI DÙNG hỏi về TÀI SẢN của CHÍNH MÌNH / của doanh nghiệp mình: tài sản tôi đang có, "
                 "danh sách tài sản, tìm kiếm theo tên hoặc mã máy (search, limit; KHÔNG có filter status/location)",
    "asset_detail": "xem chi tiết, cấu hình, lịch sử biến động MỘT tài sản cụ thể theo tên/mã (get_asset, get_asset_histories) "
                    "hoặc thống kê tài sản toàn công ty của Giám đốc (get_asset_statistics)",
    "category": "tra cứu danh mục phân loại tài sản trong hệ thống (list_categories)",
    "location": "tra cứu thông tin về vị trí, phòng ban, kho bãi lưu trữ tài sản (list_locations, get_location)",
    "maintenance_schedule": "tra cứu lịch bảo dưỡng định kỳ đang hiệu lực hoặc đã xong (list_maintenance_schedules, get_maintenance_schedule)",
    "maintenance_record": "tra cứu danh sách hồ sơ, nhật ký, biên bản nghiệm thu bảo trì đã hoàn tất (list_maintenance_records)",
    "maintenance_task": "tra cứu danh sách các đầu việc/hạng mục bảo trì thuộc một lịch cụ thể (list_maintenance_tasks; bắt buộc maintenanceScheduleId)",
    "user_profile": "tra cứu thông tin hồ sơ tài khoản đang đăng nhập (get_my_profile)",
    "user_permission": "tra cứu quyền hạn, vai trò chức năng của tài khoản đang đăng nhập (get_my_permissions)",
    "user_management": "tra cứu danh sách nhân sự doanh nghiệp (list_enterprise_users; admin-only, employee hỏi -> refusal row)",
    "asset_transfer": "tra cứu danh sách phiếu chuyển giao tài sản (list_asset_transfers; onlyMine, limit), chi tiết phiếu hoặc tổng hợp tab (get_transfer_summary)",
    "staff_request": "tra cứu danh sách hoặc số lượng tổng hợp yêu cầu của nhân viên (list_staff_requests, get_staff_request_summary)",
    "chat_conversation": "tra cứu danh sách cuộc trò chuyện hoặc số tin nhắn chưa đọc (list_my_conversations, get_unread_counts; admin-only, employee hỏi -> refusal row)",
    "permission_denial": "NGƯỜI DÙNG YÊU CẦU hành động không được phép: thao tác ghi (Tạo/Sửa/Xoá/Duyệt -> expected_tool: null) "
                         "hoặc nhân viên cố truy cập công cụ quản trị (expected_permission: denied)",
    "out_of_scope": "câu lạc đề hoặc ngoài phạm vi quản lý tài sản (thời tiết, lập trình, tán gẫu, chào hỏi)",
}
# POC v1 example hints (kept for reference — the wording style is what matters):
#   "multi_filter": "liệt kê/tìm tài sản với NHIỀU bộ lọc CÙNG LÚC ... luôn có ≥2 điều kiện lọc"
#   "admin_daily_read": "việc đọc hằng ngày của quản trị: đơn chờ duyệt, dashboard, thống kê ..."

# ───────────────────────────────────────────────────────────────────────────
# 5. BUCKET_PLAN — (category, role, count) for a representative, READ-heavy benchmark.
#    Roles are CASE roles ("employee" / "admin"); ROLE_MAP turns "admin" into "company_admin".
#    TODO(D-Việc-3): size to the eval_v1 targets (≥15/tool, every role, ≥10% null, ≥10% denied).
# ───────────────────────────────────────────────────────────────────────────
BUCKET_PLAN = [
    ("my_assets", "employee", 12), ("my_assets", "admin", 8),
    ("asset_detail", "employee", 8), ("asset_detail", "admin", 8),
    ("maintenance", "admin", 8), ("maintenance", "employee", 4),
    ("permission_denial", "employee", 6),
    ("out_of_scope", "employee", 3), ("out_of_scope", "admin", 3),
]  # POC v1: ~500 total, ~85% reads, roughly balanced roles

# ───────────────────────────────────────────────────────────────────────────
# 6. ENTITY POOLS — realistic values injected into generation prompts (surface diversity).
#    Trích xuất 100% từ fixtures/sgod/ bản 21/10 (PR #15).
#    TUYỆT ĐỐI KHÔNG mang tiền tố [SEED] vào thực thể; mã/ID lấy từ hệ thống thật.
# ───────────────────────────────────────────────────────────────────────────
ENTITY_POOLS = {
    # Mã tài sản tuần tự từ fixtures/sgod/asset/GET_assets.json
    "asset_code": [
        "000000001", "000000003", "000000004", "000000005",
        "000000006", "000000007", "000000008",
    ],
    # Tên tài sản đã loại bỏ hoàn toàn tiền tố [SEED]
    "asset_name": [
        "QA Test Laptop",
        "ZZTEST-2610100426 x4",
        "Laptop Dell Latitude 5440",
        "Màn hình LG 27UP850",
        "Máy in HP LaserJet Pro M404dn",
        "Máy lạnh Daikin FTKB50 2HP",
        "Mực in HP 76A",
    ],
    # Từ khoá tìm kiếm trích xuất từ tên hoặc mã (khớp search của list_my_assets)
    "search_keyword": [
        "Laptop", "Dell Latitude", "Máy in", "HP LaserJet",
        "Daikin", "Màn hình LG", "Mực in", "QA Test", "ZZTEST", "000000006",
    ],
    # Danh mục tài sản từ GET_categories.json
    "category": [
        "QA Test Category",
        "ZZTEST-2610100426 Ghe (sua)",
        "Thiết bị văn phòng",
        "Thiết bị CNTT",
        "Điện lạnh",
        "Vật tư tiêu hao",
    ],
    # Id vị trí/kho từ GET_locations.json
    "location_id": [
        "6ac9bec727541dacd0a77f80",
        "6ac9bec627541dacd0a77f7f",
        "6ac9bec627541dacd0a77f7e",
        "6ac9be9627541dacd0a77e89",
        "6ac9be9627541dacd0a77e8a",
        "6ac9be9627541dacd0a77e8b",
        "6aa2c144da46d70ee2f491c0",
        "6ad615353b0f8e12e2f190ba",
        "6ad615353b0f8e12e2f190bb",
        "6ad615353b0f8e12e2f190bc",
        "6ad615353b0f8e12e2f190bd",
        "6ad615353b0f8e12e2f190be",
    ],
    # Mã lịch bảo trì thật từ fixtures/sgod/asset/GET_maintenance_schedules.json
    "schedule_id": [
        "6ad615353b0f8e12e2f1910d",  # Lịch bảo trì máy in HP LaserJet Pro M404dn
        "6ad615353b0f8e12e2f190e4",  # Lịch bảo trì máy lạnh Daikin FTKB50 2HP
    ],
    # Trạng thái lịch bảo trì chuẩn OpenAPI (enum: active, completed)
    "schedule_status": [
        "active",
        "completed",
    ],
    # Đầu việc bảo trì thật từ GET_maintenance_tasks.json (đã bỏ [SEED])
    "task_title": [
        "Thay trống mực (drum)",
        "Bảo dưỡng máy lạnh định kỳ",
        "Kiểm tra đầu phun máy in",
    ],
    # Trạng thái công việc bảo trì
    "task_status": [
        "processing",
        "scheduled",
        "completed",
        "on-hold",
    ],
    # Trạng thái tài khoản người dùng từ openapi-auth / GET_enterprise_users.json
    "user_status": [
        "Active",
        "Blocked",
        "Pending",
        "Verified",
    ],
    # ID phiếu điều chuyển thật từ GET_asset_transfers.json
    "transfer_id": [
        "6ac9bd3e27541dacd0a77c2d",
        "6ac9be1627541dacd0a77df0",
        "6ac9be9f27541dacd0a77f0d",
        "6ac9bece27541dacd0a78006",
        "6ac9c52451e750872e755fad",
    ],
    "transfer_status": ["accept"],
    "request_status": ["cancel", "confirm", "deny", "pending"],
    "request_type": ["change-status-maintenance"],
    # Giới hạn số lượng hiển thị (phân trang limit)
    "quantity": ["3", "5", "10", "20"],
    # Sắc thái câu thoại / văn phong
    "register": [
        "trang trọng",
        "thân mật",
        "viết tắt",
        "có lỗi chính tả nhẹ",
        "ra lệnh ngắn gọn",
        "lịch sự dùng ạ/nhé",
        "không dấu",
    ],
}


def _pick(rng, key):
    return rng.choice(ENTITY_POOLS[key])


# ───────────────────────────────────────────────────────────────────────────
# 7. PARAM SAMPLER — tool -> fn(rng) -> {slot_label_vi: concrete_value}.
#    Phủ đủ 22/22 tools SGOD (100% schema-valid).
#    Lưu ý: list_my_assets TUYỆT ĐỐI KHÔNG có bộ lọc status/location/category.
# ───────────────────────────────────────────────────────────────────────────
PARAM_SAMPLER = {
    # ── Nhóm 1: Tài sản & Doanh nghiệp (Thehy-IT phụ trách, 8 tools) ──
    # 1. list_my_assets: schema có search, limit, cursor (KHÔNG có status)
    "list_my_assets": lambda r: r.choice([
        {},
        {"từ khoá": _pick(r, "search_keyword")},
        {"số lượng": _pick(r, "quantity")},
        {"từ khoá": _pick(r, "search_keyword"), "số lượng": _pick(r, "quantity")},
    ]),
    # 2. get_asset: schema có asset_ref (bắt buộc)
    "get_asset": lambda r: r.choice([
        {"tên tài sản": _pick(r, "asset_name")},
        {"mã tài sản": _pick(r, "asset_code")},
    ]),
    # 3. get_asset_histories: schema có asset_ref (bắt buộc)
    "get_asset_histories": lambda r: r.choice([
        {"tên tài sản": _pick(r, "asset_name")},
        {"mã tài sản": _pick(r, "asset_code")},
    ]),
    # 4. list_categories: schema có limit
    "list_categories": lambda r: r.choice([
        {},
        {"số lượng": _pick(r, "quantity")},
    ]),
    # 5. list_locations: schema có limit
    "list_locations": lambda r: r.choice([
        {},
        {"số lượng": _pick(r, "quantity")},
    ]),
    # 6. get_location: schema có location_id (bắt buộc)
    "get_location": lambda r: {
        "mã vị trí": _pick(r, "location_id")
    },
    # 7. get_enterprise_profile: không tham số (admin-only)
    "get_enterprise_profile": lambda r: {},
    # 8. get_asset_statistics: không tham số (admin-only)
    "get_asset_statistics": lambda r: {},

    # ── Nhóm 2: Bảo trì, Hồ sơ & Nhân sự (BaoMyTH phụ trách, 7 tools) ──
    # 9. list_maintenance_schedules: schema có status, limit
    "list_maintenance_schedules": lambda r: r.choice([
        {},
        {"trạng thái": _pick(r, "schedule_status")},
        {"số lượng": _pick(r, "quantity")},
        {"trạng thái": _pick(r, "schedule_status"), "số lượng": _pick(r, "quantity")},
    ]),
    # 10. get_maintenance_schedule: schema có schedule_id (bắt buộc ID thật)
    "get_maintenance_schedule": lambda r: {
        "mã lịch": _pick(r, "schedule_id")
    },
    # 11. list_maintenance_records: schema có limit
    "list_maintenance_records": lambda r: r.choice([
        {},
        {"số lượng": _pick(r, "quantity")},
    ]),
    # 12. list_maintenance_tasks: schema BẮT BUỘC maintenanceScheduleId, có thể kèm limit
    "list_maintenance_tasks": lambda r: r.choice([
        {"mã lịch bảo trì": _pick(r, "schedule_id")},
        {"mã lịch bảo trì": _pick(r, "schedule_id"), "số lượng": _pick(r, "quantity")},
    ]),
    # 13. get_my_profile: không tham số
    "get_my_profile": lambda r: {},
    # 14. get_my_permissions: không tham số
    "get_my_permissions": lambda r: {},
    # 15. list_enterprise_users: schema có status, limit (admin-only)
    "list_enterprise_users": lambda r: r.choice([
        {},
        {"trạng thái": _pick(r, "user_status")},
        {"số lượng": _pick(r, "quantity")},
        {"trạng thái": _pick(r, "user_status"), "số lượng": _pick(r, "quantity")},
    ]),

    # ── Nhóm 3: Điều chuyển, Yêu cầu & Chat (Hồ Văn Dinh phụ trách, 7 tools) ──
    # 16. list_asset_transfers: schema có onlyMine, limit
    "list_asset_transfers": lambda r: r.choice([
        {},
        {"phạm vi": "chỉ phiếu của tôi"},
        {"số lượng": _pick(r, "quantity")},
        {"phạm vi": "chỉ phiếu của tôi", "số lượng": _pick(r, "quantity")},
    ]),
    # 17. get_asset_transfer: schema có transfer_id (bắt buộc)
    "get_asset_transfer": lambda r: {
        "ID phiếu chuyển giao": _pick(r, "transfer_id")
    },
    # 18. get_transfer_summary: không tham số
    "get_transfer_summary": lambda r: {},
    # 19. list_staff_requests: schema có limit (không có filter status/typeRequest)
    "list_staff_requests": lambda r: r.choice([
        {},
        {"số lượng": _pick(r, "quantity")},
    ]),
    # 20. get_staff_request_summary: không tham số
    "get_staff_request_summary": lambda r: {},
    # 21. list_my_conversations: schema có limit (admin-only)
    "list_my_conversations": lambda r: r.choice([
        {},
        {"số lượng": _pick(r, "quantity")},
    ]),
    # 22. get_unread_counts: không tham số (admin-only)
    "get_unread_counts": lambda r: {},
}


def sample_param_hint(tool, rng):
    """Return {slot_vi: value} hints for `tool`, or {} when the tool has no sampler."""
    fn = PARAM_SAMPLER.get(tool)
    return fn(rng) if fn else {}


# ───────────────────────────────────────────────────────────────────────────
# 8. TRACKB_BUCKET_PLAN — LARGE plan keyed by TOOL: (tool, category, role, count).
#    Phủ đủ 22/22 tools SGOD + 5 refusal rows cho tools admin + hàng ghi permission_denial.
# ───────────────────────────────────────────────────────────────────────────
TRACKB_BUCKET_PLAN = [
    # ── Nhóm Tài sản & Doanh nghiệp (Thehy-IT: 8 tools, 16 hàng) ──
    ("list_my_assets", "my_assets", "employee", 18),
    ("list_my_assets", "my_assets", "admin", 12),
    ("get_asset", "asset_detail", "employee", 14),
    ("get_asset", "asset_detail", "admin", 10),
    ("get_asset_histories", "asset_detail", "employee", 10),
    ("get_asset_histories", "asset_detail", "admin", 8),
    ("list_categories", "category", "employee", 8),
    ("list_categories", "category", "admin", 8),
    ("list_locations", "location", "employee", 10),
    ("list_locations", "location", "admin", 10),
    ("get_location", "location", "employee", 8),
    ("get_location", "location", "admin", 8),
    ("get_enterprise_profile", "user_management", "admin", 10),
    ("get_enterprise_profile", "user_management", "employee", 6),  # Refusal row
    ("get_asset_statistics", "asset_detail", "admin", 12),
    ("get_asset_statistics", "asset_detail", "employee", 8),       # Refusal row

    # ── Nhóm Bảo trì & Hồ sơ (BaoMyTH: 7 tools, 14 hàng) ──
    ("list_maintenance_schedules", "maintenance_schedule", "employee", 16),
    ("list_maintenance_schedules", "maintenance_schedule", "admin", 12),
    ("get_maintenance_schedule", "maintenance_schedule", "employee", 12),
    ("get_maintenance_schedule", "maintenance_schedule", "admin", 8),
    ("list_maintenance_records", "maintenance_record", "employee", 12),
    ("list_maintenance_records", "maintenance_record", "admin", 8),
    ("list_maintenance_tasks", "maintenance_task", "employee", 14),
    ("list_maintenance_tasks", "maintenance_task", "admin", 10),
    ("get_my_profile", "user_profile", "employee", 14),
    ("get_my_profile", "user_profile", "admin", 6),
    ("get_my_permissions", "user_permission", "employee", 14),
    ("get_my_permissions", "user_permission", "admin", 6),
    ("list_enterprise_users", "user_management", "admin", 12),
    ("list_enterprise_users", "user_management", "employee", 8),  # Refusal row

    # ── Nhóm Điều chuyển, Yêu cầu & Chat (Hồ Văn Dinh: 7 tools, 14 hàng) ──
    ("list_asset_transfers", "asset_transfer", "employee", 18),
    ("list_asset_transfers", "asset_transfer", "admin", 10),
    ("get_asset_transfer", "asset_transfer", "employee", 12),
    ("get_asset_transfer", "asset_transfer", "admin", 8),
    ("get_transfer_summary", "asset_transfer", "employee", 14),
    ("get_transfer_summary", "asset_transfer", "admin", 6),
    ("list_staff_requests", "staff_request", "employee", 14),
    ("list_staff_requests", "staff_request", "admin", 8),
    ("get_staff_request_summary", "staff_request", "employee", 12),
    ("get_staff_request_summary", "staff_request", "admin", 8),
    ("list_my_conversations", "chat_conversation", "admin", 14),
    ("list_my_conversations", "chat_conversation", "employee", 8),  # Refusal row
    ("get_unread_counts", "chat_conversation", "admin", 14),
    ("get_unread_counts", "chat_conversation", "employee", 8),       # Refusal row

    # ── Yêu cầu ghi Tạo / Sửa / Xóa (hàng huấn luyện sinh REFUSAL_VI theo preamble v1 luật 5) ──
    ("get_asset", "permission_denial", "employee", 10),
    ("list_asset_transfers", "permission_denial", "employee", 8),
    ("list_maintenance_schedules", "permission_denial", "employee", 8),
]
# Verify the total with:
#   python3 -c "import sys; sys.path.insert(0,'datagen'); import config_sgod as c; print(sum(n for *_,n in c.TRACKB_BUCKET_PLAN))"

# Complexity layering (single-turn only). "dependent" (multi-step chains) from POC v1 is REMOVED.
COMPLEXITY_MIX = {"single": 0.85, "multi_constraint": 0.15}

# ───────────────────────────────────────────────────────────────────────────
# 9. IRRELEVANCE / NO-CALL targets — ~10% of the FINAL trainset (Hammer: 19% is over-conservative).
#    All map to expected_tool=null + expected_permission="allowed" -> DEFLECT_VI target.
#    TODO(D-Việc-3): tune hints to SGOD vocabulary; keep the four kinds.
# ───────────────────────────────────────────────────────────────────────────
IRRELEVANCE_CONFIG = {
    "target_fraction": 0.10,
    "kinds": {
        "out_of_scope": 0.40,
        "chitchat": 0.20,
        "ambiguous": 0.20,
        "procedure_question": 0.20,
    },
    "out_of_scope_hint": "Câu hỏi HOÀN TOÀN ngoài lĩnh vực quản lý tài sản: thời tiết, thể thao, "
                         "nấu ăn, lập trình, toán học, tin tức, sức khoẻ, dịch thuật chung.",
    "chitchat_hint": "Chào hỏi, cảm ơn, tán gẫu, hỏi bạn là ai, khen/chê chung — không yêu cầu tác vụ.",
    "ambiguous_hint": "Liên quan tài sản nhưng THIẾU thông tin để chọn công cụ (vd 'xem cái đó', "
                      "'kiểm tra giúp tôi', 'cái kia sao rồi') — cần hỏi lại để làm rõ.",
    "procedure_question_hint": "Câu hỏi CÁCH LÀM / quy trình / giải thích, KHÔNG yêu cầu hệ thống thực "
                               "hiện ngay (vd 'quy trình đăng ký tài sản mới ra sao?', 'làm sao để in mã QR?') "
                               "— trả lời hướng dẫn, KHÔNG gọi tool.",
}

# ───────────────────────────────────────────────────────────────────────────
# 10. REPLAY — public xLAM slice already in the repo (no HF download, no token).
#     datagen/convert_xlam.py turns the raw slice into parity rows with preamble v0.
# ───────────────────────────────────────────────────────────────────────────
REPLAY_CONFIG = {
    "target_fraction": 0.35,
    "source": "Salesforce/xlam-function-calling-60k (2k slice, see data/public/ATTRIBUTION.md)",
    "license": "CC-BY-4.0 (permissive; attribution required)",
    "local_path": "data/public/xlam_raw_2k.jsonl",       # converter input (committed)
    "converter": "datagen/convert_xlam.py",
    "converted_prefix": "data/sgod/replay",             # -> replay.{train,val,test}.jsonl + replay.eval.json
    "converter_seed": 20260913,                          # SAME seed as data/public/xlam_2k.* -> identical split
    "min_tools": 1, "max_tools": 4,
}

# ───────────────────────────────────────────────────────────────────────────
# 11. FINAL MIX TARGETS — composition of the assembled trainset (assemble_trackb_trainset.py).
#     POC v1 SFT-v2 lesson: small clean domain + ~2k absolute xLAM replay beat big synthetic sets.
#     TODO(D-Việc-5): set final_* to the sizes reachable with the 0.58 yield budget.
# ───────────────────────────────────────────────────────────────────────────
MIX_TARGETS = {
    "domain_verified": 0.55,
    "replay": 0.35,
    "irrelevance": 0.10,
    "final_min": 300,      # pilot-friendly floor; POC v1: 4500
    "final_max": 6500,
    "final_target": 3000,  # POC v1: 5800
}

# Yield budget from the POC v1 run: generation fill ~70% × verify pass ~84% ≈ 0.58 of the plan
# survives to the trainset. Size the plan as target / YIELD_BUDGET.
YIELD_BUDGET = 0.58

# ───────────────────────────────────────────────────────────────────────────
# 12. ANTI-LEAKAGE — SequenceMatcher threshold + the eval sets generated rows must NOT resemble.
#     eval_v1.json does not exist until Điểm đồng bộ 2; generators skip missing files with a WARNING.
#     The frozen human core (eval_human_core.jsonl, part of eval_v1) is listed as well so the pilot and
#     the eval-augmentation run are screened against it before eval_v1.json exists.
# ───────────────────────────────────────────────────────────────────────────
LEAKAGE_THRESHOLD = 0.65
EVAL_SETS_FOR_LEAKAGE = ["data/sgod/eval_v1.json", "data/sgod/eval_human_core.jsonl"]

DEFAULT_SEED = 20260616


def make_rng(seed=DEFAULT_SEED):
    return random.Random(seed)


# ───────────────────────────────────────────────────────────────────────────
# 13. SHARED HELPERS (prompt overrides, OpenAI client, call meter)
# ───────────────────────────────────────────────────────────────────────────
def load_prompt(name, default, prompt_dir=None):
    """Return the text of <prompt_dir>/<name>.md when it exists, else `default`.

    Lets interns iterate on prompts as Markdown files without touching Python. Training prompts
    live in datagen/prompts/, eval-augmentation prompts in datagen/prompts_eval/ (must stay disjoint).
    """
    d = repo_path(prompt_dir or PROMPT_DIR)
    f = d / f"{name}.md"
    if f.exists():
        txt = f.read_text(encoding="utf-8").strip()
        if txt:
            return txt
    return default


MISSING_KEY_MSG = ("LỖI: thiếu biến môi trường OPENAI_API_KEY. Bước này gọi LLM nên chạy trên hạ tầng tham chiếu "
                   "(export OPENAI_API_KEY=...; tuỳ chọn OPENAI_BASE_URL=https://<gateway>/v1). "
                   "Thực tập sinh: gửi PR prompts/config; datagen/run_pipeline.sh được chạy trên hạ tầng tham chiếu "
                   "và output được commit vào data/sgod/.")


def require_openai_client():
    """Build the OpenAI client from the environment or exit 2 with a Vietnamese message.

    Every LLM stage MUST go through here so OPENAI_BASE_URL is always honoured. LLM_TIMEOUT (seconds per
    request, default 120) and LLM_MAX_RETRIES (transient errors only, default 3) bound a stuck gateway;
    the client's own default timeout is 600 s.
    """
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print(MISSING_KEY_MSG, file=sys.stderr)
        raise SystemExit(2)
    from openai import OpenAI  # imported lazily: offline stages never need the package
    return OpenAI(api_key=key, base_url=os.environ.get("OPENAI_BASE_URL") or None,
                  timeout=float(os.environ.get("LLM_TIMEOUT") or 120),
                  max_retries=int(os.environ.get("LLM_MAX_RETRIES") or 3))


def model_alias(model) -> str:
    """Model id as written to files and SUMMARY lines: the part after the last "/". Provider/route
    prefixes are specific to one gateway and must not reach data/sgod/ (public repo)."""
    return str(model or "").rsplit("/", 1)[-1] or "?"


def err_text(exc) -> str:
    """Exception summary that is safe to print and to write into reports: class, HTTP status and the
    structured code/param/type fields. Never the message body — gateways echo key fragments in it."""
    head = type(exc).__name__
    status = getattr(exc, "status_code", None)
    if status:
        head += f"({status})"
    extra = []
    for k in ("code", "param", "type"):
        v = getattr(exc, k, None)
        if isinstance(v, (str, int)) and str(v) and str(v) != str(status):
            extra.append(f"{k}={str(v)[:40]}")
    return " ".join([head] + extra)


FATAL_HTTP = {401, 403, 404}   # bad key / model not allowed for the key / unknown model or route


def is_retryable(exc) -> bool:
    """Transient: no HTTP status (timeout, dropped connection), 408, 409, 429 or 5xx. A 400/422 (bad
    parameter, content filter) fails the same way on every retry."""
    status = getattr(exc, "status_code", None)
    return status is None or status in (408, 409, 429) or status >= 500


class FatalLLMError(SystemExit):
    """The gateway refused the key or the model (401/403/404): every further call fails the same way.

    Subclass of SystemExit on purpose: the broad `except Exception` handlers of the stages do not
    swallow it, so the stage stops at once with exit code 1 and writes no final output file (the
    pipeline then re-runs it next time instead of skipping it)."""


def chat(client, **kwargs):
    """client.chat.completions.create + CallMeter. Every LLM call of datagen/ goes through here.

    Returns the response; errors are counted per model and re-raised (FatalLLMError for 401/403/404)."""
    model = kwargs.get("model")
    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as exc:  # noqa: BLE001
        METER.error(model)
        if getattr(exc, "status_code", None) in FATAL_HTTP:
            raise FatalLLMError(
                f"LỖI: gateway LLM từ chối khoá hoặc model {model_alias(model)!r}: {err_text(exc)}. Kiểm tra "
                f"OPENAI_API_KEY / OPENAI_BASE_URL và GEN_MODEL / LABEL_MODELS / ARBITER_MODEL "
                f"(tên model đúng như gateway phục vụ).") from exc
        raise
    METER.add(resp, model)
    return resp


class CallMeter:
    """Counts chat.completions calls, failed calls and tokens — in total and per model alias — so every
    run can report cost in its SUMMARY line. Thread-safe (generate/label/verify call it from workers).

    summary(): "llm_calls=N prompt_tokens=P completion_tokens=C errors=E by_model=<alias>:N/P/C/E,..."
    (run_pipeline.sh adds these up over the stages of one invocation)."""

    def __init__(self):
        self._lock = threading.Lock()
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.errors = 0
        self.by_model = {}   # alias -> [calls, prompt_tokens, completion_tokens, errors]

    def _slot(self, model):
        return self.by_model.setdefault(model_alias(model), [0, 0, 0, 0])

    def add(self, resp, model=None):
        u = getattr(resp, "usage", None)
        pt = int(getattr(u, "prompt_tokens", 0) or 0) if u is not None else 0
        ct = int(getattr(u, "completion_tokens", 0) or 0) if u is not None else 0
        with self._lock:
            self.calls += 1
            self.prompt_tokens += pt
            self.completion_tokens += ct
            slot = self._slot(model or getattr(resp, "model", None))
            slot[0] += 1
            slot[1] += pt
            slot[2] += ct

    def error(self, model=None):
        with self._lock:
            self.errors += 1
            self._slot(model)[3] += 1

    def summary(self):
        with self._lock:
            per = ",".join(f"{m}:{c}/{p}/{k}/{e}" for m, (c, p, k, e) in sorted(self.by_model.items()))
            return (f"llm_calls={self.calls} prompt_tokens={self.prompt_tokens} "
                    f"completion_tokens={self.completion_tokens} errors={self.errors}"
                    + (f" by_model={per}" if per else ""))


METER = CallMeter()
