# Kết quả chấm: `Qwen/Qwen2.5-0.5B-Instruct+full` trên `xlam_2k.eval.json`

> **Ghi chú trục đo** — eval: `data/public/xlam_2k.eval.json` @ `6d8c803e` · tools: theo từng bản ghi · preamble: `ebcae911` · scorer: `eval_toolcall/1.2 (strict first-call; params >= half of keys; unknown tool = violation)` · sampling: `{"temperature": 0.0, "do_sample": false, "decoding": "greedy", "max_new_tokens": 256, "dtype": "float16", "device": "cuda", "batch_size": 8, "adapter": "/content/drive/MyDrive/ChatSystem/runs/xlam2k_qwen05b/full"}`. Không so sánh với bảng ở trục khác. <!-- no-prov -->

| Số đo | Giá trị |
|---|---|
| n | 200 |
| passed (strict) | 192 |
| **accuracy (strict)** | **96.0%** |
| tool_name_acc | 97.0% |
| param_acc (≥ nửa số khoá) | 98.94% |
| params_exact | 75.0% |
| json_valid_rate | 98.5% |
| latency p50 / p95 (ms) | 517 / 1477 |
| model · backend | Qwen/Qwen2.5-0.5B-Instruct+full · transformers |
| date · git_sha (dự đoán) | 2026-09-25T10:00:23+00:00 · 8eeab7ba4866 |

## Theo `source`

| group | n | passed | accuracy |
|---|---|---|---|
| public | 200 | 192 | 96.0% |

## Theo `user_role`

| group | n | passed | accuracy |
|---|---|---|---|
| employee | 200 | 192 | 96.0% |

<!-- no-prov-start -->
## Theo lý do (chẩn đoán)

| reason | count | tỷ lệ |
|---|---|---|
| ok | 192 | 96.0% |
| wrong_tool | 6 | 3.0% |
| missing_params | 2 | 1.0% |

## Bản ghi sai (tối đa 25 / 8)

| id | reason | expected | actual | detail |
|---|---|---|---|---|
| pub-5e0230f1 | missing_params | list_all_conversation_turns | list_all_conversation_turns | {"expected": ["is_id"], "got": ["conversation_id"], "matched": 0} |
| pub-66a72937 | wrong_tool | products_search | taobao_search_by_keyword | "expected one of ['products_search'], got ['taobao_search_by_keyword']" |
| pub-886927c1 | wrong_tool | is_valid_sudoku | None | "expected one of ['is_valid_sudoku'], got none" |
| pub-89f35b61 | missing_params | search_properties_for_sale | search_properties_for_sale | {"expected": ["baths_max", "beds_min", "location", "lot_sqft_max", "lot_sqft_min", "sort"], "got": ["bathrooms", "bedroo |
| pub-9267558b | wrong_tool | is_valid_sudoku | None | "expected one of ['is_valid_sudoku'], got none" |
| pub-9cb9b3a3 | wrong_tool | time_zone_api | ip_lookup_api | "expected one of ['time_zone_api'], got ['ip_lookup_api']" |
| pub-a9339a71 | wrong_tool | is_valid_sudoku | None | "expected one of ['is_valid_sudoku'], got none" |
| pub-e9e4537e | wrong_tool | search_by_name | search | "expected one of ['search_by_name'], got ['search']" |
<!-- no-prov-end -->

_Lệnh_: `python training/eval_toolcall.py --gold data/public/xlam_2k.eval.json --pred /content/drive/MyDrive/ChatSystem/runs/xlam2k_qwen05b/results/public/ft_pred.jsonl --out /content/drive/MyDrive/ChatSystem/runs/xlam2k_qwen05b/results/public/ft.json --group-by source --md /content/drive/MyDrive/ChatSystem/runs/xlam2k_qwen05b/results/public/ft.md`
