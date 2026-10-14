# INDEX fixture — số dính hậu tố "pp" (chỉ dùng cho CI của `scripts/check_provenance.py`)

Không phải INDEX thật. Chỉ có một hiệu bằng 0 để bắt lỗi đọc `+0.5pp` thành `0`.

| id | số | metric | results file | lệnh/notebook | git sha7 | eval@sha8 | tools@sha8 | model | ngày | ai |
|---|---|---|---|---|---|---|---|---|---|---|
| R911 | +0.0 pp [+0.0, +0.0] | paired diff fixture (A − B) | tests/fixtures/report_pp_unindexed.md | — | 0000000 | 6d8c803e | — | fixture | 2026-10-14 | fixture |
