# Persona người dùng SGOD — đầu vào cho lõi eval (D Việc 2) và prompt sinh (D Việc 3)

> **Trạng thái: stub.** Điền trước **2026-09-27** (S Việc 3, từ fixtures trích trên hạ tầng tham chiếu), cùng `docs/contracts/roles.md`, `tools/sgod/roles.json`
> và `prompts/system_preamble_v1.txt`. Nhóm D **không** viết câu eval trước khi tài liệu này được đánh dấu "chốt".
> Quy tắc của D Việc 2: mỗi thành viên viết 50 câu **chỉ từ** danh mục tool (`tools/sgod/tool_api_mapping.md`) và tài liệu này,
> **trước** khi đọc bất kỳ prompt sinh dữ liệu nào.

## 1. Ba tier tài khoản SGOD → vai trò chat (tóm tắt hợp đồng 3)

| Tier SGOD (endpoint đăng nhập) | `userType` | Vai trò chat | Ai là người này | Trạng thái |
|---|---|---|---|---|
| Enterprise — chủ tenant (`POST /sgod-auth/v1/enterprises/sessions`) | `enterprise` | `company_admin` | chủ doanh nghiệp / quản trị viên toàn công ty | điền trước 2026-09-27 (S Việc 3) |
| Enterprise User (`POST /sgod-auth/v1/enterprise-users/sessions`) | *chưa bắt được — bổ sung từ fixtures ở S Việc 2* | `employee` | nhân viên trực thuộc doanh nghiệp | điền trước 2026-09-27 (S Việc 3) |
| Sub-Enterprise User (`POST /sgod-auth/v1/sub-enterprises/sessions`) | *chưa bắt được — bổ sung từ fixtures ở S Việc 2* | `employee` | nhân viên của đơn vị con / chi nhánh | điền trước 2026-09-27 (S Việc 3) |
| SGOD platform admin (`/sgod-admins/sessions`) | — | `system_admin` (giữ trong từ vựng, **không dùng**) | vận hành nền tảng | ngoài phạm vi pha 2 |

Không bao giờ khoá vai trò theo ObjectId vai trò của SGOD; chỉ theo tier đăng nhập / `userType` (`roles.md`).

## 2. Persona (điền trước 2026-09-27, S Việc 3)

Mỗi persona cần: tên gọi ngắn, vai trò chat, bối cảnh công việc, 3–5 nhu cầu thông tin thường gặp, cách xưng hô / văn
phong tiếng Việt, những gì persona **không được** làm (để sinh câu `denied`), và những chủ đề ngoài phạm vi persona hay hỏi
(để sinh câu `null`).

### 2.1 `company_admin` — chủ / quản trị doanh nghiệp (`role_vi`: Quản trị viên doanh nghiệp)

- Tên gọi: *điền trước 2026-09-27*
- Bối cảnh: *điền trước 2026-09-27*
- Nhu cầu thường gặp (3–5): *điền trước 2026-09-27*
- Văn phong: *điền trước 2026-09-27*
- Không được làm trong pha 2 (tool ghi bị blocklist): *điền trước 2026-09-27*
- Câu ngoài phạm vi hay gặp: *điền trước 2026-09-27*

### 2.2 `employee` — nhân viên doanh nghiệp (Enterprise User; `role_vi`: Nhân viên)

- Tên gọi: *điền trước 2026-09-27*
- Bối cảnh: *điền trước 2026-09-27*
- Nhu cầu thường gặp (3–5): *điền trước 2026-09-27*
- Văn phong: *điền trước 2026-09-27*
- Không được làm (tool chỉ dành cho `company_admin`): *điền trước 2026-09-27*
- Câu ngoài phạm vi hay gặp: *điền trước 2026-09-27*

### 2.3 `employee` — nhân viên đơn vị con (Sub-Enterprise User)

- Tên gọi: *điền trước 2026-09-27*
- Bối cảnh (khác 2.2 ở điểm nào — chi nhánh, phạm vi dữ liệu): *điền trước 2026-09-27*
- Nhu cầu thường gặp (3–5): *điền trước 2026-09-27*
- Văn phong: *điền trước 2026-09-27*
- Không được làm: *điền trước 2026-09-27*
- Câu ngoài phạm vi hay gặp: *điền trước 2026-09-27*

## 3. Thực thể dùng trong câu hỏi (điền từ `fixtures/sgod/` trước 2026-09-27)

Tên tài sản, mã tài sản, tên vị trí / chi nhánh, tên danh mục, trạng thái (enum), khoảng thời gian — lấy **từ fixtures đã
che PII**, không bịa tên người thật. Danh sách này cũng là `ENTITY_POOLS` của `datagen/config_sgod.py` (D Việc 3).

- Tài sản: *điền trước 2026-09-27*
- Vị trí / chi nhánh: *điền trước 2026-09-27*
- Danh mục: *điền trước 2026-09-27*
- Enum trạng thái: *điền trước 2026-09-27* (xem `fixtures/sgod/README.md`)

## 4. Điều kiện chốt

- [ ] Ba persona đủ 6 mục; ít nhất một mục "không được làm" dẫn tới câu `expected_permission: denied` cho `employee`.
- [ ] Thực thể khớp với `fixtures/sgod/README.md` (S Việc 2).
- [ ] Dòng trạng thái đầu tài liệu đổi thành "chốt <ngày>" và ghi CHANGELOG (S Việc 3).
