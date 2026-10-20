# Kiểm tra 22 tool `sgod_tools` v1 trên API thật theo vai trò (S Việc 4)

> Sinh bằng `python tools/sgod/verify_tools_live.py` trên hạ tầng tham chiếu — **không sửa tay**; chạy lại để cập nhật. Mỗi lượt gọi tool là `GET` (script kiểm tra trước khi gửi); `POST` duy nhất là đăng nhập và làm mới phiên. Kết luận rẽ nhánh theo `body.success`, không theo mã HTTP (gateway có khi trả HTTP 200 cho lỗi — spec §1, §4). Chỉ ghi **tên** khoá query, không ghi giá trị (từ khoá, id, cursor); token, khoá API, mật khẩu, email và địa chỉ gateway bị chặn bởi bộ kiểm tra rò rỉ của `tools/sgod/capture_fixtures.py`.

| Mục | Giá trị |
|---|---|
| Thời điểm chạy (UTC) | 2026-10-20 21:05 |
| Gateway | `<SGOD_GATEWAY>` |
| Commit | `eb3f28d` |
| sha256 `tools/sgod/sgod_tools.json` | `cc3cb61bf1e96f489efc5e71e40406cfb54069594d1b7f23aa7c7000b5643a17` |
| sha256 `tools/sgod/tool_policy.json` | `13538574286fe40e9e90650c1b4fc47773018cad4ee8162039f61416aabfaa61` |
| Tầng đăng nhập — `company_admin` | `enterprises` (`POST /sgod-auth/v1/enterprises/sessions`) — đã chạy |
| Tầng đăng nhập — `employee` | `enterprise-users` (`POST /sgod-auth/v1/enterprise-users/sessions`) — **không chạy** — chưa có tài khoản thử tầng này |
| Số lượt gọi | 34 `GET` · 1 `POST` đăng nhập · 0 `POST` làm mới phiên |
| `limit` cho tool danh sách | 5 |

## 1. Kết quả theo tool × vai trò

