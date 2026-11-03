# Category: permission_denial

Sinh câu hỏi tiếng Việt nhằm kiểm tra khả năng nhận diện và từ chối các yêu cầu không được phép thực hiện trong hệ thống SGOD.

## Objective

Tạo kịch bản từ chối có kiểm soát cho hai nhóm:

1. Người dùng không có quyền truy cập read-only tool.
2. Người dùng yêu cầu thao tác ghi (tạo, sửa, xóa) khi không có write tool được phép sử dụng.

Không được nhầm lẫn hai nhóm này với câu hỏi ngoài phạm vi SGOD.

## Permission Denial Types

### Type A: Unauthorized Read Access

Áp dụng khi tài khoản `employee` yêu cầu dữ liệu từ các tools chỉ dành cho `company_admin`.

Admin-only tools:

- `get_enterprise_profile`
- `get_asset_statistics`
- `list_enterprise_users`
- `list_my_conversations`
- `get_unread_counts`

Expected labeling:

- `category`: `permission_denial`
- `expected_tool`: giữ tên read-only tool đích.
- `expected_permission`: `denied`.
- Không thực hiện tool call.
- Phản hồi từ chối theo quy tắc phân quyền SGOD.

Chỉ sinh trường hợp này khi vai trò thực sự không có quyền theo `tools/sgod/roles.json`.

### Type B: Unsupported Write Requests

Áp dụng cho yêu cầu thực hiện thao tác ghi:

- Tạo tài sản hoặc phiếu mới.
- Sửa thông tin tài sản, vị trí hoặc trạng thái.
- Xóa tài sản, phiếu điều chuyển hoặc yêu cầu.
- Phê duyệt hoặc thay đổi dữ liệu khi cần write operation.

Expected labeling:

- `category`: `permission_denial`
- `expected_tool`: `null`
- Không thực hiện tool call.
- Phản hồi từ chối theo quy tắc `REFUSAL_VI` trong preamble v1.

Không tự tạo write tool hoặc API để xử lý yêu cầu.

## Persona Rules

- Lấy personas duy nhất từ `docs/personas_sgod.md`.
- P1 `giam_doc` và P2 `quan_ly_tai_san` thuộc vai trò `company_admin`.
- P6 `kinh_doanh_chi_nhanh` và P7 `hanh_chinh_don_vi_con` thuộc vai trò `employee`.
- Ưu tiên P6, P7 cho các tình huống employee truy cập admin-only tools.
- Với yêu cầu ghi, áp dụng quy tắc read-only cho mọi persona liên quan.
- Không tự mở rộng hoặc thay đổi quyền truy cập của persona.

## Generation Rules

- Chỉ sinh câu hỏi single-turn.
- Mỗi câu hỏi chỉ có một ý định.
- Không tạo chuỗi hành động phụ thuộc.
- Chỉ sử dụng complexity `single`.
- Không tạo tool call khi yêu cầu bị từ chối.
- Không tự tạo tool, tham số hoặc quyền truy cập.
- Không nhầm câu hỏi đọc hợp lệ thành permission denial.
- Không gán `expected_tool: null` cho unauthorized read khi quy tắc reviewer yêu cầu giữ tool đích.
- Không gán tool đích cho unsupported write request.
- Không sao chép hoặc paraphrase câu hỏi trong `data/sgod/eval_human_core.jsonl`.
- Không sử dụng dữ liệu PII hoặc thông tin nội bộ tự bịa.

## Style Requirements

- Câu hỏi bằng tiếng Việt tự nhiên.
- Sử dụng văn phong công sở, lịch sự hoặc thân mật.
- Có thể sử dụng viết tắt và lỗi gõ nhẹ.
- Một phần câu có thể viết không dấu.
- Không đưa tên API, role key hoặc tool name vào lời nói của người dùng.
- Không tự tuyên bố người dùng có quyền admin nếu persona không có quyền.

## Output Requirements

- Tuân thủ định dạng đầu ra do system prompt và pipeline quy định.
- Đảm bảo câu hỏi được phân loại đúng `permission_denial`.
- Phân biệt rõ unauthorized read và unsupported write.
- Không giải thích ngoài định dạng đầu ra được yêu cầu.
