# `category_asset_detail.md` — Prompt Chi Tiết Tài Sản & Lịch Sử Biến Động

## Tool Mục Tiêu
1. **`get_asset`**:
   - **Quyền hạn**: `employee`, `company_admin`
   - **Tham số bắt buộc**: `asset_ref` (string - tên, mã tài sản hoặc ID).
   - **Alternates**: `list_my_assets` (khi tìm kiếm dạng lỏng lẻo).

2. **`get_asset_histories`**:
   - **Quyền hạn**: `employee`, `company_admin`
   - **Tham số bắt buộc**: `asset_ref` (string).
   - **Ngữ cảnh**: Hỏi về vòng đời, lịch sử luân chuyển, bàn giao của thiết bị.

## Hướng Dẫn Sinh Câu Hỏi
- Câu hỏi chi tiết: "xem thông số kỹ thuật laptop macbook pro", "thông tin chi tiết mã 000000001".
- Câu hỏi lịch sử: "máy photocopy tầng 2 trước đây ai dùng", "lịch sử bàn giao thiết bị TS-092".
