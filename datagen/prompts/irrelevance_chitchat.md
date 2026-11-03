# Irrelevance: chitchat

Sinh các câu nói hoặc câu hỏi tiếng Việt mang tính trò chuyện xã giao, không yêu cầu truy xuất dữ liệu hoặc thực hiện nghiệp vụ trên hệ thống SGOD.

## Objective

Tạo dữ liệu hội thoại thông thường để huấn luyện trợ lý nhận biết những tình huống không cần gọi SGOD tool.

Các câu phải thể hiện ý định trò chuyện rõ ràng và không chứa yêu cầu nghiệp vụ.

## Supported Topics

Đa dạng hóa các kiểu hội thoại:

- Chào hỏi và chào tạm biệt.
- Cảm ơn hoặc phản hồi lịch sự.
- Chúc một ngày làm việc tốt lành.
- Trò chuyện xã giao ngắn.
- Hỏi thăm mang tính giao tiếp thông thường.
- Khen ngợi hoặc thể hiện cảm xúc tích cực.
- Phản hồi tự nhiên trong giao tiếp công sở.

Không tập trung quá nhiều vào một kiểu câu.

## Generation Rules

- Chỉ sinh dữ liệu single-turn.
- Mỗi câu chỉ có một ý định giao tiếp.
- Không tạo hội thoại nhiều lượt hoặc chuỗi câu hỏi phụ thuộc.
- Không sinh câu cần gọi SGOD read-only tool.
- Không yêu cầu tra cứu tài sản, bảo trì, điều chuyển hoặc yêu cầu nhân viên.
- Không hỏi về thông tin tài khoản, hồ sơ hoặc quyền truy cập.
- Không đưa yêu cầu tạo, sửa, xóa dữ liệu vào câu trò chuyện.
- Không kết hợp chào hỏi với một yêu cầu nghiệp vụ SGOD.
- Không sinh câu hỏi yêu cầu hướng dẫn quy trình SGOD; loại đó thuộc `procedure_question`.
- Không sinh câu hỏi kiến thức ngoài phạm vi SGOD; loại đó thuộc `out_of_scope`.
- Không sinh câu quá mơ hồ khiến không xác định được ý định giao tiếp.
- Không tự tạo thông tin cá nhân hoặc dữ liệu nội bộ.
- Không sao chép hoặc paraphrase câu hỏi trong `data/sgod/eval_human_core.jsonl`.

## Language & Diversity

- Sử dụng tiếng Việt tự nhiên.
- Kết hợp văn phong lịch sự, thân mật và công sở.
- Đa dạng độ dài nhưng ưu tiên câu ngắn, dễ hiểu.
- Cho phép sử dụng viết tắt thông dụng.
- Có thể có lỗi gõ nhẹ và một phần câu không dấu.
- Tránh sinh nhiều câu trùng ý nghĩa chỉ khác dấu câu hoặc từ xưng hô.
- Không đưa tên tool, API hoặc nhãn dữ liệu vào câu nói.

## Tool Calling Rules

- Không gọi bất kỳ SGOD tool nào.
- Không cố ánh xạ câu trò chuyện sang công cụ gần giống.
- Không tự tạo tên tool hoặc tham số.
- Các câu phải phù hợp với nhãn no-call.

## Output Requirements

- Tuân thủ định dạng JSON array từ `irrelevance_system.md`.
- Mỗi phần tử là một chuỗi tiếng Việt.
- Không thêm `expected_tool`, `expected_params` hoặc metadata.
- Không sử dụng Markdown code fence.
- Không thêm giải thích ngoài dữ liệu được yêu cầu.
