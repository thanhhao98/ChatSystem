# Kết quả chấm: `gemini-3.5-flash-lite` trên `eval_v1.json`

> **Ghi chú trục đo** — eval: `data/sgod/eval_v1.json` @ `04aec49d` · tools: `cc3cb61b` · policy: `tools/sgod/tool_policy.json` · preamble: `f5da2272` · scorer: `eval_toolcall/1.3 (strict first-call; params >= half of keys; unknown tool = violation)` · sampling: `{"temperature": 0.0, "max_tokens": 256, "tool_choice": "auto", "temperature_rejected": false, "decoding": "temperature"}`. Không so sánh với bảng ở trục khác. <!-- no-prov -->

| Số đo | Giá trị |
|---|---|
| n | 500 |
| passed (strict) | 466 |
| **accuracy (strict)** | **93.2%** |
| tool_name_acc | 91.58% |
| param_acc (≥ nửa số khoá) | 99.4% |
| params_exact | 95.21% |
| json_valid_rate | 75.6% |
| latency p50 / p95 (ms) | 1156 / 2154 |
| model · backend | gemini-3.5-flash-lite · openai |
| date · git_sha (dự đoán) | 2026-11-06T10:51:18+07:00 · 1f5bd324a17b |

## Theo `source`

| group | n | passed | accuracy |
|---|---|---|---|
| gpt_aug | 350 | 321 | 91.71% |
| human | 150 | 145 | 96.67% |

## Theo `user_role`

| group | n | passed | accuracy |
|---|---|---|---|
| company_admin | 206 | 191 | 92.72% |
| employee | 294 | 275 | 93.54% |

<!-- no-prov-start -->
## Theo lý do (chẩn đoán)

| reason | count | tỷ lệ |
|---|---|---|
| ok | 336 | 67.2% |
| permission_check | 66 | 13.2% |
| no_tool_expected | 66 | 13.2% |
| wrong_tool | 31 | 6.2% |
| missing_params | 1 | 0.2% |

## Bản ghi sai (tối đa 25 / 34)

| id | reason | expected | actual | detail |
|---|---|---|---|---|
| sgod-0002 | wrong_tool | list_my_assets | get_asset | "expected one of ['list_my_assets'], got ['get_asset']" |
| sgod-0004 | wrong_tool | list_my_assets | get_asset | "expected one of ['list_my_assets'], got ['get_asset']" |
| sgod-0055 | wrong_tool | get_maintenance_schedule | list_maintenance_schedules | "expected one of ['get_maintenance_schedule'], got ['list_maintenance_schedules']" |
| sgod-0060 | wrong_tool | list_maintenance_records | None | "expected one of ['list_maintenance_records'], got none" |
| sgod-0120 | wrong_tool | get_staff_request_summary | list_staff_requests | "expected one of ['get_staff_request_summary'], got ['list_staff_requests']" |
| sgod-0174 | wrong_tool | get_asset | list_my_assets | "expected one of ['get_asset'], got ['list_my_assets']" |
| sgod-0175 | wrong_tool | get_asset | list_my_assets | "expected one of ['get_asset'], got ['list_my_assets']" |
| sgod-0196 | wrong_tool | get_asset_histories | get_asset | "expected one of ['get_asset_histories'], got ['get_asset']" |
| sgod-0198 | wrong_tool | get_asset_histories | get_asset | "expected one of ['get_asset_histories'], got ['get_asset']" |
| sgod-0199 | wrong_tool | get_asset_histories | get_asset | "expected one of ['get_asset_histories'], got ['get_asset']" |
| sgod-0202 | wrong_tool | get_asset_histories | get_asset | "expected one of ['get_asset_histories'], got ['get_asset']" |
| sgod-0203 | wrong_tool | get_asset_histories | list_asset_transfers | "expected one of ['get_asset_histories'], got ['list_asset_transfers']" |
| sgod-0223 | wrong_tool | list_locations | None | "expected one of ['list_locations'], got none" |
| sgod-0229 | wrong_tool | list_locations | None | "expected one of ['list_locations'], got none" |
| sgod-0232 | wrong_tool | get_location | list_locations | "expected one of ['get_location'], got ['list_locations']" |
| sgod-0233 | wrong_tool | get_location | list_locations | "expected one of ['get_location'], got ['list_locations']" |
| sgod-0234 | wrong_tool | get_location | list_locations | "expected one of ['get_location'], got ['list_locations']" |
| sgod-0235 | wrong_tool | get_location | list_locations | "expected one of ['get_location'], got ['list_locations']" |
| sgod-0236 | wrong_tool | get_location | list_locations | "expected one of ['get_location'], got ['list_locations']" |
| sgod-0237 | wrong_tool | get_location | list_locations | "expected one of ['get_location'], got ['list_locations']" |
| sgod-0238 | wrong_tool | get_location | list_locations | "expected one of ['get_location'], got ['list_locations']" |
| sgod-0239 | wrong_tool | get_location | list_locations | "expected one of ['get_location'], got ['list_locations']" |
| sgod-0240 | wrong_tool | get_location | list_locations | "expected one of ['get_location'], got ['list_locations']" |
| sgod-0241 | wrong_tool | get_location | list_locations | "expected one of ['get_location'], got ['list_locations']" |
| sgod-0242 | wrong_tool | get_location | list_locations | "expected one of ['get_location'], got ['list_locations']" |
<!-- no-prov-end -->

_Lệnh_: `python training/eval_toolcall.py --gold data/sgod/eval_v1.json --pred results/sgod_eval_v1/gemini-3.5-flash-lite_2026-11-06.predictions.jsonl --out results/sgod_eval_v1/gemini-3.5-flash-lite_2026-11-06.results.json --tools tools/sgod/sgod_tools.json --policy tools/sgod/tool_policy.json --preamble prompts/system_preamble_v1.txt --group-by source --md results/sgod_eval_v1/gemini-3.5-flash-lite_2026-11-06.results.md`
