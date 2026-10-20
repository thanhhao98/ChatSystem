# Persona người dùng SGOD — nguồn persona cho prompt sinh (D Việc 3) và phần GPT bổ sung của eval_v1 (D Việc 4)

> **Trạng thái: chốt 2026-10-21 (S Việc 3).** Giữ thứ tự ba mục của bản khung (1 tier, 2 persona, 3 thực thể); thêm §4 ma
> trận phủ, §5 ghi chú cho D Việc 3, §6 quy tắc gán nhãn, §7 điều kiện chốt.
>
> - **Dùng cho:** prompt sinh dữ liệu huấn luyện của **D Việc 3** (`datagen/prompts/*.md`; `datagen/config_sgod.py`:
>   `BUCKET_PLAN` = persona × intent × complexity, `ENTITY_POOLS`, `PARAM_SAMPLER`) và phần sinh bằng GPT của eval_v1 ở
>   **D Việc 4** (bộ prompt riêng `datagen/prompts_eval/`). Hai bộ prompt dùng chung persona nhưng viết tách biệt, không
>   chép prompt qua lại (`datagen/prompts/README.md`).
> - **Không dùng cho:** lõi eval người viết (**D Việc 2**, `data/sgod/eval_human_core.jsonl`, đóng băng 2026-10-20). Lõi
>   đã được viết trước, từ danh mục tool; tài liệu này không sửa, không mở rộng và không trích lõi đó.
> - **Nguồn:** vai trò — `docs/contracts/roles.md` + `tools/sgod/roles.json` (hợp đồng 3, đóng băng); tool và quyền —
>   `tools/sgod/sgod_tools.json` + `tools/sgod/tool_policy.json` (22 tool chỉ đọc); thực thể — `fixtures/sgod/` (phản hồi
>   thật đã che PII, S Việc 2); hành vi trợ lý — `prompts/system_preamble_v1.txt`. Sửa sau ngày chốt: PR `[S-V3]` +
>   `CHANGELOG.md`.

## 1. Ba tier tài khoản SGOD → vai trò chat (tóm tắt hợp đồng 3)

| Tier SGOD (endpoint đăng nhập) | `userType` | Nguồn của `userType` | Vai trò chat (`role`) | `role_vi` (`role_names_vi`) | Ai là người này |
|---|---|---|---|---|---|
| Enterprise — chủ tenant (`POST /sgod-auth/v1/enterprises/sessions`) | `"enterprise"` | **bắt được thật**: `fixtures/sgod/auth/GET_users_myself.json` (cùng giá trị trong `auth/GET_enterprises_profile.json`) | `company_admin` | Quản trị viên doanh nghiệp | chủ doanh nghiệp, hoặc người được giao vận hành tài khoản doanh nghiệp |
| Enterprise User (`POST /sgod-auth/v1/enterprise-users/sessions`) | `"enterprise_user"` | khai báo trong Swagger `LoginResponseDto.userType` (`docs/sgod/openapi-auth.json`; `fixtures/sgod/README.md` §4); **chưa bắt được thật** vì hạ tầng tham chiếu chưa có tài khoản thử tầng enterprise-user | `employee` | Nhân viên | nhân viên trực thuộc doanh nghiệp |
| Sub-Enterprise User (`POST /sgod-auth/v1/sub-enterprises/sessions`) | `"sub_enterprise"` | khai báo trong Swagger `LoginResponseDto.userType` (như trên); **chưa bắt được thật** vì hạ tầng tham chiếu chưa có tài khoản thử tầng sub-enterprise | `employee` | Nhân viên | người dùng của đơn vị con / chi nhánh |
| SGOD platform user / admin (`POST /sgod-auth/v1/sgod-users/sessions` · `/sgod-admins/sessions`) | — | — | không hỗ trợ (`system_admin` chỉ giữ chỗ trong từ vựng, không tool nào mở) | Quản trị hệ thống | vận hành nền tảng — ngoài phạm vi pha 2 |

- Swagger khai báo `LoginResponseDto.userType` ∈ `enterprise` · `enterprise_user` · `sgod_user` · `sgod_admin` ·
  `sub_enterprise` cho phản hồi **đăng nhập**; chưa kiểm được `GET /sgod-auth/v1/users/myself` trả đúng chuỗi đó cho hai tier
  `employee`. Khi có bản bắt thật, giá trị được ghi vào `roles.md` §1 (ghi chú quan sát, không đổi phiên bản — xem đầu
  `roles.md`).
- Quan sát trong fixture: danh sách nhân sự của doanh nghiệp thử (`fixtures/sgod/auth/GET_enterprise_users.json`, 6 tài
  khoản) gồm 3 tài khoản `belong: "EnterpriseUser"` và 3 tài khoản `belong: "Subenterprise"`, cùng `tenantId` với chủ doanh
  nghiệp (`belong: "Enterprise"` trong `auth/GET_session_context.json`). Cả hai tier `employee` là người dùng bên trong cùng
  một tenant, khớp lý do gộp ở `roles.md` §2.4.
- Vai trò suy theo tier đăng nhập, đối chiếu chéo bằng `userType`; **không bao giờ** theo ObjectId vai trò của SGOD
  (`roles.md` §4).
- Tool mở theo vai trò (`tools/sgod/tool_policy.json`): `company_admin` 22/22; `employee` 17, tức mọi tool trừ **5 tool chỉ
  dành cho `company_admin`**: `get_enterprise_profile`, `list_enterprise_users`, `list_my_conversations`, `get_unread_counts`,
  `get_asset_statistics`; `system_admin` 0. Hai tool chat chỉ mở cho `company_admin` vì chat-service trả 500 với token
  Enterprise User và Sub-Enterprise (spec §4, `docs/sgod-api-reference.md`).

## 2. Persona

### 2.0 Tổng quan

7 persona: 2 `company_admin`, 3 `employee` tầng Enterprise User, 2 `employee` tầng Sub-Enterprise User. Khoá persona là tên
dùng trong `BUCKET_PLAN` và trong prompt; nhãn là chức danh, không có tên người.

| # | Khoá | Nhãn (chức danh) | Tier SGOD | `role` | `role_vi` | Tool mở |
|---|---|---|---|---|---|---|
| P1 | `giam_doc` | Giám đốc doanh nghiệp (chủ tài khoản doanh nghiệp) | Enterprise | `company_admin` | Quản trị viên doanh nghiệp | 22 |
| P2 | `quan_ly_tai_san` | Chuyên viên quản lý tài sản (vận hành tài khoản doanh nghiệp) | Enterprise | `company_admin` | Quản trị viên doanh nghiệp | 22 |
| P3 | `nhan_vien_van_phong` | Nhân viên văn phòng | Enterprise User | `employee` | Nhân viên | 17 |
| P4 | `ky_thuat_vien_bao_tri` | Kỹ thuật viên bảo trì | Enterprise User | `employee` | Nhân viên | 17 |
| P5 | `thu_kho` | Thủ kho | Enterprise User | `employee` | Nhân viên | 17 |
| P6 | `kinh_doanh_chi_nhanh` | Nhân viên kinh doanh tại chi nhánh | Sub-Enterprise User | `employee` | Nhân viên | 17 |
| P7 | `hanh_chinh_don_vi_con` | Nhân viên hành chính – tổng hợp của đơn vị con | Sub-Enterprise User | `employee` | Nhân viên | 17 |

Cách đọc mỗi persona:

- **Nhu cầu** = intent, đánh số `Pk.Nn`; mỗi nhu cầu ghi tool đích (tên trong `sgod_tools.json`), luôn là tool mà
  `tool_policy.json` mở cho vai trò của persona.
