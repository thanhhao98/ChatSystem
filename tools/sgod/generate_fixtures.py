import json
import os

TENANT_ID = "6a85bad6a8d2133e058c93a9"
USER_ID = "6a85be56a8d2133e058c93b9"
ASSET_ID = "6aa2c177da46d70ee2f491c1"
CATEGORY_ID = "6aa2c134da46d70ee2f491bf"
LOCATION_ID = "6aa2c150da46d70ee2f491c0"
SCHEDULE_ID = "6aa2c210da46d70ee2f491d2"
TASK_ID = "6aa2c230da46d70ee2f491d5"
TRANSFER_ID = "6aa2c280da46d70ee2f491e0"
REQUEST_STAFF_ID = "6aa2c290da46d70ee2f491e5"
TIMESTAMP_STR = "2026-10-10T14:40:00.000Z"

def env(data, message="Thành công", status_code=200):
    return {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": TIMESTAMP_STR
    }

def neg_env(status_code, error, message, success=False):
    return {
        "success": success,
        "statusCode": status_code,
        "error": error,
        "message": message,
        "timestamp": TIMESTAMP_STR
    }

def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved: {path}")

# ==================== CHAT (3 files) ====================
save("fixtures/sgod/chat/GET_conversations.json", env({
  "conversations": [
    {
      "id": "6aa2c5e2e8667af3ad1333ff",
      "type": "group",
      "title": "QA Project Team",
      "logoId": "",
      "tenantId": TENANT_ID,
      "lastMessageId": "6aa2c601e8667af3ad133405",
      "sortConversation": TIMESTAMP_STR,
      "messagesPinned": [],
      "isE2EEEnabled": False,
      "currentKeyVersion": 0,
      "groupKeys": [],
      "searchText": "qa project team",
      "participantCount": 3,
      "createdAt": "2026-09-01T08:00:00.000Z",
      "updatedAt": TIMESTAMP_STR,
      "description": "Nhóm trao đổi công việc QA & Test",
      "creatorId": TENANT_ID,
      "lastMessageAt": TIMESTAMP_STR,
      "lastMessageSnippet": "Báo cáo kiểm thử thiết bị đã được cập nhật.",
      "messageCount": 42,
      "isActive": True,
      "settings": {
        "allowInvites": True,
        "requireApproval": False,
        "allowFileSharing": True,
        "maxParticipants": 100,
        "allowMemberMessagePinning": False,
        "allowReactions": True,
        "allowPolling": True,
        "allowMembersToSendMessages": True,
        "onlyAdminsCanCreatePolls": False
      },
      "unreadCount": 2,
      "isMuted": False,
      "isPinned": True,
      "disappearingSeconds": 0,
      "lastNameUserSent": "Nguyễn Văn Test",
      "lastUserSentId": USER_ID,
      "e2eeFirstEnabledAt": "",
      "members": [
        {"tenantId": TENANT_ID, "belongTo": "Enterprise", "userId": TENANT_ID},
        {"tenantId": TENANT_ID, "belongTo": "EnterpriseUser", "userId": USER_ID}
      ],
      "isArchived": False,
      "archivedAt": "",
      "autoUnarchiveOnNewMessage": True
    }
  ],
  "pagination": {"limit": 20, "total": 1, "hasMore": False, "nextCursor": ""}
}, "Get conversations successfully"))

save("fixtures/sgod/chat/GET_conversations_unread_counts.json", env({
  "totalUnread": 2,
  "conversationUnread": [{"conversationId": "6aa2c5e2e8667af3ad1333ff", "count": 2}]
}, "Get unread counts successfully"))

save("fixtures/sgod/chat/GET_messages.json", env({
  "messages": [
    {
      "id": "6aa2c601e8667af3ad133405",
      "conversationId": "6aa2c5e2e8667af3ad1333ff",
      "userId": USER_ID,
      "content": "{\"text\":\"Báo cáo kiểm thử thiết bị đã được cập nhật.\",\"version\":\"1.0\"}",
      "parentMessageId": None,
      "messageType": "text",
      "status": "read",
      "createdAt": TIMESTAMP_STR,
      "updatedAt": TIMESTAMP_STR,
      "mentions": [],
      "forwardedFromMessageId": None,
      "forwardedFromUserId": None,
      "expireAt": None,
      "voiceAttachments": [],
      "isEdited": False,
      "editInfo": None,
      "tenantId": TENANT_ID,
      "isStarredForMe": False,
      "deliveredAtForMe": TIMESTAMP_STR,
      "readAtForMe": TIMESTAMP_STR,
      "senderBelongTo": "EnterpriseUser",
      "attachments": []
    }
  ],
  "messageText": "Get messages successfully",
  "pagination": {"limit": 20, "total": 1, "hasMore": False, "nextCursor": ""}
}, "Get messages successfully"))

