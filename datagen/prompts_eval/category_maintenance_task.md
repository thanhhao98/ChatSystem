# `category_maintenance_task.md` — Prompt Đánh Giá Công Việc Của Lịch Bảo Trì

## Tool Mục Tiêu
- **Tool**: `list_maintenance_tasks`
- **Quyền hạn**: `employee`, `company_admin`
- **Tham số hợp lệ**:
  - `maintenanceScheduleId` (string, **BẮT BUỘC**): Mã ID định danh của lịch bảo trì cần liệt kê các đầu việc/nhiệm vụ.
  - `limit` (integer, >= 1): số lượng công việc tối đa trả về trong một trang.
  - `cursor` (string): con trỏ phân trang từ kết quả trang trước.
- **Lưu ý chống hallucination**: Tham số `maintenanceScheduleId` là bắt buộc. Phải trích xuất đúng chuỗi ID lịch bảo trì từ câu hỏi người dùng. Không được tự bịa các trường `status`, `assignedTo`, `title`.

## Bối Cảnh Người Dùng (Personas)
- **P4 (`ky_thuat_vien_bao_tri`)**: Kỹ thuật viên hiện trường xem các hạng mục công việc cụ thể của một đợt bảo trì (người thực hiện, hạn hoàn thành, tiến độ các việc như thay drum mực, bảo dưỡng cục lạnh). Văn phong gọn, xưng hô đồng nghiệp, gõ mã ID trực tiếp.
- **P3 (`nhan_vien_van_phong`)**: Tra cứu tiến độ xử lý công việc bảo trì máy móc văn phòng theo mã lịch được thông báo.
- **P5 (`thu_kho`)**: Đối soát các hạng mục công việc bảo dưỡng của thiết bị nâng hạ theo mã lịch.

## Hướng Dẫn Sinh Câu Truy Vấn & Nhãn Chuẩn Hóa
- **100% Single-Turn**: Mỗi truy vấn kích hoạt đúng 1 tool call `list_maintenance_tasks`.
- **Từ viết tắt & Không dấu**: Sử dụng tự nhiên các từ viết tắt (`cv`, `task`, `mtri`, `lich bt`, `tb`), 15% - 20% câu không dấu.
- **Quy tắc phân loại Category tất định**:
  - `single_tool`: Khi câu hỏi chỉ truyền tham số bắt buộc `maintenanceScheduleId`.
  - `multi_constraint`: Khi câu hỏi kết hợp `maintenanceScheduleId` VÀ giới hạn số lượng `limit` (>= 2 tham số).
  - TUYỆT ĐỐI KHÔNG dùng category `dependent`.

### Mẫu Câu Hỏi Tham Khảo

#### 1. Kịch bản `single_tool` (chỉ có `maintenanceScheduleId`)
- "Xem danh sách các công việc trong lịch bảo trì 6ad615353b0f8e12e2f1910d" -> `maintenanceScheduleId: "6ad615353b0f8e12e2f1910d"`
- "cac cong viec cua lich mtri 6ad615353b0f8e12e2f190e4 la gi" -> `maintenanceScheduleId: "6ad615353b0f8e12e2f190e4"`
- "Lịch bảo trì 6ad615353b0f8e12e2f1910d hiện có những task nào cần thực hiện vậy?" -> `maintenanceScheduleId: "6ad615353b0f8e12e2f1910d"`
- "task cua lich 6ad615353b0f8e12e2f190e4" -> `maintenanceScheduleId: "6ad615353b0f8e12e2f190e4"`
- "Kiểm tra các hạng mục bảo dưỡng thuộc lịch 6ad615353b0f8e12e2f1910d giúp mình" -> `maintenanceScheduleId: "6ad615353b0f8e12e2f1910d"`
- "xem cv cua lich bt 6ad615353b0f8e12e2f190e4" -> `maintenanceScheduleId: "6ad615353b0f8e12e2f190e4"`

#### 2. Kịch bản `multi_constraint` (`maintenanceScheduleId` + `limit`)
- "Liệt kê 5 công việc đầu tiên của lịch bảo trì 6ad615353b0f8e12e2f1910d" -> `maintenanceScheduleId: "6ad615353b0f8e12e2f1910d"`, `limit: 5`
- "lay 3 task dau tien cua lich 6ad615353b0f8e12e2f190e4" -> `maintenanceScheduleId: "6ad615353b0f8e12e2f190e4"`, `limit: 3`
- "Cho xem tối đa 4 công việc cần làm trong lịch bảo dưỡng 6ad615353b0f8e12e2f1910d" -> `maintenanceScheduleId: "6ad615353b0f8e12e2f1910d"`, `limit: 4`
- "xem 5 cv cua lich mtri 6ad615353b0f8e12e2f190e4" -> `maintenanceScheduleId: "6ad615353b0f8e12e2f190e4"`, `limit: 5`
