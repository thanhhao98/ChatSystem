# `category_user_profile.md` — Prompt Đánh Giá Hồ Sơ Cá Nhân Người Dùng

## Tool Mục Tiêu
- **Tool**: `get_my_profile`
- **Quyền hạn**: `employee`, `company_admin`
- **Tham số hợp lệ**: Không có tham số (`{}`). Hệ thống tự động xác thực danh tính dựa trên JWT của phiên đăng nhập.
- **Lưu ý chống hallucination**: Tuyệt đối KHÔNG trích xuất hoặc tự bịa các tham số như `user_id`, `email`, `username`.

## Bối Cảnh Người Dùng (Personas)
- **P3 (`nhan_vien_van_phong`)**: Nhân viên mở chat hỏi thông tin cá nhân, kiểm tra họ tên, email, số điện thoại hay phòng ban đang ghi nhận trên hệ thống. Văn phong xưng "em", kính ngữ "ạ", "với ạ".
- **P4 (`ky_thuat_vien_bao_tri`)**: Kỹ thuật viên kiểm tra nhanh tài khoản đăng nhập trên app điện thoại. Văn phong ngắn, tiện đâu hỏi đó.
- **P5 (`thu_kho`)**: Thủ kho kiểm tra thông tin định danh của tài khoản đang thao tác kiểm kê.

## Hướng Dẫn Sinh Câu Truy Vấn & Nhãn Chuẩn Hóa
- **100% Single-Turn**: Mỗi truy vấn kích hoạt đúng 1 tool call `get_my_profile`.
- **Từ viết tắt & Không dấu**: Sử dụng các từ viết tắt (`nv`, `tt`, `sđt`, `e`, `mk`), 15% - 20% câu không dấu.
- **Quy tắc phân loại Category tất định**:
  - `single_tool`: Tất cả truy vấn hỏi hồ sơ cá nhân đều thuộc `single_tool` với `expected_params: {}`.
  - TUYỆT ĐỐI KHÔNG dùng category `dependent`.

### Mẫu Câu Hỏi Tham Khảo (Category: `single_tool`)
- "Cho em xem thông tin hồ sơ tài khoản cá nhân của em với ạ" -> `{}`
- "thong tin tai khoan cua toi" -> `{}`
- "Tôi đang đăng nhập với thông tin họ tên, email gì trên hệ thống vậy?" -> `{}`
- "xem ho so ca nhan cua em" -> `{}`
- "Tài khoản của tôi hiện đang lưu số điện thoại nào thế?" -> `{}`
- "cho em hoi thong tin user cua em a" -> `{}`
- "Tôi muốn xem lại thông tin cá nhân và chức danh của mình trên hệ thống" -> `{}`
- "kiem tra thong tin profile cua toi" -> `{}`
- "Hồ sơ của em đang để email liên hệ là gì ạ?" -> `{}`
- "xem thong tin acc cua toi" -> `{}`
