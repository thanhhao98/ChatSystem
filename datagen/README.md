# `datagen/` — pipeline sinh, gán nhãn và kiểm định dữ liệu huấn luyện SGOD

Pipeline này được port từ hệ thống tham chiếu (POC v1) và **không import gì từ mã nguồn của hệ thống đó**.
Toàn bộ kiến thức về SGOD nằm ở ba chỗ: `tools/sgod/*.json` (danh mục tool + policy + roles),
`datagen/config_sgod.py` (taxonomy, entity pools, bucket plan) và `datagen/prompts/` (prompt sinh dữ liệu).
Đổi ba chỗ đó là đổi domain; code pipeline giữ nguyên.

Hợp đồng liên quan: `docs/contracts/training_row_format.md` (định dạng hàng), `docs/contracts/eval_metric.md`
(schema eval), `docs/contracts/roles.md` (vai trò), `docs/contracts/cli.md` (cờ dòng lệnh).

## Sơ đồ

```
tools/sgod/sgod_tools.json ─┐            prompts/system_preamble_v1.txt + prompts/fixed_replies.json
tools/sgod/tool_policy.json ─┼─ audit_test_cases.load_tools / load_permissions      │
tools/sgod/roles.json ───────┘            (nguồn DUY NHẤT về tool + quyền)           │
                                                                                     ▼
 [1] generate_scenarios.py ──► raw.json ──► [2] label_scenarios.py ──► labeled.json ──► [3] verify_trainset.py
      (GPT, chống rò rỉ                       (≥2 model đồng thuận,                      │  A format · B schema · C semantic
       với eval_v1, SimIndex)                  quyền tính bằng LUẬT)                      ├──► verified.json
                                                                                          └──► quarantine.json (người xem lại)
 [4] generate_irrelevance.py ──► irrelevance.json (tool = null, ~10%)                     │
 [5] convert_xlam.py (data/public/xlam_raw_2k.jsonl) ──► replay.train.jsonl (xLAM, preamble v0)
                                                                                          ▼
 [6] assemble_trackb_trainset.py  (55% domain · 35% replay · 10% irrelevance) ──► data/sgod/{train,val}.jsonl
     (pilot: build_parity_trainset.py ──► data/sgod/pilot_train.jsonl)                    │
                                                                                          ▼
 [7] audit_trainset_vs_api.py  (đối chiếu lại với catalogue hiện tại; exit 1 nếu lệch) ──► training/validate_dataset.py
```

Phần GPT bổ sung của eval_v1 (D Việc 4) đi đường riêng `run_pipeline.sh --eval-aug`: `generate_scenarios.py` theo
`BUCKET_PLAN` với prompt `prompts_eval/` → `label_scenarios.py` → `polish_scenarios.py` (arbiter ≠ GPT bị chấm sửa nhãn,
alternates) → `export_eval_aug.py` → `data/sgod/eval_aug.json` (bản ghi hợp đồng 2, `source: gpt_aug`); mọi tệp trung gian
mang tiền tố `eval_aug_`, không bao giờ trùng tệp của tập huấn luyện. Tuỳ chọn: `audit_test_cases.py` (kiểm tra schema +
review nhãn của một file case bất kỳ). `preflight.py` kiểm tra offline `config_sgod.py` + thư mục prompt trước mọi bước LLM.

## Bảng các bước

