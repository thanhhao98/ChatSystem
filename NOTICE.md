# NOTICE — phạm vi sử dụng, giấy phép dữ liệu và mô hình

Repo `thanhhao98/ChatSystem` phục vụ **mục đích học tập và nghiên cứu** (chương trình thực tập về tool-calling bằng mô hình
ngôn ngữ nhỏ, kế thừa hệ thống tham chiếu POC v1). Không dùng mã, dữ liệu hay mô hình trong repo cho mục đích thương mại khi
chưa có đồng ý của chủ sở hữu repo và của chủ sở hữu các thành phần dưới đây.

## Mã nguồn của nhóm

Bản quyền thuộc các tác giả trong lịch sử git của repo. Giấy phép phân phối lại mã nguồn **chưa được chọn** (repo private);
giấy phép sẽ được chọn và ghi vào tệp này trước khi công khai bất kỳ phần nào. Cho tới lúc đó: chỉ thành viên được cấp quyền
mới truy cập.

## Dữ liệu

| Thành phần | Nguồn | Giấy phép / điều kiện |
|---|---|---|
| `data/public/xlam_*` | Salesforce/xlam-function-calling-60k (APIGen, arXiv:2406.18518) | **CC-BY-4.0** — ghi công ở `data/public/ATTRIBUTION.md`; bản gốc gated trên Hugging Face |
| `data/sgod/*` (từ D Việc 2 trở đi) | do nhóm viết / sinh bằng LLM từ spec SGOD và fixtures đã che PII | nội bộ nhóm; không chứa dữ liệu cá nhân thật; không công khai khi chưa có đồng ý của chủ nền tảng SGOD |
| `fixtures/sgod/*` | phản hồi thật của API SGOD, **PII đã che** (S Việc 2) | nội bộ; không phân phối ngoài repo |
| `docs/sgod-api-reference.md`, `docs/sgod/openapi-*.json` | tài liệu nền tảng SGOD | nội bộ; mọi khóa / mật khẩu đã thay bằng placeholder; giá trị thật chỉ trong `.env` trên hạ tầng tham chiếu |

## Mô hình

| Mô hình | Giấy phép | Ghi chú |
|---|---|---|
| Qwen/Qwen2.5-0.5B-Instruct, Qwen/Qwen2.5-1.5B-Instruct | Apache-2.0 | arm của thực tập sinh trên T4 |
| Qwen/Qwen2.5-3B-Instruct | **Qwen Research License** (không phải Apache-2.0) | arm 3B chạy trên máy GPU của hạ tầng tham chiếu; chỉ dùng nghiên cứu; đọc điều khoản trên trang model trước khi phân phối adapter |
| Adapter LoRA do nhóm huấn luyện | kế thừa điều kiện của base + dữ liệu huấn luyện | adapter trên bộ SGOD không công khai |
| GPT qua gateway tương thích OpenAI | điều khoản của nhà cung cấp gateway | chỉ gọi từ hạ tầng tham chiếu; đầu ra (dự đoán) commit vào `results/` để chấm |

## Bí mật

Không có khóa API, token, mật khẩu hay email cá nhân trong repo; CI (`.github/workflows/ci.yml`) chặn các chuỗi giống bí mật.
Nếu phát hiện lộ: xoay khóa trước, xoá khỏi lịch sử sau; ghi vào comment của task và mở issue ngay.