| Tool | Vai trò | Policy | Lượt gọi | Endpoint | Query keys | HTTP | success | statusCode | Dạng data | Trường | Kết luận | Ghi chú |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `list_my_assets` | company_admin | được phép | chính | `GET /sgod-asset/v1/assets` | limit | 200 | true | — | paginated items n=5 + _fromElasticsearch, fromElasticsearch, meta{hasNextPage,limit,nextCursor} | `_importanceLevel, aliasNames, assetCode, assetType, categoryId, createdAt, createdBy, description, enterpriseId, files, id, images, importanceLevel, initialQuantity, isImportant, locations, manufacturer, name, onBlockchain, origin, qrCode, status, totalQuantity, typeEncrypt, unit, updatedAt, verifyTransfer` | OK | — |
| `list_my_assets` | company_admin | được phép | search=<từ khoá> | `GET /sgod-asset/v1/assets` | limit, search | 200 | true | — | paginated items n=1 + _fromElasticsearch, fromElasticsearch, meta{hasNextPage,limit,nextCursor} | như dòng `list_my_assets` · chính | OK | lọc đúng: 1/1 mục chứa từ khoá |
| `list_my_assets` | company_admin | được phép | cursor | `GET /sgod-asset/v1/assets` | limit, cursor | 200 | true | — | paginated items n=2 + _fromElasticsearch, fromElasticsearch, meta{hasNextPage,limit,nextCursor} | như dòng `list_my_assets` · chính | OK | trang 2: 2 mục, trùng trang 1: 0 |
| `get_asset` | company_admin | được phép | resolve | `GET /sgod-asset/v1/assets` | search | 200 | true | — | paginated items n=1 + _fromElasticsearch, fromElasticsearch, meta{hasNextPage,limit,nextCursor} | như dòng `list_my_assets` · chính | OK | resolve: 1 kết quả, 1 khớp chính xác |
| `get_asset` | company_admin | được phép | chính | `GET /sgod-asset/v1/assets/{id}` | — | 200 | true | — | object (bọc trong asset) | `_importanceLevel, aliasNames, assetCode, assetType, categoryId, createdAt, createdBy, description, enterpriseId, files, id, images, importanceLevel, initialQuantity, isImportant, locations, manufacturer, name, onBlockchain, origin, qrCode, status, totalQuantity, typeEncrypt, unit, updatedAt, verifyTransfer` | OK | ref lấy từ mục đầu list_my_assets (assetCode) |
| `list_maintenance_schedules` | company_admin | được phép | chính | `GET /sgod-asset/v1/maintenance/schedules` | limit | 200 | true | — | paginated items n=2 + meta{hasNextPage,limit,nextCursor} | `assetId, assetStatusId, createdAt, createdBy, endMaintenanceDate, enterpriseId, id, locationAsset, maintenanceType, startMaintenanceDate, status, updatedAt` | OK | hết trang (nextCursor rỗng) — không gọi trang 2 |
| `list_maintenance_schedules` | company_admin | được phép | status=active | `GET /sgod-asset/v1/maintenance/schedules` | limit, status | 200 | true | — | paginated items n=2 + meta{hasNextPage,limit,nextCursor} | như dòng `list_maintenance_schedules` · chính | OK | lọc đúng: 2/2 mục có `status=active` |
| `get_my_profile` | company_admin | được phép | chính | `GET /sgod-auth/v1/users/myself` | — | 200 | true | — | object | `createdAt, email, enterpriseName, fallBackColor, fullName{firstName,lastName}, gender, id, is2FAEnrolled, phone, primaryRoleId, roles, status, userName, userType` | OK | API: userType=enterprise |
| `get_my_permissions` | company_admin | được phép | chính | `GET /sgod-auth/v1/session/context` | — | 200 | true | — | object | `belong, deviceId, displayName, email, id, is2FAVerifiedInSession, isUse2FA, mfaEnabled, permissions, roles, tenantId` | OK | API: belong=Enterprise |
| `get_enterprise_profile` | company_admin | được phép | chính | `GET /sgod-auth/v1/enterprises/profile` | — | 200 | true | — | object | `createdAt, email, enterpriseName, fallBackColor, fullName{firstName,lastName}, gender, id, is2FAEnrolled, phone, primaryRoleId, roles, status, userName, userType` | OK | API: userType=enterprise |
| `list_enterprise_users` | company_admin | được phép | chính | `GET /sgod-auth/v1/enterprise-users` | limit | 200 | true | — | paginated users n=4 + total | `avatarUrl, belong, bossId, departmentId, email, fullName{firstName,lastName}, gender, id, isBlocked, isRemoved, isRevokedWallet, logoUrl, phone, phoneNumber, positionId, roles, status, tenantId, userName` | OK | — |
| `list_enterprise_users` | company_admin | được phép | search=<từ khoá> | `GET /sgod-auth/v1/enterprise-users` | limit, search | 200 | true | — | paginated users n=1 + total | như dòng `list_enterprise_users` · chính | OK | lọc đúng: 1/1 mục chứa từ khoá |
| `list_enterprise_users` | company_admin | được phép | status=Active | `GET /sgod-auth/v1/enterprise-users` | limit, status | 200 | true | — | paginated users n=4 + total | như dòng `list_enterprise_users` · chính | OK | lọc đúng: 4/4 mục có `status=Active` |
| `list_my_conversations` | company_admin | được phép | chính | `GET /sgod-chat/v1/conversations` | limit | 200 | true | — | paginated conversations n=2 + nextCursor | `archivedAt, autoUnarchiveOnNewMessage, createdAt, createdBy, creatorId, description, disappearingSeconds, enableE2EE, firstEnableE2EE, groupKeys, id, isActive, isArchived, isMuted, isPinned, lastMessageAt, lastMessageId, lastMessagePreview, lastNameUserSent, lastUserSentId, logoId, memberCount, members, messageCount, messagesPinned, searchText, settings{allowFileSharing,allowInvites,allowMemberMessagePinning,allowMembersToSendMessages,allowPolling,allowReactions,maxParticipants,onlyAdminsCanCreatePolls,requireApproval}, sortConversation, tenantId, title, type, unreadCount, updatedAt` | OK | hết trang (nextCursor rỗng) — không gọi trang 2 |
| `get_unread_counts` | company_admin | được phép | chính | `GET /sgod-chat/v1/conversations/unread-counts` | — | 200 | true | — | object | `conversationUnread, totalUnread` | OK | — |
| `get_asset_statistics` | company_admin | được phép | chính | `GET /sgod-asset/v1/assets/summary` | — | 200 | true | — | object | `importantAssets, openStatusSessions, totalAssets, withQrCode` | OK | — |
| `get_asset_histories` | company_admin | được phép | resolve | `GET /sgod-asset/v1/assets` | search | 200 | true | — | paginated items n=1 + _fromElasticsearch, fromElasticsearch, meta{hasNextPage,limit,nextCursor} | như dòng `list_my_assets` · chính | OK | resolve: 1 kết quả, 1 khớp chính xác |
| `get_asset_histories` | company_admin | được phép | chính | `GET /sgod-asset/v1/assets/{id}/histories` | — | 200 | true | — | paginated items n=1 + _fromElasticsearch, fromElasticsearch, meta{hasNextPage,limit,nextCursor} | `agentId, assetId, createdAtMs, dataChange, description, id` | OK | ref lấy từ mục đầu list_my_assets (name) |
| `get_maintenance_schedule` | company_admin | được phép | chính | `GET /sgod-asset/v1/maintenance/schedules/{id}` | — | 200 | true | — | object (bọc trong schedule) | `assetId, assetStatusId, createdAt, createdBy, endMaintenanceDate, enterpriseId, id, locationAsset, maintenanceType, startMaintenanceDate, status, updatedAt` | OK | id lấy từ mục đầu list_maintenance_schedules |
| `list_maintenance_records` | company_admin | được phép | chính | `GET /sgod-asset/v1/maintenance/records` | limit | 200 | true | — | paginated items n=0 + meta{hasNextPage,limit,nextCursor} | — | OK | hết trang (nextCursor rỗng) — không gọi trang 2 |
| `list_maintenance_tasks` | company_admin | được phép | chính | `GET /sgod-asset/v1/maintenance/tasks` | limit, maintenanceScheduleId | 200 | true | — | paginated items n=1 + meta{hasNextPage,limit,nextCursor} | `createdAt, description, endDate, enterpriseId, followers, id, maintenanceScheduleId, quantity, staffs, startDate, status, taskTitle, updatedAt` | OK | id lấy từ mục đầu list_maintenance_schedules; hết trang (nextCursor rỗng) — không gọi trang 2 |
| `list_asset_transfers` | company_admin | được phép | chính | `GET /sgod-asset/v1/asset-transfers` | limit | 200 | true | — | paginated items n=5 + meta{hasNextPage,limit,nextCursor} | `acceptFromManager, assetId, assetStatusId, beExecuted, causeRefusal, createdAt, deliveryStaffId, description, enterpriseId, fromUserId, holderUserId, id, locationId, quantity, recipientOwnerMode, statusAsset, statusTransfer, tempRecipientUserId, toManagerToApprove, toUserId, typeTransfer, updatedAt, workflowPhase` | OK | hết trang (nextCursor rỗng) — không gọi trang 2 |
| `list_asset_transfers` | company_admin | được phép | onlyMine=true | `GET /sgod-asset/v1/asset-transfers` | limit, onlyMine | 200 | true | — | paginated items n=5 + meta{hasNextPage,limit,nextCursor} | như dòng `list_asset_transfers` · chính | OK | n=5 (lượt chính n=5); boolean gửi dạng chuỗi `true` |
| `get_asset_transfer` | company_admin | được phép | chính | `GET /sgod-asset/v1/asset-transfers/{id}` | — | 200 | true | — | object (bọc trong assetTransfer) | `acceptFromManager, assetId, assetStatusId, beExecuted, causeRefusal, createdAt, deliveryStaffId, description, enterpriseId, fromUserId, holderUserId, id, locationId, quantity, recipientOwnerMode, statusAsset, statusTransfer, tempRecipientUserId, toManagerToApprove, toUserId, typeTransfer, updatedAt, workflowPhase` | OK | id lấy từ mục đầu list_asset_transfers |
| `get_transfer_summary` | company_admin | được phép | chính | `GET /sgod-asset/v1/asset-transfers/summary` | — | 200 | true | — | object | `receive, send, verify` | OK | — |
| `list_staff_requests` | company_admin | được phép | chính | `GET /sgod-asset/v1/request-staff` | limit | 200 | true | — | paginated items n=5 + meta{hasNextPage,limit,nextCursor} | `approvalContent, approverId, assetId, assetStatusId, createdAt, description, enterpriseId, files, id, images, locationId, previousLocationId, qrCode, quantity, requesterId, statusChange, statusOrigin, statusRequest, subjectId, subjectKind, timeEnd, timeStart, typeRequest, updatedAt` | OK | — |
| `list_staff_requests` | company_admin | được phép | cursor | `GET /sgod-asset/v1/request-staff` | limit, cursor | 200 | true | — | paginated items n=5 + meta{hasNextPage,limit,nextCursor} | như dòng `list_staff_requests` · chính | OK | trang 2: 5 mục, trùng trang 1: 0 |
| `get_staff_request_summary` | company_admin | được phép | chính | `GET /sgod-asset/v1/request-staff/summary` | — | 200 | true | — | object | `receive, send` | OK | — |
| `list_categories` | company_admin | được phép | chính | `GET /sgod-asset/v1/categories` | limit | 200 | true | — | paginated items n=5 + meta{hasNextPage,limit,nextCursor} | `aliasNames, createdAt, enterpriseId, id, name, search, subs, totalAsset, updatedAt` | OK | — |
| `list_categories` | company_admin | được phép | cursor | `GET /sgod-asset/v1/categories` | limit, cursor | 200 | true | — | paginated items n=1 + meta{hasNextPage,limit,nextCursor} | như dòng `list_categories` · chính | OK | trang 2: 1 mục, trùng trang 1: 0 |
| `list_locations` | company_admin | được phép | chính | `GET /sgod-asset/v1/locations` | limit | 200 | true | — | paginated items n=5 + meta{hasNextPage,limit,nextCursor} | `aliasNames, createdAt, detail, enterpriseId, id, map{latitude,longitude}, name, search, subs, totalAsset, updatedAt` | OK | — |
| `list_locations` | company_admin | được phép | cursor | `GET /sgod-asset/v1/locations` | limit, cursor | 200 | true | — | paginated items n=5 + meta{hasNextPage,limit,nextCursor} | `_colorIcon, aliasNames, colorIcon, createdAt, detail, enterpriseId, id, map{latitude,longitude}, name, search, subs, totalAsset, updatedAt` | OK | trang 2: 5 mục, trùng trang 1: 0 |
| `get_location` | company_admin | được phép | chính | `GET /sgod-asset/v1/locations/{id}` | — | 200 | true | — | object | `ancestors, location{aliasNames,createdAt,detail,enterpriseId,id,map,name,search,subs,totalAsset,updatedAt}, nestedSubtree` | OK | id lấy từ mục đầu list_locations |
| `get_location` | company_admin | được phép | id từ get_asset | `GET /sgod-asset/v1/locations/{id}` | — | 200 | false | 404 | — | — | tham khảo | id trong asset.locations của get_asset KHÔNG tra được bằng get_location (không tìm thấy) — mô tả get_location không được gợi ý lấy id từ get_asset; API: 5 NOT_FOUND: [LOCATION_NOT_FOUND] Location <id> not found |

