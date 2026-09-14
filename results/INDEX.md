# results/INDEX.md — sổ truy vết mọi con số được báo cáo

Quy tắc bắt buộc (xem `HUONG_DAN_LAM_VIEC.md`, mục 4): **mọi con số** xuất hiện trong một báo cáo
(`docs/reports/*.md`, `results/**/*.md`, slide, ClickUp) phải có **một dòng ở đây**.
`scripts/check_provenance.py <report.md>` đối chiếu từng phần trăm và từng `p = …` trong báo cáo với cột
`số` của bảng này; thiếu dòng → thoát mã 1 và `Đầu ra cuối kỳ` không được nhận.

- Bảng **chỉ thêm dòng, không sửa dòng cũ** (append-only). Số sai → thêm dòng mới, ghi rõ "thay R0xx" ở cột `metric`.
- `id`: `R###` tăng dần. `R000` là ví dụ và bị `check_provenance.py` bỏ qua (mọi dòng có chữ "ví dụ" đều bị bỏ qua).
- `số`: đúng con số như in trong báo cáo (kèm CI nếu có, ví dụ `61.5% [54.5, 68.0]`, hoặc `p = 0.0021`).
- `results file`: đường dẫn trong repo, dưới `results/` (dự đoán + kết quả + `.md`), đã có dòng trong `results/RUNLOG.md`.
- `lệnh/notebook`: lệnh đầy đủ tạo ra số đó, hoặc đường dẫn notebook + tên cell.
- `git sha7`: commit của repo lúc chạy. `eval@sha8`: 8 hex đầu của sha256 **byte tệp** eval (`sha256sum data/sgod/eval_v1.json`
  = `eval_sha256` trong `results.json`). `tools@sha8`: 8 hex đầu của sha256 **byte tệp** `tools/sgod/sgod_tools.json`
  (ghi `—` với bộ công khai vì tool nằm trong từng bản ghi). Sha của **preamble** (chỉ xuất hiện trong `Ghi chú trục đo`
  của tệp `.md`, không có cột riêng ở đây) là sha256 của **nội dung sau `.strip()`** — lấy đúng giá trị `header.sha256_preamble`
  mà `eval_toolcall.py --md` in, **không** phải `sha256sum` tệp (khác nhau khi tệp có newline cuối; xem `prompts/README.md`).
- Bảng do `eval_toolcall.py --md` / `bootstrap_ci.py --md` sinh (kể cả bảng theo `reason`/`source`/`user_role`, cận CI, `diff (pp)`,
  `p` McNemar) đều bị `check_provenance.py` đối chiếu: mọi số trong ô có `%`/`(pp)` ở tiêu đề cột hoặc nhãn hàng, và mọi số ở cột `p`.
  Chỉ commit tệp `.md` khi đã có dòng ở đây cho từng số, hoặc bọc phần chưa báo cáo bằng `<!-- no-prov-start -->` … `<!-- no-prov-end -->`.
- `model`: tên model + adapter (tên phục vụ, hoặc `Qwen/Qwen2.5-0.5B-Instruct + <adapter>`), hoặc tên model GPT như gateway trả về.
- `ai`: người tạo số (tên GitHub) — không dùng email cá nhân.

| id | số | metric | results file | lệnh/notebook | git sha7 | eval@sha8 | tools@sha8 | model | ngày | ai |
|---|---|---|---|---|---|---|---|---|---|---|
| R000 | 61.5% [54.5, 68.0] | strict accuracy, public eval (n=200) — **ví dụ**, không phải số thật | results/reference/R000_example_results.json | `python training/eval_toolcall.py --gold data/public/xlam_2k.eval.json --pred results/reference/R000_example.predictions.jsonl --out results/reference/R000_example_results.json` → `python training/bootstrap_ci.py --run ft=results/reference/R000_example_results.json` | 0000000 | 6d8c803e | — | Qwen/Qwen2.5-0.5B-Instruct + adapter ví dụ | 2026-09-13 | — (ví dụ) |