- **Hỏi nhưng không được** = câu `denied`: chỉ có ở persona `employee` và chỉ với 5 tool chỉ dành cho `company_admin` (§6).
  Persona `company_admin` không có câu `denied` trong v1.
- **Ngoài phạm vi** = câu `expected_tool: null`: yêu cầu ghi (tạo / sửa / xoá / duyệt), dữ liệu không có tool v1 và chủ đề
  ngoài quản lý tài sản (§6).
- **Ví dụ** (tối đa 2 mỗi persona) viết mới cho tài liệu này, chỉ để minh hoạ văn phong và nhãn; nhãn sau dấu → dành cho
  người viết prompt đối chiếu, câu sinh ra không bao giờ chứa tên tool hay tham số. Không dán nguyên văn ví dụ vào
  `datagen/prompts/` hay `datagen/prompts_eval/` làm few-shot: mỗi bộ prompt tự viết ví dụ riêng, để train và eval không
  xuất phát từ cùng một câu mẫu.

### 2.1 P1 `giam_doc` — Giám đốc doanh nghiệp (chủ tài khoản doanh nghiệp)

- **Vai trò:** `company_admin` · `role_vi`: Quản trị viên doanh nghiệp · tier Enterprise.
- **Bối cảnh:** chủ doanh nghiệp, giữ tài khoản tầng Enterprise của tenant. Không thao tác tài sản hằng ngày; mở chat vài
  lần mỗi tuần, thường trên điện thoại, để nắm số liệu tổng, xem việc gì đang chờ mình và tình trạng tài khoản nhân viên.
- **Nhu cầu thường gặp:**
  - P1.N1 Tổng quan tài sản toàn doanh nghiệp: tổng số, số tài sản quan trọng, số có mã QR, số phiên trạng thái đang mở →
    `get_asset_statistics`.
  - P1.N2 Việc đang chờ: số phiếu chuyển giao theo tab (đã gửi / chờ nhận / chờ xác thực), số yêu cầu nhân viên gửi đi /
    chờ duyệt → `get_transfer_summary`, `get_staff_request_summary`.
  - P1.N3 Tình trạng tài khoản nhân viên: đang hoạt động, bị khoá, chưa kích hoạt; xem N người → `list_enterprise_users`
    (`status`, `limit`).
  - P1.N4 Tin nhắn nội bộ: các cuộc trò chuyện của mình, số tin chưa đọc → `list_my_conversations`, `get_unread_counts`.
  - P1.N5 Hồ sơ doanh nghiệp đăng ký trên SGOD (tên doanh nghiệp, chủ tài khoản, email, số điện thoại) →
    `get_enterprise_profile`.
- **Văn phong:** xưng "tôi" hoặc "anh"; câu mệnh lệnh ngắn ("cho xem", "báo nhanh", "check giúp"), ít kính ngữ; gõ trên
  điện thoại nên hay thiếu dấu và viết tắt `cty`, `ts` (tài sản), `nv` (nhân viên), `bn` (bao nhiêu), `ko`; chen từ tiếng
  Anh `report`, `check`, `status`.
- **Hỏi nhưng không được (`denied`):** không có — `company_admin` được mở đủ 22 tool.
- **Ngoài phạm vi hay gặp (`null`):** yêu cầu ghi — duyệt hoặc từ chối phiếu chuyển giao, khoá tài khoản một nhân viên,
  nhắn tin cho cả nhóm; dữ liệu không có tool v1 — sơ đồ phòng ban, xuất báo cáo tài sản ra Excel; ngoài lĩnh vực — doanh
  thu quý, giá vàng, lịch họp, chào hỏi xã giao.
- **Ví dụ:**
  - "Cty mình tổng cộng bn ts, mấy cái là ts quan trọng?" → `get_asset_statistics` `{}` · `single`
  - "co nv nao dang bi khoa ko, list 10 nguoi thoi" → `list_enterprise_users` `{"status": "Blocked", "limit": 10}` ·
    `multi_constraint`

### 2.2 P2 `quan_ly_tai_san` — Chuyên viên quản lý tài sản (vận hành tài khoản doanh nghiệp)

- **Vai trò:** `company_admin` · `role_vi`: Quản trị viên doanh nghiệp · tier Enterprise.
- **Bối cảnh:** người được giao vận hành tài khoản doanh nghiệp trên SGOD (đăng nhập tầng Enterprise), dùng hệ thống hằng
  ngày trên máy tính: tra cứu tài sản, rà danh mục và vị trí kho, theo dõi phiếu chuyển giao và yêu cầu của nhân viên. Thuộc
  mã tài sản, hay dán nguyên mã hoặc id từ màn hình quản trị.
- **Nhu cầu thường gặp:**
  - P2.N1 Tìm tài sản theo tên, mã hoặc một đoạn tên, kèm số dòng; chi tiết và lịch sử thay đổi của một tài sản →
    `list_my_assets` (`search`, `limit`), `get_asset`, `get_asset_histories` (`asset_ref`).
  - P2.N2 Danh mục, vị trí / kho, chi tiết một vị trí khi có id → `list_categories`, `list_locations`, `get_location`
    (`location_id`).
  - P2.N3 Phiếu chuyển giao toàn doanh nghiệp, chi tiết một phiếu khi có id → `list_asset_transfers`,
    `get_asset_transfer` (`transfer_id`).
  - P2.N4 Yêu cầu của nhân viên và các lần bảo trì đã ghi nhận → `list_staff_requests`, `list_maintenance_records`.
  - P2.N5 Tài khoản nhân viên chưa kích hoạt hoặc bị khoá, khi có người báo không đăng nhập được →
    `list_enterprise_users` (`status`, `limit`).
- **Văn phong:** xưng "mình" hoặc "tôi", lịch sự trung tính ("giúp mình", "nhé"); câu rõ ràng, hay kèm số lượng ("5 cái",
  "20 dòng") và mã chính xác; dùng từ tiếng Anh `list`, `search`, `filter`, `ID`; ít lỗi chính tả nhưng hay viết tắt `ts`,
  `ds` (danh sách), `sl` (số lượng).
- **Hỏi nhưng không được (`denied`):** không có — `company_admin` được mở đủ 22 tool.
- **Ngoài phạm vi hay gặp (`null`):** yêu cầu ghi — thêm tài sản mới, đổi tên danh mục, tạo lịch bảo trì, nhập danh sách
  tài sản từ tệp Excel; dữ liệu không có tool v1 — xuất danh sách ra Excel; câu hỏi cách làm — quy trình đăng ký tài sản
  mới, cách in tem mã QR, cách tính khấu hao.
- **Ví dụ:**
  - "Tìm giúp mình 5 ts có chữ ZZTEST nhé" → `list_my_assets` `{"search": "ZZTEST", "limit": 5}` · `multi_constraint`
  - "check lịch sử thay đổi của tài sản 000000003" → `get_asset_histories` `{"asset_ref": "000000003"}` · `single`

### 2.3 P3 `nhan_vien_van_phong` — Nhân viên văn phòng

- **Vai trò:** `employee` · `role_vi`: Nhân viên · tier Enterprise User.
- **Bối cảnh:** nhân viên khối văn phòng được cấp laptop và thiết bị làm việc; mở chat khi cần biết mình đang giữ gì, một
  tài sản đang ở đâu, có phiếu bàn giao nào gửi cho mình. Ít rành hệ thống, hay hỏi vòng. Với token enterprise-user, "tài sản
  của tôi" là tài sản được giao hay toàn tenant **chưa kiểm được** (`x_sgod.notes` của `list_my_assets`): câu hỏi chỉ nói
  "của em / em đang giữ", không giả định phạm vi.
