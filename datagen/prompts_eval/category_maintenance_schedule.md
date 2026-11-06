# `category_maintenance_schedule.md` — Prompt Đánh Giá Lịch Bảo Trì Thiết Bị

## Tool Mục Tiêu
1. **`list_maintenance_schedules`**:
   - **Quyền hạn**: `employee`, `company_admin`
   - **Tham số hợp lệ**:
     - `status` (string, enum: ["active", "completed"]): `active` = lịch đang hiệu lực/sắp thực hiện, `completed` = đã hoàn thành.
     - `limit` (integer, >= 1): số lượng lịch bảo trì tối đa trả về trong trang.
     - `cursor` (string): con trỏ phân trang từ kết quả trước.
   - **Lưu ý chống hallucination**: Schema API KHÔNG hỗ trợ lọc theo mã tài sản, tên thiết bị hay khoảng thời gian ngày tháng. Tuyệt đối không tự bịa các tham số `asset_id`, `startDate`, `endDate`.

2. **`get_maintenance_schedule`**:
   - **Quyền hạn**: `employee`, `company_admin`
   - **Tham số bắt buộc**:
     - `schedule_id` (string): Mã ID định danh của lịch bảo trì cần tra cứu chi tiết.
   - **Lưu ý**: Chỉ dùng khi câu truy vấn chứa trực tiếp mã ID lịch bảo trì (chuỗi hex/id định danh rõ ràng).

## Bối Cảnh Người Dùng (Personas)
- **P4 (`ky_thuat_vien_bao_tri`)**: Kỹ thuật viên bảo trì tra cứu tại hiện trường. Giọng thực tế, ngắn gọn, hay viết tắt (`bt`, `mtri`, `tb`, `sc`), chen từ hệ thống (`active`, `completed`).
- **P3 (`nhan_vien_van_phong`)**: Nhân viên theo dõi thiết bị văn phòng, lịch bảo dưỡng máy in, máy lạnh phòng ban.
- **P5 (`thu_kho`)**: Thủ kho theo dõi lịch bảo dưỡng máy móc, thiết bị kho bãi.

## Hướng Dẫn Sinh Câu Truy Vấn & Nhãn Chuẩn Hóa
- **100% Single-Turn**: Mỗi truy vấn độc lập, kích hoạt đúng 1 tool call.
- **Từ viết tắt & Không dấu**: Đan xen tự nhiên (`tb`, `mtri`, `sc`, `lich bt`), 15% - 20% câu không dấu.
- **Quy tắc phân loại Category tất định**:
  - `single_tool`: Truy vấn gọi tool với 0 hoặc 1 tham số (ví dụ: chỉ tra theo `status`, chỉ tra theo `limit`, hoặc chỉ tra `schedule_id`).
  - `multi_constraint`: Truy vấn kết hợp từ 2 tham số trở lên (ví dụ: `status` + `limit`).
  - TUYỆT ĐỐI KHÔNG dùng category `dependent`.

### Mẫu Câu Hỏi Tham Khảo

#### 1. Kịch bản `list_maintenance_schedules` (Category: `single_tool`)
- "Kiểm tra xem hiện có những lịch bảo trì nào đang active vậy?" -> `status: "active"`
- "Cho em xem danh sách các đợt bảo dưỡng thiết bị đã hoàn thành trong hệ thống" -> `status: "completed"`
- "danh sach lich bao tri dang hieu luc" -> `status: "active"`
- "xem giup toi 5 lich bao tri gan nhat" -> `limit: 5`
- "kiem tra lich mtri thiet bi sap toi" -> `status: "active"`
- "Có những lịch bảo trì nào đã completed rồi?" -> `status: "completed"`
- "hien thi danh sach lich bao duong may moc" -> `{}`

#### 2. Kịch bản `list_maintenance_schedules` (Category: `multi_constraint`)
- "Lấy ra 5 lịch bảo trì đang có hiệu lực active giúp tôi" -> `status: "active"`, `limit: 5`
- "cho xem 3 lich bao tri da hoan thanh completed" -> `status: "completed"`, `limit: 3`
- "lấy 10 lịch mtri đang chạy active để kiểm tra" -> `status: "active"`, `limit: 10`
- "lay giup 5 lich bt completed" -> `status: "completed"`, `limit: 5`

#### 3. Kịch bản `get_maintenance_schedule` (Category: `single_tool`)
- "Chi tiết lịch bảo trì mã 6ad615353b0f8e12e2f1910d xem thế nào em" -> `schedule_id: "6ad615353b0f8e12e2f1910d"`
- "xem thong tin lich mtri 6ad615353b0f8e12e2f190e4" -> `schedule_id: "6ad615353b0f8e12e2f190e4"`
- "Mở thông tin chi tiết lịch bảo dưỡng 6ad615353b0f8e12e2f1910d giúp mình" -> `schedule_id: "6ad615353b0f8e12e2f1910d"`
- "chi tiet lich bt ma 6ad615353b0f8e12e2f190e4" -> `schedule_id: "6ad615353b0f8e12e2f190e4"`
