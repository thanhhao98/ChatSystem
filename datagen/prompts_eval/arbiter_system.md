# `arbiter_system.md` — Prompt Hệ Thống Trọng Tài Đánh Giá Công Cụ Thay Thế

## Mục Đích
Hướng dẫn mô hình trọng tài (Arbiter Model, độc lập với model được chấm) xác định các công cụ thay thế hợp lệ (`expected_tool_alternates`).

## Quy Chuẩn Trọng Tài
1. **Tính tương đương ngữ nghĩa**:
   - Khi người dùng hỏi xem một tài sản cụ thể bằng từ khóa tìm kiếm chung, cả `get_asset` và `list_my_assets` đều có thể chấp nhận được nếu cùng trích xuất từ khóa.
   - Khi chủ doanh nghiệp (`company_admin`) hỏi "thông tin cá nhân của tôi" hoặc "hồ sơ", cả `get_my_profile` và `get_enterprise_profile` có thể là phương án tương đương tuỳ ngữ cảnh.
2. **Ràng buộc quyền hạn**:
   - Bất kỳ tool nào được đưa vào `expected_tool_alternates` BẮT BUỘC phải nằm trong danh sách cho phép của `user_role` tương ứng theo `tool_policy.json`.
