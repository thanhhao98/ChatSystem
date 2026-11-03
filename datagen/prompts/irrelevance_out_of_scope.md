# Irrelevance: out_of_scope

Sinh câu hỏi tiếng Việt thuộc các lĩnh vực hoàn toàn ngoài phạm vi quản lý tài sản và nghiệp vụ của hệ thống SGOD.

## Objective

Tạo các câu hỏi không thể giải quyết bằng bất kỳ công cụ SGOD nào.

Các câu hỏi phải có ý định rõ ràng nhưng không liên quan đến dữ liệu hoặc chức năng nghiệp vụ SGOD.

## Supported Topics

Đa dạng hóa nội dung thuộc các chủ đề:

- Đời sống và sinh hoạt hằng ngày.
- Nấu ăn và thực phẩm.
- Thể thao và giải trí.
- Du lịch và văn hóa.
- Giáo dục và học tập.
- Khoa học và kiến thức phổ thông.
- Công nghệ nói chung, không liên quan đến hệ thống SGOD.

Không tập trung quá nhiều vào một chủ đề.

## Generation Rules

- Mỗi câu hỏi chỉ có một ý định.
- Chỉ sinh dữ liệu single-turn.
- Không sinh multi-turn hoặc dependent.
- Không tạo câu hỏi cần truy xuất dữ liệu SGOD.
- Không đề cập đến tài sản, phiếu điều chuyển, lịch bảo trì, yêu cầu nhân viên hoặc các chức năng SGOD.
- Không tạo câu hỏi có thể ánh xạ vào bất kỳ SGOD read-only tool nào.
- Không sinh yêu cầu tạo, sửa, xóa dữ liệu SGOD.
- Không sinh câu hỏi về quy trình sử dụng SGOD.
- Không sinh lời chào hỏi hoặc trò chuyện xã giao thuần túy; chúng thuộc `chitchat`.
- Không sinh câu hỏi mơ hồ; chúng thuộc `ambiguous`.
- Không sử dụng PII hoặc dữ liệu nội bộ.
- Không sao chép hoặc paraphrase câu hỏi trong `data/sgod/eval_human_core.jsonl`.

## Language & Diversity

- Sử dụng tiếng Việt tự nhiên.
- Câu hỏi phải có ý định rõ ràng và dễ hiểu.
- Đa dạng cách diễn đạt, độ dài và chủ đề.
- Kết hợp văn phong lịch sự, thân mật và ngắn gọn.
- Cho phép viết tắt thông dụng, lỗi gõ nhẹ và một phần câu không dấu.
- Không tạo nhiều câu trùng ý nghĩa chỉ bằng cách thay đổi từ ngữ.

## Tool Calling Rules

- Không gọi bất kỳ SGOD tool nào.
- Không tự tạo tên tool hoặc tham số.
- Không cố ánh xạ câu hỏi ngoài phạm vi sang công cụ gần giống.
- Các câu hỏi phải phù hợp với nhãn no-call.

## Output Requirements

- Tuân thủ định dạng JSON array do `irrelevance_system.md` quy định.
- Mỗi phần tử là một chuỗi câu hỏi tiếng Việt.
- Không đưa nhãn `expected_tool`, `expected_params` hoặc metadata vào đầu ra.
- Không sử dụng Markdown code fence.
- Không thêm giải thích ngoài dữ liệu được yêu cầu.
