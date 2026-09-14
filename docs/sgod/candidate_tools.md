# Danh mục tool SGOD ứng viên cho **D Việc 1** (chỉ đọc, ~20 tool)

> Tài liệu **định hướng** cho nhóm Dữ liệu khi viết `tools/sgod/sgod_tools.json` v1 (hạn 2026-10-04, chốt bằng tag
> `tools-v1` sau S Việc 4). Nguồn duy nhất về API: `docs/sgod-api-reference.md` (spec §2 bảng "Key endpoints",
> §3 bảng "Natural-language intent → API call", §4 "Known issues", §5 phụ lục). Ba tool đầu đã được viết mẫu đầy đủ trong
> `sgod_tools.json`; các tool còn lại là gợi ý — tên cuối cùng, tham số và enum do nhóm quyết định và `validate_tools.py`
> kiểm tra.

## 0. Điều quan trọng nhất: phụ lục spec **không có** tham số truy vấn

Bảng §5 chỉ liệt kê `Method · Path · Summary`. Spec chỉ xác nhận được:

| Tham số | Chứng cứ trong spec |
|---|---|
| `limit`, `cursor` (phân trang) | §3 dòng "Which assets do I own?": *paginate with `?limit&cursor`*; mẫu `GET /assets?limit=5` |
| `q` của `/assets/suggest` | §3 dòng "Show asset <name>": `GET /sgod-asset/v1/assets/suggest?q=<name>` |
| `status` của tài sản | mẫu §2: `"status": "active"` — **chỉ một giá trị** |
| `status` lịch bảo trì | §5: "Đếm lịch **active / complete** theo user — CountMaintenanceScheduleTabs" |
| `subject` của import-templates | §5: "v1 GET /imports?subject=<type>" (không liên quan v1 chat) |

Mọi tham số lọc khác (theo danh mục, vị trí, ngày, người được giao, loại phiếu…) đều là **giả định** cho đến khi có
`docs/sgod/query_params.md` (S Việc 1, 2026-09-27) và `fixtures/sgod/` (S Việc 2) — trích từ API thật trên hạ tầng tham
chiếu, commit vào repo. Cột "Cần bắt fixture" bên dưới đánh dấu tool nào bị chặn bởi việc này; tool `get_*` theo id chỉ cần tham chiếu id nên không bị chặn.

Quy tắc chung (xem `docs/contracts/` và `validate_tools.py`): tên snake_case; mô tả tiếng Việt; **không** tham số
company/tenant/enterprise id; chỉ GET, `writes: false`; endpoint phải có trong bảng spec; không dùng 5 GET hỏng ở §4;
mọi tool `/sgod-chat/v1` chỉ mở cho `company_admin`.

## 1. Ứng viên chính (mục tiêu ~20)

Ký hiệu vai trò: **E** = employee, **A** = company_admin. ✔ = đã có mẫu trong `sgod_tools.json`.

### 1a. Tài sản (asset-service, nhóm `sgod-assets`)

| # | Tên gợi ý | Endpoint | Vì sao (intent §3 / nhu cầu) | Vai trò | Tham số & câu hỏi mở | Cần bắt fixture |
|---|---|---|---|---|---|---|
| 1 ✔ | `list_my_assets` | `GET /sgod-asset/v1/assets` | "Which assets do I own?" — câu hỏi số 1 của người dùng | E, A | `q`, `status` (enum chỉ `active`), `limit`, `cursor`. **Mở:** với token enterprise-user, kết quả là tài sản *được giao cho tôi* hay *cả tenant*? | ✅ tham số lọc |
| 2 ✔ | `get_asset` | `GET /sgod-asset/v1/assets/{id}` + resolve `GET /assets/suggest?q=` | "Show asset <name>", "Where is asset X" | E, A | `asset_ref` (tên \| assetCode \| id). **Mở:** hình dạng phản hồi của `suggest` (danh sách id? tên?) để executor chọn kết quả đầu; xử lý khi nhiều kết quả trùng tên | ✅ mẫu `suggest` |
| 3 | `search_assets` | `GET /sgod-asset/v1/assets/suggest` | "Có tài sản nào tên giống X không?" — trả nhiều ứng viên thay vì một | E, A | `q`\*. Cân nhắc gộp vào #1 (`q`) nếu `/assets` đã tìm theo tên; giữ nếu ES search-as-you-type tốt hơn | ✅ |
| 4 | `get_asset_histories` | `GET /sgod-asset/v1/assets/{id}/histories` | "Lịch sử thay đổi của tài sản X" (tương đương `get_asset_history` ở POC) | E, A | `asset_ref` + resolve như #2; có phân trang? | ✅ mẫu phản hồi |
| 5 | `get_asset_status_history` | `GET /sgod-asset/v1/asset-statuses/history/{assetId}` | "Tài sản X đã qua những trạng thái nào / đổi vị trí khi nào" | E, A | `asset_ref` + resolve. **Mở:** khác gì #4 (histories) — cần fixture để quyết định giữ một hay cả hai | ✅ |
| 6 | `list_asset_statuses` | `GET /sgod-asset/v1/asset-statuses/by-asset/{assetId}` | "Phiên trạng thái hiện tại / số lượng theo vị trí của tài sản X" | E, A | `asset_ref` + resolve. Khái niệm "asset status session" chưa rõ — đọc fixture trước khi viết mô tả | ✅ |

