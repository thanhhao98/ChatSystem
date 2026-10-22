"""Cấu hình tạm cá nhân của HỒ VĂN DINH cho Task 3 [D-V3].
Phạm vi phụ trách:
- 2 Personas SSOT: P6 kinh_doanh_chi_nhanh, P7 hanh_chinh_don_vi_con
- 7 Tools Điều chuyển - Yêu cầu nhân viên - Chat:
  1. list_asset_transfers
  2. get_asset_transfer
  3. get_transfer_summary
  4. list_staff_requests
  5. get_staff_request_summary
  6. list_my_conversations
  7. get_unread_counts
- Thực thể ENTITY_POOLS_DINH lấy động từ fixtures/sgod/ (không bịa dữ liệu)
- Nhóm Track B Plan & Refusal rows (employee gọi 2 tools chat admin-only)

File tạm: nhóm tích hợp vào datagen/config_sgod.py rồi xoá trước khi mở PR.
"""

import json
from pathlib import Path


# Thực thể do Văn Dinh phụ trách lấy từ fixtures/sgod/ bản 21/10.
# Giữ cách đọc động để tránh sao chép ID/trạng thái và lệch so với fixture.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_DIR = _REPO_ROOT / "fixtures" / "sgod" / "asset"


def _load_items(filename):
    """Đọc danh sách data.items từ fixture thật."""
    path = _FIXTURE_DIR / filename
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload["data"]["items"]
    if not isinstance(items, list):
        raise ValueError(f"Fixture không có data.items dạng list: {path}")
    return items


def _unique_values(items, field):
    """Lấy các giá trị chuỗi không rỗng, không trùng lặp."""
    return sorted({
        item[field].strip()
        for item in items
        if isinstance(item, dict)
        and isinstance(item.get(field), str)
        and item[field].strip()
    })


_transfers = _load_items("GET_asset_transfers.json")
_requests = _load_items("GET_request_staff.json")

ENTITY_POOLS_DINH = {
    # ID phiếu điều chuyển thật từ GET_asset_transfers.json
    "transfer_id": _unique_values(_transfers, "id"),
    # Trạng thái điều chuyển chỉ là NGỮ CẢNH; không phải filter của list_asset_transfers
    "transfer_status": _unique_values(_transfers, "statusTransfer"),
    # Loại/trạng thái yêu cầu chỉ là NGỮ CẢNH; không phải filter của list_staff_requests
    "request_status": _unique_values(_requests, "statusRequest"),
    "request_type": _unique_values(_requests, "typeRequest"),
    # Giới hạn hiển thị (cùng convention chuỗi với hai đồng đội)
    "quantity": ["3", "5", "10", "20"],
    # Sắc thái câu thoại / văn phong
    "register": [
        "trang trọng", "thân mật", "viết tắt", "có lỗi chính tả nhẹ",
        "ra lệnh ngắn gọn", "lịch sự dùng ạ/nhé", "không dấu",
    ],
}

for _name in ("transfer_id", "transfer_status", "request_status", "request_type"):
    if not ENTITY_POOLS_DINH[_name]:
        raise ValueError(f"Entity pool trống: {_name}")


def _pick(rng, key):
    return rng.choice(ENTITY_POOLS_DINH[key])


# PARAM_SAMPLER cho 7 tools do Văn Dinh phụ trách.
# Đây là GỢI Ý câu hỏi bằng tiếng Việt, không phải tool arguments trực tiếp.
# Schema: list_asset_transfers(onlyMine, limit, cursor); get_asset_transfer(transfer_id);
# get_transfer_summary({}); list_staff_requests(limit, cursor);
# get_staff_request_summary({}); list_my_conversations(limit, cursor); get_unread_counts({}).
# Không sinh cursor nếu không có token phân trang thật từ response trước.
PARAM_SAMPLER_DINH = {
    # 1. list_asset_transfers: hỗ trợ multi_constraint (onlyMine + limit)
    "list_asset_transfers": lambda r: r.choice([
        {},
        {"phạm vi": "chỉ phiếu của tôi"},
        {"số lượng": _pick(r, "quantity")},
        {"phạm vi": "chỉ phiếu của tôi", "số lượng": _pick(r, "quantity")},
    ]),
    # 2. get_asset_transfer: transfer_id bắt buộc, ID lấy từ fixture
    "get_asset_transfer": lambda r: {
        "ID phiếu chuyển giao": _pick(r, "transfer_id")
    },
    # 3. get_transfer_summary: không tham số
    "get_transfer_summary": lambda r: {},
    # 4. list_staff_requests: hỗ trợ limit, không bịa status/request_type filter
    "list_staff_requests": lambda r: r.choice([
        {},
        {"số lượng": _pick(r, "quantity")},
    ]),
    # 5. get_staff_request_summary: không tham số
    "get_staff_request_summary": lambda r: {},
    # 6. list_my_conversations: company_admin-only; hỗ trợ limit
    "list_my_conversations": lambda r: r.choice([
        {},
        {"số lượng": _pick(r, "quantity")},
    ]),
    # 7. get_unread_counts: company_admin-only, không tham số
    "get_unread_counts": lambda r: {},
}


# Kế hoạch phân bổ Track B cho 7 tools của Văn Dinh.
# Các hàng employee gọi 2 tools chat admin-only là refusal rows.
# Reviewer phải gán expected_permission="denied" và category="permission_denial".
# Các write requests (tạo/sửa/xoá) có expected_tool=null, thuộc bucket
# permission_denial riêng; không tự tạo write tool giả trong plan này.
TRACKB_PLAN_DINH = [
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
]