- **Nhu cầu thường gặp:**
  - P3.N1 Tài sản mình đang giữ / được giao, có thể kèm từ khoá → `list_my_assets`.
  - P3.N2 Chi tiết, tình trạng hoặc vị trí một tài sản cụ thể theo tên hoặc mã → `get_asset`.
  - P3.N3 Thông tin tài khoản và quyền của mình → `get_my_profile`, `get_my_permissions`.
  - P3.N4 Phiếu chuyển giao của mình, số phiếu đang chờ mình nhận → `list_asset_transfers` (`onlyMine: true`),
    `get_transfer_summary`.
- **Văn phong:** xưng "em", nhiều kính ngữ ("cho em hỏi", "ạ", "với ạ"); câu dài, đôi khi kể bối cảnh trước khi hỏi; lỗi
  gõ nhẹ và viết tắt `e`, `dc`, `ko`; thỉnh thoảng thiếu dấu.
- **Hỏi nhưng không được (`denied`):**
  - danh sách đồng nghiệp kèm email / số điện thoại → `list_enterprise_users`;
  - tin nhắn chưa đọc, các cuộc trò chuyện của mình → `get_unread_counts`, `list_my_conversations`.
- **Ngoài phạm vi hay gặp (`null`):** yêu cầu ghi — báo hỏng laptop, xin cấp thêm màn hình, đổi mật khẩu, cập nhật số điện
  thoại; ngoài lĩnh vực — đơn nghỉ phép, bảng lương, thời tiết, quán ăn trưa; chào hỏi, cảm ơn.
- **Ví dụ:**
  - "Cho em hỏi QA Test Laptop hiện đang để ở đâu ạ?" → `get_asset` `{"asset_ref": "QA Test Laptop"}` · `single`
  - "e xin sđt mấy anh chị cùng cty dc ko ạ" → `list_enterprise_users`, `denied` · `permission_denial`

### 2.4 P4 `ky_thuat_vien_bao_tri` — Kỹ thuật viên bảo trì

- **Vai trò:** `employee` · `role_vi`: Nhân viên · tier Enterprise User.
- **Bối cảnh:** phụ trách bảo trì thiết bị, làm ở hiện trường, tra cứu bằng điện thoại giữa hai ca. Quan tâm lịch nào đang
  hiệu lực, công việc của từng lịch, các lần bảo trì đã ghi nhận và các yêu cầu đổi trạng thái công việc bảo trì mình đã
  gửi (`typeRequest` `change-status-maintenance`, §3.5).
- **Nhu cầu thường gặp:**
  - P4.N1 Lịch bảo trì đang hiệu lực hoặc đã hoàn thành, kèm số lượng → `list_maintenance_schedules` (`status`, `limit`).
  - P4.N2 Chi tiết một lịch và các công việc của lịch đó, khi có id lịch → `get_maintenance_schedule` (`schedule_id`),
    `list_maintenance_tasks` (`maintenanceScheduleId`, `limit`). Fixture chưa có id lịch nào (§3.6).
  - P4.N3 Các lần bảo trì đã ghi nhận → `list_maintenance_records`.
  - P4.N4 Yêu cầu đổi trạng thái đã gửi, số yêu cầu gửi đi / chờ duyệt → `list_staff_requests`,
    `get_staff_request_summary`.
  - P4.N5 Lịch sử thay đổi của một tài sản trước khi xử lý → `get_asset_histories` (`asset_ref`).
- **Văn phong:** ngắn, gần như không xưng hô; hay bỏ dấu và viết tắt `bt` (bảo trì), `cv` (công việc), `ts`, `ko`, `dc`;
  dùng nguyên từ tiếng Anh của hệ thống `active`, `completed`, `on-hold`, `task`, `done`.
- **Hỏi nhưng không được (`denied`):**
  - thống kê tài sản toàn công ty → `get_asset_statistics`;
  - các cuộc trò chuyện của tổ bảo trì → `list_my_conversations`.
- **Ngoài phạm vi hay gặp (`null`):** yêu cầu ghi — đánh dấu công việc hoàn thành, chuyển công việc sang `on-hold`, tạo lịch
  bảo trì mới; câu hỏi cách làm và ngoài lĩnh vực — cách sửa máy in kẹt giấy, giá linh kiện, dự báo thời tiết.
- **Ví dụ:**
  - "lich bt dang active cho xem 10 cai" → `list_maintenance_schedules` `{"status": "active", "limit": 10}` ·
    `multi_constraint`
  - "Thống kê tổng ts toàn cty giúp với" → `get_asset_statistics`, `denied` · `permission_denial`

### 2.5 P5 `thu_kho` — Thủ kho

- **Vai trò:** `employee` · `role_vi`: Nhân viên · tier Enterprise User.
- **Bối cảnh:** quản lý kho và vị trí lưu trữ (doanh nghiệp thử có các vị trí dạng `ZZTEST-… Kho A`, `Kho B`,
  `Kho A - Tang 1 (sua)`, §3.2), đối chiếu tài sản theo mã khi kiểm kê, theo dõi phiếu chuyển giao. Hay gõ mã số và dán id
  từ màn hình.
- **Nhu cầu thường gặp:**
  - P5.N1 Danh sách vị trí / kho và số tài sản ở mỗi nơi; chi tiết một vị trí khi có id → `list_locations`,
    `get_location` (`location_id`).
  - P5.N2 Danh mục tài sản đang khai báo → `list_categories`.
  - P5.N3 Tra một tài sản theo mã khi kiểm kê, hoặc tìm theo đoạn tên → `get_asset`, `list_my_assets` (`search`).
  - P5.N4 Phiếu chuyển giao: danh sách, chi tiết một phiếu theo id, số phiếu theo tab → `list_asset_transfers`,
    `get_asset_transfer` (`transfer_id`), `get_transfer_summary`.
- **Văn phong:** xưng "tôi" hoặc "mình", giọng thực tế; câu ngắn, hay mở đầu bằng mã hoặc tên kho; viết tắt `sl` (số
  lượng), `vt` (vị trí), `ts`; thiếu dấu khi vội.
- **Hỏi nhưng không được (`denied`):**
  - tổng tài sản toàn doanh nghiệp → `get_asset_statistics`;
  - hồ sơ doanh nghiệp (tên, email đăng ký) → `get_enterprise_profile`.
- **Ngoài phạm vi hay gặp (`null`):** yêu cầu ghi — nhập kho, xuất kho, tạo phiếu chuyển giao, xác nhận đã nhận phiếu, thêm
  vị trí kho mới; dữ liệu không có tool v1 — xuất tồn kho ra Excel; câu hỏi cách làm — cách in mã QR.
- **Ví dụ:**
  - "Xem chi tiết vị trí 6ac9bec727541dacd0a77f80" → `get_location` `{"location_id": "6ac9bec727541dacd0a77f80"}` · `single`
  - "phiếu chuyển giao 6ac9c52451e750872e755fad gồm những gì" → `get_asset_transfer`
    `{"transfer_id": "6ac9c52451e750872e755fad"}` · `single`

### 2.6 P6 `kinh_doanh_chi_nhanh` — Nhân viên kinh doanh tại chi nhánh

- **Vai trò:** `employee` · `role_vi`: Nhân viên · tier Sub-Enterprise User.
- **Bối cảnh:** làm ở một đơn vị con / chi nhánh; tài khoản thuộc tầng Sub-Enterprise trong cùng tenant
  (`belong: "Subenterprise"`, §1). Dùng laptop và thiết bị công ty cấp; hỏi khi nhận bàn giao hoặc khi cần xác nhận mình
  đang giữ gì. Khác persona tầng Enterprise User ở cách nói ("bên chi nhánh mình", "bên công ty"); bộ tool giống hệt (17
  tool `employee`). Phạm vi dữ liệu mà token sub-enterprise thấy **chưa kiểm được**, nên câu hỏi không giả định phạm vi
  khác Enterprise User.
