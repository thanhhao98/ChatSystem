# Fixture phản hồi SGOD (S Việc 2)

> **Nguồn:** mọi tệp `.json` trong thư mục này là **toàn bộ body thật** do gateway SGOD trả về, chụp trên hạ tầng tham chiếu
> bằng `tools/sgod/capture_fixtures.py capture` ngày **2026-10-14**, chụp lại **2026-10-21** (tài khoản thử tầng enterprise, chỉ `GET` + đăng nhập / làm mới phiên), sau đó che PII bằng giá trị giả nhất
> quán. Lần chụp lại chỉ thay các tệp có dữ liệu đổi (11 tệp, §5); tệp khác giữ bản 2026-10-14 (cột thời điểm của `manifest.tsv`). Không tệp nào được viết tay hay sinh từ mẫu. `manifest.tsv` ghi cho từng tệp: endpoint đã gọi (kèm query), tầng tài
> khoản, mã HTTP, thời điểm chụp và sha256. Thực tập sinh không gọi SGOD trực tiếp: cần thêm hoặc chụp lại fixture thì bình
> luận vào task S Việc 2 để chạy lại script trên hạ tầng tham chiếu.

## 1. Quy ước đặt tên

`fixtures/sgod/<service>/<METHOD>_<slug>.json`

- `<service>`: `asset`, `auth`, `chat`; các ca lỗi nằm trong `negative/`.
- `<slug>`: phần đường dẫn sau `/v1/`, đổi `/` và `-` thành `_`, bỏ ngoặc của tham số đường dẫn
  (`/sgod-asset/v1/asset-statuses/by-asset/{assetId}` → `GET_asset_statuses_by_asset_assetId.json`).
- Tệp gọi bằng token enterprise-user (thay vì token enterprise) có hậu tố `__as_enterprise_user`.
- Body giữ nguyên phong bì gateway: thành công `{success, data, message, timestamp, …}`, lỗi
  `{success: false, statusCode, error, message, …}`. Gateway có khi trả HTTP 200 cho lỗi, nên mã HTTP thật nằm ở cột
  `http_status` của `manifest.tsv`, không suy từ tên tệp.
- `negative/FLOW_401_refresh_retry_success.json` là luồng 3 bước thật (401 → `POST /sgod-auth/v1/sessions/refresh` → gọi
  lại thành công); mỗi bước gồm `request`, `http_status`, `body`; token đã che.

## 2. Che PII

Cùng một giá trị thật luôn thành cùng một giá trị giả ở **mọi** tệp: email → `userNN@example.com`; số điện thoại →
`+84000000NNN`; họ tên → `TestNN Nguyễn` / `Người dùng NN`; `userName` → `userNN`; tên doanh nghiệp → `Doanh nghiệp Demo NN`;
địa chỉ → `Địa chỉ mẫu NN`; URL ảnh → `https://example.com/media/NN.png`; IP → `203.0.113.N`; token → `<redacted-token>`.
**Giữ nguyên:** ObjectId, mã tài sản, tên tài sản / danh mục / vị trí và mọi giá trị enum. Script dừng và không ghi tệp nếu
sau khi che vẫn còn email ngoài `example.com`, số điện thoại Việt Nam, JWT, địa chỉ gateway hay khóa API.

## 3. Danh mục tệp

31 tệp (asset 16 · auth 6 · chat 3 · negative 6), sinh từ `manifest.tsv`:

