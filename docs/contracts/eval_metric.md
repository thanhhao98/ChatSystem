# Hợp đồng 2 — Bộ đánh giá, thước đo, schema dự đoán / kết quả và giả thuyết H1

| | |
|---|---|
| Phiên bản | v1 (Drop 0, 2026-09-13) |
| Đóng băng | **Điểm đồng bộ 2 — 2026-10-25** (nhóm D, ký sau review). Từ đó `data/sgod/eval_v1.json` bất biến; sửa lỗi → `eval_v1.1` + errata + sha mới. |
| Cổng máy | `training/eval_toolcall.py` (chấm), `training/bootstrap_ci.py` (CI + McNemar + kết luận H1), `training/predict_toolcall.py` (dự đoán, ghi header sha256). Dòng lệnh: `docs/contracts/cli.md`. |
| Nguồn gốc | Thang chấm chuyển từ `slm_baseline.py::evaluate` (L120–197) của hệ thống tham chiếu (POC v1), với hai nâng cấp ghi ở mục 4. |

## 1. Bản ghi eval

Một bộ eval là **một tệp JSON** chứa một list bản ghi:

```
{
  "id":                      <string ổn định, có tiền tố: "sgod-0001" (eval_v1), "pilot-0001" (pilot), "pub-xxxxxxxx" (bộ công khai)>,
  "category":                <string; nhóm câu hỏi — ví dụ single_tool | multi_constraint | dependent | out_of_scope | permission_denial; tập giá trị chốt trong docs/eval_v1_card.md>,
  "user_role":               <"employee" | "company_admin" | "system_admin">,
  "input":                   <string; câu hỏi tiếng Việt một lượt>,
  "expected_tool":           <string | null; null = không được gọi tool nào (ngoài phạm vi, hoặc bị từ chối)>,
  "expected_params":         <object; các tham số kỳ vọng — chỉ những giá trị suy ra được từ câu hỏi>,
  "expected_permission":     <"allowed" | "denied">,
  "expected_tool_alternates": <list string, tuỳ chọn; tool khác cũng chấp nhận được (do arbiter ≠ GPT bị chấm quyết định)>,
  "source":                  <"human" | "gpt_aug" | "public">,
  "tools":                   <list OpenAI function object, CHỈ bộ công khai — mỗi bản ghi mang danh mục riêng>
}
```

Bộ SGOD **không** có trường `tools`: predictor và scorer đọc `tools/sgod/sgod_tools.json` + `tool_policy.json`
(`--tools`, `--policy`) và lọc theo `user_role`.

Ví dụ (bản ghi đầu của `data/public/xlam_2k.eval.json`, rút gọn còn tool đầu trong 2 tool):

```json
{"id": "pub-00e39916", "category": "public", "user_role": "employee", "source": "public",
 "input": "Fetch credit card data for a Mastercard.",
 "expected_tool": "receive_the_credit_card_data",
 "expected_params": {"visa_type": "mastercard"},
 "expected_permission": "allowed",
 "expected_tool_alternates": [],
 "tools": [
   {"type": "function", "function": {"name": "receive_the_credit_card_data",
     "description": "Fetch credit card data from a simulated API based on the specified card type.",
     "parameters": {"type": "object",
       "properties": {"visa_type": {"description": "Type of visa card to generate. Defaults to 'visa'. …", "type": "str", "default": "visa"}},
       "required": []}}}
 ]}
```

Yêu cầu tối thiểu của `eval_v1.json` (D Việc 4): mục tiêu 500 bản ghi, sàn 400; ≥ 15 bản ghi/tool; mọi vai trò xuất
hiện; ≥ 10 % `expected_tool: null`; ≥ 10 % `expected_permission: denied`; lõi người viết (`source: human`, ≥ 150 câu,
D Việc 2) viết **trước** khi đọc bất kỳ prompt sinh dữ liệu nào; phần `gpt_aug` sinh bằng bộ prompt riêng
`datagen/prompts_eval/`; `expected_permission` gán **bằng luật** từ `tool_policy.json`, không bằng LLM.

