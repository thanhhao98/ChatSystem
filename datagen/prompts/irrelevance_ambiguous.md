# Irrelevance: ambiguous

Sinh câu hỏi tiếng Việt có liên quan đến SGOD nhưng chưa đủ thông tin để xác định ý định, đối tượng hoặc công cụ cần sử dụng.

## Objective

Tạo dữ liệu câu hỏi mơ hồ để huấn luyện trợ lý nhận biết khi nào cần yêu cầu người dùng làm rõ thay vì tự suy đoán và gọi SGOD tool.

Các câu phải có liên quan đến bối cảnh SGOD nhưng thiếu thông tin quan trọng để xử lý chính xác.

## Ambiguity Types

### Unclear Reference

- Người dùng nhắc đến "cái đó", "phiếu kia", "thiết bị ấy" mà không xác định đối tượng.
- Không có ngữ cảnh trước đó để suy ra đối tượng đang được nói đến.
- Không tự tạo ID hoặc tên thực thể để hoàn thiện câu hỏi.

### Unclear Intent

- Người dùng đưa ra một yêu cầu chung chung, chưa xác định muốn tra cứu thông tin gì.
- Không đủ thông tin để lựa chọn duy nhất một SGOD tool.
- Không tự suy đoán ý định cụ thể.

### Missing Required Information

- Câu hỏi nhắm đến một đối tượng cụ thể nhưng thiếu thông tin bắt buộc để truy xuất.
- Chỉ sử dụng tình huống này khi không tồn tại cách xử lý hợp lệ bằng một tool khác.
- Không coi việc thiếu tham số tùy chọn là ambiguous.

## Generation Rules

- Chỉ sinh dữ liệu single-turn.
- Mỗi câu chỉ có một ý định chưa rõ ràng.
- Không tạo hội thoại nhiều lượt hoặc dependent.
- Câu hỏi phải thuộc ngữ cảnh nghiệp vụ SGOD.
- Chỉ tạo câu thật sự cần làm rõ trước khi lựa chọn tool.
- Không tạo câu đã có thể ánh xạ rõ ràng tới một read-only tool.
- Không biến câu hỏi tra cứu danh sách hợp lệ thành ambiguous chỉ vì thiếu ID.
- Không tự bổ sung thực thể, trạng thái, ID hoặc điều kiện lọc.
- Không tạo tình huống thiếu quyền truy cập; loại này thuộc `permission_denial`.
- Không tạo yêu cầu ghi trực tiếp như tạo, sửa, xóa hoặc phê duyệt.
- Không sinh câu hỏi kiến thức ngoài SGOD; loại đó thuộc `out_of_scope`.
- Không sinh câu trò chuyện xã giao; loại đó thuộc `chitchat`.
- Không sinh câu hỏi hướng dẫn quy trình rõ ràng; loại đó thuộc `procedure_question`.
- Không sao chép hoặc paraphrase câu hỏi trong `data/sgod/eval_human_core.jsonl`.

## Language & Diversity

- Sử dụng tiếng Việt tự nhiên.
- Đa dạng cách diễn đạt và mức độ mơ hồ.
- Kết hợp văn phong công sở, lịch sự và thân mật.
- Cho phép viết tắt, lỗi gõ nhẹ và một phần câu không dấu.
- Các câu phải giống những yêu cầu thiếu rõ ràng trong môi trường làm việc thực tế.
- Không tạo nhiều câu trùng ý nghĩa chỉ bằng cách thay đổi đại từ hoặc dấu câu.
- Không đưa tên SGOD tool hoặc tham số kỹ thuật vào câu hỏi.

## Tool Calling Rules

- Không gọi bất kỳ SGOD tool nào khi chưa đủ thông tin.
- Không tự chọn tool bằng suy đoán.
- Không tự tạo ID hoặc dữ liệu để giải quyết sự mơ hồ.
- Các câu phải phù hợp với nhãn no-call.

## Output Requirements

- Tuân thủ định dạng JSON array từ `irrelevance_system.md`.
- Mỗi phần tử là một chuỗi câu hỏi hoặc yêu cầu tiếng Việt.
- Không thêm `expected_tool`, `expected_params` hoặc metadata.
- Không sử dụng Markdown code fence.
- Không thêm lời giải thích ngoài dữ liệu được yêu cầu.