| Tệp | Endpoint (đã gọi) | Tầng | HTTP | Ghi chú |
|---|---|---|---|---|
| `auth/GET_users_myself.json` | `GET /sgod-auth/v1/users/myself` | enterprise | 200 |  |
| `auth/GET_session_context.json` | `GET /sgod-auth/v1/session/context` | enterprise | 200 |  |
| `auth/GET_enterprises_profile.json` | `GET /sgod-auth/v1/enterprises/profile` | enterprise | 200 |  |
| `auth/GET_enterprise_users.json` | `GET /sgod-auth/v1/enterprise-users` `{"limit": 10}` | enterprise | 200 |  |
| `auth/GET_roles.json` | `GET /sgod-auth/v1/roles` | enterprise | 200 |  |
| `auth/GET_departments_tree.json` | `GET /sgod-auth/v1/departments/tree` | enterprise | 200 |  |
| `asset/GET_assets.json` | `GET /sgod-asset/v1/assets` `{"limit": 10}` | enterprise | 200 |  |
| `asset/GET_assets_id.json` | `GET /sgod-asset/v1/assets/6ac9be9827541dacd0a77e9f` | enterprise | 200 |  |
| `negative/GET_assets_suggest__HTTP200.json` | `GET /sgod-asset/v1/assets/suggest` `{"q": "ZZTEST-2610100426"}` | enterprise | 200 | route đã bỏ: HTTP 200 nhưng `success:false`, `statusCode` 404 (đường dẫn rơi vào `/assets/{id}`); tìm theo tên/mã dùng `GET /assets?search=` |
| `asset/GET_assets_id_histories.json` | `GET /sgod-asset/v1/assets/6ac9be9827541dacd0a77e9f/histories` `{"limit": 10}` | enterprise | 200 |  |
| `asset/GET_asset_statuses_by_asset_assetId.json` | `GET /sgod-asset/v1/asset-statuses/by-asset/6ac9be9827541dacd0a77e9f` `{"limit": 10}` | enterprise | 200 |  |
| `negative/GET_asset_statuses_history_assetId__HTTP404.json` | `GET /sgod-asset/v1/asset-statuses/history/6ac9be9827541dacd0a77e9f` `{"limit": 10}` | enterprise | 404 | route không có trong Swagger 2026-10-14 |
| `asset/GET_categories.json` | `GET /sgod-asset/v1/categories` `{"limit": 20}` | enterprise | 200 |  |
| `asset/GET_locations.json` | `GET /sgod-asset/v1/locations` `{"limit": 20}` | enterprise | 200 |  |
| `asset/GET_locations_id.json` | `GET /sgod-asset/v1/locations/6ac9bec727541dacd0a77f80` | enterprise | 200 |  |
| `asset/GET_maintenance_schedules.json` | `GET /sgod-asset/v1/maintenance/schedules` `{"limit": 10}` | enterprise | 200 | 2 lịch (chụp lại 2026-10-21; bản 2026-10-14 là danh sách rỗng) |
| `asset/GET_maintenance_schedules_id.json` | `GET /sgod-asset/v1/maintenance/schedules/6ad615353b0f8e12e2f1910d` | enterprise | 200 | mới 2026-10-21 |
| `asset/GET_maintenance_tasks.json` | `GET /sgod-asset/v1/maintenance/tasks` `{"maintenanceScheduleId": "6ad615353b0f8e12e2f1910d", "limit": 10}` | enterprise | 200 | mới 2026-10-21 |
| `asset/GET_maintenance_records.json` | `GET /sgod-asset/v1/maintenance/records` `{"limit": 10}` | enterprise | 200 | danh sách rỗng |
| `asset/GET_asset_transfers.json` | `GET /sgod-asset/v1/asset-transfers` `{"limit": 10}` | enterprise | 200 |  |
| `asset/GET_asset_transfers_id.json` | `GET /sgod-asset/v1/asset-transfers/6ac9c52451e750872e755fad` | enterprise | 200 |  |
| `asset/GET_asset_transfers_summary.json` | `GET /sgod-asset/v1/asset-transfers/summary` | enterprise | 200 |  |
| `asset/GET_request_staff.json` | `GET /sgod-asset/v1/request-staff` `{"limit": 10}` | enterprise | 200 |  |
| `asset/GET_request_staff_summary.json` | `GET /sgod-asset/v1/request-staff/summary` | enterprise | 200 |  |
| `negative/GET_dashboard_statistics_asset__HTTP404.json` | `GET /sgod-asset/v1/dashboard/statistics-asset` | enterprise | 404 | route đã bỏ (cả nhóm `/dashboard/*`); tổng quan dùng `GET /assets/summary` |
| `chat/GET_conversations.json` | `GET /sgod-chat/v1/conversations` `{"limit": 10}` | enterprise | 200 |  |
| `chat/GET_conversations_unread_counts.json` | `GET /sgod-chat/v1/conversations/unread-counts` | enterprise | 200 |  |
| `chat/GET_messages.json` | `GET /sgod-chat/v1/messages` `{"conversationId": "6aa2c5e2e8667af3ad1333ff", "limit": 10}` | enterprise | 200 |  |
| — | `GET /sgod-asset/v1/maintenance/schedules/count-by-tab` | enterprise | 200 | không còn lỗi: trả `success:true` (spec §4 ghi lỗi gRPC) — không dùng làm ca âm |
| `negative/HTTP200_success_false.json` | `GET /sgod-asset/v1/import-export/exports` | enterprise | 200 | ca âm 1 — lỗi bị che thành HTTP 200, mã thật ở `statusCode` (spec §4) |
| `negative/HTTP401_expired_token.json` | `GET /sgod-auth/v1/users/myself` | enterprise (stale token) | 401 | ca âm 2 — token hết hạn thật (TTL 900 s) |
| `negative/FLOW_401_refresh_retry_success.json` | `FLOW /sgod-auth/v1/users/myself` | enterprise | 401->200->200 | ca âm 3 — luồng 3 bước thật, token đã che |
| — (`negative/HTTP500_chat_conversations_enterprise_user.json`) | `GET /sgod-chat/v1/conversations` | enterprise-user | — | ca âm 4 chưa chụp: hạ tầng tham chiếu chưa có tài khoản thử tầng enterprise-user (spec §4 ghi 500, tái hiện 8/8) |

