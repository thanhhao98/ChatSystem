# irrelevance_system.md — Quy chuẩn sinh kịch bản Irrelevance SGOD

## 1. Mục tiêu

Hướng dẫn sinh các câu hỏi tiếng Việt tự nhiên nhằm đánh giá khả năng nhận diện yêu cầu không thể thực hiện bằng các công cụ SGOD hiện hành.

Bộ kịch bản này phục vụ Eval Augmentation trong Task D-V4 và phải được xây dựng độc lập với prompts huấn luyện.

## 2. Phạm vi

Bộ Irrelevance bao gồm bốn nhóm:

1. unsupported_actions — 40%
2. chitchat — 20%
3. ambiguous — 20%
4. procedure_question — 20%

Tỷ lệ trên là mục tiêu phân bổ trong tập Irrelevance, không phải tỷ lệ của toàn bộ eval_v1.

Không tự động áp dụng các tỷ lệ này cho permission_denial.

## 3. Nguyên tắc chung

- 100% câu hỏi single-turn.
- Mỗi câu chỉ chứa một ý định chính.
- Khoảng 15–20% câu sử dụng tiếng Việt không dấu.
- Ngôn ngữ tự nhiên, phù hợp người dùng doanh nghiệp.
- Không phụ thuộc hội thoại trước.
- Không sử dụng tên tool, API hoặc tham số backend trong lời người dùng.
- Không sao chép câu từ tập train, eval core hoặc các dataset khác.
- Không sử dụng thông tin cá nhân thật, token hay dữ liệu nhạy cảm.

## 4. Phân biệt các loại yêu cầu

### Unsupported Actions

Người dùng yêu cầu một chức năng không có trong bộ 22 công cụ SGOD.

Ví dụ về loại hành động:

- Tạo dữ liệu.
- Cập nhật dữ liệu.
- Xóa dữ liệu.
- Phê duyệt thao tác.
- Gửi tin nhắn.

Không sử dụng một công cụ đọc để thay thế hành động ghi.

### Chitchat

Người dùng giao tiếp thông thường mà không yêu cầu dữ liệu từ SGOD.

Bao gồm:

- Chào hỏi.
- Cảm ơn.
- Khen ngợi.
- Hỏi thăm.
- Trò chuyện xã giao.

Không kết hợp thêm yêu cầu tra cứu nghiệp vụ.

### Ambiguous

Người dùng đưa ra câu hỏi không đủ rõ để xác định một tool call duy nhất.

Chỉ sinh trường hợp mà ý định thực sự không thể xác định từ một lượt hỏi.

Không coi mọi câu ngắn là mơ hồ.

Không tự động coi yêu cầu thiếu một tham số bắt buộc là out_of_scope nếu ý định gọi tool vẫn rõ ràng; trường hợp này cần được xử lý theo quy định gán nhãn của dự án.

### Procedure Question

Người dùng hỏi cách thực hiện một quy trình hoặc quy định mà hệ thống không có công cụ tra cứu phù hợp.

Không tự sáng tác chính sách nội bộ của SGOD.

Phân biệt câu hỏi giải thích quy trình với câu hỏi tra cứu dữ liệu thực tế.

## 5. Quy tắc gán nhãn

Đối với câu hỏi được xác nhận không có tool phù hợp:

- category: out_of_scope
- expected_tool: null
- expected_permission: allowed
- expected_params: {}

Đối với yêu cầu có tool tồn tại nhưng role không được phép gọi:

- category: permission_denial
- expected_tool: tên tool bị chặn
- expected_permission: denied

Không gộp hai loại trên.

Không dùng category dependent.

## 6. Kiểm soát chất lượng

Trước khi chấp nhận một câu hỏi, kiểm tra:

1. Câu hỏi có độc lập không?
2. Ý định có thực sự không được bộ công cụ hỗ trợ không?
3. Có công cụ nào phù hợp nhưng bị chặn quyền không?
4. Có trường hợp mơ hồ cần giải quyết theo hợp đồng gán nhãn không?
5. Category và expected_tool có nhất quán không?
6. Câu hỏi có tự nhiên, đa dạng và không trùng dữ liệu có sẵn không?

Không ép một câu hỏi vào out_of_scope chỉ để đạt chỉ tiêu số lượng.

## 7. Tổ chức các prompt chuyên biệt

Các kịch bản được mô tả chi tiết tại:

- irrelevance_out_of_scope.md
- irrelevance_chitchat.md
- irrelevance_ambiguous.md
- irrelevance_procedure_question.md

Các file này là thành phần đặc tả riêng.

Việc sử dụng chúng trong pipeline phải được cấu hình rõ ràng; không giả định rằng hệ thống tự động nạp các file chỉ vì chúng tồn tại.

## 8. Ràng buộc bảo mật và độc lập dữ liệu

- Không đọc hoặc sao chép datagen/prompts/.
- Không sử dụng câu hỏi có sẵn làm few-shot.
- Không tạo dữ liệu nhằm khớp với văn phong của tập huấn luyện.
- Không sử dụng bí mật, thông tin xác thực hoặc dữ liệu người dùng thật.
- Không thay đổi schema hoặc phân quyền của các tool.
