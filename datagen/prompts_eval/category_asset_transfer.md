# category_asset_transfer.md — Đánh giá truy vấn điều chuyển tài sản

## 1. Mục tiêu

Sinh các câu hỏi tiếng Việt tự nhiên để đánh giá khả năng chọn đúng công cụ tra cứu điều chuyển tài sản trong SGOD.

Mỗi câu hỏi phải độc lập (single-turn), có ý định rõ ràng và chỉ cần tối đa một tool call.

## 2. Danh sách công cụ

### list_asset_transfers

Mục đích: Tra cứu danh sách các lượt điều chuyển tài sản.

Roles được phép:

- employee
- company_admin

Tham số hợp lệ:

- onlyMine: boolean, tùy chọn.
- limit: integer, tùy chọn.
- cursor: string, tùy chọn.

Quy tắc:

- Khi yêu cầu chỉ xem điều chuyển của bản thân, dùng onlyMine=true.
- Khi yêu cầu số lượng kết quả cụ thể, dùng limit.
- Không tự tạo cursor khi người dùng chưa cung cấp giá trị.
- Không suy đoán quyền xem dữ liệu ngoài phạm vi JWT.
- Không tự thêm bộ lọc trạng thái, ngày tháng, nhân viên hoặc tài sản.

### get_asset_transfer

Mục đích: Xem chi tiết một lượt điều chuyển tài sản.

Roles được phép:

- employee
- company_admin

Tham số bắt buộc:

- transfer_id: string.

Quy tắc:

- Chỉ sử dụng khi câu hỏi chứa mã định danh điều chuyển đủ rõ.
- Mã phải lấy từ fixture hợp lệ hoặc nguồn định danh được phê duyệt.
- Không tự tạo ID ngẫu nhiên.
- Không sử dụng tên tài sản hoặc tên nhân viên thay cho transfer_id.
- Không yêu cầu tạo, sửa hoặc phê duyệt điều chuyển.

### get_transfer_summary

Mục đích: Lấy thông tin tổng hợp về điều chuyển tài sản.

Roles được phép:

- employee
- company_admin

Tham số: Không có.

Quy tắc:

- Sử dụng cho yêu cầu tổng hợp, thống kê chung.
- expected_params phải là {}.
- Không sinh yêu cầu lọc theo thời gian, phòng ban hoặc trạng thái mà API không hỗ trợ.
- Không giả định dữ liệu trả về là thống kê toàn doanh nghiệp đối với mọi role.

## 3. Ngữ cảnh và personas

Ưu tiên các tình huống thực tế:

- Nhân viên văn phòng kiểm tra việc bàn giao hoặc điều chuyển thiết bị của mình.
- Thủ kho tra cứu danh sách điều chuyển phục vụ theo dõi tài sản.
- Quản trị viên doanh nghiệp tra cứu danh sách và tổng hợp điều chuyển.

Sử dụng ngôn ngữ công sở tự nhiên, không bắt buộc câu hỏi phải có thuật ngữ kỹ thuật.

## 4. Nguyên tắc sinh câu hỏi

- 100% single-turn.
- Khoảng 15–20% câu tiếng Việt không dấu.
- Đa dạng độ dài, văn phong và cách diễn đạt.
- Phân biệt rõ ý định xem danh sách, xem chi tiết và xem tổng hợp.
- Không sử dụng câu hỏi phụ thuộc hội thoại trước.
- Không chèn tên tham số API hoặc thuật ngữ backend vào lời người dùng.
- Không sao chép câu hỏi từ bất kỳ dataset có sẵn nào.
- Không sử dụng dữ liệu nhạy cảm, JWT, API key hoặc thông tin thật của người dùng.

## 5. Quy tắc nhãn

### single_tool

Áp dụng khi:

- expected_permission là allowed.
- expected_tool không null.
- Có 0 hoặc 1 tham số trong expected_params.

### multi_constraint

Áp dụng khi:

- expected_permission là allowed.
- expected_tool không null.
- Có ít nhất 2 tham số hợp lệ trong expected_params.

Đối với list_asset_transfers, ưu tiên tổ hợp onlyMine và limit để tạo truy vấn nhiều ràng buộc.

### Loại trừ

- Không dùng category dependent.
- Không tạo tool call có tham số ngoài schema.
- Không gán permission_denial chỉ vì suy đoán phạm vi dữ liệu.
- Không dùng get_asset_transfer nếu không có transfer_id hợp lệ.
- Các tình huống ngoài phạm vi hoặc yêu cầu ghi được xử lý bằng prompt âm tính riêng.

## 6. Kiểm soát chất lượng

Với mỗi câu sinh ra, kiểm tra:

1. Ý định truy vấn có tương ứng đúng một tool không?
2. Tất cả tham số có hợp lệ theo schema không?
3. Tham số có được suy ra trực tiếp từ câu hỏi không?
4. Vai trò người dùng có được gọi tool không?
5. Category có phù hợp với số tham số không?
6. Câu hỏi có độc lập, tự nhiên và không trùng dữ liệu hiện có không?

Không tạo hoặc sửa dữ liệu doanh nghiệp. Chỉ sinh câu hỏi đánh giá cho các API đọc.