## 2. Tệp dự đoán (`*.predictions.jsonl`)

Dòng **đầu** là header; các dòng sau mỗi bản ghi eval một dòng, cùng thứ tự với tệp eval.

```json
{"header": true, "model": "Qwen/Qwen2.5-0.5B-Instruct+sgod-0.5b-v1-s42", "base_url_host": "localhost:8000", "date": "2026-11-09", "git_sha": "abc1234def5678", "sha256_eval": "6d8c803e5b05ea1ddfe1412eda8d3d006d2b05cfd97af170e0c314792b653a67", "sha256_tools": null, "sha256_preamble": "ebcae91113cd2d4cec962f9405bb1f8ed4e261c25d71d8bc58f155e9484ad147", "sampling": {"temperature": 0, "max_new_tokens": 256, "seed": 42}}
{"id": "pub-00e39916", "predicted_tool_calls": [{"name": "receive_the_credit_card_data", "arguments": {"visa_type": "mastercard"}}], "predicted_tool": "receive_the_credit_card_data", "raw_text": "<tool_call>{\"name\": \"receive_the_credit_card_data\", \"arguments\": {\"visa_type\": \"mastercard\"}}</tool_call>", "finish_reason": "stop", "latency_ms": 412, "error": null}
```

| Trường header | Nghĩa |
|---|---|
| `model` | tên model như gateway/vLLM trả về (`served-model-name`), hoặc `base+adapter` với backend transformers |
| `base_url_host` | host của endpoint (không kèm khóa) hoặc `"transformers"` |
| `git_sha` | commit của repo ChatSystem lúc chạy |
| `sha256_eval` | sha256 **tệp** eval (`sha256sum data/sgod/eval_v1.json`) |
| `sha256_tools` | sha256 tệp `tools/sgod/sgod_tools.json`; `null` khi bản ghi eval mang `tools` riêng (bộ công khai) |
| `sha256_preamble` | sha256 của nội dung preamble sau `.strip()` |
| `sampling` | `temperature` (mặc định 0), `max_new_tokens`, `seed`, và các tham số khác nếu có |

| Trường bản ghi | Nghĩa |
|---|---|
| `predicted_tool_calls` | list `{name, arguments}`; `arguments` là **dict** (predictor parse từ tag `<tool_call>` hoặc từ `tool_calls` của API; call nào JSON hỏng thì **bỏ khỏi list**, vẫn giữ trong `raw_text`) |
| `predicted_tool` | `predicted_tool_calls[0].name` hoặc `null` |
| `raw_text` | toàn bộ text model sinh (để kiểm JSON validity và điều tra) |
| `finish_reason` | `stop` \| `length` \| `tool_calls` \| … |
| `latency_ms` | thời gian một lượt (ms) |
| `error` | `null`, hoặc thông điệp lỗi transport/sinh (timeout, HTTP 5xx, OOM) |

`eval_toolcall.py` **từ chối chấm** nếu `sha256_eval`, `sha256_tools` (khi khác `null`) hoặc `sha256_preamble` khác
tệp cục bộ (`--no-header-check` chỉ dùng khi điều tra, không dùng cho số báo cáo).

## 3. Tệp kết quả (`results.json`, theo `docs/contracts/cli.md` § Định dạng chung)

```json
{"model": "Qwen/Qwen2.5-0.5B-Instruct+sgod-0.5b-v1-s42",
 "eval_set": "xlam_2k.eval.json",
 "eval_path": "data/public/xlam_2k.eval.json",
 "eval_sha256": "6d8c803e5b05ea1ddfe1412eda8d3d006d2b05cfd97af170e0c314792b653a67",
 "n": 200, "passed": 123,
 "by_reason": {"ok": 123, "wrong_tool": 40, "missing_params": 20, "no_tool_expected": 0, "permission_check": 0, "api_error": 17},
 "results": [
   {"id": "pub-00e39916", "pass": true, "reason": "ok",
    "expected_tool": "receive_the_credit_card_data", "actual_tool": "receive_the_credit_card_data",
    "source": "public", "user_role": "employee"}
 ]}
```