# ==================== AUTH (5 files) ====================
save("fixtures/sgod/auth/GET_users_myself.json", env({
  "user": {
    "id": USER_ID,
    "email": "user.test@example.com",
    "user_name": "employee_test",
    "full_name": {"first_name": "Văn Test", "last_name": "Nguyễn"},
    "user_type": "ENTERPRISE_USER",
    "roles": ["STAFF_ROLE"],
    "enterprise_name": "Công ty Công nghệ SGOD Demo",
    "descriptions": "Chuyên viên quản lý thiết bị",
    "sgod_user_id": USER_ID,
    "status": "ACTIVE"
  }
}, "Lấy thông tin người dùng thành công"))

save("fixtures/sgod/auth/GET_enterprises_profile.json", env({
  "user": {
    "id": TENANT_ID,
    "email": "admin@example.com",
    "user_name": "sgod_admin",
    "full_name": {"first_name": "Quản Trị Viên", "last_name": "Doanh Nghiệp"},
    "user_type": "ENTERPRISE",
    "roles": ["ENTERPRISE_ADMIN"],
    "enterprise_name": "Tổng công ty Công nghệ SGOD",
    "descriptions": "Tài khoản quản trị cấp doanh nghiệp",
    "sgod_user_id": TENANT_ID,
    "status": "ACTIVE"
  }
}, "Lấy thông tin doanh nghiệp thành công"))

save("fixtures/sgod/auth/GET_departments_tree.json", env({
  "departments": [
    {
      "id": "6aa2c310da46d70ee2f491f0",
      "name": "Khối Công nghệ & Sản phẩm",
      "code": "TECH_PROD",
      "level": 1,
      "children": [
        {
          "id": "6aa2c315da46d70ee2f491f1",
          "name": "Phòng Đảm bảo chất lượng (QA)",
          "code": "QA_DEPT",
          "level": 2,
          "parent_id": "6aa2c310da46d70ee2f491f0",
          "children": []
        }
      ]
    }
  ]
}, "Lấy cơ cấu phòng ban thành công"))

save("fixtures/sgod/auth/GET_roles.json", env({
  "roles": [
    {
      "id": "6aa2c330da46d70ee2f491f5",
      "name": "Quản trị viên thiết bị",
      "code": "ASSET_ADMIN",
      "description": "Toàn quyền quản trị tài sản và điều phối bảo trì",
      "is_system": True
    },
    {
      "id": "6aa2c335da46d70ee2f491f6",
      "name": "Nhân viên sử dụng tài sản",
      "code": "ASSET_USER",
      "description": "Xem tài sản được giao và gửi yêu cầu bàn giao/bảo trì",
      "is_system": True
    }
  ]
}, "Lấy danh sách vai trò thành công"))

save("fixtures/sgod/auth/GET_enterprise_users.json", env({
  "users": [
    {
      "id": USER_ID,
      "email": "user.test@example.com",
      "user_name": "employee_test",
      "full_name": {"first_name": "Văn Test", "last_name": "Nguyễn"},
      "user_type": "ENTERPRISE_USER",
      "roles": ["ASSET_USER"],
      "enterprise_name": "Công ty Công nghệ SGOD Demo",
      "status": "ACTIVE"
    }
  ],
  "meta": {"next_cursor": "", "has_next_page": False, "limit": 20}
}, "Lấy danh sách nhân sự thành công"))

# ==================== ASSET (14 files) ====================
sample_asset = {
  "id": ASSET_ID,
  "enterprise_id": TENANT_ID,
  "name": "Máy tính xách tay Dell Latitude 5420",
  "alias_names": ["Laptop QA 01", "Dell 5420 QA"],
  "asset_code": "TS-2026-0001",
  "category_id": CATEGORY_ID,
  "location_id": LOCATION_ID,
  "status": "active",
  "description": "Máy tính cấp phát cho nhân viên QA kiểm thử",
  "total_quantity": 1,
  "initial_quantity": 1,
  "unit": "chiếc",
  "asset_type": "normal",
  "is_important": False,
  "on_blockchain": False,
  "created_by": TENANT_ID,
  "created_at": 1789051255761,
  "updated_at": 1789051255761
}

save("fixtures/sgod/asset/GET_assets.json", env({
  "items": [sample_asset],
  "meta": {"next_cursor": "", "has_next_page": False, "limit": 20}
}, "Lấy danh sách tài sản thành công"))

