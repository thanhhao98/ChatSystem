# prompts/ — preamble (system turn) và câu trả lời cố định

Các tệp `.txt` trong thư mục này là **văn bản thuần đưa thẳng cho model**:

- `datagen/build_parity_trainset.py` sao **nguyên văn** (đã điền slot) vào `messages[0]` của mọi hàng SGOD;
- `training/predict_toolcall.py` gửi làm system turn khi dự đoán; backend gửi khi phục vụ;
- `tools/sgod/validate_tools.py` đếm token của nó (ngân sách ≤ 1.000 token, hợp đồng 1 §4);
- header dự đoán và `Ghi chú trục đo` ghi sha256 của **nội dung sau `.strip()`** (hợp đồng 2 §2, §6).

Vì vậy **không** đặt chú thích HTML (`<!-- … -->`), ghi chú trạng thái, TODO, tiêu đề Markdown hay bất kỳ dòng nào
không dành cho model trong tệp prompt — mọi ghi chú nằm ở tệp README này. CI (`.github/workflows/ci.yml`, bước
*Prompt files are pure model-facing text*) **thất bại** nếu `prompts/*.txt` chứa `<!--`.

## Trạng thái từng tệp (2026-10-14)

| Tệp | Dùng cho | Trạng thái | Việc / khi |
|---|---|---|---|
| `system_preamble_v0.txt` | hàng công khai xLAM (`data/public/*.jsonl`) và bộ eval công khai | **đóng băng** (Drop 0). sha256 nội dung sau `.strip()`: `ebcae91113cd2d4cec962f9405bb1f8ed4e261c25d71d8bc58f155e9484ad147` | Drop 0; không đổi trong pha 2 |
| `system_preamble_v1.txt` | hàng SGOD (`data/sgod/*.jsonl`), `eval_v1`, phục vụ | **Văn bản nền đóng băng** — Điểm đồng bộ 1 (2026-09-27; ghi ngày 2026-10-14). sha256 nội dung sau `.strip()`: `f5da2272cb7fac03fcc8e24f3a0d855b67095e1dc01e7b3541f564b90411903b` (655 token Qwen theo `tools/sgod/validate_tools.py`; hai dòng *Quy tắc chọn tool* có sẵn đã sửa theo tham số API thật trong PR #5 trước khi ghi sha này — `search`, `completed`). Hạn bổ sung *Quy tắc chọn tool* 2026-10-11 **đã qua, chưa bổ sung dòng mới** (danh mục v1 merge 2026-10-14, PR #5; tag `tools-v1` dời sang 2026-11-04). Chỉ được **thêm** dòng vào mục *Quy tắc chọn tool* cho tool của `tools-v1`, trong PR `[S-V3]` riêng, **trước tag `tools-v1`** (không sửa/xoá dòng có sẵn; ghi sha256 mới vào bảng này); sau tag → **đóng băng hẳn**, đổi = v1.1 + trục đo mới (hợp đồng 2 §6). Chưa có hàng SGOD hay dự đoán nào dùng preamble v1. | S Việc 3 |
| `fixed_replies.json` | hai chuỗi cố định `REFUSAL_VI` / `DEFLECT_VI` (hợp đồng 1 §2) | **đóng băng** (Drop 0) | Drop 0; không đổi |

Việc còn mở cho v1 (đến tag `tools-v1`, 2026-11-04): chỉ **thêm** quy tắc chọn tool cho từng tool mới của `sgod_tools` v1
(hiện có luật cho `list_my_assets`, `get_asset`, `list_maintenance_schedules`); mỗi lần thêm chạy
`python tools/sgod/validate_tools.py` (≤ 1.000 token) và ghi sha256 mới vào bảng trên.

## Slot của `system_preamble_v1.txt`

`{full_name}`, `{role_vi}`, `{user_id}`. Lúc huấn luyện điền ngữ cảnh **generic** (`Người dùng` / tên vai trò theo
`tools/sgod/roles.json.role_names_vi` / `usr-001`) — hợp đồng 1 §1; lúc phục vụ backend điền giá trị thật.
`tools/sgod/validate_tools.py` từ chối slot lạ và mọi nhắc tới mã doanh nghiệp/tenant.

## Hash

Mọi nơi (header `sha256_preamble`, `Ghi chú trục đo`, `results/INDEX.md`) dùng sha256 của **nội dung sau `.strip()`**
— đúng giá trị `eval_toolcall.py --md` in ở mục `preamble:`. `sha256sum <tệp>` cho giá trị **khác** khi tệp có newline
cuối; không dùng cho preamble.
