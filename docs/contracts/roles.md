# Hợp đồng 3 — Ánh xạ vai trò SGOD → vai trò chat (`roles.md`)

> **Trạng thái: BẢN NHÁP** — chốt tại **Điểm đồng bộ 1 (2026-09-27)** (S Việc 3). Sau mốc này, mọi thay đổi ở
> `tools/sgod/roles.json` buộc phải **gán nhãn lại / sinh lại toàn bộ** dữ liệu SGOD (eval_v1 và tập huấn luyện),
> vì `role` nằm trong từng hàng huấn luyện và `user_role` nằm trong từng bản ghi eval.
> Bản máy đọc: `tools/sgod/roles.json` (khoá `_note` ghi "bản nháp — chốt 2026-09-27 (Điểm đồng bộ 1)").

## 1. Bảng ánh xạ

| Tier tài khoản SGOD (spec §1) | Endpoint đăng nhập | `userType` trong `GET /users/myself` | Vai trò chat (`role`) | Tên tiếng Việt (`role_names_vi`) |
|---|---|---|---|---|
| Enterprise (chủ tenant / chủ doanh nghiệp) | `POST /sgod-auth/v1/enterprises/sessions` | `"enterprise"` (đã thấy trong mẫu spec §2) | `company_admin` | Quản trị viên doanh nghiệp |
| Enterprise User (nhân viên của doanh nghiệp) | `POST /sgod-auth/v1/enterprise-users/sessions` | *chưa bắt được — bổ sung từ fixtures ở S Việc 2* | `employee` | Nhân viên |
| Sub-Enterprise User | `POST /sgod-auth/v1/sub-enterprises/sessions` | *chưa bắt được — bổ sung từ fixtures ở S Việc 2* | `employee` | Nhân viên |
| SGOD platform user / admin | `POST /sgod-auth/v1/sgod-users/sessions` · `/sgod-admins/sessions` | — | **không hỗ trợ** (`system_admin` chỉ giữ chỗ trong từ vựng, không có tool nào mở cho vai trò này) | Quản trị hệ thống |

Tập giá trị hợp lệ của `role` (và của `user_role` trong eval): `["employee", "company_admin", "system_admin"]` — giữ nguyên
từ vựng của hệ thống tham chiếu (POC v1, `chat_policy.py`) để tái dùng `authorize_tool_call`, bộ chấm điểm và các script không đổi.
`system_admin` **không** được ánh xạ từ bất kỳ tier SGOD nào và **không** xuất hiện trong `allowed_roles` của tool nào ở v1.

## 2. Vì sao ánh xạ như vậy

1. **Spec §1 "Identity scoping"** — mọi truy vấn đã được SGOD *tự động* giới hạn theo JWT của người gọi
   (`GET /sgod-asset/v1/assets` chỉ trả tài sản của tenant đó). Vì vậy chat **không cần** và **không được** có tham số
   company / tenant / enterprise id; phạm vi dữ liệu của người dùng do JWT quyết định, còn vai trò chat chỉ quyết định
   **tool nào được mở** cho model và **tool nào executor cho phép chạy**.
2. **Chủ doanh nghiệp = `company_admin`.** Chỉ tier `enterprises` là chủ tenant; các endpoint quản trị (danh sách
   enterprise-users, cây phòng ban, hồ sơ doanh nghiệp, thống kê dashboard) mang nghĩa "toàn doanh nghiệp" và chỉ hợp lý
   với vai trò này.
3. **Spec §4, dòng "High / chat / all endpoints for non-owner"** — chat-service trả `500` cho token Enterprise-User và
   Sub-Enterprise, chỉ chủ doanh nghiệp dùng được (tái hiện 8/8). Do đó mọi tool `/sgod-chat/v1/...` chỉ được
   `allowed_roles: ["company_admin"]`; `validate_tools.py` chặn mọi trường hợp khác.
4. **Hai tier còn lại gộp thành `employee`.** Về mặt quyền dữ liệu, cả Enterprise User và Sub-Enterprise User đều là
   người dùng *trong* một tenant, không sở hữu tenant. Tách thành hai vai trò sẽ làm bộ eval phải phủ thêm một vai trò
   mà chưa có bằng chứng nào trong spec cho thấy tool surface khác nhau. Nếu S Việc 2 (fixtures) cho thấy khác biệt,
   quyết định lại **trước** 2026-09-27.

## 3. Cái gì đóng băng, khi nào

| Mốc | Ngày | Đóng băng |
|---|---|---|
| Điểm đồng bộ 1 | 2026-09-27 | `tools/sgod/roles.json` (roles, tiers, login_endpoints, role_names_vi) và tài liệu này |
| Tag `tools-v1` (S Việc 4) | 2026-10-08 | `allowed_roles` / `tool_policy.json` của từng tool |
| Preamble v1 | 2026-10-11 | Văn bản `prompts/system_preamble_v1.txt` (kể cả tên vai trò tiếng Việt được chèn vào `{role_vi}`) |
| Điểm đồng bộ 2 | 2026-10-25 | `eval_v1.json` — từ đây `user_role` và `expected_permission` bất biến |