`eval_set` là **tên tệp** (`Path(--gold).name`), `eval_path` là đường dẫn như đã truyền cho `--gold` — đúng như
`eval_toolcall.py` ghi. Các khoá trên là **tối thiểu** (`cli.md` § Định dạng chung); `eval_toolcall.py` ghi thêm `accuracy`, `tool_name_acc`,
`param_acc`, `params_exact`, `json_valid_rate`, `latency_p50_ms`, `latency_p95_ms`, `by_source`, `by_role`, `by_group`,
`header`, `header_check`, `policy`, `scorer`, và mỗi phần tử `results[]` có thêm `category`, `json_valid`, `latency_ms`, `detail`.
`results[]` là tập con của bản ghi `slm_baseline.py` (L262–277) mà `bootstrap_ci.py` đọc: chỉ cần `id` và `pass`
để bootstrap và McNemar; `reason`, `expected_tool`, `actual_tool`, `source`, `user_role` để nhóm và điều tra.
Tệp `.md` đi kèm (`--md`) in bảng tổng + bảng theo `source` (`--group-by source`) + `by_reason` + p50/p95 `latency_ms`.

## 4. Thang chấm (một bản ghi → `pass` + `reason`)

Áp dụng theo thứ tự; dừng ở bước đầu tiên khớp.

| # | Điều kiện | Kết quả | `reason` |
|---|---|---|---|
| 0a | không có dòng dự đoán cho `id` này | fail | `missing_prediction` |
| 0b | `error` khác `null` | fail | `api_error` |
| 1 | `expected_permission == "denied"` | pass **khi và chỉ khi** không có call nào trong `predicted_tool_calls` trỏ tới tool mà `tool_policy.json[tool].roles` **không chứa** `user_role`. Tool không có trong `tool_policy.json` (bịa tên) coi là không cho phép với mọi vai trò. Nếu scorer chạy **không có** `--policy` mà gặp bản ghi denied: không có call → pass; có call → fail `policy_missing` (bộ công khai không có bản ghi denied nên không gặp). | `permission_check` (hoặc `policy_missing`) |
| 2 | `expected_tool` là `null` | pass khi và chỉ khi `predicted_tool_calls` rỗng | `no_tool_expected` |
| 3 | **call đầu tiên** (`predicted_tool_calls[0]`) không có `name ∈ {expected_tool} ∪ expected_tool_alternates` — kể cả khi `predicted_tool_calls` rỗng | fail | `wrong_tool` |
| 4 | với **call đầu tiên**: số khoá của `expected_params` có mặt trong `arguments` `< max(1, len(expected_params) // 2)` | fail | `missing_params` |
| 5 | còn lại | pass | `ok` |

**Strict first-call.** Bước 3–4 chỉ xét `predicted_tool_calls[0]`; call thứ hai trở đi **bị bỏ qua** khi chấm tên và
tham số. Đầu ra nhiều call mà call đầu sai tool là `wrong_tool` dù một call sau đúng. (Bước 1 — từ chối — vẫn xét
**mọi** call: chỉ cần một call vượt quyền là fail.) `eval_toolcall.py` cài đặt đúng điều này (`STRICT_FIRST_CALL = True`)
và ghi `strict first-call` trong trường `scorer` của `results.json`; đổi sang "call khớp đầu tiên bất kỳ" là đổi thang
chấm = trục đo mới (mục 6).

Ba khác biệt so với POC v1: (a) bước 1 thay tập admin tool ghi cứng bằng **`tool_policy.json`** (từ chối ⇔ không
gọi tool ngoài quyền của vai trò); (b) bỏ nhánh `multi_step` (pha 2 chỉ một lượt); (c) bước 3 xét **call đầu tiên**
thay cho "call khớp đầu tiên bất kỳ" của `slm_baseline.py` (strict). Bước 4 giữ nguyên ngưỡng một nửa số **khoá**
(`max(1, len // 2)`, không so giá trị) như POC v1.

