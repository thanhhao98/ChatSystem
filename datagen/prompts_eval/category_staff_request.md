# category_staff_request.md — Đánh giá truy vấn yêu cầu nhân viên

## 1. Mục tiêu

Sinh các câu hỏi tiếng Việt tự nhiên nhằm đánh giá khả năng lựa chọn công cụ tra cứu danh sách và thông tin tổng hợp yêu cầu nhân viên trong hệ thống SGOD.

Mỗi câu hỏi phải độc lập (single-turn), có ý định rõ ràng và chỉ cần tối đa một tool call.

## 2. Công cụ mục tiêu

### list_staff_requests

Mục đích:
Tra cứu danh sách yêu cầu nhân viên trong hệ thống.

Roles được phép:

- employee
- company_admin

Tham số hợp lệ:

- limit: integer, tùy chọn.
- cursor: string, tùy chọn.

Quy tắc:

- Chọn tool khi người dùng yêu cầu xem danh sách yêu cầu nhân viên.
- Chỉ truyền limit khi câu hỏi nêu số lượng cụ thể.
- Không tự tạo cursor hoặc giả định có trang dữ liệu trước đó.
- Không tự thêm status, date, employee_id, request_id hoặc các bộ lọc ngoài schema.
- Không mặc định API hỗ trợ tìm kiếm theo tên nhân viên.
- Không suy đoán thứ tự sắp xếp mặc định của API.

### get_staff_request_summary

Mục đích:
Truy vấn thông tin tổng hợp về các yêu cầu nhân viên.

Roles được phép:

- employee
- company_admin

Tham số:

- Không có.

Quy tắc:

- Chọn tool khi người dùng muốn xem thông tin tổng quan hoặc tổng hợp yêu cầu.
- expected_params phải là {}.
- Không sinh yêu cầu lọc theo thời gian, trạng thái hoặc phòng ban khi API không hỗ trợ.
- Không suy đoán các chỉ số cụ thể mà API có thể trả về.

## 3. Ngữ cảnh và Personas

Ưu tiên các tình huống công sở thực tế:

- Nhân viên văn phòng muốn xem danh sách yêu cầu trong hệ thống.
- Nhân viên hành chính theo dõi các yêu cầu liên quan đến công việc.
- Quản trị viên doanh nghiệp muốn xem thông tin tổng hợp yêu cầu.

Không mặc định các persona có quyền truy cập dữ liệu vượt quá phạm vi được API cho phép.

## 4. Hướng dẫn sinh câu hỏi

- 100% single-turn, không phụ thuộc hội thoại trước.
- Khoảng 15–20% câu tiếng Việt không dấu.
- Đa dạng độ dài, cách diễn đạt và giọng văn.
- Phân biệt rõ yêu cầu xem danh sách và xem tổng hợp.
- Ưu tiên văn phong công sở tự nhiên, không máy móc.
- Không sử dụng tên tool hoặc tham số kỹ thuật trong câu hỏi.
- Không sao chép câu hỏi từ dataset có sẵn.
- Không sử dụng thông tin cá nhân thật, token hoặc dữ liệu nhạy cảm.

## 5. Quy tắc gán nhãn

### single_tool

Áp dụng khi:

- expected_permission: allowed.
- expected_tool tương ứng với ý định truy vấn.
- expected_params chứa 0 hoặc 1 tham số hợp lệ.

### multi_constraint

Chỉ áp dụng khi:

- expected_permission: allowed.
- expected_tool không null.
- Câu hỏi chứa ít nhất 2 tham số hợp lệ có căn cứ trực tiếp.

Không cố tình tạo multi_constraint bằng cách bịa cursor hoặc yêu cầu phân trang không có ngữ cảnh.

### Loại trừ

- Không sử dụng category dependent.
- Không tạo tham số ngoài schema.
- Không suy đoán employee hoặc company_admin bị từ chối quyền khi cả hai được phép gọi tool.
- Không sử dụng tool đọc để biểu diễn yêu cầu tạo, sửa hoặc xóa.
- Các tình huống không có tool phù hợp phải được chuyển sang nhóm out_of_scope.

## 6. Kiểm soát chất lượng

Với mỗi record được sinh, xác minh:

1. Ý định truy vấn tương ứng chính xác với tool nào?
2. Role người dùng có quyền gọi tool đó không?
3. Tất cả tham số có đúng schema không?
4. Có giá trị tham số nào bị tự suy đoán không?
5. Category có phù hợp với số tham số và quyền không?
6. Câu hỏi có độc lập, tự nhiên và không trùng dữ liệu hiện có không?

Không tạo hoặc sửa dữ liệu doanh nghiệp. Chỉ sinh câu hỏi đánh giá cho các API đọc.