Sau Điểm đồng bộ 1, sửa `roles.json` = mở một *trục đo mới* (xem quy tắc phiên bản trong `eval_metric.md`).

## 4. Executor suy ra vai trò như thế nào

Thứ tự ưu tiên (S Việc 6/7 cài đặt; một hàm `build_user_context` duy nhất đọc `roles.json`):

1. **Tier = endpoint đăng nhập thành công.** Backend chat gọi `POST /sgod-auth/v1/<tier>/sessions` với `credential`
   + `password`. Nếu người dùng không chọn tier, dùng `POST /sgod-auth/v1/emails/check-exists {email}` để lấy
   `accountType` rồi chọn endpoint (spec §3 bước 2); hoặc thử lần lượt `enterprises` → `enterprise-users` →
   `sub-enterprises` và lấy tier đầu tiên trả `success: true`. `role = roles.json["tiers"][tier]`.
2. **Xác nhận chéo bằng `userType`** từ `GET /sgod-auth/v1/users/myself`: `"enterprise"` ⇔ `company_admin`.
   Giá trị `userType` của hai tier còn lại chưa có trong spec — được ghi vào fixtures (S Việc 2, trích trên hạ tầng
   tham chiếu) rồi bổ sung vào bảng §1. Khi tier và `userType` mâu thuẫn: ghi log cảnh báo và **giữ vai trò theo tier** (nguồn đăng nhập là
   thứ hệ thống kiểm soát được).
3. **Không dựa vào ObjectId của role.** `roles: ["6a85bad6…"]` và `primaryRoleId` trong `/users/myself`, cũng như
   `GET /sgod-auth/v1/roles`, là ObjectId theo từng tenant — khác nhau giữa các doanh nghiệp, có thể đổi khi admin
   tạo/xoá role, và không mang nghĩa ổn định. Chúng **không** được dùng để quyết định `role`, không được ghi vào dữ
   liệu huấn luyện, không xuất hiện trong preamble.
4. `GET /sgod-auth/v1/session/context` (roles/permissions của phiên) chỉ dùng để **hiển thị** "quyền của tôi" qua một
   tool đọc; không dùng để suy `role`.

`user_context` tối thiểu mà executor và preamble cần: `{"user_id": data.id, "full_name": <firstName lastName>,
"role": <theo trên>, "tier": <tier>}` — **không có** `company_id`/`tenant_id` (JWT đã mang thông tin đó).

## 5. Ai đọc `roles.json`

| Thành phần | Dùng khoá | Mục đích |
|---|---|---|
| `datagen/config_sgod.py` (`ROLE_MAP`) và labeler | `roles`, `tiers` | Gán `user_role` cho kịch bản sinh ra; đánh `expected_permission` |
| `tools/sgod/validate_tools.py` | `roles`, `tiers["enterprises"]`, `role_names_vi` | `allowed_roles ⊂ roles`; chat chỉ mở cho vai trò chủ; điền `{role_vi}` khi đếm token (thay từng slot bằng `str.replace`, cùng renderer với `datagen/build_parity_trainset.py`, nên preamble được phép chứa ví dụ JSON `{...}`) |
| `training/validate_dataset.py --roles` | `roles` | Tập giá trị hợp lệ của trường `role` trong hàng huấn luyện |
| `training/finetune_qlora.py`, `training/predict_toolcall.py` | (qua `tool_policy.json`) | Lọc tool theo vai trò khi render `apply_chat_template(tools=)` |
| `training/eval_toolcall.py` | (qua `tool_policy.json`) | `denied` ⇔ tool dự đoán có `roles` không chứa vai trò người gọi |
| Executor / backend đăng nhập (S Việc 6/7) | `tiers`, `login_endpoints`, `role_names_vi` | Suy `role`, chọn endpoint đăng nhập, điền preamble |

## 6. Hệ quả cho dữ liệu và đánh giá

- Mỗi bản ghi eval có `user_role ∈ roles`; `expected_permission: "denied"` **khi và chỉ khi** `expected_tool` có
  `tool_policy.json[tool].roles` không chứa `user_role`. Với v1 (3 tool đều mở cho `employee` và `company_admin`), câu
  "denied" chỉ phát sinh từ các tool chat/quản trị sẽ thêm ở D Việc 1 — nhóm Dữ liệu cần ≥ 10% câu denied trong eval_v1,
  nên danh mục v1 **phải** có ít nhất vài tool `company_admin`-only.
- Trợ lý trả lời từ chối theo `REFUSAL_VI` (`prompts/fixed_replies.json`) và **không gọi tool**; quyền do executor
  quyết định bằng mã, model chỉ được thấy các tool hợp lệ với vai trò của mình (Layer 1) và vẫn bị chặn lại ở
  `authorize_tool_call` (Layer 2).
