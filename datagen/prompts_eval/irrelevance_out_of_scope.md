# irrelevance_out_of_scope.md — Kịch bản ngoài khả năng công cụ SGOD

## 1. Mục tiêu

Hướng dẫn sinh câu hỏi tiếng Việt tự nhiên nhằm đánh giá khả năng nhận diện những yêu cầu không được bộ 22 công cụ SGOD hiện hành hỗ trợ.

Đây là nhóm Unsupported Actions, thuộc bộ Irrelevance của Task D-V4.

Tỷ trọng mục tiêu: 40% trong tập Irrelevance, không phải 40% toàn bộ eval_v1.

## 2. Phạm vi tình huống

### 2.1. Tạo mới dữ liệu

Người dùng muốn tạo mới:

- Tài sản hoặc thiết bị.
- Phiếu điều chuyển tài sản.
- Lịch bảo trì.
- Yêu cầu nhân viên.
- Cuộc hội thoại hoặc tin nhắn.

Các công cụ SGOD v1 chỉ hỗ trợ đọc dữ liệu, không có công cụ tạo mới.

### 2.2. Cập nhật dữ liệu

Người dùng muốn:

- Chỉnh sửa thông tin tài sản.
- Thay đổi thông tin phiếu điều chuyển.
- Cập nhật trạng thái yêu cầu.
- Sửa thông tin lịch bảo trì.
- Thay đổi nội dung hội thoại.

Không thay thế hành động cập nhật bằng công cụ tra cứu.

### 2.3. Xóa dữ liệu

Người dùng yêu cầu:

- Xóa tài sản.
- Xóa hồ sơ bảo trì.
- Xóa yêu cầu nhân viên.
- Xóa hội thoại hoặc tin nhắn.

Không có công cụ DELETE tương ứng trong danh mục hiện hành.

### 2.4. Hành động nghiệp vụ không được hỗ trợ

Bao gồm:

- Phê duyệt hoặc từ chối phiếu.
- Thực hiện điều chuyển tài sản.
- Gửi thông báo.
- Thực hiện thao tác thay đổi dữ liệu.

Chỉ đưa vào nhóm này khi xác minh không có tool tương ứng.

### 2.5. Yêu cầu ngoài lĩnh vực hệ thống

Có thể bao gồm những yêu cầu thuộc lĩnh vực khác nhưng không có công cụ SGOD phù hợp.

Không sử dụng nhóm này để thay thế chitchat, ambiguous hoặc procedure_question khi các nhóm đó được phân loại riêng.

## 3. Quy tắc gán nhãn

Với mỗi tình huống được xác minh là out_of_scope:

- category: out_of_scope
- expected_tool: null
- expected_permission: allowed
- expected_params: {}

Không tạo tên tool giả.

Không dùng một tool đọc để thay thế hành động ghi.

Không gán expected_permission: denied khi hệ thống không có công cụ tương ứng.

## 4. Phân biệt với Permission Denial

Permission Denial:

- Tool tồn tại trong danh mục.
- Role không có quyền gọi.
- expected_tool giữ tên công cụ bị chặn.
- expected_permission: denied.

Out of Scope:

- Không tồn tại công cụ phù hợp.
- expected_tool: null.
- expected_permission: allowed.

Không phân loại yêu cầu tạo, sửa, xóa thành permission_denial chỉ vì hệ thống hiện không cho phép thao tác ghi.

## 5. Quy chuẩn sinh câu hỏi

- 100% single-turn.
- Mỗi câu chỉ có một ý định chính.
- Khoảng 15–20% câu tiếng Việt không dấu.
- Văn phong tự nhiên trong môi trường công sở.
- Đa dạng cách diễn đạt và độ dài.
- Không sử dụng tên API hoặc tên tham số kỹ thuật.
- Không phụ thuộc ngữ cảnh hội thoại trước.
- Không sao chép dữ liệu từ tập train hoặc eval có sẵn.
- Không sử dụng dữ liệu cá nhân thật hoặc thông tin xác thực.

## 6. Kiểm soát chất lượng

Với mỗi câu sinh ra, xác minh:

1. Có công cụ SGOD nào thực sự hỗ trợ yêu cầu không?
2. Câu hỏi có phải yêu cầu ghi dữ liệu không?
3. Có nhầm lẫn với trường hợp bị chặn quyền không?
4. Ý định có độc lập và rõ ràng không?
5. Category, expected_tool và expected_permission có nhất quán không?
6. Câu hỏi có tự nhiên và không trùng dữ liệu đã có không?

Nếu một công cụ đọc hợp lệ có thể đáp ứng trực tiếp yêu cầu, không đưa câu hỏi vào nhóm out_of_scope.

Không cố tình tăng số lượng câu ngoài phạm vi bằng cách phân loại sai các yêu cầu có thể thực hiện được.

## 7. Tích hợp

File này là prompt chuyên biệt của nhóm Unsupported Actions.

Prompt tổng hợp cho pipeline hiện tại:

- category_out_of_scope.md

Prompt điều phối:

- irrelevance_system.md

Pipeline hiện chưa tự động nạp file này. Việc tích hợp phải được xác minh trước khi sinh dữ liệu đánh giá chính thức.
