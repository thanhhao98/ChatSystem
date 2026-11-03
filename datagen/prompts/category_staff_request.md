# Category: staff_request

Sinh câu hỏi tiếng Việt về việc tra cứu danh sách và thống kê yêu cầu của nhân viên trong hệ thống SGOD.

## Tool Selection

- `list_staff_requests`: Tra cứu danh sách các yêu cầu của nhân viên. Có thể giới hạn số lượng kết quả (`limit`) hoặc sử dụng con trỏ phân trang (`cursor`) nếu có dữ liệu hợp lệ.
- `get_staff_request_summary`: Tra cứu số lượng tổng hợp yêu cầu nhân viên, bao gồm yêu cầu đã gửi và yêu cầu chờ duyệt tiếp nhận. Tool này không có tham số.

## Persona & Style

- Ưu tiên P6 `kinh_doanh_chi_nhanh` và P7 `hanh_chinh_don_vi_con` theo `docs/personas_sgod.md`.
- Ngữ cảnh tập trung vào việc tra cứu yêu cầu đổi trạng thái tài sản, đổi vị trí tài sản và xem tổng hợp yêu cầu.
- Sử dụng ngôn ngữ công sở tự nhiên, kết hợp câu lịch sự, ngắn gọn và một số từ viết tắt thông dụng.
- Cho phép lỗi gõ nhẹ và một phần câu không dấu, nhưng câu hỏi phải dễ hiểu.
- Không đưa tên tham số kỹ thuật vào lời nói của người dùng.

## Generation Rules

- Mỗi câu hỏi chỉ có một ý định và tối đa một tool call.
- Chỉ sinh kịch bản `single` cho hai tools này.
- `list_staff_requests` chỉ được sử dụng các tham số `limit` và `cursor`.
- `get_staff_request_summary` phải dùng object tham số rỗng `{}`.
- Chỉ sử dụng `cursor` khi có giá trị hợp lệ từ dữ liệu được cung cấp.
- Không tự tạo tham số `status`, `request_type`, `employee_id` hoặc bộ lọc khác ngoài schema.
- Không tự giả định người dùng có thể lọc yêu cầu theo trạng thái hoặc loại yêu cầu.
- Không tự tạo ID, tên nhân viên hoặc thông tin cá nhân.
- Không sinh yêu cầu tạo, sửa, xóa hoặc duyệt yêu cầu; các yêu cầu ghi thuộc category `permission_denial`.
- Tuân thủ quyền truy cập từ `tools/sgod/roles.json`.
- Không sao chép hoặc paraphrase các câu hỏi trong `data/sgod/eval_human_core.jsonl`.
- Không sinh kịch bản multi-turn hoặc dependent.

## Output Requirements

- Câu hỏi phải thể hiện rõ nhu cầu xem danh sách hoặc xem thống kê.
- Sử dụng tiếng Việt tự nhiên, phù hợp ngữ cảnh SGOD.
- Không tiết lộ API endpoint, tên tham số hoặc cấu trúc JSON trong câu hỏi.
- Chỉ trả về mảng JSON chứa các chuỗi câu hỏi tiếng Việt, không giải thích.