Lượt gọi: **chính** = gọi đúng như executor gọi tool (tool danh sách: `limit`); **resolve** = bước tra ref → id của `x_sgod.resolve`; **<tham số>=…** = một tham số lọc tuỳ chọn của tool (từ khoá tìm lấy từ mục đầu của lượt chính, giá trị enum ưu tiên giá trị có trong dữ liệu); **cursor** = trang 2 bằng `nextCursor` của lượt chính; **id từ get_asset** = kiểm tra thêm: id trong `asset.locations` có dùng được cho `get_location` không.

Kết luận: **OK** = `success:true` trên dữ liệu thật · **OK ⚠** = `success:true` nhưng có dấu hiệu API bỏ qua tham số hoặc thiếu cursor (xem ghi chú) · **route OK, không có dữ liệu** = nguồn rỗng nên gọi bằng ObjectId hợp lệ không tồn tại; route có (phong bì không tìm thấy) · **route MISSING** = gateway trả `Cannot GET` · **LỖI** / **BỎ QUA** = thất bại ở vai trò được phép · **CHẶN (policy)** = vai trò không có trong `tool_policy.json` của tool: chat từ chối (Layer 1 + Layer 2, §3.6); lượt gọi chỉ để ghi lại SGOD tự trả gì · **tham khảo** = kiểm tra thêm, không tính vào kết luận của tool.