| # | Script | Đầu vào | Đầu ra | Cần LLM? | Ai chạy |
|---|---|---|---|---|---|
| 1 | `generate_scenarios.py --trackb` | `config_sgod.TRACKB_BUCKET_PLAN`, `PARAM_SAMPLER`, `prompts/`, `EVAL_SETS_FOR_LEAKAGE` | `data/sgod/raw.json` | **Có** (GEN_MODEL) | hạ tầng tham chiếu |
| 2 | `label_scenarios.py` | `raw.json`, catalogue | `labeled.json`, `label_report.json` | **Có** (LABEL_MODELS) | hạ tầng tham chiếu |
| 3 | `verify_trainset.py` | `labeled.json` | `verified.json`, `quarantine.json`, `verify_report.json` | Có ở stage C (`--no-semantic` = offline) | hạ tầng tham chiếu / intern (offline) |
| 4 | `generate_irrelevance.py` | `IRRELEVANCE_CONFIG` | `irrelevance.json` | **Có** | hạ tầng tham chiếu |
| 5 | `convert_xlam.py` | `data/public/xlam_raw_2k.jsonl`, preamble v0 | `data/sgod/replay.{train,val,test}.jsonl` | Không | ai cũng được |
| 6 | `assemble_trackb_trainset.py` / `build_parity_trainset.py` | 3 luồng ở trên, preamble v1, `fixed_replies.json` | `train.jsonl`, `val.jsonl` (hoặc `pilot_train.jsonl`) | Không | ai cũng được |
| 7 | `audit_trainset_vs_api.py` | `train.jsonl`, `val.jsonl`, catalogue | `alignment_report.json`, exit 0/1 | Không | ai cũng được, CI |
| — | `audit_test_cases.py --dry-run` | file case bất kỳ | `audit_report.json` | Không (`--dry-run`) / Có (pass 2) | intern / hạ tầng tham chiếu |
| — | `polish_scenarios.py` (`--eval-aug`) | `eval_aug_labeled.json` | `eval_aug_polished.json` | **Có** (ARBITER_MODEL) | hạ tầng tham chiếu |
| — | `export_eval_aug.py` (`--eval-aug`) | `eval_aug_polished.json` | `eval_aug.json` (hợp đồng 2, `source: gpt_aug`) | Không | ai cũng được |
| — | `preflight.py` (`run_pipeline.sh --check`) | `config_sgod.py`, thư mục prompt, catalogue | lỗi/cảnh báo, exit 0/1 | Không | intern trước khi mở PR; tự chạy trước mọi bước LLM |

Mọi script đều có `--help`, thoát mã 0 khi thành công, in **một dòng `SUMMARY ...`** cuối cùng (kèm số lần gọi LLM và
token, tổng và theo từng model: `by_model=<alias>:calls/prompt/completion/errors`). Script cần LLM sẽ thoát mã **2** kèm
thông báo tiếng Việt nếu thiếu `OPENAI_API_KEY`; `OPENAI_BASE_URL` luôn được tôn trọng. Gateway từ chối khoá hoặc model
(HTTP 401/403/404) ⇒ bước dừng ngay, thoát mã khác 0, không ghi tệp đầu ra; lỗi tạm thời (timeout, 429, 5xx) được thử lại.

## Ngân sách hiệu suất (yield) 0.58

Từ lần chạy trên hệ thống tham chiếu (POC v1): tỉ lệ sinh đủ bucket ≈ 70% × tỉ lệ qua kiểm định ≈ 84% ⇒ **≈ 0.58** số hàng trong kế hoạch đi tới
trainset. Muốn N hàng domain đã kiểm định thì đặt tổng `TRACKB_BUCKET_PLAN` ≈ N / 0.58 (hoặc dùng `SCALE=`).
Báo cáo chất lượng (D Việc 5) phải nêu yield thực tế so với 0.58, độ tương đồng lớn nhất với `eval_v1`, và số hàng
cách ly (`quarantine.json`) theo stage A/B/C.

## Chạy trên hạ tầng tham chiếu (Epic S Việc 5)

Biến môi trường (chỉ tên; giá trị nằm trên hạ tầng tham chiếu, **không bao giờ** commit):

