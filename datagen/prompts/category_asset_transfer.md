# Category: asset_transfer

Sinh câu hỏi tiếng Việt về việc tra cứu phiếu chuyển giao tài sản trên SGOD.

## Tool Selection

- `list_asset_transfers`: Tra cứu danh sách các phiếu chuyển giao. Có thể yêu cầu chỉ xem phiếu của mình (`onlyMine: true`) và giới hạn số lượng (`limit`). Chỉ dùng khi người dùng muốn xem danh sách nhiều phiếu.
- `get_asset_transfer`: Xem thông tin chi tiết của DUY NHẤT MỘT phiếu khi người dùng cung cấp mã phiếu cụ thể (ví dụ `TRF-2026-001`, `6ad61535...`).
- `get_transfer_summary`: Hỏi số lượng tổng hợp, thống kê đếm tổng số phiếu: "có bao nhiêu phiếu chuyển giao", "tổng số phiếu chờ nhận", "tổng số phiếu đã gửi", "tình hình tổng hợp điều chuyển". Tool này không có tham số.

## Persona & Style

- Ưu tiên P6 `kinh_doanh_chi_nhanh` khi hỏi danh sách phiếu của mình hoặc số phiếu chờ nhận.
- Với kịch bản tra cứu chi tiết phiếu hoặc xem tổng hợp phiếu, có thể sử dụng persona quản lý tài sản P2 hoặc thủ kho P5 theo ma trận nhu cầu.
- Văn phong tự nhiên, trộn lịch sự và thân mật, có viết tắt công sở, lỗi gõ nhẹ, một phần câu không dấu.

## Generation Rules

- Một câu hỏi chỉ có một ý định và tối đa một tool call.
- Chỉ dùng `single` hoặc `multi_constraint`.
- `multi_constraint` chỉ áp dụng cho `list_asset_transfers` khi kết hợp `onlyMine` và `limit`.
- Chỉ dùng ID phiếu tồn tại trong `fixtures/sgod/asset/GET_asset_transfers.json`.
- Không tự tạo ID, tham số, trạng thái hoặc bộ lọc ngoài schema.
- Không sinh yêu cầu tạo, sửa, xóa hoặc phê duyệt phiếu trong category này; các yêu cầu ghi thuộc `permission_denial`.
- Không sao chép hoặc paraphrase tập `eval_human_core.jsonl`.
- Không để lộ PII hoặc tên tham số kỹ thuật trong câu hỏi được sinh.

Chỉ trả về mảng JSON gồm các chuỗi câu hỏi tiếng Việt, không giải thích.