- **Nhu cầu thường gặp:**
  - P6.N1 Tài sản mình đang dùng, chi tiết một tài sản → `list_my_assets`, `get_asset`.
  - P6.N2 Phiếu chuyển giao gửi cho mình: số phiếu chờ nhận, danh sách phiếu của mình → `get_transfer_summary`,
    `list_asset_transfers` (`onlyMine: true`, `limit`).
  - P6.N3 Tài khoản, vai trò và quyền của mình trên hệ thống → `get_my_profile`, `get_my_permissions`.
- **Văn phong:** xưng "mình" hoặc "em", thân mật, hay dùng "bên mình", "chi nhánh mình"; câu kiểu nhắn tin: thiếu dấu,
  `ko`, `j` (gì), `ok`, `pls`, đôi khi kéo dài chữ cuối ("nhaaa").
- **Hỏi nhưng không được (`denied`):**
  - tin nhắn chưa đọc, danh sách cuộc trò chuyện → `get_unread_counts`, `list_my_conversations`;
  - danh sách nhân viên toàn công ty → `list_enterprise_users`.
- **Ngoài phạm vi hay gặp (`null`):** yêu cầu ghi — xin cấp tài sản mới, bấm nhận phiếu chuyển giao; ngoài lĩnh vực — doanh
  số tháng, thông tin khách hàng, giờ mở cửa chi nhánh, bóng đá, thời tiết.
- **Ví dụ:**
  - "Bên mình đang có bao nhiêu phiếu chuyển giao chờ nhận vậy" → `get_transfer_summary` `{}` · `single`
  - "minh co tin nhan nao chua doc ko" → `get_unread_counts`, `denied` · `permission_denial`

### 2.7 P7 `hanh_chinh_don_vi_con` — Nhân viên hành chính – tổng hợp của đơn vị con

- **Vai trò:** `employee` · `role_vi`: Nhân viên · tier Sub-Enterprise User.
- **Bối cảnh:** phụ trách giấy tờ và cơ sở vật chất ở một đơn vị con (tầng Sub-Enterprise); tổng hợp danh mục, vị trí, lịch
  bảo trì và yêu cầu của nhân viên để báo cáo định kỳ lên công ty. Không phải chủ tenant nên không xem được dữ liệu cấp
  doanh nghiệp, dù hay hỏi.
- **Nhu cầu thường gặp:**
  - P7.N1 Danh mục tài sản và vị trí đang khai báo → `list_categories`, `list_locations` (`limit`).
  - P7.N2 Lịch bảo trì đang hiệu lực / đã hoàn thành → `list_maintenance_schedules` (`status`, `limit`).
  - P7.N3 Yêu cầu của nhân viên: danh sách, số yêu cầu gửi đi / chờ duyệt → `list_staff_requests`,
    `get_staff_request_summary`.
  - P7.N4 Quyền của tài khoản mình (có được tạo, sửa tài sản không) → `get_my_permissions`.
- **Văn phong:** xưng "tôi", văn phong hành chính, lịch sự ("Vui lòng", "Cho tôi xin", "Trân trọng"); câu đầy đủ, có dấu;
  hay gộp hai ràng buộc vào một câu (trạng thái + số lượng); thỉnh thoảng gõ sai một chữ.
- **Hỏi nhưng không được (`denied`):**
  - hồ sơ doanh nghiệp → `get_enterprise_profile`;
  - danh sách nhân viên toàn doanh nghiệp, tài khoản bị khoá → `list_enterprise_users`;
  - số liệu tổng tài sản toàn doanh nghiệp → `get_asset_statistics`.
- **Ngoài phạm vi hay gặp (`null`):** yêu cầu ghi — tạo danh mục mới, đổi tên vị trí, huỷ một yêu cầu; dữ liệu không có tool
  v1 — sơ đồ phòng ban, xuất báo cáo Word / Excel; ngoài lĩnh vực — soạn công văn, thuế, luật lao động.
- **Ví dụ:**
  - "Vui lòng liệt kê 3 lịch bảo trì đã hoàn thành." → `list_maintenance_schedules`
    `{"status": "completed", "limit": 3}` · `multi_constraint`
  - "Cho tôi xin hồ sơ doanh nghiệp đang đăng ký trên hệ thống." → `get_enterprise_profile`, `denied` ·
    `permission_denial`

## 3. Thực thể dùng trong câu hỏi (chỉ từ `fixtures/sgod/`)

- Mọi giá trị dưới đây có trong tệp ghi ở dòng **Nguồn** (đường dẫn tính từ `fixtures/sgod/`). Đây là **toàn bộ** giá trị
  được phép trong `ENTITY_POOLS` của `datagen/config_sgod.py`. Giá trị mẫu đang có trong config chỉ là chỗ giữ chỗ và phần
  lớn không truy được về fixture (dải mã `000000001`…`000000059`, trạng thái `inactive`, `date_phrase`, đa số tên tài sản /
  vị trí / danh mục mẫu): thay bằng các bảng dưới.
- Doanh nghiệp thử là tenant của môi trường QA (`fixtures/sgod/README.md` §5): tên dạng `ZZTEST-…`, `QA Test …`, có chữ
  không dấu và hậu tố `(sua)`. Câu sinh ra dùng **nguyên văn** các giá trị này; không Việt hoá, không sửa chính tả, không
  suy ra giá trị "còn thiếu" theo mẫu (mã kế tiếp, thêm Kho A / Kho B cho mọi tiền tố).
- Giá trị chỉ có trong Swagger (2026-10-14) được phép dùng, luôn ghi **"khai báo trong Swagger, chưa thấy trong dữ liệu"**
  (nguồn: `fixtures/sgod/README.md` §4, `docs/sgod/openapi-*.json`).
- Cột **Tham số v1** cho biết giá trị vào được tham số nào; "chỉ ngữ cảnh" = chỉ làm câu tự nhiên hơn, không bao giờ thành
  tham số (§5.4).

### 3.1 Tài sản

Nguồn: `asset/GET_assets.json` (cả hai tài sản); `asset/GET_assets_id.json` (`ZZTEST-2610100426 x4`).

| Tên (`name`) | Mã (`assetCode`) | id | Khoá gợi ý | Tham số v1 |
|---|---|---|---|---|
| `QA Test Laptop` | `000000001` | `6aa2c177da46d70ee2f491c1` | `asset_name`, `asset_code`, `asset_id` | `asset_ref` của `get_asset`, `get_asset_histories`; `search` của `list_my_assets` |
| `ZZTEST-2610100426 x4` | `000000003` | `6ac9be9827541dacd0a77e9f` | `asset_name`, `asset_code`, `asset_id` | như trên |

- `asset_ref` nhận tên, mã hoặc id. `search` nhận tên, mã hoặc một đoạn nguyên văn của chúng (vd `QA Test`, `Laptop`,
  `ZZTEST`, `ZZTEST-2610100426`); `search` chỉ khớp `name` / `assetCode` (`x_sgod.notes` của `list_my_assets`).
- Doanh nghiệp thử chỉ có 2 tài sản này; không dùng mã hay tên tài sản nào khác. Các `assetId` khác xuất hiện trong phiếu
  chuyển giao và yêu cầu nhân viên (`asset/GET_asset_transfers.json`, `asset/GET_request_staff.json`) không có trong danh
  sách tài sản, nên không dùng làm `asset_ref`.