## 4. Bảng enum (field · value · source file)

| field | value | source file(s) | declared in live OpenAPI enum |
|---|---|---|---|
| `assetType` | `expendable` | `asset/GET_assets.json` | GET /sgod-asset/v1/assets/summary (query); schema CreateAssetDto.assetType (+1) |
| `assetType` | `normal` | `asset/GET_assets.json`, `asset/GET_assets_id.json` | GET /sgod-asset/v1/assets/summary (query); schema CreateAssetDto.assetType (+1) |
| `belong` | `Enterprise` | `auth/GET_session_context.json` | schema InitiateResetPasswordDto.belong |
| `belong` | `EnterpriseUser` | `auth/GET_enterprise_users.json` | schema InitiateResetPasswordDto.belong |
| `belong` | `Subenterprise` | `auth/GET_enterprise_users.json` | schema InitiateResetPasswordDto.belong |
| `belongTo` | `Enterprise` | `chat/GET_conversations.json` | — |
| `belongTo` | `EnterpriseUser` | `chat/GET_conversations.json` | — |
| `gender` | `Female` | `auth/GET_enterprise_users.json` | — |
| `gender` | `Male` | `auth/GET_enterprise_users.json` | — |
| `gender` | `Other` | `auth/GET_enterprise_users.json`, `auth/GET_enterprises_profile.json`, `auth/GET_users_myself.json`, `negative/FLOW_401_refresh_retry_success.json` | — |
| `importanceLevel` | `normal` | `asset/GET_assets.json`, `asset/GET_assets_id.json` | GET /sgod-asset/v1/assets (query); GET /sgod-asset/v1/assets/summary (query) (+2) |
| `layer` | `Enterprise` | `auth/GET_roles.json` | schema CreatePositionDto.layer |
| `layer` | `EnterpriseUser` | `auth/GET_roles.json` | schema CreateRoleDto.layer |
| `layer` | `Subenterprise` | `auth/GET_roles.json` | schema CreateRoleDto.layer |
| `locationAsset` | `internal` | `asset/GET_maintenance_schedules.json`, `asset/GET_maintenance_schedules_id.json` | schema CreateMaintenanceScheduleDto.locationAsset; schema UpdateMaintenanceScheduleDto.locationAsset |
| `maintenanceType` | `condition-based` | `asset/GET_maintenance_schedules.json`, `asset/GET_maintenance_schedules_id.json` | schema CreateMaintenanceScheduleDto.maintenanceType |
| `maintenanceType` | `preventive` | `asset/GET_maintenance_schedules.json` | schema CreateMaintenanceScheduleDto.maintenanceType |
| `roleType` | `ENTERPRISE` | `auth/GET_roles.json` | schema CreateRoleDto.role_type |
| `sourceType` | `SYSTEM` | `auth/GET_roles.json` | — |
| `status` | `Active` | `auth/GET_enterprise_users.json`, `auth/GET_enterprises_profile.json`, `auth/GET_users_myself.json`, `negative/FLOW_401_refresh_retry_success.json` | GET /sgod-auth/v1/departments/deleted (query); GET /sgod-auth/v1/enterprise-users (query) (+10) |
| `status` | `active` | `asset/GET_asset_statuses_by_asset_assetId.json`, `asset/GET_assets.json`, `asset/GET_assets_id.json`, `asset/GET_maintenance_schedules.json`, `asset/GET_maintenance_schedules_id.json` | GET /sgod-asset/v1/maintenance/schedules (query); schema AddAssetLocationDto.status (+3) |
| `status` | `processing` | `asset/GET_maintenance_tasks.json` | schema ChangeMaintenanceTaskStatusDto.status |
| `statusAsset` | `active` | `asset/GET_asset_transfers.json`, `asset/GET_asset_transfers_id.json` | — |
| `statusChange` | `completed` | `asset/GET_request_staff.json` | — |
| `statusChange` | `on-hold` | `asset/GET_request_staff.json` | — |
| `statusChange` | `processing` | `asset/GET_request_staff.json` | — |
| `statusOrigin` | `processing` | `asset/GET_request_staff.json` | — |
| `statusOrigin` | `scheduled` | `asset/GET_request_staff.json` | — |
| `statusRequest` | `cancel` | `asset/GET_request_staff.json` | — |
| `statusRequest` | `confirm` | `asset/GET_request_staff.json` | schema ApproveRequestStaffDto.statusRequest |
| `statusRequest` | `deny` | `asset/GET_request_staff.json` | schema ApproveRequestStaffDto.statusRequest |
| `statusRequest` | `pending` | `asset/GET_request_staff.json` | — |
| `statusTransfer` | `accept` | `asset/GET_asset_transfers.json`, `asset/GET_asset_transfers_id.json` | GET /sgod-asset/v1/asset-transfers/history (query) |
| `subjectKind` | `maintenance_task` | `asset/GET_request_staff.json` | — |
| `type` | `change-status` | `asset/GET_asset_statuses_by_asset_assetId.json` | — |
| `type` | `group` | `chat/GET_conversations.json` | GET /sgod-chat/v1/conversations (query) |
| `type` | `private` | `chat/GET_conversations.json` | GET /sgod-chat/v1/conversations (query) |
| `typeRequest` | `change-status-maintenance` | `asset/GET_request_staff.json` | schema CreateRequestStaffChangeStatusDto.typeRequest |
| `typeTransfer` | `revoke-asset` | `asset/GET_asset_transfers.json`, `asset/GET_asset_transfers_id.json` | — |
| `unit` | `cái` | `asset/GET_assets.json` | — |
| `unit` | `hộp` | `asset/GET_assets.json` | — |
| `unit` | `piece` | `asset/GET_assets.json`, `asset/GET_assets_id.json` | GET /sgod-asset/v1/assets/summary (query); schema CreateAssetDto.unit (+1) |
| `userType` | `enterprise` | `auth/GET_enterprises_profile.json`, `auth/GET_users_myself.json`, `negative/FLOW_401_refresh_retry_success.json` | schema LoginResponseDto.userType |
| `workflowPhase` | `completed` | `asset/GET_asset_transfers.json`, `asset/GET_asset_transfers_id.json` | — |

