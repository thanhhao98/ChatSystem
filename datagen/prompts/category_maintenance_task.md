Tra cứu danh sách các công việc (task bảo trì) thuộc về một lịch bảo trì cụ thể (`list_maintenance_tasks`): xem người thực hiện, thời hạn và trạng thái xử lý các đầu việc.

Lưu ý quan trọng về schema:
- Schema OpenAPI và API thực tế BẮT BUỘC phải cung cấp tham số `maintenanceScheduleId` (mã định danh lịch bảo trì, ví dụ: `6ad615353b0f8e12e2f1910d`, `6ad615353b0f8e12e2f190e4`), có thể kèm theo giới hạn số lượng (`limit`).
- API không hỗ trợ lọc trạng thái task qua query param, chỉ hỗ trợ phân trang (`limit`, `cursor`).

Hướng dẫn văn phong:
- Thể hiện kỹ thuật viên bảo trì (P4) tra cứu nhanh trên điện thoại tại hiện trường hoặc quản lý tài sản theo dõi tiến độ công việc.
- Đơn lượt (single-turn), 1 tool call, tự nhiên, sử dụng từ vựng kỹ thuật (`task`, `cv`, `done`, `pending`), viết tắt (`tb`, `bt`, `ql`), có 15-20% câu không dấu.
- Người hỏi luôn nêu kèm mã lịch bảo trì thật được cấp từ hệ thống để làm căn cứ tra cứu đầu việc. Tuyệt đối không chứa tiền tố `[SEED]`.
- Tuyệt đối không sao chép hoặc paraphrase từ tập đánh giá `eval_human_core.jsonl`.

Trả về mảng JSON các chuỗi câu hỏi tiếng Việt.
