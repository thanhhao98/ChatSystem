# `category_my_assets.md` — Prompt Danh Mục Tài Sản Của Tôi (`list_my_assets`)

## Tool Mục Tiêu
- **Tool**: `list_my_assets`
- **Quyền hạn**: `employee`, `company_admin`
- **Tham số**:
  - `search` (string): từ khóa tìm theo tên hoặc mã tài sản.
  - `limit` (integer): số lượng bản ghi hiển thị.
  - `cursor` (string): con trỏ phân trang.

## Hướng Dẫn Sinh Câu Hỏi
- Câu hỏi về danh sách tài sản cá nhân được bàn giao hoặc tài sản công ty quản lý.
- Tự nhiên, ngắn gọn, có câu không dấu ("tai san cua toi", "cac may moc dang giu").
- Kịch bản multi_constraint: kết hợp tìm kiếm theo tên và giới hạn số lượng (vd: "tìm 5 máy tính Dell").
