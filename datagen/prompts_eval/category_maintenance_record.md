# `category_maintenance_record.md` — Prompt Đánh Giá Bản Ghi Bảo Trì Tài Sản

## Tool Mục Tiêu
- **Tool**: `list_maintenance_records`
- **Quyền hạn**: `employee`, `company_admin`
- **Tham số hợp lệ**:
  - `limit` (integer, >= 1): số lượng bản ghi bảo trì tối đa trả về trong một trang.
  - `cursor` (string): con trỏ phân trang từ kết quả trang trước.
- **Lưu ý chống hallucination**: Schema API của tool này chỉ hỗ trợ phân trang (`limit`, `cursor`). KHÔNG hỗ trợ lọc theo trạng thái (`status`), tên tài sản hay loại bảo trì. Tuyệt đối KHÔNG tự bịa các tham số không có trong schema.

## Bối Cảnh Người Dùng (Personas)
- **P4 (`ky_thuat_vien_bao_tri`)**: Tra cứu nhật ký, các biên bản bảo trì và chi phí các lần bảo dưỡng đã thực hiện để đối soát kỹ thuật.
- **P3 (`nhan_vien_van_phong`)**: Hỏi về các lần bảo dưỡng máy in, máy tính văn phòng đã được xử lý xong chưa.
- **P5 (`thu_kho`)**: Kiểm tra biên bản bảo trì các phương tiện nâng hạ, trang thiết bị trong kho bãi.

## Hướng Dẫn Sinh Câu Truy Vấn & Nhãn Chuẩn Hóa
- **100% Single-Turn**: Mỗi truy vấn là 1 lượt hỏi duy nhất, kích hoạt đúng 1 tool call `list_maintenance_records`.
- **Từ viết tắt & Không dấu**: Sử dụng tự nhiên các từ viết tắt công sở (`bb`, `mtri`, `sc`, `tb`, `nv`), 15% - 20% câu không dấu.
- **Quy tắc phân loại Category tất định**:
  - `single_tool`: Tất cả các truy vấn của tool này thuộc category `single_tool` (do tối đa chỉ trích xuất tham số `limit` hoặc không có tham số).
  - TUYỆT ĐỐI KHÔNG dùng category `dependent`.

### Mẫu Câu Hỏi Tham Khảo (Category: `single_tool`)
- "Cho tôi xem danh sách các bản ghi bảo trì tài sản đã thực hiện" -> `{}`
- "danh sach nhat ky bao tri thiet bi cty" -> `{}`
- "Kiểm tra biên bản bảo dưỡng thiết bị gần đây xem có những lần nào" -> `{}`
- "Lấy ra 5 bản ghi bảo trì mới nhất trên hệ thống" -> `limit: 5`
- "cho xem 10 bien ban bao tri gan day nhat" -> `limit: 10`
- "Các lần bảo trì, sửa chữa thiết bị trước đây có ghi nhận biên bản nào không?" -> `{}`
- "xem lich su bao tri sc may moc" -> `{}`
- "Hiển thị 3 bản ghi bảo dưỡng gần nhất để mình rà soát chi phí" -> `limit: 3`
- "xem 5 nhat ky bao duong gan nhat" -> `limit: 5`