### 1b. Bảo trì (nhóm `sgod-asset-maintenance`)

| # | Tên gợi ý | Endpoint | Vì sao | Vai trò | Tham số & câu hỏi mở | Cần bắt fixture |
|---|---|---|---|---|---|---|
| 7 ✔ | `list_maintenance_schedules` | `GET /sgod-asset/v1/maintenance/schedules` | "Assets needing maintenance" | E, A | `status` (`active`/`complete`), `limit`, `cursor`. **Mở:** lọc theo tài sản? theo khoảng ngày? | ✅ tham số lọc |
| 8 | `get_maintenance_schedule` | `GET /sgod-asset/v1/maintenance/schedules/{id}` | "Chi tiết lịch bảo trì số …" | E, A | `schedule_id`\*. Người dùng hiếm khi biết id → cân nhắc resolve qua #7 + tên tài sản | — |
| 9 | `list_maintenance_records` | `GET /sgod-asset/v1/maintenance/records` | "Tài sản X đã bảo trì những lần nào / chi phí" | E, A | lọc theo tài sản, ngày? | ✅ |
| 10 | `list_maintenance_tasks` | `GET /sgod-asset/v1/maintenance/tasks` | "Việc bảo trì nào đang giao cho tôi" (task có staff/follower — §5 `update-user`) | E, A | lọc theo trạng thái/người thực hiện? **Mở:** JWT có tự lọc theo người được giao không | ✅ |

> **Không dùng:** `GET /maintenance/schedules/count-by-tab` (§4 hỏng). Số lịch active/complete ⇒ đếm từ #7.

### 1c. Chuyển giao & yêu cầu nhân viên (nhóm `sgod-asset-transfers`, `sgod-asset-request-staff`)

| # | Tên gợi ý | Endpoint | Vì sao | Vai trò | Tham số & câu hỏi mở | Cần bắt fixture |
|---|---|---|---|---|---|---|
| 11 | `list_asset_transfers` | `GET /sgod-asset/v1/asset-transfers` | "My asset transfers" (§3) | E, A | lọc theo tab gửi/nhận/xác thực (§5 summary có 3 tab), trạng thái, `limit`, `cursor` | ✅ |
| 12 | `get_asset_transfer` | `GET /sgod-asset/v1/asset-transfers/{id}` | "Chi tiết phiếu chuyển giao …" | E, A | `transfer_id`\* | — |
| 13 | `get_transfer_summary` | `GET /sgod-asset/v1/asset-transfers/summary` | "Tôi có bao nhiêu phiếu chờ nhận / chờ xác thực" — đếm theo tab | E, A | không tham số (kỳ vọng); hình dạng phản hồi? | ✅ mẫu |
| 14 | `list_staff_requests` | `GET /sgod-asset/v1/request-staff` | "Yêu cầu đổi trạng thái / đổi vị trí của tôi đang ở đâu" | E, A | lọc theo tab gửi/nhận, trạng thái | ✅ |
| 15 | `get_staff_request_summary` | `GET /sgod-asset/v1/request-staff/summary` | "Có bao nhiêu yêu cầu chờ tôi duyệt" (A) / "tôi đã gửi" (E) | E, A | không tham số (kỳ vọng) | ✅ mẫu |

