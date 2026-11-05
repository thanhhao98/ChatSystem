# irrelevance_ambiguous.md — Kịch bản yêu cầu mơ hồ SGOD

## 1. Mục tiêu

Sinh các phát ngôn tiếng Việt tự nhiên nhằm đánh giá khả năng nhận diện yêu cầu không đủ rõ ràng để xác định một công cụ SGOD phù hợp.

Đây là nhóm Ambiguous thuộc bộ Irrelevance của Task D-V4.

Tỷ trọng mục tiêu: 20% trong tập Irrelevance, không phải 20% toàn bộ eval_v1.

## 2. Phạm vi

### 2.1. Ý định không xác định

Người dùng đưa ra yêu cầu quá chung chung, không nêu rõ nghiệp vụ hoặc loại dữ liệu muốn truy vấn.

Không tự suy đoán người dùng muốn xem tài sản, bảo trì, điều chuyển hay nhân sự.

### 2.2. Đối tượng truy vấn không rõ

Phát ngôn không xác định được đối tượng nghiệp vụ cần xử lý và không đủ căn cứ để lựa chọn một công cụ.

Không tự tạo tên tài sản, mã phiếu, định danh hoặc thông tin bổ sung.

### 2.3. Nhiều cách diễn giải

Một phát ngôn có thể được hiểu theo nhiều nghiệp vụ khác nhau nhưng không có dấu hiệu đủ mạnh để chọn duy nhất một tool.

Không lựa chọn ngẫu nhiên một công cụ chỉ để tạo nhãn.

### 2.4. Thiếu ngữ cảnh nghiệp vụ

Câu hỏi không mang đủ thông tin để nhận diện ý định độc lập.

Chỉ sử dụng phát ngôn single-turn. Không tạo câu cố tình tham chiếu lượt hội thoại trước như một dạng multi-turn.

## 3. Phân biệt câu mơ hồ và câu thiếu tham số

Hai tình huống không hoàn toàn giống nhau.

Nếu người dùng muốn xem chi tiết phiếu điều chuyển nhưng thiếu transfer_id:
- Ý định nghiệp vụ vẫn có thể rõ ràng.
- Công cụ get_asset_transfer tồn tại.
- Không tự động phân loại thành out_of_scope.
- Không tự tạo transfer_id.
- Chỉ gán nhãn khi hợp đồng đánh giá quy định rõ cách xử lý yêu cầu thiếu tham số bắt buộc.

Nếu không thể nhận diện một yêu cầu nghiệp vụ có thể ánh xạ đến công cụ:
- Có thể xem xét nhóm Ambiguous.
- Không ép gán nhãn khi chưa có căn cứ đầy đủ.

Các trường hợp không xác định được nhãn chính xác phải được loại khỏi tập eval hoặc chuyển sang bước review.

## 4. Quy tắc gán nhãn

Chỉ chấp nhận vào nhóm out_of_scope những phát ngôn được xác nhận không tạo thành một yêu cầu gọi tool hợp lệ theo Contract 2.

Khi được xác nhận là out_of_scope:

- category: out_of_scope
- expected_tool: null
- expected_permission: allowed
- expected_params: {}

Không dùng expected_tool: null đơn thuần vì thiếu một tham số của công cụ đã xác định.

Không sử dụng category dependent.

Không gán permission_denial nếu chưa xác định được công cụ thực sự bị chặn quyền.

## 5. Quy chuẩn sinh câu hỏi

- 100% single-turn.
- Mỗi câu là một phát ngôn độc lập.
- Khoảng 15–20% câu tiếng Việt không dấu.
- Văn phong tự nhiên, giống giao tiếp công sở thực tế.
- Đa dạng độ dài và cách diễn đạt.
- Không dùng thuật ngữ backend hoặc tên tham số API.
- Không tự thêm dữ liệu để làm rõ ý định.
- Không sử dụng dữ liệu nhạy cảm hoặc định danh thật.
- Không sao chép câu hỏi từ dataset hiện có.
- Không tạo câu vô nghĩa hoặc ngẫu nhiên chỉ để đủ số lượng.

## 6. Phân biệt với nhóm khác

### Ambiguous và Chitchat

Chitchat có ý định giao tiếp xã giao rõ ràng.

Ambiguous thiếu thông tin để xác định ý định truy vấn cụ thể.

### Ambiguous và Unsupported Actions

Unsupported Actions là yêu cầu rõ ràng nhưng không có tool hỗ trợ.

Ambiguous là trường hợp chưa xác định được một ý định nghiệp vụ đủ rõ.

### Ambiguous và Permission Denial

Permission Denial yêu cầu xác định được công cụ tồn tại và role không có quyền gọi.

Không gán denied nếu chưa xác định được công cụ.

### Ambiguous và truy vấn hợp lệ

Câu ngắn, viết tắt hoặc không dấu không đồng nghĩa với mơ hồ.

Nếu ý định và tham số hợp lệ có thể xác định đáng tin cậy, phải ưu tiên công cụ phù hợp.

## 7. Kiểm soát chất lượng

Với từng câu:

1. Có thực sự không xác định được ý định không?
2. Có một tool phù hợp rõ ràng không?
3. Có chỉ đơn thuần thiếu tham số bắt buộc không?
4. Có phụ thuộc hội thoại trước không?
5. Nhãn out_of_scope có phù hợp Contract 2 không?
6. Có đang cố tạo câu mơ hồ để đạt tỷ lệ không?

Loại khỏi tập đánh giá mọi trường hợp có nhãn không thể thống nhất.

## 8. Tích hợp

Prompt điều phối:
- irrelevance_system.md

Prompt tổng hợp:
- category_out_of_scope.md

File này là đặc tả chuyên biệt. Pipeline hiện chưa tự động nạp các file irrelevance_*.

Không thay đổi BUCKET_PLAN hoặc logic phân quyền tại đây.