## 2. Tóm tắt

- `company_admin`: 22 tool · 34 lượt gọi — OK 33 · LỖI 0 · tham khảo 1
- `employee`: **không gọi API thật** — hạ tầng tham chiếu chưa có tài khoản thử tầng `enterprise-users` (`SGOD_EUSER_EMAIL` / `SGOD_EUSER_PASSWORD` không đặt). Từ chối cho `employee` do `tool_policy.json` bảo đảm bằng mã: Layer 1 — danh sách tool render cho `employee` không chứa tool chỉ dành cho `company_admin`; Layer 2 — `authorize_tool_call` trả *denied* (§3.6).

**Checkpoint S Việc 4** (mỗi tool: ≥ 1 lượt `success:true` thật cho vai trò được phép; ≥ 1 vai trò bị từ chối đúng):

| Tool | `success:true` thật (vai trò được phép) | Từ chối đúng (vai trò bị chặn) |
|---|---|---|
| `list_my_assets` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `get_asset` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `list_maintenance_schedules` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `get_my_profile` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `get_my_permissions` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `get_enterprise_profile` | ✓ company_admin | ✓ employee (Layer 1 + Layer 2; chưa gọi thật)<br>✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `list_enterprise_users` | ✓ company_admin | ✓ employee (Layer 1 + Layer 2; chưa gọi thật)<br>✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `list_my_conversations` | ✓ company_admin | ✓ employee (Layer 1 + Layer 2; chưa gọi thật)<br>✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `get_unread_counts` | ✓ company_admin | ✓ employee (Layer 1 + Layer 2; chưa gọi thật)<br>✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `get_asset_statistics` | ✓ company_admin | ✓ employee (Layer 1 + Layer 2; chưa gọi thật)<br>✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `get_asset_histories` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `get_maintenance_schedule` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `list_maintenance_records` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `list_maintenance_tasks` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `list_asset_transfers` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `get_asset_transfer` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `get_transfer_summary` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `list_staff_requests` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `get_staff_request_summary` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `list_categories` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `list_locations` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |
| `get_location` | ✓ company_admin | ✓ system_admin (Layer 1 + Layer 2; không có tầng đăng nhập SGOD) |

