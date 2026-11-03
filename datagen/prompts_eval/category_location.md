# `category_location.md` — Prompt Vị Trí & Phòng Ban Doanh Nghiệp

## Tool Mục Tiêu
1. **`list_locations`**:
   - **Quyền hạn**: `employee`, `company_admin`
   - **Tham số**: `limit` (integer), `cursor` (string).
   - **Câu hỏi**: "danh sách các phòng ban", "xem các kho hàng hiện có", "cac chi nhanh cong ty".
2. **`get_location`**:
   - **Quyền hạn**: `employee`, `company_admin`
   - **Tham số bắt buộc**: `location_ref` (string).
   - **Câu hỏi**: "chi tiết phòng họp tầng 3", "thông tin kho A1", "dia chi van phong quan 1".