Sinh bằng `python tools/sgod/capture_fixtures.py inventory --fixtures fixtures/sgod --openapi-enums <enum Swagger 2026-10-14>`;
cột cuối là nơi Swagger khai báo cùng giá trị (tối đa 2 nơi, `(+N)` = còn N nơi khác).

**Khai báo trong Swagger 2026-10-14, chưa thấy trong dữ liệu** (doanh nghiệp thử ít dữ liệu — dùng khi cần giá trị cho dữ liệu sinh, ghi rõ nguồn là Swagger):

| Trường (nơi khai báo) | Giá trị khai báo | Đã thấy trong fixture |
|---|---|---|
| `status` của lịch bảo trì (`GET /maintenance/schedules`, query) | `draft` · `active` · `completed` | `active` (2026-10-21) |
| `status` của task bảo trì (`ChangeMaintenanceTaskStatusDto`) | `scheduled` · `processing` · `completed` · `overdue` · `on-hold` | `processing` (`asset/GET_maintenance_tasks.json`); `completed`, `on-hold` (qua `statusChange` / `statusOrigin` của request-staff) |
| `maintenanceType` (`CreateMaintenanceScheduleDto`) | `schedule` · `preventive` · `emergency` · `corrective` · `condition-based` | `condition-based`, `preventive` (2026-10-21) |
| `status` trạng thái tài sản tại vị trí (`CreateAssetStatusDto`) | `active` · `repair` · `not_use` · `broken` · `sold` · `used_up` | `active` |
| `importanceLevel` (`GET /assets`, query) | `normal` · `important` · `confidential` | `normal` |
| `assetType` | `normal` · `expendable` | `normal`, `expendable` (2026-10-21) |
| `unit` | `can` · `piece` · `box` · `bottle` · `pack` · `tree` · `pot` · `set` · `jar` · `kg` · `gram` · `m` | `piece`; dữ liệu 2026-10-21 còn có `cái`, `hộp` (không có trong enum Swagger) |
| `status` phiếu chuyển giao (`GET /asset-transfers`, query) | `pending` · `accept` · `deny` · `revoke` · `cancel` | `accept` |
| `typeRequest` (`CreateRequestStaffChangeStatusDto`) | `change-status` · `change-status-maintenance` | `change-status-maintenance` |
| `statusRequest` (`ApproveRequestStaffDto`) | `confirm` · `deny` | `confirm`, `deny`, và `cancel`, `pending` (chỉ thấy trong dữ liệu) |
| `type` của request-staff (`GET /request-staff`, query) | `send` · `receive` | — (tham số lọc) |
| `status` tài khoản (`GET /enterprise-users`, query) | `Pending` · `Verified` · `Active` · `Blocked` | `Active` |
| `userType` (`LoginResponseDto`) | `enterprise` · `enterprise_user` · `sub_enterprise` · `sgod_user` · `sgod_admin` | `enterprise` |
| `type` hội thoại (`GET /conversations`, query) | `group` · `private` · `all` | `group`, `private` |

