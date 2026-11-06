# irrelevance_chitchat.md — Kịch bản hội thoại xã giao SGOD

## 1. Mục tiêu

Sinh các phát ngôn tiếng Việt tự nhiên nhằm đánh giá khả năng nhận diện hội thoại xã giao không cần sử dụng công cụ SGOD.

Đây là nhóm Chitchat thuộc bộ Irrelevance trong Task D-V4.

Tỷ trọng mục tiêu: 20% trong tập Irrelevance, không phải 20% của toàn bộ eval_v1.

## 2. Phạm vi tình huống

### 2.1. Chào hỏi

Người dùng bắt đầu tương tác bằng lời chào thông thường.

Không kết hợp yêu cầu tra cứu nghiệp vụ.

### 2.2. Cảm ơn

Người dùng bày tỏ sự cảm ơn hoặc ghi nhận sự hỗ trợ.

Không kèm yêu cầu mới cần thực hiện.

### 2.3. Khen ngợi

Người dùng đưa ra nhận xét tích cực về trải nghiệm tương tác.

Không yêu cầu truy xuất dữ liệu doanh nghiệp hoặc đánh giá một bản ghi cụ thể.

### 2.4. Hỏi thăm

Người dùng thực hiện các tương tác giao tiếp thông thường, không mang ý định nghiệp vụ.

### 2.5. Trò chuyện xã giao

Các phát ngôn giao tiếp không liên quan đến công cụ quản lý tài sản, bảo trì, nhân sự hoặc hội thoại của SGOD.

Không tạo câu hỏi yêu cầu thông tin thực tế có thể được hỗ trợ bởi tool hiện có.

## 3. Quy tắc gán nhãn kỳ vọng

Đối với Chitchat không yêu cầu công cụ:

- category: out_of_scope
- expected_tool: null
- expected_permission: allowed
- expected_params: {}

Chitchat là nhóm tình huống phục vụ phân tích, không phải category chính mới trong schema eval_v1.

Không tạo tool giả để xử lý lời chào, cảm ơn hoặc khen ngợi.

Không gán expected_permission: denied cho hội thoại xã giao không có tool cần gọi.

## 4. Phân biệt với các nhóm khác

### Chitchat và yêu cầu nghiệp vụ

Nếu câu hỏi có ý định tra cứu thông tin SGOD rõ ràng, không phân loại là Chitchat chỉ vì có lời chào hoặc cách nói thân mật.

### Chitchat và Unsupported Actions

Chitchat không yêu cầu thao tác nghiệp vụ.

Unsupported Actions bao gồm những yêu cầu cụ thể mà bộ công cụ SGOD hiện tại không hỗ trợ.

### Chitchat và Ambiguous

Chitchat thể hiện ý định giao tiếp xã giao có thể nhận diện được.

Ambiguous là tình huống không đủ thông tin để xác định ý định hoặc công cụ phù hợp.

### Chitchat và Permission Denial

Chitchat không liên quan đến việc truy cập công cụ bị giới hạn quyền.

Không sử dụng permission_denial nếu người dùng không yêu cầu gọi tool.

## 5. Quy chuẩn sinh câu hỏi

- 100% single-turn.
- Mỗi phát ngôn chỉ thể hiện một ý định giao tiếp.
- Khoảng 15–20% câu tiếng Việt không dấu.
- Đa dạng cách diễn đạt, độ dài và mức độ trang trọng.
- Có thể sử dụng văn phong thân mật, tự nhiên.
- Không lạm dụng một số mẫu câu chào hỏi phổ biến.
- Không sử dụng thuật ngữ kỹ thuật backend.
- Không sao chép dữ liệu từ tập train hoặc eval hiện có.
- Không chứa dữ liệu cá nhân, token hoặc thông tin nhạy cảm.

## 6. Ràng buộc chất lượng

Không sinh các câu có những đặc điểm sau:

- Chứa yêu cầu truy vấn dữ liệu SGOD rõ ràng.
- Chứa yêu cầu tạo, sửa, xóa dữ liệu.
- Chứa yêu cầu truy cập tool bị hạn chế quyền.
- Kết hợp nhiều ý định khác nhau.
- Phụ thuộc vào phản hồi hoặc cuộc hội thoại trước đó.
- Có thể ánh xạ trực tiếp đến một tool trong danh mục hiện hành.

Không cố tình tạo câu vô nghĩa chỉ để đạt tỷ lệ 20%.

## 7. Kiểm soát chất lượng

Với mỗi phát ngôn, kiểm tra:

1. Ý định chính có phải giao tiếp xã giao không?
2. Có yêu cầu nghiệp vụ cần sử dụng tool không?
3. Có bị nhầm với nhóm Ambiguous không?
4. Có tồn tại một tool SGOD phù hợp trực tiếp không?
5. Nhãn out_of_scope có chính xác không?
6. Câu có độc lập, tự nhiên và không trùng lặp không?

Chỉ chấp nhận các câu không cần tool SGOD và phù hợp với mục tiêu đánh giá Chitchat.

## 8. Tích hợp

Prompt điều phối:

- irrelevance_system.md

Prompt tổng hợp được pipeline hiện tại nhận diện:

- category_out_of_scope.md

File này là prompt chuyên biệt, chưa được xác nhận là được pipeline tự động nạp.

Việc tích hợp phải được kiểm chứng trước khi sử dụng để sinh dữ liệu đánh giá chính thức.
