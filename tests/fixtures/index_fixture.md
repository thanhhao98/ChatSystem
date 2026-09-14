# INDEX fixture — chỉ dùng cho CI của `scripts/check_provenance.py`

Không phải INDEX thật. INDEX thật nằm ở `results/INDEX.md`.

| id | số | metric | results file | lệnh/notebook | git sha7 | eval@sha8 | tools@sha8 | model | ngày | ai |
|---|---|---|---|---|---|---|---|---|---|---|
| R901 | 61.5% [54.5, 68.0] | strict accuracy, public eval (n=200) | results/reference/fixture_ft.json | `python training/eval_toolcall.py --gold data/public/xlam_2k.eval.json --pred results/reference/fixture_ft.predictions.jsonl --out results/reference/fixture_ft.json` | abc1234 | 6d8c803e | — | Qwen/Qwen2.5-0.5B-Instruct + fixture-adapter | 2026-09-13 | fixture |
| R902 | 48.0% | strict accuracy, public eval (n=200) | results/reference/fixture_base.json | `python training/eval_toolcall.py --gold data/public/xlam_2k.eval.json --pred results/reference/fixture_base.predictions.jsonl --out results/reference/fixture_base.json` | abc1234 | 6d8c803e | — | Qwen/Qwen2.5-0.5B-Instruct (zero-shot) | 2026-09-13 | fixture |
| R903 | p = 0.0021 | McNemar exact hai phía, base vs ft | results/reference/fixture_pair.md | `python training/bootstrap_ci.py --run base=results/reference/fixture_base.json --run ft=results/reference/fixture_ft.json --pair base ft` | abc1234 | 6d8c803e | — | — | 2026-09-13 | fixture |
| R904 | 74.5% | strict accuracy, public eval (n=200) — synthetic-sample, cho `tests/fixtures/eval_report_ok.md` (cũng là accuracy theo `source`/`user_role` và tỷ lệ `ok`) | tests/fixtures/eval_report_ok.md | `python training/eval_toolcall.py --gold data/public/xlam_2k.eval.json --pred data/public/sample_pred.jsonl --preamble prompts/system_preamble_v0.txt --out /tmp/r.json --md tests/fixtures/eval_report_ok.md` | 0000000 | 6d8c803e | — | synthetic-sample | 2026-09-13 | fixture |
| R905 | 82.5% | tool_name_acc, cùng run R904 | tests/fixtures/eval_report_ok.md | như R904 | 0000000 | 6d8c803e | — | synthetic-sample | 2026-09-13 | fixture |
| R906 | 89.94% | param_acc = params_exact, cùng run R904 | tests/fixtures/eval_report_ok.md | như R904 | 0000000 | 6d8c803e | — | synthetic-sample | 2026-09-13 | fixture |
| R907 | 96.0% | json_valid_rate, cùng run R904 | tests/fixtures/eval_report_ok.md | như R904 | 0000000 | 6d8c803e | — | synthetic-sample | 2026-09-13 | fixture |
| R908 | 17.5% | tỷ lệ `wrong_tool` (35/200), cùng run R904 | tests/fixtures/eval_report_ok.md | như R904 | 0000000 | 6d8c803e | — | synthetic-sample | 2026-09-13 | fixture |
| R909 | 8.0% | tỷ lệ `missing_params` (16/200), cùng run R904 | tests/fixtures/eval_report_ok.md | như R904 | 0000000 | 6d8c803e | — | synthetic-sample | 2026-09-13 | fixture |
| R000 | 99.9% | ví dụ — dòng này phải bị bỏ qua khi đối chiếu | — | — | 0000000 | — | — | — | 2026-09-13 | fixture (ví dụ) |