**Thước đo chính — strict accuracy** = `passed / n` × 100 %. Thước đo phụ (báo cáo, không quyết định H1), đúng tên khoá
mà `eval_toolcall.py` ghi vào `results.json`: `tool_name_acc` (bước 3 qua, trên bản ghi có `expected_tool` và không denied),
`param_acc` (bước 4 qua, trên bản ghi đã khớp tool và có `expected_params`), `params_exact` (mọi khoá kỳ vọng có mặt và giá
trị bằng nhau sau khi ép về chuỗi, cùng mẫu số với `param_acc`), `json_valid_rate` (mọi tag `<tool_call>` trong `raw_text`
parse được), `latency_p50_ms` / `latency_p95_ms`, và các số trên chia theo `by_source` (`human` / `gpt_aug`), `by_role`,
`by_group` (`--group-by`).

## 5. Khoảng tin cậy, kiểm định và giả thuyết đăng ký trước

`training/bootstrap_ci.py --run <label>=<results.json> … --pair A B … --paired-diff-margin 5 --n-boot 2000 --seed 20260625`

- **CI mỗi run**: bootstrap phần trăm (percentile), 2.000 lần lấy mẫu lại, seed `20260625`, CI 95 % = phân vị 2,5 và 97,5.
- **Mỗi cặp A–B** (cùng tập `id`): CI bootstrap **ghép đôi** của hiệu `acc(A) − acc(B)` (lấy mẫu lại theo `id`,
  cùng seed), và **McNemar chính xác hai phía** trên hai ô bất đồng: `b` = A đúng & B sai, `c` = A sai & B đúng,
  `p = min(1, 2 · Σ_{j≤min(b,c)} C(b+c, j) · 0,5^(b+c))`.

### H1 (đăng ký trước, đóng băng cùng eval_v1 tại Điểm đồng bộ 2)

> **H1.** Trên `eval_v1`, strict accuracy của SLM đã fine-tune **không thấp hơn GPT quá 5 điểm phần trăm**.
>
> **Quy tắc quyết định.** Tính CI bootstrap ghép đôi 95 % của hiệu `acc(SLM) − acc(GPT)` (2.000 lần, seed 20260625).
> **H1 giữ** khi và chỉ khi phân vị 2,5 của hiệu **> −5 pp**. Ngược lại: **H1 không giữ**. Kết luận in đúng một trong
> hai chuỗi `H1 giữ` / `H1 không giữ` trong `docs/reports/<date>_sgod_sft_vs_gpt.md`.
>
> **Kiểm định tương đương kèm theo.** McNemar chính xác hai phía (b, c, p) cho cặp SLM–GPT, báo cáo bên cạnh, không
> thay quy tắc quyết định.
>
> **Run SLM chính.** Huấn luyện ≥ 3 seed cùng recipe; run chính = seed có accuracy **trung vị**; báo cáo thêm
> mean ± std trên các seed. GPT chạy một lần với `temperature 0` trên hạ tầng tham chiếu (S Việc 8).
>
> **Cặp phụ.** base zero-shot vs fine-tuned (cùng kích cỡ), cùng quy trình; không tham gia quyết định H1.
>
> **Lát cắt.** Mọi số báo cáo riêng cho `source: human` và `source: gpt_aug`; số toàn bộ là số chính.

Arm trong bảng cuối (F Việc 4): 3B zero-shot (hạ tầng tham chiếu) · 1.5B SFT (T4) · 3B SFT (máy GPU của hạ tầng tham
chiếu, recipe sản xuất) · GPT. Arm 3B trên máy GPU của hạ tầng tham chiếu là arm so sánh được với POC v1; 1.5B là
ablation kích cỡ.

## 6. Quy tắc phiên bản — không trộn trục đo

