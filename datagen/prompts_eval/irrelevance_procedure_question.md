# irrelevance_procedure_question.md — Kịch bản câu hỏi quy trình SGOD

## 1. Mục tiêu

Sinh các câu hỏi tiếng Việt tự nhiên về quy trình, hướng dẫn và chính sách nghiệp vụ mà bộ công cụ SGOD hiện tại không hỗ trợ tra cứu trực tiếp.

Đây là nhóm Procedure Question thuộc bộ Irrelevance của Task D-V4.

Tỷ trọng mục tiêu: 20% trong tập Irrelevance, không phải 20% toàn bộ eval_v1.

## 2. Phạm vi nghiệp vụ

### 2.1. Quy trình quản lý tài sản

Các câu hỏi về:
- Các bước đăng ký cấp phát thiết bị.
- Hướng dẫn bàn giao hoặc thu hồi tài sản.
- Trình tự xử lý tài sản bị thất lạc.
- Quy định kiểm kê hoặc quản lý tài sản.

Không nhầm lẫn với yêu cầu xem danh sách hoặc chi tiết tài sản.

### 2.2. Quy trình điều chuyển tài sản

Các câu hỏi về:
- Trình tự đề xuất điều chuyển.
- Các bước xét duyệt điều chuyển.
- Trách nhiệm của các bên liên quan.
- Quy trình bàn giao sau khi được phê duyệt.

Không nhầm với việc tra cứu phiếu điều chuyển hiện có bằng list_asset_transfers hoặc get_asset_transfer.

### 2.3. Quy trình bảo trì thiết bị

Các câu hỏi về:
- Cách đăng ký bảo trì.
- Trình tự báo hỏng thiết bị.
- Quy trình xác nhận sửa chữa.
- Cách xử lý thiết bị hỏng ngoài lịch.

Không nhầm với truy vấn lịch bảo trì, hồ sơ bảo trì hoặc nhiệm vụ bảo trì hiện có.

### 2.4. Quy trình yêu cầu nhân viên

Các câu hỏi về:
- Cách gửi yêu cầu nội bộ.
- Các bước xử lý yêu cầu.
- Quy trình phê duyệt yêu cầu.
- Trách nhiệm xử lý yêu cầu của các bộ phận.

Không nhầm với việc truy vấn danh sách hoặc thông tin tổng hợp yêu cầu nhân viên.

### 2.5. Chính sách và quy định nội bộ

Các câu hỏi về:
- Quy định sử dụng thiết bị công ty.
- Chính sách bàn giao tài sản.
- Quy trình xử lý vi phạm.
- Thẩm quyền phê duyệt nghiệp vụ.

Không tự tạo chính sách hoặc khẳng định một quy định chưa được xác minh.

## 3. Phân biệt câu hỏi quy trình và truy vấn dữ liệu

### Câu hỏi quy trình

Người dùng muốn biết cách thực hiện, các bước cần làm, trách nhiệm hoặc quy định của một hoạt động.

Chỉ đưa vào nhóm này khi không có công cụ phù hợp để cung cấp thông tin được hỏi.

### Truy vấn dữ liệu

Người dùng muốn kiểm tra thông tin thực tế hiện có trong hệ thống.

Nếu danh mục 22 tools có công cụ đáp ứng trực tiếp thì không được đưa vào nhóm Procedure Question.

### Yêu cầu thực hiện hành động

Người dùng muốn hệ thống trực tiếp tạo, sửa, xóa hoặc phê duyệt dữ liệu.

Đây là Unsupported Actions nếu không có công cụ hỗ trợ, không phải câu hỏi tìm hiểu quy trình.

## 4. Quy tắc gán nhãn

Khi xác nhận không có công cụ SGOD hỗ trợ truy vấn quy trình:

- category: out_of_scope
- expected_tool: null
- expected_permission: allowed
- expected_params: {}

Không tạo tool giả để tra cứu chính sách hoặc hướng dẫn nội bộ.

Không dùng permission_denial chỉ vì hệ thống không có công cụ đọc quy trình.

Không dùng category dependent.

## 5. Quy chuẩn sinh câu hỏi

- 100% single-turn.
- Mỗi câu tập trung vào một quy trình hoặc quy định.
- Khoảng 15–20% câu tiếng Việt không dấu.
- Văn phong tự nhiên trong môi trường doanh nghiệp.
- Đa dạng cách hỏi và mức độ trang trọng.
- Có thể sử dụng cách diễn đạt của nhân viên, thủ kho hoặc quản trị viên.
- Không đưa tên API, tool hoặc tham số kỹ thuật vào câu hỏi.
- Không sao chép câu hỏi từ dataset hiện có.
- Không chứa thông tin cá nhân thật hoặc dữ liệu nhạy cảm.
- Không tự tạo nội dung chính sách SGOD trong prompt.

## 6. Giới hạn nội dung

Không yêu cầu mô hình sinh câu trả lời hoặc tài liệu chính sách giả định.

Chỉ sinh câu hỏi để đánh giá Function Calling.

Không đưa vào nhóm này các yêu cầu:
- Tra cứu danh sách tài sản.
- Kiểm tra lịch bảo trì hiện có.
- Xem chi tiết phiếu điều chuyển.
- Xem danh sách yêu cầu nhân viên.
- Xem quyền hạn tài khoản.
- Xem số lượng cuộc hội thoại chưa đọc.

Những yêu cầu trên có công cụ đọc tương ứng trong SGOD.

Không phân loại sai các yêu cầu có thể thực hiện chỉ để đạt tỷ trọng 20%.

## 7. Kiểm soát chất lượng

Với từng câu:

1. Đây có phải câu hỏi về quy trình hoặc chính sách không?
2. Người dùng đang hỏi cách làm hay yêu cầu thực thi hành động?
3. Có tool nào thực sự trả lời được yêu cầu không?
4. Nội dung có giả định chính sách chưa xác minh không?
5. expected_tool: null có phù hợp không?
6. Câu hỏi có độc lập, tự nhiên và không trùng lặp không?

Loại bỏ những câu có thể ánh xạ trực tiếp tới một công cụ SGOD hợp lệ.

## 8. Tích hợp

Prompt điều phối:
- irrelevance_system.md

Prompt tổng hợp:
- category_out_of_scope.md

File này là đặc tả chuyên biệt.

Pipeline hiện chưa tự động nạp file này. Việc sử dụng trong quá trình generate phải được tích hợp và xác minh.

Không tự thay đổi BUCKET_PLAN, schema hoặc phân quyền.
