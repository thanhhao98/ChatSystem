# category_out_of_scope.md — Đánh giá yêu cầu ngoài phạm vi SGOD

## 1. Mục tiêu

Sinh các câu hỏi tiếng Việt tự nhiên để kiểm tra khả năng nhận biết khi không có công cụ SGOD phù hợp với yêu cầu của người dùng.

Mỗi câu hỏi độc lập (single-turn), không cần ngữ cảnh hội thoại trước đó.

Đây là prompt dành riêng cho eval augmentation, được xây dựng độc lập với dữ liệu và prompts huấn luyện.

## 2. Quy tắc chung

Mọi tình huống trong nhóm này phải thỏa mãn:

- category: out_of_scope
- expected_tool: null
- expected_permission: allowed
- expected_params: {}

Không sử dụng tên tool giả hoặc chuyển sang một tool không phù hợp.

Không đồng nhất out_of_scope với permission_denial.

Nếu SGOD có tool đáp ứng yêu cầu nhưng role không được gọi, chuyển sang nhóm permission_denial.

## 3. Phân loại tình huống

### A. Unsupported Actions — 40%

Các yêu cầu nằm ngoài khả năng của bộ 22 tools SGOD.

Bao gồm:

- Tạo mới tài sản.
- Cập nhật hoặc xóa tài sản.
- Phê duyệt phiếu điều chuyển.
- Tạo yêu cầu nhân viên mới.
- Gửi tin nhắn hoặc xóa cuộc trò chuyện.
- Các tác vụ không thuộc chức năng của hệ thống.

Chỉ tạo tình huống khi không tồn tại tool tương ứng trong danh mục hiện hành.

Không gán expected_permission=denied cho các yêu cầu không có tool.

### B. Chitchat — 20%

Các tương tác giao tiếp thông thường không yêu cầu truy xuất dữ liệu doanh nghiệp.

Bao gồm:

- Chào hỏi.
- Cảm ơn.
- Khen ngợi.
- Hỏi thăm chung.
- Trò chuyện không liên quan đến nghiệp vụ.

Không trộn thêm yêu cầu đọc dữ liệu SGOD vào cùng một câu.

### C. Ambiguous Queries — 20%

Các câu hỏi thiếu thông tin hoặc không thể xác định chính xác một công cụ cần gọi.

Đặc điểm:

- Ý định không rõ ràng.
- Thiếu đối tượng cần truy vấn.
- Không đủ ngữ cảnh để phân biệt các tool.
- Không thể suy ra tham số bắt buộc một cách đáng tin cậy.

Không tự tạo thông tin còn thiếu.

Không sử dụng câu phụ thuộc hội thoại trước.

Chỉ đưa vào nhóm này khi không thể xác định một tool call hợp lệ. Câu ngắn nhưng rõ ý định vẫn phải được xử lý bằng tool tương ứng.

### D. Procedure Questions — 20%

Các yêu cầu giải thích quy trình, quy định hoặc hướng dẫn nghiệp vụ không có tool tra cứu tương ứng.

Bao gồm:

- Quy trình đăng ký cấp phát tài sản.
- Các bước đề nghị điều chuyển thiết bị.
- Chính sách phê duyệt yêu cầu.
- Quy trình báo hỏng và sửa chữa thiết bị.

Không bịa nội dung chính sách hoặc quy trình của doanh nghiệp.

Phân biệt câu hỏi quy trình với yêu cầu xem hồ sơ, trạng thái hay danh sách dữ liệu thực tế có tool hỗ trợ.

## 4. Quy chuẩn sinh dữ liệu

- 100% single-turn.
- Khoảng 15–20% câu tiếng Việt không dấu.
- Văn phong công sở tự nhiên.
- Đa dạng độ dài và mức độ trang trọng.
- Không sử dụng thuật ngữ kỹ thuật backend trong lời người dùng.
- Không sao chép câu từ dataset hiện có.
- Không chứa thông tin cá nhân thật hoặc dữ liệu nhạy cảm.
- Không sinh yêu cầu có thể ánh xạ chắc chắn đến một tool hợp lệ.

## 5. Kiểm tra nhãn

Với từng câu được sinh, xác minh:

1. Không tồn tại tool hỗ trợ trực tiếp yêu cầu.
2. Không phải trường hợp role bị chặn quyền gọi một tool có thật.
3. Không phải yêu cầu đọc dữ liệu hợp lệ.
4. Không tự tạo tham số hoặc tên tool.
5. Category là out_of_scope.
6. expected_tool là null.
7. expected_permission là allowed.

## 6. Kiểm soát phân phối

Phân phối mục tiêu trong nhóm irrelevance:

- unsupported_actions: 40%
- chitchat: 20%
- ambiguous: 20%
- procedure_question: 20%

Các tỷ lệ này là mục tiêu để kiểm tra tập dữ liệu sau khi sinh, không phải bằng chứng rằng pipeline tự động đảm bảo đúng phân phối.

Không thay đổi BUCKET_PLAN hoặc logic sinh dữ liệu tại file này.