Bất kỳ thay đổi nào của **(i)** `eval_v1.json`, **(ii)** `tools/sgod/sgod_tools.json` / `tool_policy.json`,
**(iii)** preamble (`system_preamble_v1.txt`), hoặc **(iv)** thang chấm ở mục 4 tạo ra một **trục đo mới**. Số ở hai
trục **không bao giờ đứng chung một bảng** hay được trừ cho nhau (tiền lệ POC v1: đổi phiên bản model GPT qua gateway
OpenAI-compatible phải chạy lại baseline; ba trục pre-RBAC / post-RBAC / post-fix không trộn). Mọi tệp `docs/reports/*.md`,
`results/**/*.md` bắt đầu bằng header sau, ngay dưới tiêu đề:

```markdown
> **Ghi chú trục đo** — eval: `data/sgod/eval_v1.json` @ `<sha8>` · tools: `tools/sgod/sgod_tools.json` @ `<sha8>` (tag `tools-v1`) ·
> policy: `tools/sgod/tool_policy.json` @ `<sha8>` · preamble: `prompts/system_preamble_v1.txt` @ `<sha8>` ·
> scorer: `training/eval_toolcall.py` @ git `<sha7>` · sampling: temperature 0. Không so sánh với bảng ở trục khác.
```

`<sha8>` = 8 hex đầu của sha256, theo đúng quy ước của header dự đoán (mục 2):

- **eval / tools / policy**: sha256 **byte của tệp** (`sha256sum <tệp>`) — bằng `sha256_eval` / `sha256_tools` trong header
  và `eval_sha256` trong `results.json`;
- **preamble**: sha256 của **nội dung sau `.strip()`** — là `header.sha256_preamble` mà `eval_toolcall.py --md` in ở mục
  `preamble:` của dòng này. `sha256sum prompts/system_preamble_v1.txt` cho giá trị **khác** khi tệp có newline cuối;
  **không dùng** cho preamble (xem `prompts/README.md`);
- bộ công khai ghi `tools: theo từng bản ghi`.

Cách chắc nhất: **copy dòng `Ghi chú trục đo` mà `eval_toolcall.py --md` đã in** thay vì gõ tay. `scripts/check_provenance.py`
cảnh báo khi thiếu header này và **thoát mã 1** khi có phần trăm, số trong ô bảng có `%`/`(pp)`/cột `p`, hoặc `p = …`
không có dòng trong `results/INDEX.md` (dòng `Ghi chú trục đo`, inline code và ngưỡng `≥50%` không bị đối chiếu).

Tên tệp nộp: `results/sgod_eval_v1/<model>_<YYYY-MM-DD>.predictions.jsonl` + `.json` + `.md`; bộ công khai:
`results/public/<model>_<date>.*`. Mỗi tệp có một dòng trong `results/RUNLOG.md`; mỗi số báo cáo có một dòng trong
`results/INDEX.md`.

## 7. Ai đóng băng gì, khi nào

| Hạng mục | Việc / nguồn | Khi | Ghi chú |
|---|---|---|---|
| `data/sgod/eval_human_core.jsonl` | nhóm D (Việc 2) | 2026-10-08 (Thu) | sha256 dán vào bình luận ClickUp; viết trước khi đọc prompt sinh |
| `data/sgod/pilot_eval.json` + `pilot_train.jsonl` | nhóm D → nhóm F | 2026-10-20 | đầu vào F Việc 3; không dùng cho số báo cáo |
| `data/sgod/eval_v1.json` + `eval_v1.sha256` + `docs/eval_v1_card.md` | nhóm D (Việc 4), ký sau review | **Điểm đồng bộ 2 — 2026-10-25** | bất biến; sửa → `eval_v1.1` + errata + sha mới |
| Tài liệu này (schema + thang chấm + H1) | Drop 0 → Điểm đồng bộ 2 | Điểm đồng bộ 2 | `eval_toolcall.py` / `bootstrap_ci.py` phải khớp ở cùng commit |
| Baseline GPT trên eval_v1 | S Việc 8 (chạy trên hạ tầng tham chiếu) | 2026-10-29 (Thu) | dự đoán commit vào `results/sgod_eval_v1/`; nhóm F chấm → INDEX R001 |
| `tools-v1` (tag) | D Việc 1 + S Việc 4 | 2026-10-08 | đổi tool = trục đo mới |