### 1d. Danh mục, vị trí, thống kê (nhóm `categories`, `locations`, `dashboard`)

| # | Tên gợi ý | Endpoint | Vì sao | Vai trò | Tham số & câu hỏi mở | Cần bắt fixture |
|---|---|---|---|---|---|---|
| 16 | `list_categories` | `GET /sgod-asset/v1/categories` (hoặc `/categories/tree`) | "Có những danh mục tài sản nào" — dữ liệu tham chiếu, giúp model trả lời và người dùng lọc | E, A | `q`? Chọn flat hay tree (tree tốn token hơn) | ✅ |
| 17 | `list_locations` | `GET /sgod-asset/v1/locations` (hoặc `/locations/tree`) | "Công ty có những vị trí/kho nào" | E, A | như #16 | ✅ |
| 18 | `get_location` | `GET /sgod-asset/v1/locations/{id}` | "Where is asset X" bước 2 (§3: `GET /assets/{id}` + `GET /locations/{id}`) | E, A | `location_id`\*; **Mở:** có nên để executor tự gọi sau `get_asset` (một tool) thay vì tool riêng? | — |
| 19 | `get_asset_statistics` | `GET /sgod-asset/v1/dashboard/statistics-asset` | "How many assets by status" (§3) — thống kê theo thời gian | **A** (E: cân nhắc) | khoảng ngày? granularity? | ✅ |
| 20 | `get_dashboard_es_stats` | `GET /sgod-asset/v1/dashboard/es-stats` | "Phân bổ theo trạng thái, xu hướng theo tháng, top vị trí" — một call cho nhiều câu thống kê | **A** | không tham số (kỳ vọng); phản hồi lớn → tóm tắt | ✅ mẫu |
| 21 | `get_dashboard_categories` | `GET /sgod-asset/v1/dashboard/categories` | "Tài sản theo danh mục" | **A** | như #20 | ✅ |

> **Không dùng:** `GET /dashboard/summary` (§4 hỏng: `countSummary is not a function`).

### 1e. Tài khoản & tổ chức (auth-service)

| # | Tên gợi ý | Endpoint | Vì sao | Vai trò | Tham số & câu hỏi mở | Cần bắt fixture |
|---|---|---|---|---|---|---|
| 22 | `get_my_profile` | `GET /sgod-auth/v1/users/myself` | "Who am I / my profile" (§3) | E, A | không tham số; mẫu đã có trong §2 | — |
| 23 | `get_my_permissions` | `GET /sgod-auth/v1/session/context` | "My roles / permissions" (§3) — chỉ để **hiển thị**, không dùng suy vai trò (roles.md §4) | E, A | không tham số | ✅ mẫu |
| 24 | `get_enterprise_profile` | `GET /sgod-auth/v1/enterprises/profile` | "Thông tin doanh nghiệp của tôi" | **A** | không tham số. **Mở:** employee gọi được không (401/403 hay 200)? → quyết định `allowed_roles` | ✅ với cả 2 token |
| 25 | `list_enterprise_users` | `GET /sgod-auth/v1/enterprise-users` | "Ai đang làm trong công ty tôi / tìm nhân viên A" (tương đương `list_users` POC) | **A** | `q`?, phân trang? PII → trả tối thiểu | ✅ |
| 26 | `get_department_tree` | `GET /sgod-auth/v1/departments/tree` | "Sơ đồ phòng ban" | **A** | không tham số | ✅ mẫu |

### 1f. Chat-service — chỉ chủ doanh nghiệp (spec §4)

| # | Tên gợi ý | Endpoint | Vì sao | Vai trò | Tham số & câu hỏi mở | Cần bắt fixture |
|---|---|---|---|---|---|---|
| 27 | `list_my_conversations` | `GET /sgod-chat/v1/conversations` | "My conversations" (§3) | **A only** | `limit`, `cursor`? JWKS gRPC lỗi ngắt quãng (§4 Med) → executor cần retry | ✅ |
| 28 | `get_unread_counts` | `GET /sgod-chat/v1/conversations/unread-counts` | "My unread messages" (§3) | **A only** | không tham số | ✅ mẫu |