| Biến | Ý nghĩa |
|---|---|
| `OPENAI_API_KEY`, `OPENAI_BASE_URL` | khoá và địa chỉ gateway LLM tương thích OpenAI (`https://<openai-compatible-gateway>/v1`) |
| `GEN_MODEL`, `LABEL_MODELS` (cách nhau bởi dấu cách), `ARBITER_MODEL` | tên model **đúng như gateway phục vụ**; giá trị trong `config_sgod.py` chỉ là placeholder |
| `SCORED_MODEL` | model GPT sẽ được chấm (S Việc 8). Pipeline từ chối mọi GEN/LABEL/ARBITER trùng tên (hợp đồng 2: arbiter ≠ GPT bị chấm); **bắt buộc** với `--eval-aug` |
| `MAX_TOTAL`, `SCALE`, `IRREL_COUNT`, `GEN_WORKERS`/`LBL_WORKERS`/`VER_WORKERS` | cỡ kế hoạch; `--pilot` mặc định 60 / 8 / 4 nhưng giá trị export vẫn được ưu tiên |
| `PROMPT_DIR`, `OUT_DIR`, `VERIFY_MODE`, `TOOL_DEFS_PATH`/`TOOL_POLICY_PATH`/`ROLES_PATH` | như trong `run_pipeline.sh --help` |
| `LLM_TIMEOUT`, `LLM_MAX_RETRIES` | giây cho mỗi request (mặc định 120) và số lần thử lại lỗi tạm thời (mặc định 3) |

```bash
bash datagen/run_pipeline.sh --check --pilot      # preflight offline, không cần key — chạy ngay khi PR của nhóm D tới
bash datagen/run_pipeline.sh --pilot              # pilot_* -> data/sgod/pilot_train.jsonl (kế hoạch 60 + 8 irrelevance)
bash datagen/run_pipeline.sh --eval-aug           # eval_aug_* -> data/sgod/eval_aug.json (D Việc 4; cần SCORED_MODEL)
bash datagen/run_pipeline.sh                      # chạy đủ (D Việc 5); bước nào có output rồi thì bỏ qua (resumable)
bash datagen/run_pipeline.sh --stage verify --force         # chạy lại một bước
bash datagen/run_pipeline.sh --stage replay,assemble,audit  # các bước offline, không cần key
python training/validate_dataset.py data/sgod/pilot_train.jsonl --preamble prompts/system_preamble_v1.txt \
    --tools tools/sgod/sgod_tools.json --roles tools/sgod/roles.json
```

- Mỗi lần chạy ghi `OUT_DIR/<tiền tố>pipeline.log` (bị `.gitignore`); dòng cuối `SUMMARY run_pipeline: ... | llm_calls=…
  prompt_tokens=… completion_tokens=… errors=… by_model=…` cộng mọi bước của lần chạy đó — dán dòng này vào comment
  ClickUp của task. Một lần chạy trên cùng `OUT_DIR` + chế độ tại một thời điểm (khoá `.<tiền tố>pipeline.lock`).
- Bước bị ngắt giữa chừng chỉ để lại `<đầu ra>.partial` nên lần chạy sau làm lại bước đó; sinh lại đầu vào của một bước
  thì chạy lại bước sau với `--force` (pipeline cảnh báo khi đầu vào mới hơn đầu ra).
- Tệp trong `data/sgod/` chỉ ghi tên model rút gọn (phần sau dấu `/` cuối) và loại lỗi + mã HTTP, không ghi nội dung lỗi
  của gateway. Không commit tên model có tiền tố nhà cung cấp, địa chỉ gateway hay khoá.
- `val.jsonl` chỉ có hàng domain nên qua `validate_dataset.py` như trên. `train.jsonl` đầy đủ trộn hàng replay mang
  preamble v0 (hợp đồng 1 §5) trong khi `validate_dataset.py` chỉ so với một `--preamble`: hàng replay báo
  `preamble_mismatch` cho tới khi cổng hợp đồng 1 nhận cả hai preamble.
- Sau mỗi lần chạy trên hạ tầng tham chiếu, output của từng stage được commit vào `data/sgod/` (trừ `*.log`, `*.partial`)
  và dòng `SUMMARY` được ghi vào comment ClickUp của task trong ≤ 2 ngày làm việc.

## Thực tập sinh sửa gì

