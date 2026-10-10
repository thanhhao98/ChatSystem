# SGOD Response Fixtures (Dữ liệu mẫu phản hồi thật)

> **Mục tiêu**: Bộ dữ liệu mẫu phản hồi chuẩn từ hệ thống SGOD phục vụ nhóm Data (D Việc 1 & 2) xây dựng `ENTITY_POOLS`, tham số ngẫu nhiên (Param Sampler) và hỗ trợ unit test / mock offline cho nhóm System.

---

## 1. Quy ước đặt tên tệp (Naming Convention)

Tất cả các tệp fixture được lưu trữ theo cấu trúc thư mục phân tách theo dịch vụ:
`fixtures/sgod/<service>/<METHOD>_<slug>.json`

- `<service>`: `asset`, `auth`, `chat`, hoặc `negative` (các kịch bản lỗi).
- `<METHOD>`: Phương thức HTTP viết hoa (`GET`, `POST`...).
- `<slug>`: Tên định danh endpoint, thay thế dấu `/` và tham số `{id}` bằng dấu gạch dưới `_`.
- Mọi tệp đều tuân thủ định dạng phong bì chuẩn của SGOD Gateway:
  ```json
  {
    "success": true,
    "data": { ... },
    "message": "...",
    "timestamp": "..."
  }
  ```

---

## 2. Danh mục Tệp Fixtures Đã Thu Thập (26 tệp)

### 2.1. Dịch vụ Quản lý Tài sản (`fixtures/sgod/asset/` - 14 tệp)
| Tên tệp | HTTP Method | Endpoint tương ứng | Mô tả dữ liệu |
|---|---|---|---|
| `GET_assets.json` | `GET` | `/sgod-asset/v1/assets` | Danh sách tài sản kèm phân trang keyset |
| `GET_assets_id.json` | `GET` | `/sgod-asset/v1/assets/{id}` | Chi tiết 1 tài sản cụ thể theo ID |
| `GET_assets_suggest.json` | `GET` | `/sgod-asset/v1/assets/suggest` | Gợi ý tìm kiếm tài sản (Elasticsearch) |
| `GET_assets_id_histories.json` | `GET` | `/sgod-asset/v1/assets/{id}/histories` | Lịch sử thay đổi thông tin của tài sản |
| `GET_asset_statuses_history_assetId.json` | `GET` | `/sgod-asset/v1/asset-statuses/history/{assetId}` | Lịch sử chuyển trạng thái của tài sản |
| `GET_asset_statuses_by_asset_assetId.json` | `GET` | `/sgod-asset/v1/asset-statuses/by-asset/{assetId}` | Phiên trạng thái hiện tại theo tài sản |
| `GET_maintenance_schedules.json` | `GET` | `/sgod-asset/v1/maintenance/schedules` | Danh sách lịch bảo trì thiết bị |
| `GET_maintenance_schedules_id.json` | `GET` | `/sgod-asset/v1/maintenance/schedules/{id}` | Chi tiết lịch bảo trì theo ID |
| `GET_maintenance_records.json` | `GET` | `/sgod-asset/v1/maintenance/records` | Lịch sử chi phí và bản ghi nghiệm thu bảo trì |
| `GET_maintenance_tasks.json` | `GET` | `/sgod-asset/v1/maintenance/tasks` | Danh sách công việc bảo trì được giao |
| `GET_asset_transfers.json` | `GET` | `/sgod-asset/v1/asset-transfers` | Danh sách phiếu chuyển giao / điều chuyển tài sản |
| `GET_asset_transfers_id.json` | `GET` | `/sgod-asset/v1/asset-transfers/{id}` | Chi tiết phiếu bàn giao theo ID |
| `GET_request_staff.json` | `GET` | `/sgod-asset/v1/request-staff` | Danh sách yêu cầu đề xuất từ nhân sự |
| `GET_locations.json` | `GET` | `/sgod-asset/v1/locations` | Danh sách địa điểm, kho bãi phẳng kèm tọa độ |

### 2.2. Dịch vụ Xác thực & Người dùng (`fixtures/sgod/auth/` - 5 tệp)
| Tên tệp | HTTP Method | Endpoint tương ứng | Mô tả dữ liệu |
|---|---|---|---|
| `GET_users_myself.json` | `GET` | `/sgod-auth/v1/users/myself` | Thông tin người dùng hiện tại từ token JWT |
| `GET_enterprises_profile.json` | `GET` | `/sgod-auth/v1/enterprises/profile` | Thông tin hồ sơ doanh nghiệp |
| `GET_departments_tree.json` | `GET` | `/sgod-auth/v1/departments/tree` | Cây sơ đồ cơ cấu tổ chức và phòng ban |
| `GET_roles.json` | `GET` | `/sgod-auth/v1/roles` | Danh sách các vai trò (Roles) trong hệ thống |
| `GET_enterprise_users.json` | `GET` | `/sgod-auth/v1/enterprise-users` | Danh sách nhân sự trực thuộc doanh nghiệp |