Hai tool này **hữu ích cho eval**: mọi câu hỏi chat của `employee` là câu "denied" hợp lệ (≥ 10% denied trong eval_v1).

## 2. Gợi ý cách chọn 20 trong 28

- **Bắt buộc (đã có intent trong §3):** #1, #2, #7, #11, #19, #22, #23, #27, #28 và #18 (hoặc gộp vào #2).
- **Nên có để phủ câu hỏi thường gặp:** #4, #8, #9, #12, #13, #14, #16, #17, #24, #25.
- **Dự phòng / quyết định theo fixture:** #3, #5, #6, #10, #15, #20, #21, #26.
- Cần **ít nhất 4–5 tool `company_admin`-only** (#19–#21, #24–#28) để eval_v1 có đủ câu denied cho `employee`.
- Ưu tiên tool có **mẫu phản hồi thật** trong `fixtures/sgod/` — mô tả tiếng Việt viết theo dữ liệu thật, không đoán.

## 3. Không đưa vào v1 (và vì sao)

| Nhóm | Ví dụ | Lý do |
|---|---|---|
| 5 GET hỏng (§4) | `/dashboard/summary`, `/maintenance/schedules/count-by-tab`, `/import-export/exports`, `/asset-offers`, `/categories-offer` | Trả 500 / "No handler found" — `validate_tools.py` chặn |
| Mọi thao tác ghi | `POST /assets`, `PATCH /asset-transfers/{id}/respond`, `POST /request-staff`, `PATCH /asset-statuses/{id}/*` | §3 "Start read-only; gate all writes behind confirmation" — cân nhắc sau `tools-v1` |
| Chat cho non-owner | mọi `/sgod-chat/v1` với `employee` | §4 High: 500 cho token Enterprise-User / Sub-Enterprise |
| Quản trị nền tảng | `/sgod-auth/v1/sgod/*`, `/sgod-users`, `/sgod-admins`, `/roles/tenant/{tenantId}` | Ngoài phạm vi tenant; `system_admin` không dùng; có tham số tenantId bị cấm |
| Alias trùng | `/maintenance/schedules/{id}/get-by-id`, `/maintenance/tasks/{id}/get-by-id`, `/participants/members` | Trùng với endpoint chính, chỉ tốn token |
| Kỹ thuật / dev | `/health*`, `/test-crypto/*`, `/dev/emails`, `/emails/token`, `/sessions/devices`, MFA, blockchain info | Không phải câu hỏi nghiệp vụ; một số chỉ dành cho dev |
| Đăng nhập / refresh / logout | `POST /<tier>/sessions`, `POST /sessions/refresh`, `DELETE /sessions` | Backend làm trước khi chat, không phải tool của model (spec §3 bước 1–6) |

## 4. Câu hỏi mở cần trả lời từ API thật (S Việc 1–2, hạ tầng tham chiếu) trước 2026-10-04

1. Tên và kiểu **tham số truy vấn** của mọi GET danh sách (`docs/sgod/query_params.md`): phân trang là `limit/cursor` hay
   `page/pageSize`? có `q`/`search`/`keyword`? lọc `status`, `categoryId`, `locationId`, khoảng ngày?
2. **Enum** đầy đủ: trạng thái tài sản (ngoài `active`), trạng thái phiếu chuyển giao, request-staff, task bảo trì.
3. Với **token enterprise-user**: `GET /assets` trả tài sản *được giao cho tôi* hay *toàn tenant*? Quyết định mô tả của
   `list_my_assets` và có cần tool "tài sản toàn công ty" riêng cho `company_admin` không.
4. Hình dạng phản hồi `GET /assets/suggest` (để executor thực hiện `resolve`) và của `*/summary`, `dashboard/*`.
5. `GET /enterprises/profile`, `GET /enterprise-users`, `GET /departments/tree` với token employee: 200, 401 hay 403?
   (quyết định `allowed_roles` #24–#26).
6. `userType` của Enterprise User và Sub-Enterprise User trong `/users/myself` (điền vào `roles.md` §1).
