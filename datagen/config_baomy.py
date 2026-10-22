"""Cấu hình tạm cá nhân của BAOMYTH cho Task 3 [D-V3].
Phạm vi phụ trách:
- 3 Personas SSOT: P3 nhan_vien_van_phong, P4 ky_thuat_vien_bao_tri, P5 thu_kho
- 7 Tools Bảo trì - Hồ sơ - Quản lý người dùng:
  1. list_maintenance_schedules
  2. get_maintenance_schedule
  3. list_maintenance_records
  4. list_maintenance_tasks
  5. get_my_profile
  6. get_my_permissions
  7. list_enterprise_users
- Thực thể ENTITY_POOLS_BAOMY trích xuất từ fixtures/sgod/ (loại bỏ hoàn toàn tiền tố [SEED])
- Nhóm Track B Plan & Refusal rows (employee cố tình gọi list_enterprise_users)
"""
import random

# Thực thể do BaoMyTH phụ trách trích xuất từ fixtures/sgod/ bản 21/10
ENTITY_POOLS_BAOMY = {
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
    # Đầu việc bảo trì thật từ GET_maintenance_tasks.json (đã bỏ tiền tố [SEED])
    "task_title": [
        "Thay trống mực (drum)",
        "Bảo dưỡng máy lạnh định kỳ",
        "Kiểm tra đầu phun máy in",
    ],
    # Trạng thái công việc bảo trì (ngữ cảnh Swagger / task)
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
    # Giới hạn số lượng hiển thị (phân trang limit)
    "quantity": [
        "3",
        "5",
        "10",
        "20",
    ],
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
    return rng.choice(ENTITY_POOLS_BAOMY[key])


# PARAM_SAMPLER cho 7 tools do BaoMyTH phụ trách
# Tuân thủ nghiêm ngặt schema OpenAPI:
# - list_maintenance_schedules: status (active/completed), limit
# - get_maintenance_schedule: schedule_id (bắt buộc)
# - list_maintenance_records: limit
# - list_maintenance_tasks: maintenanceScheduleId (bắt buộc), limit
# - get_my_profile: {}
# - get_my_permissions: {}
# - list_enterprise_users: status, limit
PARAM_SAMPLER_BAOMY = {
    # 1. list_maintenance_schedules: hỗ trợ kịch bản multi_constraint (trạng thái + số lượng)
    "list_maintenance_schedules": lambda r: r.choice([
        {},
        {"trạng thái": _pick(r, "schedule_status")},
        {"số lượng": _pick(r, "quantity")},
        {"trạng thái": _pick(r, "schedule_status"), "số lượng": _pick(r, "quantity")},
    ]),
    # 2. get_maintenance_schedule: schema có schedule_id (bắt buộc dùng ID thật từ fixture)
    "get_maintenance_schedule": lambda r: {
        "mã lịch": _pick(r, "schedule_id")
    },
    # 3. list_maintenance_records: schema có limit
    "list_maintenance_records": lambda r: r.choice([
        {},
        {"số lượng": _pick(r, "quantity")},
    ]),
    # 4. list_maintenance_tasks: schema BẮT BUỘC maintenanceScheduleId, có thể kèm limit
    "list_maintenance_tasks": lambda r: r.choice([
        {"mã lịch bảo trì": _pick(r, "schedule_id")},
        {"mã lịch bảo trì": _pick(r, "schedule_id"), "số lượng": _pick(r, "quantity")},
    ]),
    # 5. get_my_profile: không tham số
    "get_my_profile": lambda r: {},
    # 6. get_my_permissions: không tham số
    "get_my_permissions": lambda r: {},
    # 7. list_enterprise_users: schema có status, limit
    "list_enterprise_users": lambda r: r.choice([
        {},
        {"trạng thái": _pick(r, "user_status")},
        {"số lượng": _pick(r, "quantity")},
        {"trạng thái": _pick(r, "user_status"), "số lượng": _pick(r, "quantity")},
    ]),
}

# Kế hoạch phân bổ Track B cho 7 tools của BaoMyTH
# Bổ sung hàng employee cố gọi list_enterprise_users để sinh Refusal rows (expected_permission: "denied")
TRACKB_PLAN_BAOMY = [
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
]
