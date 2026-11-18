Tra cứu và quản lý lịch bảo trì máy móc, thiết bị trong hệ thống (`list_maintenance_schedules`, `get_maintenance_schedule`):
- Khi tra cứu danh sách: xem danh sách lịch bảo dưỡng định kỳ đang hiệu lực (`active`) hoặc đã hoàn thành (`completed`), có thể kết hợp giới hạn số lượng (`limit`) để tạo kịch bản lọc đa điều kiện (`multi_constraint` ≥ 2 filters).
- Khi tra cứu MỘT lịch bảo trì cụ thể: người dùng hỏi chi tiết kế hoạch, ngày thực hiện, thời hạn, thông số của 1 lịch bảo trì khi có mã định danh cụ thể (ví dụ: `6ad615353b0f8e12e2f1910d`, `6ad615353b0f8e12e2f190e4`, `sch-2026-001`). Cần hỏi trực tiếp vào mã lịch bảo trì đó.

Hướng dẫn văn phong:
- Thể hiện các vai trò kỹ thuật viên bảo trì (P4), nhân viên văn phòng (P3) hoặc quản lý tài sản kiểm tra kế hoạch kỹ thuật.
- Đơn lượt (single-turn), 1 tool call, tự nhiên, sử dụng các từ viết tắt công sở phổ biến (`tb`, `bt`, `nv`, `ql`, `cty`), có 15-20% câu không dấu kiểu gõ nhanh trên điện thoại.
- Với câu hỏi chi tiết MỘT lịch, nêu rõ mã lịch cụ thể và hỏi hạn chót, chi tiết kế hoạch bảo trì. Tuyệt đối không chứa tiền tố `[SEED]`.
- Tuyệt đối không sao chép hoặc paraphrase từ tập đánh giá `eval_human_core.jsonl`.

Trả về mảng JSON các chuỗi câu hỏi tiếng Việt.