## 5. Đối chiếu khi chụp (2026-10-14, chụp lại 2026-10-21)

- **2026-10-21:** doanh nghiệp thử có thêm dữ liệu mẫu đánh dấu `[SEED]` (tài sản `[SEED] Laptop Dell Latitude 5440`…,
  danh mục, vị trí, 2 lịch bảo trì, 1 công việc bảo trì, phiếu yêu cầu); danh sách nhân sự còn 4 tài khoản (3 `EnterpriseUser`,
  1 `Subenterprise`). Chụp lại toàn bộ, chỉ commit 11 tệp có dữ liệu đổi: `asset/GET_{assets,categories,locations,locations_id,
  maintenance_schedules,request_staff,request_staff_summary}.json`, `auth/GET_{enterprise_users,roles}.json` và 2 tệp mới
  `asset/GET_maintenance_schedules_id.json`, `asset/GET_maintenance_tasks.json`. Mọi giá trị của bản 2026-10-14 vẫn có trong
  bản mới (chỉ thêm). Tiền tố `[SEED] ` là dấu dữ liệu mẫu, không phải tên người dùng gõ.
- Danh mục tool v1 (`tools/sgod/sgod_tools.json`, 22 tool): cả 22 tool có lượt gọi thật `success:true` ngày 2026-10-21 —
  xem `docs/sgod/tools_v1_live_check.md` (S Việc 4; `GET /assets/summary` của `get_asset_statistics` được kiểm ở đó, không
  có tệp mẫu ở đây).
- Spec §4: `GET /maintenance/schedules/count-by-tab` nay trả `success:true`; `GET /dashboard/summary`, `GET /asset-offers`,
  `GET /categories-offer` trả 404 (route đã bỏ); `GET /import-export/exports` vẫn lỗi (HTTP 200 + `success:false`, 500).
- Access token sống 900 s (`expiresIn` trong phản hồi làm mới phiên).
- Dữ liệu là doanh nghiệp thử của môi trường QA (tên tài sản / vị trí dạng `ZZTEST-…`, `QA Test Laptop`).

## 6. Chụp lại

```bash
# Chỉ trên hạ tầng tham chiếu. Biến lấy từ .env (mẫu: .env.example); không bao giờ commit .env.
set -a; . ./.env; set +a
python tools/sgod/capture_fixtures.py capture --dry-run          # xem kế hoạch, không gọi mạng
python tools/sgod/capture_fixtures.py capture --out fixtures/sgod --employee-samples
python tools/sgod/capture_fixtures.py inventory --fixtures fixtures/sgod
```
