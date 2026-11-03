Quản trị và tra cứu danh sách tài khoản nhân viên trong doanh nghiệp (`list_enterprise_users`): xem danh sách nhân sự, lọc theo trạng thái tài khoản (`status`: `Pending`, `Verified`, `Active`, `Blocked`), kèm theo giới hạn số lượng hiển thị (`limit`).

Lưu ý cốt lõi về phân quyền bảo mật:
- Công cụ này CHỈ DÀNH CHO Quản trị viên doanh nghiệp (`company_admin`: P1, P2).
- Khi vai trò là Nhân viên (`employee`: P3, P4, P5) cố tình yêu cầu xem danh sách nhân sự, tra cứu số điện thoại hay email của đồng nghiệp, câu hỏi này phục vụ sinh kịch bản Từ chối thẩm quyền (Refusal rows: `expected_permission: "denied"`).

Hướng dẫn văn phong:
- Với Quản trị viên (P1, P2): Câu mệnh lệnh ngắn gọn, rà soát nhân sự ("xem nhân viên đang bị khóa", "danh sách tài khoản mới kích hoạt", "lấy 10 người đang active"), gõ nhanh, viết tắt (`nv`, `cty`, `acc`), có 15-20% câu không dấu.
- Với Nhân viên (P3, P4, P5): Văn phong thắc mắc, tò mò xin thông tin nội bộ ("xin sđt mấy anh chị cùng cty", "xem danh sách nhân viên phòng khác"), xưng hô em/mình lịch sự.
- Tuyệt đối không sao chép hoặc paraphrase từ tập đánh giá `eval_human_core.jsonl`.

Trả về mảng JSON các chuỗi câu hỏi tiếng Việt.
