Tra cứu danh sách các bản ghi, nhật ký hoặc biên bản nghiệm thu bảo trì thiết bị đã hoàn tất trong hệ thống (`list_maintenance_records`): xem các lần bảo dưỡng đã thực hiện trong quá khứ, lịch sử sửa chữa hoặc kiểm tra kỹ thuật, có thể kèm theo giới hạn số lượng hiển thị (`limit`).

Hướng dẫn văn phong:
- Thể hiện kỹ thuật viên bảo trì (P4), thủ kho (P5) hoặc người quản lý rà soát hồ sơ bảo dưỡng cơ sở vật chất.
- Đơn lượt (single-turn), 1 tool call, tự nhiên, xưng hô đa dạng (anh/em/tôi/mình), đan xen các từ viết tắt công sở (`bb`, `tb`, `bt`, `nv`, `ql`), có 15-20% câu không dấu.
- Nêu rõ nhu cầu muốn xem lại biên bản nghiệm thu, chi phí hoặc nhật ký hoàn thành bảo dưỡng gần đây.
- Tuyệt đối không sao chép hoặc paraphrase từ tập đánh giá `eval_human_core.jsonl`.

Trả về mảng JSON các chuỗi câu hỏi tiếng Việt.
