# Kết quả chấm: `Qwen/Qwen2.5-0.5B-Instruct` trên `xlam_2k.eval.json`

> **Ghi chú trục đo** — eval: `data/public/xlam_2k.eval.json` @ `6d8c803e` · tools: theo từng bản ghi · preamble: `ebcae911` · scorer: `eval_toolcall/1.2 (strict first-call; params >= half of keys; unknown tool = violation)` · sampling: `{"temperature": 0.0, "do_sample": false, "decoding": "greedy", "max_new_tokens": 256, "dtype": "float16", "device": "cuda", "batch_size": 8, "adapter": null}`. Không so sánh với bảng ở trục khác. <!-- no-prov -->

| Số đo | Giá trị |
|---|---|
| n | 200 |
| passed (strict) | 190 |
| **accuracy (strict)** | **95.0%** |
| tool_name_acc | 96.5% |
| param_acc (≥ nửa số khoá) | 98.4% |
| params_exact | 74.33% |
| json_valid_rate | 98.0% |
| latency p50 / p95 (ms) | 274 / 807 |
| model · backend | Qwen/Qwen2.5-0.5B-Instruct · transformers |
| date · git_sha (dự đoán) | 2026-09-25T09:38:03+00:00 · 6047c502ce56 |

## Theo `source`

| group | n | passed | accuracy |
|---|---|---|---|
| public | 200 | 190 | 95.0% |

## Theo `user_role`

| group | n | passed | accuracy |
|---|---|---|---|
| employee | 200 | 190 | 95.0% |

<!-- no-prov-start -->
## Theo lý do (chẩn đoán)

| reason | count | tỷ lệ |
|---|---|---|
| ok | 190 | 95.0% |
| wrong_tool | 7 | 3.5% |
| missing_params | 3 | 1.5% |

## Bản ghi sai (tối đa 25 / 10)

| id | reason | expected | actual | detail |
|---|---|---|---|---|
| pub-5e0230f1 | missing_params | list_all_conversation_turns | list_all_conversation_turns | {"expected": ["is_id"], "got": ["conversation_id"], "matched": 0} |
| pub-75308398 | wrong_tool | generate_a_qr_code_image | qr_code_image | "expected one of ['generate_a_qr_code_image'], got ['qr_code_image']" |
| pub-886927c1 | wrong_tool | is_valid_sudoku | None | "expected one of ['is_valid_sudoku'], got none" |
| pub-89f35b61 | missing_params | search_properties_for_sale | search_properties_for_sale | {"expected": ["baths_max", "beds_min", "location", "lot_sqft_max", "lot_sqft_min", "sort"], "got": ["bathrooms", "bedroo |
| pub-9267558b | wrong_tool | is_valid_sudoku | None | "expected one of ['is_valid_sudoku'], got none" |
| pub-9cb9b3a3 | wrong_tool | time_zone_api | ip_lookup_api | "expected one of ['time_zone_api'], got ['ip_lookup_api']" |
| pub-a9339a71 | wrong_tool | is_valid_sudoku | None | "expected one of ['is_valid_sudoku'], got none" |
| pub-afc118eb | wrong_tool | polygon_area_shoelace | None | "expected one of ['polygon_area_shoelace'], got none" |
| pub-e9e4537e | wrong_tool | search_by_name | search | "expected one of ['search_by_name'], got ['search']" |
| pub-f09c0e55 | missing_params | carbonfootprintfrommotorbike | carbonfootprintfrommotorbike | {"expected": ["distance", "type"], "got": [], "matched": 0} |
<!-- no-prov-end -->

_Lệnh_: `python training/eval_toolcall.py --gold data/public/xlam_2k.eval.json --pred /content/drive/MyDrive/ChatSystem/runs/xlam2k_qwen05b/results/public/base_pred.jsonl --out /content/drive/MyDrive/ChatSystem/runs/xlam2k_qwen05b/results/public/base.json --group-by source --md /content/drive/MyDrive/ChatSystem/runs/xlam2k_qwen05b/results/public/base.md`