- Chỉ ngữ cảnh (trường chi tiết trả về, không phải tham số): `manufacturer` `Hoa Phat`, `origin` `VN` (chỉ
  `ZZTEST-2610100426 x4`); sự kiện lịch sử `register_asset` (`asset/GET_assets_id_histories.json`); thuộc tính ở §3.9.
  Không dùng hãng hay xuất xứ làm từ khoá `search`.

### 3.2 Vị trí / kho

Nguồn: `asset/GET_locations.json` (15 vị trí); `ZZTEST-2610100427 Kho B` có thêm bản chi tiết `asset/GET_locations_id.json`.

| Tên vị trí (`name`) | id | Ghi chú |
|---|---|---|
| `ZZTEST-2610100427 Kho A` | `6ac9bec627541dacd0a77f7e` | có vị trí con |
| `ZZTEST-2610100427 Kho A - Tang 1 (sua)` | `6ac9bec627541dacd0a77f7f` | con của `ZZTEST-2610100427 Kho A`; bí danh `tang mot` |
| `ZZTEST-2610100427 Kho B` | `6ac9bec727541dacd0a77f80` | |
| `ZZTEST-2610100426 Kho A` | `6ac9be9627541dacd0a77e89` | có vị trí con |
| `ZZTEST-2610100426 Kho A - Tang 1 (sua)` | `6ac9be9627541dacd0a77e8a` | con của `ZZTEST-2610100426 Kho A`; bí danh `tang mot` |
| `ZZTEST-2610100426 Kho B` | `6ac9be9627541dacd0a77e8b` | |
| `ZZTEST-2610100424 Kho A` | `6ac9be0d27541dacd0a77d69` | có vị trí con |
| `ZZTEST-2610100424 Kho A - Tang 1 (sua)` | `6ac9be0d27541dacd0a77d6a` | con của `ZZTEST-2610100424 Kho A`; bí danh `tang mot` |
| `ZZTEST-2610100424 Kho B` | `6ac9be0d27541dacd0a77d6b` | |
| `ZZTEST-2610100423 Kho A - Tang 1 (sua)` | `6ac9bde027541dacd0a77c9f` | bí danh `tang mot`; không có vị trí cha trong danh sách |
| `ZZTEST-2610100423 Kho B` | `6ac9bde027541dacd0a77ca0` | |
| `ZZTEST-2610100421 Kho A` | `6ac9bd3527541dacd0a77bad` | có vị trí con |
| `ZZTEST-2610100421 Kho A - Tang 1 (sua)` | `6ac9bd3527541dacd0a77bae` | con của `ZZTEST-2610100421 Kho A`; bí danh `tang mot` |
| `ZZTEST-2610100421 Kho B` | `6ac9bd3527541dacd0a77baf` | |
| `QA Test Location` | `6aa2c144da46d70ee2f491c0` | |

- Khoá gợi ý: `location_name` (chỉ ngữ cảnh: `list_locations` không có tham số tìm theo tên) và `location_id` (tham số
  `location_id` của `get_location`).
- Mọi vị trí có `totalAsset: 0`. Trường `detail` là địa chỉ đã che (`Địa chỉ mẫu NN`), không dùng. Chỉ dùng id trong bảng
  làm `location_id` (id `0000000000000000000000ff` trong `locations` của tài sản không phải một vị trí trong danh sách).

### 3.3 Danh mục

Nguồn: `asset/GET_categories.json`.

| Tên danh mục (`name`) | Ghi chú |
|---|---|
| `QA Test Category` | `totalAsset: 1` |
| `ZZTEST-2610100426 Ghe (sua)` | `totalAsset: 1`; chữ không dấu, giữ nguyên |

- Khoá gợi ý: `category_name`, **chỉ ngữ cảnh**: v1 không có tham số lọc theo danh mục (`categoryId` không có trong schema
  `list_my_assets`). Câu "danh mục X có mấy tài sản" → `list_categories` (phản hồi có `totalAsset`), không phải
  `list_my_assets` với `search` (vì `search` chỉ khớp tên / mã tài sản).

### 3.4 Phiếu chuyển giao

Nguồn: `asset/GET_asset_transfers.json` (5 phiếu), `asset/GET_asset_transfers_id.json` (phiếu đầu),
`asset/GET_asset_transfers_summary.json`.

| Trường | Thấy trong dữ liệu | Khai báo trong Swagger, chưa thấy trong dữ liệu | Tham số v1 |
|---|---|---|---|
| id phiếu | `6ac9c52451e750872e755fad`, `6ac9bece27541dacd0a78006`, `6ac9be9f27541dacd0a77f0d`, `6ac9be1627541dacd0a77df0`, `6ac9bd3e27541dacd0a77c2d` | — | `transfer_id` của `get_asset_transfer` (khoá gợi ý `transfer_id`) |
| `statusTransfer` | `accept` | `pending`, `deny`, `revoke`, `cancel` (query `status` của `GET /asset-transfers`) | chỉ ngữ cảnh |
| `typeTransfer` | `revoke-asset` | — | chỉ ngữ cảnh |
| `workflowPhase` | `completed` | — | chỉ ngữ cảnh |
| tab đếm (khoá của `data` trong `..._summary.json`) | `send`, `receive`, `verify` = phiếu đã gửi / chờ nhận / chờ xác thực | — | `get_transfer_summary` không tham số |

- `list_asset_transfers` v1 chỉ có `onlyMine` / `limit` / `cursor`: trạng thái hay loại phiếu nêu trong câu không thành tham
  số.

### 3.5 Yêu cầu của nhân viên

Nguồn: `asset/GET_request_staff.json`, `asset/GET_request_staff_summary.json`.

| Trường | Thấy trong dữ liệu | Khai báo trong Swagger, chưa thấy trong dữ liệu |
|---|---|---|
| `typeRequest` | `change-status-maintenance` | `change-status` (`CreateRequestStaffChangeStatusDto`) |
| `statusRequest` | `confirm`, `deny`, `cancel` | — |
| `statusChange` | `processing`, `completed`, `on-hold` | — |
| `statusOrigin` | `scheduled`, `processing` | — |
| `subjectKind` | `maintenance_task` | — |
| tab đếm (khoá của `data` trong `..._summary.json`) | `send`, `receive` = yêu cầu gửi đi / chờ duyệt tiếp nhận | — |
| bộ lọc `type` (query `GET /request-staff`) | — | `send`, `receive` |

- Tất cả **chỉ ngữ cảnh**: `list_staff_requests` v1 chỉ có `limit` / `cursor`; `get_staff_request_summary` không tham số.

### 3.6 Bảo trì

Nguồn: `asset/GET_maintenance_schedules.json`, `asset/GET_maintenance_records.json` (đều là danh sách rỗng);
`asset/GET_request_staff.json`.

| Trường | Thấy trong dữ liệu | Khai báo trong Swagger, chưa thấy trong dữ liệu | Tham số v1 |
|---|---|---|---|
| trạng thái lịch (`status`, query `GET /maintenance/schedules`) | — (danh sách lịch rỗng) | `draft`, `active`, `completed` | `status` của `list_maintenance_schedules`; schema chỉ nhận `active` (đang hiệu lực) và `completed` (đã hoàn thành) |
| trạng thái công việc bảo trì (`ChangeMaintenanceTaskStatusDto`) | `scheduled`, `processing`, `completed`, `on-hold` (qua `statusOrigin` / `statusChange`, §3.5) | `overdue` | chỉ ngữ cảnh |
| id lịch bảo trì | **không có** | — | `schedule_id`, `maintenanceScheduleId`: chưa có giá trị truy được |

