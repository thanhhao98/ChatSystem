# prompts/ — preamble (system turn) và câu trả lời cố định

Các tệp `.txt` trong thư mục này là **văn bản thuần đưa thẳng cho model**:

- `datagen/build_parity_trainset.py` sao **nguyên văn** (đã điền slot) vào `messages[0]` của mọi hàng SGOD;
- `training/predict_toolcall.py` gửi làm system turn khi dự đoán; backend gửi khi phục vụ;
- `tools/sgod/validate_tools.py` đếm token của nó (ngân sách ≤ 1.000 token, hợp đồng 1 §4);
- header dự đoán và `Ghi chú trục đo` ghi sha256 của **nội dung sau `.strip()`** (hợp đồng 2 §2, §6).

Vì vậy **không** đặt chú thích HTML (`<!-- … -->`), ghi chú trạng thái, TODO, tiêu đề Markdown hay bất kỳ dòng nào
không dành cho model trong tệp prompt — mọi ghi chú nằm ở tệp README này. CI (`.github/workflows/ci.yml`, bước
*Prompt files are pure model-facing text*) **thất bại** nếu `prompts/*.txt` chứa `<!--`.

## Trạng thái từng tệp (2026-10-21)

| Tệp | Dùng cho | Trạng thái | Việc / khi |
|---|---|---|---|
| `system_preamble_v0.txt` | hàng công khai xLAM (`data/public/*.jsonl`) và bộ eval công khai | **đóng băng** (Drop 0). sha256 nội dung sau `.strip()`: `ebcae91113cd2d4cec962f9405bb1f8ed4e261c25d71d8bc58f155e9484ad147` | Drop 0; không đổi trong pha 2 |
| `system_preamble_v1.txt` | hàng SGOD (`data/sgod/*.jsonl`), `eval_v1`, phục vụ | **Đóng băng hẳn** từ tag `tools-v1` (2026-10-21, S Việc 4). sha256 nội dung sau `.strip()`: `f5da2272cb7fac03fcc8e24f3a0d855b67095e1dc01e7b3541f564b90411903b` (655 token Qwen theo `tools/sgod/validate_tools.py`) — không đổi kể từ Điểm đồng bộ 1: văn bản nền đóng băng 2026-09-27 (ghi ngày 2026-10-14; hai dòng *Quy tắc chọn tool* có sẵn đã sửa theo tham số API thật trong PR #5 trước khi ghi sha — `search`, `completed`); không thêm dòng *Quy tắc chọn tool* nào trước tag, giữ ba luật có sẵn. Đổi = v1.1 + trục đo mới (hợp đồng 2 §6). | S Việc 3, S Việc 4 |
| `fixed_replies.json` | hai chuỗi cố định `REFUSAL_VI` / `DEFLECT_VI` (hợp đồng 1 §2) | **đóng băng** (Drop 0) | Drop 0; không đổi |

Preamble v1 không còn việc mở: tag `tools-v1` (2026-10-21) đóng băng nó cùng ba luật *Quy tắc chọn tool* có sẵn
(`list_my_assets`, `get_asset`, `list_maintenance_schedules`). Prompt gán nhãn của `datagen/` (D Việc 3, D Việc 4) phải
nhắc lại đúng ba luật này để nhãn khớp với hành vi model được yêu cầu; thêm luật mới = preamble v1.1 + trục đo mới.

## Slot của `system_preamble_v1.txt`

`{full_name}`, `{role_vi}`, `{user_id}`. Lúc huấn luyện điền ngữ cảnh **generic** (`Người dùng` / tên vai trò theo
`tools/sgod/roles.json.role_names_vi` / `usr-001`) — hợp đồng 1 §1; lúc phục vụ backend điền giá trị thật.
`tools/sgod/validate_tools.py` từ chối slot lạ và mọi nhắc tới mã doanh nghiệp/tenant.

## Hash

Mọi nơi (header `sha256_preamble`, `Ghi chú trục đo`, `results/INDEX.md`) dùng sha256 của **nội dung sau `.strip()`**
— đúng giá trị `eval_toolcall.py --md` in ở mục `preamble:`. `sha256sum <tệp>` cho giá trị **khác** khi tệp có newline
cuối; không dùng cho preamble.
