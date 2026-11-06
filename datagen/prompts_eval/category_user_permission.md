# `category_user_permission.md` — Prompt Đánh Giá Quyền Hạn Người Dùng

## Tool Mục Tiêu
- **Tool**: `get_my_permissions`
- **Quyền hạn**: `employee`, `company_admin`
- **Tham số hợp lệ**: Không có tham số (`{}`). Hệ thống tự động trích xuất ngữ cảnh phiên làm việc và danh sách quyền từ JWT của tài khoản.
- **Lưu ý chống hallucination**: Tuyệt đối KHÔNG trích xuất hoặc tự bịa các tham số như `role`, `permission_id`, `scope`.

## Bối Cảnh Người Dùng (Personas)
- **P3 (`nhan_vien_van_phong`)**: Nhân viên muốn biết mình có quyền gì, có được duyệt phiếu hay gửi yêu cầu cấp phát không. Văn phong lễ phép, xưng "em".
- **P4 (`ky_thuat_vien_bao_tri`)**: Kỹ thuật viên kiểm tra quyền xem lịch, quyền cập nhật trạng thái bảo trì thiết bị.
- **P5 (`thu_kho`)**: Thủ kho kiểm tra quyền hạn thao tác kho, quyền duyệt hoặc tạo phiếu chuyển giao tài sản.

## Hướng Dẫn Sinh Câu Truy Vấn & Nhãn Chuẩn Hóa
- **100% Single-Turn**: Mỗi truy vấn kích hoạt đúng 1 tool call `get_my_permissions`.
- **Từ viết tắt & Không dấu**: Sử dụng tự nhiên các từ viết tắt (`nv`, `ql`, `quyen`, `e`, `duyet`), 15% - 20% câu không dấu.
- **Quy tắc phân loại Category tất định**:
  - `single_tool`: Tất cả truy vấn hỏi quyền hạn người dùng đều thuộc `single_tool` với `expected_params: {}`.
  - TUYỆT ĐỐI KHÔNG dùng category `dependent`.

### Mẫu Câu Hỏi Tham Khảo (Category: `single_tool`)
- "Tài khoản của tôi hiện tại có những quyền hạn gì trên hệ thống?" -> `{}`
- "tai khoan cua em co nhung quyen gi the a" -> `{}`
- "Cho em kiểm tra xem vai trò và danh sách quyền của em gồm những gì với ạ" -> `{}`
- "xem quyen han cua toi tren he thong" -> `{}`
- "Tôi có quyền duyệt các phiếu chuyển giao hay yêu cầu tài sản không?" -> `{}`
- "vai tro va quyen truy cap cua tai khoan nay la gi" -> `{}`
- "Kiểm tra giúp mình danh sách quyền hạn được cấp cho tài khoản này" -> `{}`
- "em co quyen thao tac gi tren phan mem vay a" -> `{}`
- "Cho xem quyền truy cập và phân quyền của tài khoản hiện tại" -> `{}`
- "kiem tra quyen han he thong cua toi" -> `{}`
