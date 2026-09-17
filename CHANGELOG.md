# CHANGELOG

Mọi thay đổi đáng kể của repo ghi ở đây, **trong cùng commit** với thay đổi (quy tắc PR). Định dạng:
`YYYY-MM-DD — [mã việc] tóm tắt (PR #n)`. Mới nhất ở trên.

## 2026-09-17 — sửa torch_dtype=HALF và ép kiểu tham số LoRA trong finetune_qlora.py

- `training/finetune_qlora.py`: Sửa `AutoModelForCausalLM.from_pretrained` dùng `torch_dtype=HALF` thay vì `dtype=HALF` và ép kiểu các tham số LoRA trainable về `HALF` (float16) để tránh lỗi `NotImplementedError: _amp_foreach_non_finite_check_and_unscale_cuda not implemented for BFloat16` trong PyTorch AMP GradScaler trên GPU T4.

## 2026-09-14 — rà soát từ ngữ, truy cập GitHub, phạm vi grep bí mật

- Tài liệu gốc (`README.md`, `HUONG_DAN_LAM_VIEC.md`, `NOTICE.md`, `.env.example`, `data/public/ATTRIBUTION.md`, `main-guard.yml`, `requirements-train.txt`, `.gitignore`): mô tả công việc không theo cá nhân — mọi bước chạy bằng máy GPU / gateway LLM / khóa SGOD gọi là **hạ tầng tham chiếu**, đầu ra commit vào repo (`results/`, `fixtures/`, `docs/sgod/`, `data/sgod/`); hệ thống đi trước gọi là **hệ thống tham chiếu (POC v1)**; list S đổi tên thành `S — Hệ thống & hạ tầng tham chiếu`.
- Truy cập GitHub: repo private thuộc tài khoản cá nhân → collaborator dùng **Personal access token (classic)** scope `repo` (chỉ classic mới hoạt động với collaborator), lưu trong Colab/Kaggle Secrets (`GITHUB_TOKEN`), không in token. Vào `main` là chỉ-PR theo quy ước + `main-guard.yml`; không có branch protection.
- CI grep bí mật: bỏ qua `data/public/` (văn bản bên thứ ba chứa email mẫu), bỏ mẫu email; giữ `Sgod(2025|123)`, `sk-…`, thêm chuỗi thử nghiệm SGOD viết dưới dạng không tự khớp. README §7 đồng bộ lệnh.
- `--max-len`: tài liệu đồng bộ với `DEFAULT_MAX_LEN = 2560` của `training/finetune_qlora.py` (1536 chỉ còn được nhắc là giá trị làm 5 hàng vượt giới hạn).

## 2026-09-13 — sửa sau review Drop 0 (tài liệu + plumbing)

- `prompts/system_preamble_v1.txt`: bỏ hai chú thích HTML (chúng lọt vào `messages[0]` của mọi hàng SGOD và vào ngân sách token: 753 → 658 token); ghi chú trạng thái/lịch chốt chuyển sang `prompts/README.md` (mới); CI chặn `<!--` trong `prompts/*.txt`.
- Hợp đồng 2 (`docs/contracts/eval_metric.md`): §4 bước 3–4 xét **call đầu tiên** (strict first-call) đúng như `eval_toolcall.py`, ghi rõ đầu ra nhiều call; §3 `eval_set` = tên tệp + `eval_path`; §6 sha8 preamble = hash nội dung sau `.strip()` (giá trị scorer in), eval/tools = byte tệp. `results/INDEX.md` ghi chú tương ứng.
- `scripts/check_provenance.py`: đối chiếu cả số trần trong ô bảng có `%`/`(pp)` ở tiêu đề cột hoặc nhãn hàng và cột `p`; bỏ qua inline code, dòng `Ghi chú trục đo`, ngưỡng `≥50%`, alpha `p<0.05`. Fixture mới từ đầu ra thật: `tests/fixtures/eval_report_ok.md` (phải 0), `bootstrap_report_unindexed.md` (phải 1); `index_fixture.md` thêm R904–R909.
- `--max-len` cho bộ công khai: notebook 01 và CI dùng **2560** (hàng dài nhất 2.426 token; ở 1536 có 5 hàng vượt → `over_limit=5`). Cập nhật README §7/§9, hợp đồng 1 §4, `docs/roadmap.md`, `HUONG_DAN_LAM_VIEC.md` §6.1; CI thêm bước `finetune_qlora.py --dry-run --max-len 2560` (CPU, `transformers==5.12.1 jinja2`, không torch).
- CI grep bí mật viết lại không chứa chuỗi bí mật (`Sgod(2025|123)`), bỏ tự loại trừ `ci.yml`.
- `HUONG_DAN_LAM_VIEC.md` §1: Cell 1 trỏ về `notebooks/_setup_snippet.md` (token chỉ trong `.git/config` của VM tạm, không pip trong ô 1, push qua `origin`); §1.2 Kaggle tự nhận; §5 Drive mount ở Cell 3.
- Chưa sửa (ngoài quyền sở hữu, ghi ở báo cáo review): `docs/contracts/cli.md` thiếu `--timeout` của `predict_toolcall.py` và mục cho `tools/sgod/gen_tool_api_mapping.py`, `scripts/make_sample_pred.py`; kiểm tra `<!--` trong `validate_tools.py` / `validate_dataset.py`.

## 2026-09-13 — khởi tạo repo (Drop 0)

- Tạo cây thư mục `thanhhao98/ChatSystem` cho chương trình 6 thực tập sinh (nhóm D — Dữ liệu, nhóm F — Huấn luyện & Phục vụ, epic S — Hệ thống & hạ tầng tham chiếu).
- Bộ dữ liệu công khai `data/public/xlam_2k.*` (2.000 hàng xLAM, chia 1600/200/200 theo nhóm tool, seed 20260913) + `xlam_2k.eval.json` + `ATTRIBUTION.md`.
- Hợp đồng: `docs/contracts/cli.md`, `training_row_format.md`, `eval_metric.md`; preamble v0 và `fixed_replies.json`.
- Tài liệu: `README.md`, `HUONG_DAN_LAM_VIEC.md`, `docs/architecture.md`, `docs/roadmap.md`, `docs/serving.md`, `docs/personas_sgod.md` (stub), `docs/sgod-api-reference.md` (đã ẩn bí mật), `docs/onboarding_slides.pdf`.
- Plumbing: CI (`.github/workflows/ci.yml`), `main-guard.yml`, PR template, `.env.example`, `.gitignore`, `requirements.txt`, `results/INDEX.md` + `RUNLOG.md`, `scripts/check_provenance.py` + fixtures, `NOTICE.md`.