Kết quả checkpoint: **22/22** tool có `success:true` thật cho vai trò được phép; **22/22** tool có ≥ 1 vai trò bị từ chối đúng theo `tool_policy.json` (Layer 1 + Layer 2).

## 3. Kiểm tra offline `tool_policy.json` (không gọi mạng)

### 3.1 `validate_tools.check_tools` (cấu trúc, spec, danh sách chặn, chat, resolve, policy)

0 lỗi, 0 cảnh báo trên 22 tool.

### 3.2 Không tham số company / tenant / enterprise id

Đã quét 32 tên tham số (kể cả lồng nhau) và khoá query của bước resolve theo mẫu `(company|tenant|enterprise)_?id`: **0** khớp.
JWT quyết định tenant (spec §1).

### 3.3 Tool `/sgod-chat` chỉ mở cho `company_admin`

| Tool | `roles` trong policy | Đạt |
|---|---|---|
| `list_my_conversations` | company_admin | ✓ |
| `get_unread_counts` | company_admin | ✓ |

Spec §4: chat-service trả 500 cho token enterprise-user / sub-enterprise.

### 3.4 Không dùng route đã bỏ / hỏng

Danh sách chặn (spec §4 qua `validate_tools.parse_spec_blocklist` + route đã bỏ khi gọi thật 2026-10-14): `/sgod-asset/v1/asset-offers`, `/sgod-asset/v1/assets/suggest`, `/sgod-asset/v1/categories-offer`, `/sgod-asset/v1/dashboard/*`, `/sgod-asset/v1/dashboard/statistics-asset`, `/sgod-asset/v1/dashboard/summary`, `/sgod-asset/v1/import-export/exports`, `/sgod-asset/v1/maintenance/schedules/count-by-tab`.
Số tool dùng các route này (đường dẫn hoặc bước resolve): **0**.