- `datagen/prompts/*.md` — prompt sinh dữ liệu huấn luyện (xem `prompts/README.md`). File nào tồn tại sẽ **ghi đè**
  chuỗi mặc định trong code (`domain_system.md`, `category_<tên>.md`, `label_system.md`, `arbiter_system.md`,
  `reviewer_system.md`, `irrelevance_system.md`, `irrelevance_<kind>.md`).
- `datagen/config_sgod.py` — mọi khối `TODO(D-Việc-3)`: `DOMAIN_SYSTEM`, `CATEGORY_HINTS`, `BUCKET_PLAN`, `ENTITY_POOLS`
  (từ `fixtures/sgod/`), `PARAM_SAMPLER` (một entry cho **mỗi** tool trong `sgod_tools.json`), `TRACKB_BUCKET_PLAN`,
  `IRRELEVANCE_CONFIG`, `MIX_TARGETS`. Mỗi khối có 1–2 ví dụ đã điền (`list_my_assets`, `get_asset`,
  `list_maintenance_schedules`) và giá trị của hệ thống tham chiếu (POC v1) trong comment để tham khảo độ dày.
- Trước khi mở PR prompt/config: `bash datagen/run_pipeline.sh --check --pilot` (và `--check --eval-aug` cho
  `prompts_eval/`) — không cần key; `ERROR` (tool/role sai trong plan, `PARAM_SAMPLER` lỗi, thiếu hint irrelevance) thì
  pipeline sẽ không chạy; `WARN` liệt kê tool chưa có trong `TRACKB_BUCKET_PLAN` và tệp `.md` không bước nào đọc (sai tên).
- Xem lại `data/sgod/quarantine.json` sau mỗi lần chạy trên hạ tầng tham chiếu, đề xuất sửa prompt/config qua PR.
- Các chỗ đánh dấu `# TODO(SGOD):` trong code là phần còn phụ thuộc hệ thống tham chiếu POC v1 (danh sách cặp tool mơ hồ trong
  `REVIEWER_SYSTEM`, bảng đổi tên tham số `PARAM_RENAME`, quy tắc slot id trong `verify_trainset.ID_SLOT_SUFFIXES`).

## Preamble v1 và các slot

`build_parity_trainset.py` / `assemble_trackb_trainset.py` điền các slot của `prompts/system_preamble_v1.txt` **giống hệt**
`tools/sgod/validate_tools.py` (cùng `GENERIC_CONTEXT`): `{role}` → khoá vai trò, `{role_vi}` → `roles.json["role_names_vi"]`,
`{full_name}` → `Người dùng`, `{user_id}` → `usr-001`. Hàng huấn luyện mang giá trị generic; khi phục vụ, backend điền
người dùng thật. `audit_trainset_vs_api.py` kiểm tra lại `messages[0]` đúng bằng bản render theo vai trò. Cờ
`--keep-placeholders` (cả ba script) giữ nguyên template khi cần so khớp chữ-với-chữ với file gốc.

## Quy tắc không đổi

- **Chỉ đơn lượt (single-turn), một tool call mỗi hàng.** Nhãn dạng list (multi_step) bị stage A/B loại.
- **Quyền do luật quyết định**, không do LLM: `tool_policy.json` ⇒ `writes == true` là admin-only; tool không được phép
  cho vai trò ⇒ `expected_tool = null`, `expected_permission = "denied"` ⇒ hàng huấn luyện là `REFUSAL_VI`.
- **Chống rò rỉ**: mọi câu sinh ra phải có SequenceMatcher < 0.65 với `data/sgod/eval_v1.json` (khi file chưa tồn tại,
  script cảnh báo và bỏ qua — trước Điểm đồng bộ 2 chỉ chạy pilot).
- **Không bịa tham số mã doanh nghiệp/tenant** — JWT đã scope (spec §1).
- Đổi `sgod_tools.json`, `tool_policy.json` hoặc preamble là một trục đo mới: chạy lại `audit_trainset_vs_api.py`
  và không trộn số liệu giữa các trục.
