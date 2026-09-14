# `datagen/prompts/` — prompt sinh dữ liệu **huấn luyện** (D Việc 3)

Thư mục này chứa các file Markdown mà pipeline đọc **thay cho** chuỗi mặc định trong code. Thực tập sinh sửa
prompt ở đây bằng PR, không cần chạm vào Python. File nào không tồn tại thì script dùng mặc định trong
`config_sgod.py` / script tương ứng.

| File | Ghi đè | Dùng bởi |
|---|---|---|
| `domain_system.md` | `config_sgod.DOMAIN_SYSTEM` — system prompt sinh câu truy vấn (domain, ngôn ngữ, ví dụ thực thể, văn phong) | `generate_scenarios.py` |
| `category_<tên>.md` | `CATEGORY_HINTS["<tên>"]` — gợi ý một dòng cho một loại tình huống (vd `category_my_assets.md`) | `generate_scenarios.py` |
| `label_system.md` | `label_scenarios.LABEL_SYS_DEFAULT` — hướng dẫn model gán nhãn chọn **một** tool | `label_scenarios.py`, `verify_trainset.py` (stage C) |
| `arbiter_system.md` | `polish_scenarios.ARB_SYS_DEFAULT` — arbiter sửa nhãn + đánh bóng câu | `polish_scenarios.py` |
| `reviewer_system.md` | `audit_test_cases.REVIEWER_SYSTEM_DEFAULT` — reviewer nhãn (có danh sách cặp tool mơ hồ) | `audit_test_cases.py` |
| `irrelevance_system.md` | `generate_irrelevance.SYS_DEFAULT` | `generate_irrelevance.py` |
| `irrelevance_<kind>.md` | `IRRELEVANCE_CONFIG["<kind>_hint"]`, kind ∈ `out_of_scope`, `chitchat`, `ambiguous`, `procedure_question` | `generate_irrelevance.py` |

Nội dung prompt viết bằng tiếng Việt (model sinh câu tiếng Việt), thuật ngữ kỹ thuật giữ nguyên tiếng Anh.

## Yêu cầu cho prompt sinh dữ liệu huấn luyện

- Persona + intent + ràng buộc **đơn** hoặc **đa** (nhiều bộ lọc trong một câu) + câu ngoài phạm vi. **KHÔNG đa lượt**,
  không "làm A rồi B".
- Không nêu tên tool hay tên tham số kỹ thuật trong câu; câu phải giống người dùng thật gõ (trộn văn phong, viết tắt,
  lỗi chính tả nhẹ).
- Thực thể lấy từ `fixtures/sgod/` (tên tài sản, mã tài sản dạng số, vị trí, danh mục, trạng thái lịch bảo trì) — không
  dùng tên người thật, email, số điện thoại.
- Mỗi lần đổi prompt: ghi vào CHANGELOG, mở PR `data/...`; `run_pipeline.sh --pilot` được chạy trên hạ tầng tham chiếu
  và kết quả (`data/sgod/pilot_*`) được commit + ghi vào comment của task trong ≤ 2 ngày làm việc; xem
  `data/sgod/pilot_quarantine.json` để biết prompt đang sinh lỗi gì.

## Không được làm

- **Không** sao chép prompt sang `datagen/prompts_eval/` hay ngược lại (xem `prompts_eval/README.md`).
- **Không** đưa câu trong `data/sgod/eval_human_core.jsonl` / `eval_v1.json` vào prompt làm ví dụ few-shot — đó là rò rỉ
  trực tiếp vào tập đánh giá; ví dụ trong prompt phải tự viết mới.
- Không chứa khoá API, mật khẩu, token.