### 3.5 Chỉ đọc

22/22 tool có `x_sgod.method = GET`, `x_sgod.writes = false` và policy `writes = false`.

### 3.6 Ma trận từ chối — Layer 1 + Layer 2

Layer 1: model chỉ thấy tool có vai trò trong `tool_policy.json` (`validate_tools.tools_for_role`, cùng bộ lọc mà `finetune_qlora.py` / `predict_toolcall.py` dùng khi render `tools=`). Layer 2: executor gọi `authorize_tool_call` — vai trò ∉ `tool_policy.json[tool].roles` → *denied*, trả `REFUSAL_VI` và không gọi SGOD (hợp đồng 3 §6). Quyền do mã quyết định, không do model.

| Vai trò | Tầng đăng nhập SGOD | Số tool mở (Layer 1) | Tool bị từ chối (Layer 2) |
|---|---|---|---|
| `employee` | `enterprise-users`, `sub-enterprises` | 17 | `get_enterprise_profile`, `list_enterprise_users`, `list_my_conversations`, `get_unread_counts`, `get_asset_statistics` |
| `company_admin` | `enterprises` | 22 | — |
| `system_admin` | không có (không hỗ trợ) | 0 | `list_my_assets`, `get_asset`, `list_maintenance_schedules`, `get_my_profile`, `get_my_permissions`, `get_enterprise_profile`, `list_enterprise_users`, `list_my_conversations`, `get_unread_counts`, `get_asset_statistics`, `get_asset_histories`, `get_maintenance_schedule`, `list_maintenance_records`, `list_maintenance_tasks`, `list_asset_transfers`, `get_asset_transfer`, `get_transfer_summary`, `list_staff_requests`, `get_staff_request_summary`, `list_categories`, `list_locations`, `get_location` |

Layer 1 ≡ Layer 2 ≡ `x_sgod.allowed_roles` cho mọi cặp (vai trò, tool): **✓**.
Kết luận kiểm tra offline: **đạt**.

## 4. Phạm vi dữ liệu `employee` so với `company_admin`

Chưa so sánh được (cần lượt chính thành công của cả hai vai trò).

## 5. Chạy lại

```bash
# Chỉ trên hạ tầng tham chiếu. Biến lấy từ .env (mẫu: .env.example); không bao giờ commit .env.
set -a; . ./.env; set +a
python tools/sgod/verify_tools_live.py --dry-run     # kế hoạch + kiểm tra offline, không gọi mạng
python tools/sgod/verify_tools_live.py --out docs/sgod/tools_v1_live_check.md
```