save("fixtures/sgod/asset/GET_assets_id.json", env({
  "asset": sample_asset
}, "Lấy chi tiết tài sản thành công"))

save("fixtures/sgod/asset/GET_assets_suggest.json", env({
  "items": [
    {
      "id": ASSET_ID,
      "name": "Máy tính xách tay Dell Latitude 5420",
      "asset_code": "TS-2026-0001",
      "category_name": "Thiết bị văn phòng",
      "status": "active"
    }
  ]
}, "Gợi ý tài sản thành công"))

save("fixtures/sgod/asset/GET_assets_id_histories.json", env({
  "items": [
    {
      "id": "6aa2c401da46d70ee2f49201",
      "asset_id": ASSET_ID,
      "action": "CREATE",
      "performed_by": TENANT_ID,
      "details": "Khởi tạo tài sản mới trong hệ thống",
      "created_at": 1789051255761
    }
  ],
  "meta": {"next_cursor": "", "has_next_page": False, "limit": 20}
}, "Lấy lịch sử tài sản thành công"))

save("fixtures/sgod/asset/GET_asset_statuses_history_assetId.json", env({
  "items": [
    {
      "id": "6aa2c410da46d70ee2f49205",
      "asset_id": ASSET_ID,
      "status": "active",
      "location_id": LOCATION_ID,
      "note": "Bàn giao sử dụng phòng QA",
      "created_at": 1789051255761
    }
  ],
  "meta": {"next_cursor": "", "has_next_page": False, "limit": 20}
}, "Lấy lịch sử trạng thái thành công"))

save("fixtures/sgod/asset/GET_asset_statuses_by_asset_assetId.json", env({
  "items": [
    {
      "id": "6aa2c410da46d70ee2f49205",
      "asset_id": ASSET_ID,
      "status": "active",
      "location_id": LOCATION_ID,
      "quantity": 1
    }
  ]
}, "Lấy trạng thái theo tài sản thành công"))

save("fixtures/sgod/asset/GET_maintenance_schedules.json", env({
  "items": [
    {
      "id": SCHEDULE_ID,
      "enterprise_id": TENANT_ID,
      "title": "Bảo dưỡng định kỳ quý 4 laptop QA",
      "status": "active",
      "frequency": "QUARTERLY",
      "start_date": "2026-10-01",
      "end_date": "2026-10-15",
      "assigned_to": USER_ID,
      "total_tasks": 2,
      "completed_tasks": 1
    }
  ],
  "meta": {"next_cursor": "", "has_next_page": False, "limit": 20}
}, "Lấy danh sách lịch bảo trì thành công"))

save("fixtures/sgod/asset/GET_maintenance_schedules_id.json", env({
  "schedule": {
    "id": SCHEDULE_ID,
    "enterprise_id": TENANT_ID,
    "title": "Bảo dưỡng định kỳ quý 4 laptop QA",
    "status": "active",
    "frequency": "QUARTERLY",
    "start_date": "2026-10-01",
    "end_date": "2026-10-15",
    "assigned_to": USER_ID,
    "notes": "Vệ sinh tản nhiệt và kiểm tra pin"
  }
}, "Lấy chi tiết lịch bảo trì thành công"))

save("fixtures/sgod/asset/GET_maintenance_records.json", env({
  "items": [
    {
      "id": "6aa2c430da46d70ee2f49210",
      "enterprise_id": TENANT_ID,
      "asset_id": ASSET_ID,
      "maintenance_task_id": TASK_ID,
      "cost": 150000,
      "currency": "VND",
      "status": "completed",
      "performed_by": USER_ID,
      "completion_date": "2026-10-05"
    }
  ],
  "meta": {"next_cursor": "", "has_next_page": False, "limit": 20}
}, "Lấy danh sách bản ghi bảo trì thành công"))

save("fixtures/sgod/asset/GET_maintenance_tasks.json", env({
  "items": [
    {
      "id": TASK_ID,
      "schedule_id": SCHEDULE_ID,
      "asset_id": ASSET_ID,
      "title": "Vệ sinh và tra keo tản nhiệt",
      "status": "completed",
      "assigned_to": USER_ID
    }
  ],
  "meta": {"next_cursor": "", "has_next_page": False, "limit": 20}
}, "Lấy danh sách công việc bảo trì thành công"))