- Doanh nghiệp thử chưa có lịch bảo trì nên `asset/GET_maintenance_schedules_id.json` và `asset/GET_maintenance_tasks.json`
  không được chụp (`fixtures/sgod/README.md` §3). Vì vậy `get_maintenance_schedule` và `list_maintenance_tasks` chưa có
  `PARAM_SAMPLER` (§5.2). Cần id thật thì bình luận vào task S Việc 2 để chụp lại trên hạ tầng tham chiếu.
- `subjectId` của yêu cầu nhân viên là id **công việc** bảo trì (`subjectKind: maintenance_task`), không phải id lịch: không
  dùng làm `schedule_id` hay `maintenanceScheduleId`.

### 3.7 Tài khoản nhân viên

Nguồn: `auth/GET_enterprise_users.json`; `belong: "Enterprise"` lấy từ `auth/GET_session_context.json`.

| Trường | Thấy trong dữ liệu | Khai báo trong Swagger, chưa thấy trong dữ liệu | Tham số v1 |
|---|---|---|---|
| `status` | `Active` | `Pending`, `Verified`, `Blocked` | `status` của `list_enterprise_users` (enum schema: `Pending` = chưa kích hoạt, `Verified`, `Active`, `Blocked` = bị khoá); khoá gợi ý `user_status` |
| `belong` | `EnterpriseUser`, `Subenterprise`, `Enterprise` | — | chỉ ngữ cảnh |

- Không có giá trị truy được cho `search` của `list_enterprise_users`: họ tên, email và `userName` trong fixture đều là PII
  đã che (§3.10). Không sinh câu tìm một người cụ thể theo tên hay email; dùng `status` và `limit`.

### 3.8 Hội thoại

Nguồn: `chat/GET_conversations.json`, `chat/GET_conversations_unread_counts.json`.

| Trường | Thấy trong dữ liệu | Khai báo trong Swagger, chưa thấy trong dữ liệu | Tham số v1 |
|---|---|---|---|
| `type` | `group`, `private` | `all` (query `type` của `GET /conversations`) | chỉ ngữ cảnh |
| tên nhóm (`title` của hội thoại `group`) | `QA Project Team` | — | chỉ ngữ cảnh |

- Tiêu đề hội thoại `private` ghép từ họ tên đã che: không dùng. `list_my_conversations` v1 chỉ có `limit` / `cursor`;
  `get_unread_counts` không tham số (doanh nghiệp thử: `totalUnread` 0).

### 3.9 Thuộc tính tài sản

Nguồn: `asset/GET_assets.json`, `asset/GET_assets_id.json`; trạng thái `active` còn có trong
`asset/GET_asset_statuses_by_asset_assetId.json`.

| Trường | Thấy trong dữ liệu | Khai báo trong Swagger, chưa thấy trong dữ liệu |
|---|---|---|
| `unit` (đơn vị) | `piece` | `can`, `box`, `bottle`, `pack`, `tree`, `pot`, `set`, `jar`, `kg`, `gram`, `m` |
| `importanceLevel` (mức quan trọng) | `normal` | `important`, `confidential` |
| `assetType` (loại) | `normal` | `expendable` |
| `status` (trạng thái tài sản / phiên trạng thái) | `active` | `repair`, `not_use`, `broken`, `sold`, `used_up` (`CreateAssetStatusDto`) |

- Tất cả **chỉ ngữ cảnh**: không tool v1 nào lọc theo đơn vị, mức quan trọng, loại hay trạng thái tài sản (`GET /assets`
  không có bộ lọc trạng thái, `x_sgod.notes` của `list_my_assets`). "Bao nhiêu tài sản quan trọng" ở cấp toàn doanh nghiệp →
  `get_asset_statistics` (trường `importantAssets`).

### 3.10 Không dùng làm thực thể

- PII đã che (`fixtures/sgod/README.md` §2): `TestNN Nguyễn`, `Người dùng NN`, `userNN`, `userNN@example.com`,
  `Doanh nghiệp Demo NN`, `Địa chỉ mẫu NN`, cùng số điện thoại / URL ảnh / IP đã che, và mọi chuỗi ghép từ chúng (tiêu đề
  hội thoại `private`, tên vai trò dạng `Enterprise … - <id>` trong `auth/GET_roles.json`).
- `enterpriseId`, `tenantId`, id người dùng (`createdBy`, `fromUserId`, `toUserId`, `requesterId`, `approverId`,
  `staffId`…) và ObjectId vai trò (`roles`, `primaryRoleId`): preamble quy tắc 2 cấm truyền mã doanh nghiệp / tenant,
  `roles.md` §4 cấm dựa vào ObjectId vai trò.
- Mã quyền trong `auth/GET_session_context.json` (`auth:ReadAsset`…) là quyền của tài khoản chủ doanh nghiệp, không phải
  của `employee`; câu hỏi về quyền viết bằng lời ("tôi có được tạo tài sản không").
- `cursor` (vd `meta.nextCursor` trong `asset/GET_request_staff.json`): câu một lượt không có con trỏ trang (§5.3).
- Nội dung ca âm trong `negative/` (route đã bỏ hoặc phản hồi lỗi).

## 4. Ma trận phủ persona × tool

✓ = nhu cầu được phép (§2) · `denied` = câu persona `employee` hỏi nhưng bị từ chối. Thứ tự tool theo `sgod_tools.json`;
cột "Vai trò được phép" chép từ `tool_policy.json`.

| Tool | Vai trò được phép | P1 | P2 | P3 | P4 | P5 | P6 | P7 |
|---|---|---|---|---|---|---|---|---|
| `list_my_assets` | employee, company_admin | | ✓ | ✓ | | ✓ | ✓ | |
| `get_asset` | employee, company_admin | | ✓ | ✓ | | ✓ | ✓ | |
| `list_maintenance_schedules` | employee, company_admin | | | | ✓ | | | ✓ |
| `get_my_profile` | employee, company_admin | | | ✓ | | | ✓ | |
| `get_my_permissions` | employee, company_admin | | | ✓ | | | ✓ | ✓ |
| `get_enterprise_profile` | company_admin | ✓ | | | | `denied` | | `denied` |
| `list_enterprise_users` | company_admin | ✓ | ✓ | `denied` | | | `denied` | `denied` |
| `list_my_conversations` | company_admin | ✓ | | `denied` | `denied` | | `denied` | |
| `get_unread_counts` | company_admin | ✓ | | `denied` | | | `denied` | |
| `get_asset_statistics` | company_admin | ✓ | | | `denied` | `denied` | | `denied` |
| `get_asset_histories` | employee, company_admin | | ✓ | | ✓ | | | |
| `get_maintenance_schedule` | employee, company_admin | | | | ✓ | | | |
| `list_maintenance_records` | employee, company_admin | | ✓ | | ✓ | | | |
| `list_maintenance_tasks` | employee, company_admin | | | | ✓ | | | |
| `list_asset_transfers` | employee, company_admin | | ✓ | ✓ | | ✓ | ✓ | |
| `get_asset_transfer` | employee, company_admin | | ✓ | | | ✓ | | |
| `get_transfer_summary` | employee, company_admin | ✓ | | ✓ | | ✓ | ✓ | |
| `list_staff_requests` | employee, company_admin | | ✓ | | ✓ | | | ✓ |
| `get_staff_request_summary` | employee, company_admin | ✓ | | | ✓ | | | ✓ |
| `list_categories` | employee, company_admin | | ✓ | | | ✓ | | ✓ |
| `list_locations` | employee, company_admin | | ✓ | | | ✓ | | ✓ |
| `get_location` | employee, company_admin | | ✓ | | | ✓ | | |

Kiểm tra trên bảng:

