# Irrelevance: procedure_question

Sinh các câu hỏi tiếng Việt về cách sử dụng, hướng dẫn thao tác và quy trình nghiệp vụ trong hệ thống SGOD mà không yêu cầu hệ thống thực hiện hành động trực tiếp.

## Objective

Tạo dữ liệu câu hỏi hướng dẫn (procedure questions) để huấn luyện trợ lý phân biệt giữa việc hỏi cách thực hiện và yêu cầu thực hiện nghiệp vụ.

Các câu hỏi thuộc loại này không cần gọi SGOD read-only tools.

## Supported Topics

Đa dạng hóa câu hỏi hướng dẫn trong các nghiệp vụ SGOD:

- Cách tra cứu danh sách và thông tin tài sản.
- Quy trình tạo hoặc gửi phiếu điều chuyển tài sản.
- Cách kiểm tra hoặc theo dõi trạng thái phiếu điều chuyển.
- Quy trình báo hỏng hoặc yêu cầu bảo trì tài sản.
- Cách gửi yêu cầu thay đổi trạng thái hoặc vị trí tài sản.
- Hướng dẫn xem hồ sơ và lịch sử bảo trì.
- Cách sử dụng các chức năng quản lý tài sản.
- Quy trình xử lý và phê duyệt yêu cầu trong hệ thống.

Chỉ sinh câu hỏi về quy trình, không yêu cầu hệ thống thực hiện thao tác.

## Question Classification

### Valid Procedure Questions

- Người dùng hỏi "Làm thế nào", "Cách nào", "Quy trình ra sao" hoặc "Hướng dẫn tôi".
- Ý định là tìm hiểu các bước thực hiện nghiệp vụ.
- Không yêu cầu truy xuất dữ liệu cụ thể.
- Không yêu cầu thực hiện thao tác ghi ngay lập tức.

### Not Procedure Questions

- Yêu cầu xem danh sách hoặc chi tiết dữ liệu: thuộc nhóm SGOD read-only tool phù hợp.
- Yêu cầu tạo, sửa, xóa hoặc phê duyệt dữ liệu: thuộc `permission_denial`.
- Câu hỏi không rõ ý định: thuộc `ambiguous`.
- Câu hỏi hoàn toàn ngoài SGOD: thuộc `out_of_scope`.
- Câu chào hỏi hoặc trò chuyện: thuộc `chitchat`.

## Generation Rules

- Chỉ sinh dữ liệu single-turn.
- Mỗi câu hỏi chỉ có một ý định hướng dẫn.
- Không tạo hội thoại nhiều lượt hoặc chuỗi hành động phụ thuộc.
- Không kết hợp câu hỏi hướng dẫn với yêu cầu thực hiện nghiệp vụ.
- Không sinh câu hỏi yêu cầu truy xuất dữ liệu thực tế từ SGOD.
- Không tạo yêu cầu trực tiếp tạo, sửa, xóa hoặc phê duyệt dữ liệu.
- Không chuyển câu hỏi hướng dẫn thành tool call.
- Không tự tạo tên tool, API endpoint hoặc tham số kỹ thuật.
- Không tự khẳng định những bước thao tác cụ thể chưa được xác minh.
- Không sử dụng thông tin cá nhân hoặc dữ liệu nội bộ.
- Không sao chép hoặc paraphrase câu hỏi trong `data/sgod/eval_human_core.jsonl`.

## Persona & Context

- Sử dụng ngữ cảnh nghiệp vụ từ `docs/personas_sgod.md`.
- Ưu tiên P6 `kinh_doanh_chi_nhanh` và P7 `hanh_chinh_don_vi_con`.
- Câu hỏi phải phản ánh nhu cầu tìm hiểu cách sử dụng SGOD trong công việc.
- Không tự mở rộng quyền truy cập hoặc chức năng của persona.
- Không tạo câu hỏi yêu cầu thực thi thao tác không được phép.

## Language & Diversity

- Sử dụng tiếng Việt tự nhiên.
- Đa dạng cách diễn đạt câu hỏi hướng dẫn.
- Kết hợp văn phong lịch sự, thân mật và công sở.
- Có thể sử dụng viết tắt phổ biến và lỗi gõ nhẹ.
- Một phần câu có thể viết không dấu.
- Tránh tạo nhiều câu trùng ý nghĩa chỉ khác cách diễn đạt.
- Không đưa tên tool hoặc tham số kỹ thuật vào câu hỏi.

## Tool Calling Rules

- Không gọi bất kỳ SGOD tool nào.
- Không tự chọn tool để thực hiện hành động.
- Không biến yêu cầu hướng dẫn thành yêu cầu truy xuất dữ liệu.
- Các câu hỏi phải phù hợp với nhãn no-call.
- Việc gán `expected_tool` và `expected_params` do pipeline thực hiện.

## Output Requirements

- Tuân thủ định dạng JSON array từ `irrelevance_system.md`.
- Mỗi phần tử là một chuỗi câu hỏi tiếng Việt.
- Không đưa nhãn `expected_tool`, `expected_params` hoặc metadata vào đầu ra.
- Không sử dụng Markdown code fence.
- Không thêm giải thích ngoài dữ liệu được yêu cầu.