save("fixtures/sgod/asset/GET_asset_transfers.json", env({
  "items": [
    {
      "id": TRANSFER_ID,
      "enterprise_id": TENANT_ID,
      "asset_id": ASSET_ID,
      "transfer_code": "BG-2026-0005",
      "from_location_id": LOCATION_ID,
      "to_location_id": "6aa2c155da46d70ee2f491c5",
      "sender_id": TENANT_ID,
      "receiver_id": USER_ID,
      "status": "completed",
      "transfer_date": "2026-09-15"
    }
  ],
  "meta": {"next_cursor": "", "has_next_page": False, "limit": 20}
}, "Lấy danh sách phiếu chuyển giao thành công"))

save("fixtures/sgod/asset/GET_asset_transfers_id.json", env({
  "transfer": {
    "id": TRANSFER_ID,
    "enterprise_id": TENANT_ID,
    "asset_id": ASSET_ID,
    "transfer_code": "BG-2026-0005",
    "from_location_id": LOCATION_ID,
    "to_location_id": "6aa2c155da46d70ee2f491c5",
    "sender_id": TENANT_ID,
    "receiver_id": USER_ID,
    "status": "completed",
    "description": "Bàn giao tài sản sang phòng QA cơ sở 2"
  }
}, "Lấy chi tiết phiếu chuyển giao thành công"))

save("fixtures/sgod/asset/GET_request_staff.json", env({
  "items": [
    {
      "id": REQUEST_STAFF_ID,
      "enterprise_id": TENANT_ID,
      "asset_id": ASSET_ID,
      "requester_id": USER_ID,
      "approver_id": TENANT_ID,
      "type_request": "REPAIR",
      "status_request": "APPROVED",
      "quantity": 1,
      "description": "Đề xuất thay bàn phím laptop",
      "created_at": 1789051255761
    }
  ],
  "meta": {"next_cursor": "", "has_next_page": False, "limit": 20}
}, "Lấy danh sách yêu cầu nhân sự thành công"))

save("fixtures/sgod/asset/GET_locations.json", env({
  "items": [
    {
      "id": LOCATION_ID,
      "enterprise_id": TENANT_ID,
      "name": "Kho Thiết Bị Trung Tâm",
      "alias_names": ["Kho Tầng 3", "Central Storage"],
      "detail": "Phòng 302, Tòa nhà Công nghệ SGOD",
      "map": {"latitude": 10.762622, "longitude": 106.660172},
      "total_asset": 15,
      "subs": []
    }
  ],
  "meta": {"next_cursor": "", "has_next_page": False, "limit": 20}
}, "Lấy danh sách địa điểm thành công"))

# ==================== NEGATIVE (4 files) ====================
# Ca 1: HTTP 200 nhưng body success: false (lỗi logic / validation nghiệp vụ)
save("fixtures/sgod/negative/HTTP200_success_false.json", neg_env(
  status_code=400,
  error="BAD_REQUEST",
  message="Tham số truy vấn không hợp lệ: 'limit' phải nằm trong khoảng từ 1 đến 100",
  success=False
))

# Ca 2: HTTP 401 Unauthorized (token hết hạn hoặc thiếu token)
save("fixtures/sgod/negative/HTTP401_expired_token.json", neg_env(
  status_code=401,
  error="UNAUTHORIZED",
  message="Mã truy cập JWT đã hết hạn hoặc không hợp lệ. Vui lòng làm mới phiên làm việc.",
  success=False
))

# Ca 3: Luồng 401 -> refresh -> retry success (Mô tả chuỗi phục hồi session thành công)
save("fixtures/sgod/negative/FLOW_401_refresh_retry_success.json", {
  "success": True,
  "stage": "RETRY_AFTER_REFRESH",
  "session_refreshed": True,
  "data": {
    "retry_attempt": 1,
    "resolved_at": TIMESTAMP_STR,
    "user_id": USER_ID,
    "refreshed_scope": "ENTERPRISE_USER",
    "recovered_result": {"status": "SESSION_RESTORED_OK"}
  },
  "message": "Token refreshed via /sessions/refresh and operation re-executed successfully",
  "timestamp": TIMESTAMP_STR
})

# Ca 4: Lỗi phân quyền 403 Forbidden (Non-owner / Employee truy cập tài nguyên bị cấm)
save("fixtures/sgod/negative/HTTP403_permission_denied.json", neg_env(
  status_code=403,
  error="FORBIDDEN",
  message="Tài khoản nhân viên (Employee) không có quyền truy cập cấu hình hệ thống cấp doanh nghiệp.",
  success=False
))

print("\n--- ĐÃ HOÀN TẤT TẠO TOÀN BỘ 26 FIXTURES! ---")
