# category_chat_conversation.md — Đánh giá truy vấn hội thoại SGOD

## 1. Mục tiêu

Sinh câu hỏi tiếng Việt tự nhiên nhằm đánh giá khả năng lựa chọn chính xác công cụ tra cứu hội thoại và số lượng chưa đọc trong SGOD.

Mỗi câu hỏi phải độc lập (single-turn), thể hiện một ý định truy vấn rõ ràng và chỉ yêu cầu tối đa một tool call.

## 2. Công cụ mục tiêu

### list_my_conversations

Mục đích:
Tra cứu danh sách cuộc hội thoại của tài khoản có quyền sử dụng dịch vụ Chat.

Roles được phép:

- company_admin

Tham số hợp lệ:

- limit: integer, tùy chọn.
- cursor: string, tùy chọn.

Quy tắc:

- Chọn công cụ khi người dùng muốn xem danh sách hội thoại.
- Chỉ dùng limit khi câu hỏi yêu cầu số lượng cụ thể.
- Không tự tạo cursor hoặc giả định đã có kết quả phân trang trước đó.
- Không tự thêm conversation_id, user_id, search, status hoặc bộ lọc thời gian.
- Không giả định thứ tự trả về nếu API chưa xác nhận.
- Không sử dụng công cụ này để xem nội dung chi tiết một tin nhắn.

### get_unread_counts

Mục đích:
Tra cứu thông tin số lượng chưa đọc từ dịch vụ hội thoại.

Roles được phép:

- company_admin

Tham số:

- Không có.

Quy tắc:

- Chọn công cụ khi người dùng muốn kiểm tra số lượng chưa đọc.
- expected_params phải là {}.
- Không tự thêm conversation_id hoặc các bộ lọc không tồn tại.
- Không suy đoán cấu trúc chi tiết dữ liệu trả về.

## 3. Phân quyền

Đối với company_admin:

- Các yêu cầu đọc hợp lệ có thể được gán expected_permission: allowed.

Đối với employee:

- Nếu yêu cầu ánh xạ đến một trong hai tool trên, gán expected_permission: denied.
- Giữ nguyên tên công cụ bị chặn trong expected_tool.
- Chuyển trường hợp này sang category permission_denial.

Không gán expected_tool: null chỉ vì employee thiếu quyền.

## 4. Hướng dẫn sinh câu hỏi

- 100% single-turn.
- Khoảng 15–20% câu tiếng Việt không dấu.
- Văn phong tự nhiên, giống người dùng trong môi trường công sở.
- Đa dạng độ dài, từ ngữ và cách diễn đạt.
- Phân biệt rõ ý định xem danh sách hội thoại và kiểm tra số lượng chưa đọc.
- Không dùng thuật ngữ backend hoặc tên tham số API trong lời người dùng.
- Không sao chép câu hỏi từ dataset có sẵn.
- Không đưa thông tin nhạy cảm hoặc định danh người dùng thật vào dữ liệu.

## 5. Quy tắc nhãn

### single_tool

- expected_permission: allowed.
- expected_tool tương ứng với ý định truy vấn.
- expected_params chứa 0 hoặc 1 tham số hợp lệ.

### multi_constraint

- Chỉ áp dụng khi câu hỏi có ít nhất 2 tham số hợp lệ được xác định rõ.
- Không cố tạo truy vấn nhiều ràng buộc bằng cursor không có căn cứ.

### permission_denial

- Áp dụng khi employee yêu cầu sử dụng tool chỉ dành cho company_admin.
- expected_tool giữ tên tool bị chặn.
- expected_permission: denied.

## 6. Các trường hợp loại trừ

Không sử dụng hai công cụ đọc để xử lý:

- Gửi tin nhắn mới.
- Xóa cuộc hội thoại.
- Chỉnh sửa nội dung tin nhắn.
- Đánh dấu đã đọc.
- Tìm kiếm nội dung tin nhắn khi API không hỗ trợ.

Các hành động không có tool tương ứng thuộc out_of_scope.

Không dùng category dependent hoặc tạo ngữ cảnh nhiều lượt.

## 7. Kiểm soát chất lượng

Với mỗi record:

1. Ý định có ánh xạ chính xác đến tool không?
2. Role có được phép gọi tool không?
3. Tham số có đúng schema không?
4. Có dữ liệu hoặc tham số nào được tự suy đoán không?
5. Category có tuân thủ quy tắc gán nhãn không?
6. Câu hỏi có độc lập và tự nhiên không?

Chỉ sinh dữ liệu đánh giá; không thực thi các thao tác Chat thực tế.
