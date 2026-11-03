Tra cứu thông tin hồ sơ của tài khoản người dùng hiện tại đang đăng nhập (`get_my_profile`): xem họ tên, email, số điện thoại, chức vụ, phòng ban hoặc mã số nhân viên trên hệ thống SGOD.

Lưu ý: Công cụ này không nhận tham số (`{}`), lấy trực tiếp ngữ cảnh từ phiên làm việc.

Hướng dẫn văn phong:
- Thể hiện nhân viên văn phòng (P3), kỹ thuật viên (P4), thủ kho (P5) hoặc quản lý muốn kiểm tra lại thông tin cá nhân của mình ("tôi là ai", "hồ sơ tài khoản của tôi", "xem lại email và số điện thoại đăng ký").
- Đơn lượt (single-turn), 1 tool call, tự nhiên, xưng hô thân mật (em/tôi/mình), đan xen từ viết tắt (`tt`, `nv`, `sđt`, `p.`), có 15-20% câu không dấu.
- Tuyệt đối không sao chép hoặc paraphrase từ tập đánh giá `eval_human_core.jsonl`.

Trả về mảng JSON các chuỗi câu hỏi tiếng Việt.
