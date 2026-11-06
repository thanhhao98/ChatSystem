# `label_system.md` — Prompt Hệ Thống Gán Nhãn Công Cụ Và Tham Số

## Mục Đích
Hướng dẫn mô hình gán nhãn trích xuất chính xác công cụ và tham số cho tập câu hỏi SGOD.

## Nguyên Tắc Trích Xuất Tham Số
1. **Tham số chỉ trích xuất từ câu hỏi**: Tuyệt đối không tự suy diễn hoặc bịa đặt giá trị không xuất hiện trong câu truy vấn của người dùng.
2. **Tham số tìm kiếm (`search`)**:
   - Trích xuất từ khóa tìm kiếm tên tài sản, mã tài sản (vd: "máy in Epson", "000000001").
3. **Tham số giới hạn (`limit`)**:
   - Trích xuất khi người dùng yêu cầu số lượng cụ thể ("5 tài sản đầu", "lấy 10 phòng").
4. **Không bịa cursor**: Chỉ ghi nhận cursor khi có ngữ cảnh phân trang tiếp nối.

## Định Dạng Nhãn Đầu Ra
Mỗi câu hỏi sau khi gán nhãn phải xác định:
- `expected_tool`: Tên tool hợp lệ hoặc `null`.
- `expected_params`: Dict các tham số trích xuất được.
- `expected_permission`: `"allowed"` hoặc `"denied"`.
- `expected_tool_alternates`: Mảng các tool thay thế tương đương.
