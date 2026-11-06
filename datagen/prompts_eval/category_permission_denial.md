# category_permission_denial.md — Đánh giá từ chối quyền truy cập

## 1. Mục tiêu

Sinh câu hỏi tiếng Việt tự nhiên nhằm kiểm tra khả năng nhận diện yêu cầu truy cập công cụ mà vai trò người dùng không được phép gọi.

Chỉ sinh tình huống có tool tồn tại trong SGOD nhưng quyền truy cập bị từ chối.

## 2. Phạm vi công cụ

Các công cụ company_admin-only:

- get_enterprise_profile
- list_enterprise_users
- list_my_conversations
- get_unread_counts
- get_asset_statistics

Vai trò tạo tình huống denied:

- employee

Không tự suy đoán quyền truy cập của các công cụ khác.

## 3. Nguyên tắc sinh câu hỏi

- 100% single-turn.
- Khoảng 15–20% câu tiếng Việt không dấu.
- Ngôn ngữ tự nhiên, phù hợp môi trường doanh nghiệp.
- Mỗi câu thể hiện một ý định đọc dữ liệu rõ ràng.
- Ý định phải ánh xạ được đến một tool có thật.
- Không tạo tình huống phụ thuộc hội thoại trước.
- Không chèn dữ liệu nhạy cảm hoặc định danh người dùng thật.
- Không sao chép câu từ các dataset có sẵn.

## 4. Quy tắc nhãn kỳ vọng

Với mỗi tình huống thuộc permission_denial:

- category: permission_denial
- expected_permission: denied
- expected_tool: tên công cụ bị chặn
- expected_params: chỉ chứa tham số có căn cứ trong câu hỏi và hợp lệ theo schema.

Ví dụ về nguyên tắc:

Nếu employee muốn xem danh sách nhân viên:

- Tool tương ứng: list_enterprise_users
- Permission: denied

Không biến tên tool thành null chỉ vì người dùng thiếu quyền.

Nếu sử dụng expected_tool_alternates:

- Chỉ đưa vào các tool mà role thực sự có quyền gọi.
- Không sử dụng alternate để vượt qua giới hạn phân quyền.
- Khi alternate cần tham số từ câu hỏi, phải cung cấp expected_params_alternates phù hợp.

## 5. Loại trừ

Không đưa các tình huống sau vào permission_denial:

- Tạo tài sản.
- Cập nhật tài sản.
- Xóa tài sản.
- Phê duyệt điều chuyển.
- Gửi tin nhắn mới.
- Các yêu cầu không có tool đọc tương ứng.

Các trường hợp trên thuộc out_of_scope khi bộ công cụ hiện tại không hỗ trợ.

Không gán denied cho các tool mà employee được phép gọi theo roles và tool policy hiện hành.

## 6. Kiểm soát chất lượng

Trước khi chấp nhận một trường hợp:

1. Tool được yêu cầu có tồn tại trong danh mục 22 tools.
2. Role thực sự không có quyền gọi tool.
3. Ý định người dùng tương ứng với đúng tool bị chặn.
4. Không tự tạo tham số ngoài schema.
5. Không nhầm lẫn với out_of_scope.
6. Câu hỏi độc lập và tự nhiên.

Mục tiêu là đánh giá phân quyền, không đánh giá việc từ chối những thao tác mà hệ thống chưa có công cụ.
