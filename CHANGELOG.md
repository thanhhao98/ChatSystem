# CHANGELOG
- 2026-10-10 — [S-V1] trích xuất OpenAPI JSON, script tự động hoá extract_openapi.py và bảng query_params.md cho 22 GET endpoints SGOD (asset, auth, chat).
- 2026-10-14 — [F-V1] bổ sung lưới recipe chạy lại trên RTX PRO 6000 (bf16) của pthao3113: dự đoán + kết quả 6 run trong `results/public/recipe_grid_bf16/` (gồm arm 1.5B `recipe_arm_1p5b.yaml`, bắt buộc, và arm tự chọn `recipe_arm_r32.yaml`), bootstrap anchor-vs-arm và đối chiếu chéo T4↔bf16 (`bootstrap_ci.py --md`), INDEX R031–R054, 8 dòng RUNLOG, 6 dòng `results.csv`, mục *Bổ sung* trong `findings/2026-10-02_recipe_grid_xlam.md`; lần chạy T4 của wynn187z chỉ ghi chú, không có số (không commit tệp kết quả) (PR #11).
- 2026-10-14 — [F-V2] baseline GPT trên eval_v1 nhận dòng INDEX kế tiếp còn trống thay cho R001 (R001–R030 đã dùng cho F Tuần 2 + F Việc 1): `docs/roadmap.md`, `docs/contracts/eval_metric.md` (PR #4).
- 2026-10-14 — [F-T2][F-V1] sửa sau review: `training/recipes/results.csv` chép đúng `results.json` (param_acc, json_valid_rate, tool_name_acc của comp0); cột `arm` = khoá `arm` trong yaml (`arm_*`); RUNLOG `data@sha8` = `933c4ecd` (`xlam_2k.train.jsonl`) cho 5 run của lưới (huấn luyện 2026-10-02); INDEX: git sha/ngày khớp header dự đoán, lệnh đầy đủ, thêm R029–R030 (json_valid_rate base/ft); findings ghi đủ trục đo, cấu hình `--no-amp`, arm free không cho thông tin; notebook 04 dùng ô thiết lập + ô probe chuẩn, `--model-path`, bỏ arm 1.5B; `notebooks/finetune/README.md` liệt kê notebook 04; khôi phục mục [F-T2] bị mất ở merge `e2ef147` (PR #4).
- 2026-10-07 — [F-V1] lưới recipe trên lát xLAM: anchor + 4 arm (`training/recipes/recipe_arm_{r8,lr2e4,comp0,free}.yaml`), dự đoán + `results.json` trong `results/public/`, `findings/2026-10-02_recipe_grid_xlam.md`, INDEX R012–R028, 5 dòng RUNLOG, 5 dòng `results.csv`, notebook `notebooks/finetune/04_recipe_grid_colab.ipynb` (PR #4).
- 2026-09-25 — [F-T2] base vs ft trên `data/public/xlam_2k.eval.json`: dự đoán, `results/public/{base,ft}.{json,md}`, bootstrap CI + McNemar (`results/public/bootstrap.md`), INDEX R001–R011, 2 dòng RUNLOG; notebook 02 gỡ `torchao` ở Cell 2 (PR #4).
- 2026-09-19 — [D-T1] hoàn thành khảo sát bộ dữ liệu công khai xLAM 2k raw và báo cáo nghiệm thu tuần 1 (nhóm D).
- 2026-09-18 — repo chuyển sang public + bảo vệ nhánh main (PR, 1 approve, CI `checks`); thay địa chỉ gateway nội bộ trong spec bằng placeholder `<SGOD_GATEWAY>`; secret grep CI thêm mẫu IP nội bộ.

Mọi thay đổi đáng kể của repo ghi ở đây, **trong cùng commit** với thay đổi (quy tắc PR). Định dạng:
`YYYY-MM-DD — [mã việc] tóm tắt (PR #n)`. Mới nhất ở trên.

## 2026-10-14 — [D-V1] danh mục tool SGOD v1: 22 tool chỉ đọc, tool_policy, mapping — nhóm D: Hy, My, Dinh (PR #5)

- `tools/sgod/sgod_tools.json`: từ 3 tool mẫu lên 22 tool chỉ đọc (`writes: false`). Nền là PR #5 (Hy, 21 tool); gộp `list_maintenance_tasks` từ PR #6 (My) với query bắt buộc `maintenanceScheduleId`, và `list_enterprise_users` (chỉ `company_admin`) từ PR #7 (Dinh) với `search`/`status`/`limit`/`cursor` theo `docs/sgod/openapi-*.json` (PR #9). Giữ từ PR #5: chặn 5 GET hỏng của spec §4; `/sgod-chat/v1` chỉ cho `company_admin`.
- Đối chiếu bằng gọi thật trên hạ tầng tham chiếu (2026-10-14, tài khoản thử enterprise): bỏ `search_assets` (`/assets/suggest` → 404, trùng `list_my_assets`); `get_asset_statistics` trỏ `GET /sgod-asset/v1/assets/summary` (`/dashboard/statistics-asset` → 404); 3 tool mẫu: `list_my_assets` dùng `search` (API bỏ qua `q`, `status`), `list_maintenance_schedules` enum `completed` (`complete` → 400), `get_asset` / `get_asset_histories` resolve bằng `GET /assets?search=`; `list_asset_transfers` thêm `onlyMine`; mô tả `get_enterprise_profile` theo trường thật. Kết quả từng lần gọi ghi trong `x_sgod.notes`.
- Rút gọn mô tả (bỏ nhãn "(company_admin)" thừa và câu phân trang lặp lại; bỏ "phòng ban" khỏi `list_locations`; lấy mô tả chính xác hơn từ PR #6/#7) để vừa ngân sách: lượt system company_admin 3332/3400 token, employee 2818.
- `prompts/system_preamble_v1.txt`: hai dòng *Quy tắc chọn tool* đổi theo (`search`, `completed`); sha256 nội dung sau `.strip()` `6352dac1…` → `f5da2272…` (`prompts/README.md`). Chưa có hàng SGOD hay dự đoán nào dùng preamble v1.
- `docs/sgod-api-reference.md` (§2, §3, §4), `docs/sgod/candidate_tools.md`, `docs/architecture.md`, `datagen/config_sgod.py` (`schedule_status`): đồng bộ theo gọi thật.
- `tools/sgod/tool_policy.json`: 1:1 với 22 tool. `tools/sgod/tool_api_mapping.md`: sinh lại bằng `gen_tool_api_mapping.py` (`--check` OK).

## 2026-09-23 — [F-T1] điều chỉnh dtypes tham số LoRA sang fp32 và khôi phục fp16=True trong SFTConfig theo feedback review

- `training/finetune_qlora.py`: Ép các tham số LoRA trainable về `float32` (kế thừa cơ chế chuẩn của `prepare_model_for_kbit_training`), sử dụng `dtype=HALF` trong `from_pretrained`, và giữ fp16 AMP (GradScaler) bật mặc định trong `SFTConfig` để có loss scaling chống underflow/NaN; thêm cờ `--no-amp` làm lối thoát nếu runtime T4 vẫn lỗi ở `grad_scaler.unscale_` (PR #1).
- `training/predict_toolcall.py`: Đóng gói patch `is_torchao_available` thành helper gọn trước lệnh nạp `PeftModel`.
- `notebooks/finetune/01_qlora_sft_colab.ipynb`: Thêm `pip uninstall -y -q torchao` ở Cell 2 để làm sạch môi trường Colab pre-installed packages.

## 2026-09-17 — [F-T1] cập nhật cờ --resume-from-checkpoint sang checkpoint-250 và sửa lỗi torchao trong predict_toolcall.py

- `notebooks/finetune/01_qlora_sft_colab.ipynb`: Đổi cờ `--resume-from-checkpoint $OUT/full/checkpoint-100` thành `checkpoint-250` ở Bước 4 (diễn tập ngắt kết nối) phù hợp với số checkpoint tối đa được giữ lại (`SAVE_TOTAL_LIMIT = 2`).
- `training/predict_toolcall.py`: Thêm guard `is_torchao_available` nhằm bỏ qua kiểm tra phiên bản `torchao` cũ (<0.16.0) cài sẵn trên môi trường Colab mới.

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
