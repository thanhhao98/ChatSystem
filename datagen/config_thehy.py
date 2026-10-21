"""Cấu hình tạm cá nhân của THEHY-IT cho Task 3 [D-V3].
Phạm vi phụ trách:
- 2 Personas Company Admin: P1 giam_doc, P2 quan_ly_tai_san
- 8 Tools Tài sản - Vị trí - Doanh nghiệp:
  1. list_my_assets
  2. get_asset
  3. get_asset_histories
  4. list_categories
  5. list_locations
  6. get_location
  7. get_enterprise_profile
  8. get_asset_statistics
- Thực thể ENTITY_POOLS_THEHY từ fixtures/sgod/ (loại bỏ tiền tố [SEED])
- Nhóm Track B Plan & Refusal rows cho công cụ admin
"""
import random

# Thực thể do Thehy-IT phụ trách trích xuất từ fixtures/sgod/ bản 21/10
ENTITY_POOLS_THEHY = {
    # Mã tài sản tuần tự (fixtures/sgod/asset/GET_assets.json)
    "asset_code": [
        "000000001", "000000003", "000000004", "000000005",
        "000000006", "000000007", "000000008"
    ],
    # Tên tài sản đã loại bỏ hoàn toàn tiền tố [SEED]
    "asset_name": [
        "QA Test Laptop",
        "ZZTEST-2610100426 x4",
        "Laptop Dell Latitude 5440",
        "Màn hình LG 27UP850",
        "Máy in HP LaserJet Pro M404dn",
        "Máy lạnh Daikin FTKB50 2HP",
        "Mực in HP 76A"
    ],
    # Từ khoá tìm kiếm trích xuất từ tên hoặc mã (khớp search của GET /assets)
    "search_keyword": [
        "Laptop", "Dell Latitude", "Máy in", "HP LaserJet",
        "Daikin", "Màn hình LG", "Mực in", "QA Test", "ZZTEST", "000000006"
    ],
    # Danh mục tài sản từ GET_categories.json
    "category": [
        "QA Test Category",
        "ZZTEST-2610100426 Ghe (sua)",
        "Thiết bị văn phòng",
        "Thiết bị CNTT",
        "Điện lạnh",
        "Vật tư tiêu hao"
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
        "6ad615353b0f8e12e2f190be"
    ],
    "quantity": ["3", "5", "10", "20"],
    "register": [
        "trang trọng", "thân mật", "viết tắt", "có lỗi chính tả nhẹ",
        "ra lệnh ngắn gọn", "lịch sự dùng ạ/nhé", "không dấu"
    ],
}


def _pick(rng, key):
    return rng.choice(ENTITY_POOLS_THEHY[key])


# PARAM_SAMPLER cho 8 tools do Thehy-IT phụ trách
# 100% schema-valid: list_my_assets KHÔNG có filter status/category/location
PARAM_SAMPLER_THEHY = {
    # 1. list_my_assets: schema có search, limit
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
    # 7. get_enterprise_profile: không tham số
    "get_enterprise_profile": lambda r: {},
    # 8. get_asset_statistics: không tham số
    "get_asset_statistics": lambda r: {},
}

# Kế hoạch phân bổ Track B cho 8 tools của Thehy-IT
# Bổ sung hàng employee gọi get_enterprise_profile và get_asset_statistics để sinh refusal rows
TRACKB_PLAN_THEHY = [
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
]