- 22/22 tool là nhu cầu ✓ của ít nhất 1 persona. Tool có đúng 1 persona cần: `get_enterprise_profile`,
  `list_my_conversations`, `get_unread_counts`, `get_asset_statistics` (P1) và `get_maintenance_schedule`,
  `list_maintenance_tasks` (P4; chưa có id truy được, §3.6).
- 5/5 tool chỉ dành cho `company_admin` là câu `denied` của ít nhất 2 persona `employee`: `get_enterprise_profile` (P5, P7),
  `list_enterprise_users` (P3, P6, P7), `list_my_conversations` (P3, P4, P6), `get_unread_counts` (P3, P6),
  `get_asset_statistics` (P4, P5, P7). Cả năm tool là nhu cầu ✓ của P1; `list_enterprise_users` còn là nhu cầu của P2.
- Mọi persona `employee` có ít nhất 2 câu `denied`; không ô ✓ nào trỏ tới tool ngoài quyền của vai trò persona.

## 5. Ghi chú cho D Việc 3

### 5.1 Độ phức tạp: `single` và `multi_constraint`

- Khớp `config_sgod.COMPLEXITY_MIX` (`single` 0,85 · `multi_constraint` 0,15). `multi_constraint` = **ít nhất 2 ràng buộc
  trong một câu**, mỗi ràng buộc là **một tham số có trong schema** của tool đích (vd từ khoá + số lượng, trạng thái + số
  lượng). Ràng buộc không có tham số tương ứng (§5.4) không được tính.
- Chỉ các tool sau có từ 2 tham số lấy mẫu được, nên chỉ chúng có bucket `multi_constraint`: `list_my_assets` (`search` +
  `limit`), `list_maintenance_schedules` (`status` + `limit`), `list_enterprise_users` (`status` + `limit`; với persona
  `employee` câu vẫn là `denied`), `list_asset_transfers` (`onlyMine` + `limit`). `list_maintenance_tasks`
  (`maintenanceScheduleId` + `limit`) chỉ khi fixture có id lịch. Các tool còn lại chỉ có `single`.
- Không có `dependent` hay chuỗi nhiều bước: pha 2 chỉ một lượt (`docs/contracts/eval_metric.md` §4).

### 5.2 Tham số lấy mẫu theo tool (`PARAM_SAMPLER`)

Một mục cho mỗi tool trong `sgod_tools.json`; tên tham số đúng schema; giá trị lấy từ §3 hoặc từ ràng buộc của schema / API.
`limit` là số nguyên ≥ 1 (schema), tối đa theo API là 100 cho `GET /assets`, `GET /enterprise-users`, `GET /conversations`
và 500 cho các danh sách còn lại (`docs/sgod/query_params.md`); nên dùng số nhỏ người dùng hay nói (3, 5, 10, 20). Không bao
giờ lấy mẫu `cursor`.

| Tool | Tham số lấy mẫu → nguồn giá trị | Sampler |
|---|---|---|
| `list_my_assets` | `search` → §3.1 (tên, mã, đoạn nguyên văn); `limit` | có |
| `get_asset`, `get_asset_histories` | `asset_ref` → §3.1 (tên, mã hoặc id) | có |
| `list_maintenance_schedules` | `status` → `active` / `completed` (§3.6); `limit` | có |
| `list_enterprise_users` | `status` → §3.7; `limit`; `search`: không có giá trị truy được | có |
| `list_asset_transfers` | `onlyMine` → `true` khi câu nói "của tôi / của mình"; `limit` | có |
| `get_asset_transfer` | `transfer_id` → 5 id ở §3.4 | có |
| `get_location` | `location_id` → 15 id ở §3.2 | có |
| `list_my_conversations`, `list_maintenance_records`, `list_staff_requests`, `list_categories`, `list_locations` | `limit` | có |
| `get_my_profile`, `get_my_permissions`, `get_enterprise_profile`, `get_unread_counts`, `get_asset_statistics`, `get_transfer_summary`, `get_staff_request_summary` | không tham số → `{}` | có (rỗng) |
| `get_maintenance_schedule` | `schedule_id` (bắt buộc): không có id truy được (§3.6) | **chưa**: để ngoài `BUCKET_PLAN` |
| `list_maintenance_tasks` | `maintenanceScheduleId` (bắt buộc): không có id truy được (§3.6) | **chưa**: để ngoài `BUCKET_PLAN` |

### 5.3 Một lượt, một lần gọi tool

- Không đa lượt: không "trang sau", "cái đó", "như lúc nãy", không câu cần lịch sử hội thoại hay kết quả tool trước.
- Không "làm A rồi B" và không gộp hai yêu cầu vào một câu (vd vừa hỏi lịch bảo trì vừa hỏi tin nhắn chưa đọc).
- Câu nêu **tên hoặc mã tài sản** vẫn là **một** lần gọi: executor tự tra tên → id qua `x_sgod.resolve`
  (`GET /sgod-asset/v1/assets?search=`) cho `asset_ref` của `get_asset` và `get_asset_histories`.
- Tool cần id mà không có `resolve` (`get_location`, `get_asset_transfer`, `get_maintenance_schedule`,
  `list_maintenance_tasks`): chỉ sinh câu **chứa sẵn id** (§3). Không sinh câu phải tra trước rồi mới gọi được (chi tiết một
  kho nêu bằng tên, công việc bảo trì của một tài sản, chi tiết phiếu chuyển giao của một tài sản): các câu này cần hai lần
  gọi tool.
- Câu chứa id chỉ nên là phần nhỏ của bucket: người dùng thật ít khi gõ ObjectId; diễn đạt như dán id từ màn hình.

### 5.4 Thời gian và ràng buộc ngoài schema

- Tool v1 **không có tham số ngày**. Mốc thời gian ("tuần này", "tháng trước", "gần nhất") có thể xuất hiện tự nhiên nhưng
  không bao giờ thành tham số và không tính là ràng buộc của `multi_constraint`. Khoá `date_phrase` đang có trong
  `ENTITY_POOLS` và `PARAM_SAMPLER["list_maintenance_schedules"]` không truy được về fixture và dễ sinh tham số bịa: bỏ khi
  điền config.
- Bộ lọc không có trong schema v1 cũng vậy: trạng thái / danh mục / vị trí / mức quan trọng của tài sản (`list_my_assets`),
  trạng thái / loại phiếu chuyển giao, trạng thái / loại yêu cầu nhân viên, loại hội thoại. `label_scenarios.py` bỏ khoá
  ngoài schema (`fix_params_for_tool`, có ghi log), nên câu dựa trên các bộ lọc này mất ràng buộc và lệch bucket.
- Lỗi chính tả, viết tắt, thiếu dấu chỉ áp vào phần lời. Giá trị tự do thành tham số (tên, mã, id) giữ đúng chuỗi ở §3 để
  nhãn chép nguyên văn được (preamble quy tắc 4); trạng thái có thể nói bằng lời ("đang hiệu lực", "bị khoá") và được gán về
  giá trị enum (§6).
- Không nêu tên tool hay tên tham số kỹ thuật trong câu; không tên người, email, số điện thoại; không mã doanh nghiệp /
  tenant (preamble quy tắc 2).

### 5.5 Chống rò rỉ

- Không chép hay diễn đạt lại hàng nào của lõi eval hay của bất kỳ tập dữ liệu nào trong repo (`data/`) vào prompt.
  `data/sgod/eval_human_core.jsonl` là tập kiểm tra đóng băng: phía sinh không mở tệp này, và D Việc 3 không mở
  `datagen/prompts_eval/`. Ví dụ trong prompt tự viết mới.
