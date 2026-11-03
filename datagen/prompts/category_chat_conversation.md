# Category: chat_conversation

Sinh câu hỏi tiếng Việt về việc tra cứu danh sách cuộc hội thoại và số lượng tin nhắn chưa đọc trong hệ thống SGOD.

## Tool Selection

- `list_my_conversations`: Tra cứu danh sách cuộc hội thoại của tài khoản hiện tại. Chỉ sử dụng `limit` và `cursor` nếu phù hợp với câu hỏi.
- `get_unread_counts`: Tra cứu số lượng tin nhắn chưa đọc. Tool không có tham số, sử dụng `{}`.

## Persona & Style

- P1 `giam_doc`: Quản trị viên doanh nghiệp, cần kiểm tra hội thoại và số tin nhắn chưa đọc.
- P2 `quan_ly_tai_san`: Quản trị viên doanh nghiệp, cần theo dõi hội thoại trong công việc.
- P6 `kinh_doanh_chi_nhanh`: Nhân viên chi nhánh, dùng để tạo tình huống bị từ chối quyền truy cập.
- P7 `hanh_chinh_don_vi_con`: Nhân viên đơn vị con, dùng để tạo tình huống bị từ chối quyền truy cập.
- Sử dụng ngôn ngữ tự nhiên, kết hợp cách hỏi lịch sự, ngắn gọn, viết tắt công sở và một phần câu không dấu.
- Không tiết lộ tên tool hoặc tên tham số kỹ thuật trong câu hỏi.

## Permission Rules

- Hai tools chỉ dành cho vai trò `company_admin`.
- P1 và P2 được phép gọi cả hai tools.
- P6 và P7 thuộc vai trò `employee`, không được phép gọi hai tools này.
- Với câu hỏi của `employee` nhắm đến tool chat bị chặn:
  - `expected_tool`: giữ tên tool đích.
  - `expected_permission`: `"denied"`.
  - `category`: `"permission_denial"`.
- Trường hợp bị từ chối không được thực hiện tool call.
- Không nhầm tình huống thiếu quyền với yêu cầu ghi hoặc câu hỏi ngoài phạm vi.

## Generation Rules

- Mỗi câu hỏi chỉ có một ý định và tối đa một tool call.
- Chỉ sử dụng độ phức tạp `single` cho hai tools này.
- `list_my_conversations` chỉ sử dụng `limit` và `cursor`.
- `limit` phải là số nguyên từ 1 trở lên.
- `cursor` chỉ được sử dụng khi có giá trị hợp lệ từ kết quả phân trang trước.
- `get_unread_counts` không nhận bất kỳ tham số nào.
- Không tự tạo các tham số `status`, `conversation_id`, `type`, `user_id` hoặc bộ lọc khác ngoài schema.
- Không tạo câu hỏi đòi lọc hội thoại theo người tham gia hoặc loại hội thoại.
- Không tự tạo tên người, nội dung hội thoại hoặc dữ liệu cá nhân.
- Không sinh yêu cầu gửi tin nhắn, xóa hội thoại hoặc đánh dấu đã đọc; các yêu cầu ghi thuộc `permission_denial`.
- Không sinh kịch bản multi-turn hoặc dependent.
- Không sao chép hoặc paraphrase câu hỏi trong `data/sgod/eval_human_core.jsonl`.

## Output Requirements

- Phân biệt rõ yêu cầu xem danh sách hội thoại và yêu cầu đếm tin chưa đọc.
- Câu hỏi phải phù hợp persona và quyền truy cập của người dùng.
- Sử dụng tiếng Việt tự nhiên trong ngữ cảnh SGOD.
- Không chứa tên API, endpoint hoặc tham số kỹ thuật trong câu hỏi.
- Chỉ trả về mảng JSON gồm các chuỗi câu hỏi tiếng Việt, không giải thích.
