# Báo cáo mẫu (fixture) — số dính hậu tố "pp" vẫn phải được kiểm

> **Ghi chú trục đo** — eval: `data/public/xlam_2k.eval.json` @ `6d8c803e` · tools: theo từng bản ghi (bộ công khai) · preamble: `prompts/system_preamble_v0.txt` @ `ebcae911` · scorer: `training/eval_toolcall.py` @ `abc1234`.

| A | B | diff (pp) |
|---|---|---|
| base | ft | +0.5pp |

`+0.5pp` không có dòng trong `tests/fixtures/index_pp_fixture.md` (chỉ có `+0.0 pp`) → check_provenance phải thoát mã 1.
