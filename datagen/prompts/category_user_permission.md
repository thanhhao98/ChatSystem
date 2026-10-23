Tra cứu vai trò, thẩm quyền và ngữ cảnh phiên làm việc của tài khoản hiện tại (`get_my_permissions`): kiểm tra xem tài khoản đang có quyền hạn gì, vai trò ra sao, có được phép duyệt phiếu hoặc thực hiện các thao tác quản trị trên hệ thống hay không.

Lưu ý: Công cụ này không nhận tham số (`{}`), trả về danh sách quyền của tài khoản trong phiên đăng nhập.

Hướng dẫn văn phong:
- Thể hiện nhân viên văn phòng (P3), kỹ thuật viên (P4), thủ kho (P5) hoặc hành chính (P7) thắc mắc về phân quyền chức năng ("tài khoản em có quyền gì", "anh có quyền duyệt phiếu không", "check quyền thao tác trên SGOD").
- Đơn lượt (single-turn), 1 tool call, tự nhiên, văn phong thắc mắc, viết tắt (`ql`, `nv`, `tb`), có 15-20% câu không dấu.
- Tuyệt đối không sao chép hoặc paraphrase từ tập đánh giá `eval_human_core.jsonl`.

Trả về mảng JSON các chuỗi câu hỏi tiếng Việt.