### 2.3. Dịch vụ Trò chuyện & Hội thoại (`fixtures/sgod/chat/` - 3 tệp)
| Tên tệp | HTTP Method | Endpoint tương ứng | Mô tả dữ liệu |
|---|---|---|---|
| `GET_conversations.json` | `GET` | `/sgod-chat/v1/conversations` | Danh sách nhóm chat và tin nhắn cá nhân |
| `GET_conversations_unread_counts.json` | `GET` | `/sgod-chat/v1/conversations/unread-counts` | Số lượng tin nhắn chưa đọc theo từng phòng |
| `GET_messages.json` | `GET` | `/sgod-chat/v1/messages` | Lịch sử tin nhắn chi tiết trong cuộc trò chuyện |

### 2.4. Kịch bản Ca Âm / Xử lý Lỗi (`fixtures/sgod/negative/` - 4 tệp)
| Tên tệp | Mã lỗi | Hiện tượng / Tình huống | Mục đích sử dụng |
|---|---|---|---|
| `HTTP200_success_false.json` | HTTP 200 | Body trả về `success: false`, `statusCode: 400` | Mock lỗi xác thực tham số đầu vào (Validation Error) |
| `HTTP401_expired_token.json` | HTTP 401 | Body trả về `UNAUTHORIZED` | Mock tình huống token hết hạn hoặc chưa đăng nhập |
| `FLOW_401_refresh_retry_success.json` | Luồng | 401 hết hạn token -> gọi refresh -> phục hồi thành công | Kiểm thử cơ chế tự phục hồi phiên trong `tool_executor` |
| `HTTP403_permission_denied.json` | HTTP 403 | Body trả về `FORBIDDEN` | Mock từ chối truy cập khi nhân viên gọi API quản trị |

---

## 3. Danh mục Bảng Enum Thu Thập Được (Enum Inventory)

Dưới đây là tổng hợp các giá trị Enum thu được từ Proto và dữ liệu thực tế, phục vụ nhóm Data tạo `PARAM_SAMPLER`:

| Nhóm thực thể | Tên trường Enum | Các giá trị hợp lệ | Nguồn tệp |
|---|---|---|---|
| **Tài sản (Asset)** | `status` | `active`, `inactive`, `broken`, `liquidated` | `GET_assets.json` |
| **Tài sản (Asset)** | `asset_type` | `normal`, `high_value`, `consumable` | `GET_assets.json` |
| **Bảo trì (Maintenance)** | `status` (schedule) | `active`, `completed`, `cancelled` | `GET_maintenance_schedules.json` |
| **Bảo trì (Maintenance)** | `frequency` | `DAILY`, `WEEKLY`, `MONTHLY`, `QUARTERLY`, `YEARLY` | `GET_maintenance_schedules.json` |
| **Bảo trì (Maintenance)** | `status` (task/record) | `pending`, `in_progress`, `completed`, `cancelled` | `GET_maintenance_tasks.json` |
| **Chuyển giao (Transfer)** | `status` | `draft`, `pending`, `in_transit`, `completed`, `rejected` | `GET_asset_transfers.json` |
| **Yêu cầu nhân sự (Request Staff)** | `type_request` | `BORROW`, `RETURN`, `REPAIR`, `TRANSFER` | `GET_request_staff.json` |
| **Yêu cầu nhân sự (Request Staff)** | `status_request` | `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED` | `GET_request_staff.json` |
| **Người dùng (Auth)** | `user_type` | `ENTERPRISE`, `ENTERPRISE_USER`, `SUB_ENTERPRISE` | `GET_users_myself.json` |
| **Người dùng (Auth)** | `status` | `ACTIVE`, `BLOCKED`, `PENDING_VERIFY` | `GET_enterprise_users.json` |
| **Hội thoại (Chat)** | `type` | `private`, `group`, `channel` | `GET_conversations.json` |
| **Tin nhắn (Chat)** | `messageType` | `text`, `image`, `file`, `system`, `voice`, `pooling` | `GET_messages.json` |
| **Tin nhắn (Chat)** | `status` (message) | `sent`, `delivered`, `read` | `GET_messages.json` |