- Kiểm bằng máy: `generate_scenarios.py` loại câu có SequenceMatcher ≥ 0,65 so với `EVAL_SETS_FOR_LEAKAGE`
  (`data/sgod/eval_v1.json`, gồm cả lõi người viết) khi tệp đã có. Trước Điểm đồng bộ 2 tệp chưa tồn tại, nên pilot chỉ được
  bảo vệ bằng kỷ luật prompt.

### 5.6 `BUCKET_PLAN` = persona × intent × complexity

- **Persona:** 7 khoá ở §2.0; vai trò của bucket theo cột `role` (`BUCKET_PLAN` dùng nhãn `employee` / `admin`, `ROLE_MAP`
  đổi `admin` → `company_admin`). Prompt sinh nêu rõ persona (nhãn, bối cảnh, văn phong ở §2), vai trò (`role` + `role_vi`)
  và danh sách tool mở cho vai trò đó (17 hoặc 22, §1).
- **Intent:** các nhu cầu `Pk.Nn` ở §2 (tool đích); thêm bucket `permission_denial` cho mỗi persona `employee` × tool `denied`
  của persona đó, và bucket `out_of_scope` (yêu cầu ghi, dữ liệu không có tool, ngoài lĩnh vực) cho mọi persona.
- **Complexity:** `single` / `multi_constraint` theo §5.1, chỉ với tool có từ 2 tham số lấy mẫu được.
- Tool chưa có sampler (`get_maintenance_schedule`, `list_maintenance_tasks`) để ngoài `BUCKET_PLAN` /
  `TRACKB_BUCKET_PLAN` cho đến khi có fixture chứa id lịch. Hệ quả cho D Việc 4: phần GPT bổ sung cũng không sinh được câu
  cho hai tool này từ giá trị truy được, nên mức ≥ 15 bản ghi / tool của eval_v1 (`eval_metric.md` §1) cần id lịch thật.

## 6. Quy tắc gán nhãn (hợp đồng 3 §6)

Áp cho nhãn của D Việc 3 (`label_system.md`, labeler) và cho bản ghi eval sinh bằng GPT ở D Việc 4. Quyền gán **bằng
luật** từ `tool_policy.json`, không bằng LLM (`eval_metric.md` §1).

| Tình huống | `expected_tool` | `expected_permission` | `category` |
|---|---|---|---|
| Câu ứng với một tool mà vai trò được phép | tên tool | `allowed` | `single_tool` hoặc `multi_constraint` |
| Câu ứng với một tool **có trong** `sgod_tools.json` nhưng `tool_policy.json[tool].roles` không chứa `user_role`; ở v1 chỉ xảy ra khi `employee` hỏi 1 trong 5 tool chỉ dành cho `company_admin` | **giữ tên tool đó** | `denied` | `permission_denial` |
| Yêu cầu ghi (tạo / sửa / xoá / duyệt / từ chối / nhận phiếu / khoá tài khoản / gửi tin nhắn / đánh dấu đã đọc / đổi mật khẩu …): v1 không có tool ghi | `null` | `allowed` | `out_of_scope` |
| Không tool nào phù hợp: ngoài lĩnh vực, chào hỏi, hỏi cách làm, câu mơ hồ, dữ liệu không có tool v1 (sơ đồ phòng ban, xuất Excel …) | `null` | `allowed` | `out_of_scope` |

- `denied` ⇔ tool đích có trong `sgod_tools.json` và `tool_policy.json[tool].roles` không chứa `user_role` (`roles.md` §6).
  `company_admin` không bao giờ có câu `denied` trong v1 (được mở đủ 22 tool).
- Bản ghi eval `denied` **giữ tên tool bị chặn** trong `expected_tool` (như lõi eval, CHANGELOG `[D-V2]`). Thang chấm bước 1
  chỉ xét không có call nào trỏ tới tool ngoài quyền; thang chấm không xét câu chữ từ chối (`eval_metric.md` §4). Pipeline
  huấn luyện hiện tại (`label_scenarios.py`, stage A của `verify_trainset.py`) lưu hàng `denied` với `expected_tool: null`;
  hàng parity sinh ra vẫn là `REFUSAL_VI` nên nội dung hàng huấn luyện không đổi. Quy tắc giữ tên tool áp cho bản ghi eval.
- Yêu cầu ghi **không bao giờ** là `denied`, kể cả khi người hỏi là `employee` và đối tượng là dữ liệu chỉ dành cho
  `company_admin` (vd khoá tài khoản một nhân viên): không có tool nào để chặn, nên nhãn là `null` / `allowed` /
  `out_of_scope`. Preamble quy tắc 5 vẫn buộc trợ lý từ chối và không gọi tool.
- Dữ liệu cấp doanh nghiệp mà v1 không có tool (vd sơ đồ phòng ban) cũng là `null`, không phải `denied`, kể cả với
  `employee`.
- `category` theo một luật như lõi eval (CHANGELOG `[D-V2]`): `null` → `out_of_scope`; `denied` → `permission_denial`;
  ≥ 2 khoá trong `expected_params` → `multi_constraint`; còn lại `single_tool`. Không dùng `dependent`.
- `expected_params`: chỉ khoá có trong schema của tool đích, giá trị lấy từ câu, không bịa (preamble quy tắc 4):
  `asset_ref` = nguyên văn tên / mã / id người dùng nêu; `search` = từ khoá người dùng nêu; `limit` chỉ khi câu nêu số
  lượng; `onlyMine: true` khi câu nói rõ phiếu chuyển giao "của tôi / của mình". Trạng thái nói bằng lời gán về enum: lịch
  bảo trì "đang hiệu lực / sắp / cần bảo trì" → `active`, "đã xong / đã hoàn thành" → `completed`; tài khoản "chưa kích hoạt"
  → `Pending`, "bị khoá" → `Blocked`, "đang hoạt động" → `Active`, "đã xác minh" → `Verified`.
- Cặp tool dễ nhầm (cho danh sách cặp mơ hồ của `reviewer_system.md`; ghi `expected_tool_alternates` khi hai tool cùng hợp
  lý, alternates do arbiter ≠ GPT bị chấm quyết định):
  - `list_my_assets` (liệt kê / tìm theo từ khoá) ↔ `get_asset` (một tài sản cụ thể nêu tên hoặc mã);
  - `list_my_assets` ("tôi có bao nhiêu tài sản") ↔ `get_asset_statistics` (số liệu toàn doanh nghiệp; với `employee` là
    `denied`), nên câu sinh ra phải nói rõ phạm vi;
  - `list_asset_transfers` ↔ `get_transfer_summary` ("bao nhiêu phiếu" → tổng hợp theo tab; "những phiếu nào" → danh sách);
  - `list_staff_requests` ↔ `get_staff_request_summary` (như trên);
  - `get_my_profile` ↔ `get_my_permissions` (mô tả của cả hai nhắc "vai trò"; "quyền" → `get_my_permissions`, "hồ sơ /
    thông tin tài khoản" → `get_my_profile`);
  - `list_my_conversations` ↔ `get_unread_counts` ("tin chưa đọc" → `get_unread_counts`).

## 7. Điều kiện chốt

- [x] 7 persona (2 `company_admin`, 3 Enterprise User, 2 Sub-Enterprise User), mỗi persona đủ mục; `role` / `role_vi` chép
  từ `tools/sgod/roles.json`.
- [x] 22/22 tool là nhu cầu của ít nhất 1 persona; 5/5 tool chỉ dành cho `company_admin` có câu `denied` từ persona
  `employee` (§4).
- [x] Thực thể chỉ lấy từ `fixtures/sgod/`, mỗi danh sách ghi tệp nguồn, khớp bảng enum `fixtures/sgod/README.md` §4 (§3).
- [x] Dòng trạng thái đổi thành "chốt 2026-10-21" và ghi `CHANGELOG.md` (S Việc 3).
