# Notebook nhóm Fine-tune (F) — Colab / Kaggle T4

Ba notebook trong thư mục này là **giao diện chạy** cho các script chung trong `training/` (hợp đồng cờ:
`docs/contracts/cli.md`). Notebook chỉ *gọi* script; không cài đặt lại logic huấn luyện hay chấm điểm trong cell.
Nếu bạn thấy mình phải sửa code trong cell để có kết quả → dừng lại, đó là việc của một PR vào `training/`.

| Notebook | Task ClickUp | Cần GPU | Thời gian (T4) | Đầu ra chính |
|---|---|---|---|---|
| `01_qlora_sft_colab.ipynb` | F Tuần 1 | Có (T4, 15 GB) | *điền sau lần chạy kiểm chứng trên Colab T4* — ước lượng: smoke ≈ 3 phút, full 300 bước ≈ 45–90 phút | `$OUT/smoke/`, `$OUT/full/` (adapter, `checkpoint-*/`, `log_history.json`, `training_config.json`, `loss_curve.png`), `dry_run.log`, `train_*.log`, `resume.log` |
| `02_eval_toolcalling.ipynb` | F Tuần 2 | Có (T4) cho 2 bước dự đoán; chấm điểm và CI chạy CPU | *điền sau lần chạy kiểm chứng trên Colab T4* — ước lượng: 2 × 200 bản ghi ≈ 5–10 phút | `$OUT/results/public/{base,ft}_pred.jsonl`, `{base,ft}.json`, `{base,ft}.md`, `bootstrap.md`, `bootstrap.log` |
| `03_serve_vllm_colab.ipynb` | Bước nâng cao (không bắt buộc) | Có (T4) + `pip install vllm` | *điền sau lần chạy kiểm chứng trên Colab T4* — cài vLLM 3–10 phút, server 1–5 phút, 50 bản ghi < 2 phút | `$OUT/vllm_pred.jsonl`, `vllm_results.{json,md}`, `vllm_server.log` |

Thứ tự: 01 → 02 → (03). Notebook 02/03 cần adapter `$OUT/full` của 01, vì vậy **`RUN_NAME` phải giống nhau** ở cả ba.

## Chuẩn bị một lần

1. **GITHUB_TOKEN** — Personal access token (**classic**, scope `repo`; `thanhhao98/ChatSystem` là repo private thuộc tài khoản
   cá nhân nên token chi tiết theo repo không dùng được cho collaborator — cách tạo trong `notebooks/README.md`). Colab: biểu tượng
   chìa khóa ở thanh bên trái → *Add new secret* → Name `GITHUB_TOKEN` → bật *Notebook access*. Không dán token vào cell.
2. **Google Drive** — Cell 3 gọi `drive.mount`; chấp nhận quyền khi được hỏi. Thư mục kết quả sẽ là
   `MyDrive/ChatSystem/runs/<RUN_NAME>/`. Kiểm tra còn ≥ 2 GB trống (mỗi checkpoint 0.5B r16 ≈ 30–60 MB, adapter ≈ 10 MB,
   nhưng `optimizer.pt` trong checkpoint lớn hơn).
3. **GPU** — *Runtime → Change runtime type → T4 GPU*. Cell 2 phải in `Tesla T4 · 15 GB · (7, 5) · USE_BF16=False → fp16`.
4. **`HF_TOKEN`** không cần cho `Qwen/Qwen2.5-0.5B-Instruct` (model công khai).

## Cấu trúc chung của mỗi notebook

- **Cell 1 — Thiết lập:** copy nguyên văn từ `notebooks/_setup_snippet.md` (clone repo, `chdir`, đặt `REPO`, `GIT_SHA`,
  `IN_COLAB`, `AUTHOR`, hàm `run()`).
- **Cell 2 — Pins + GPU probe:** `pip install -q -r requirements-train.txt` (chỉ trên Colab/Kaggle) rồi in GPU, VRAM, compute
  capability, `USE_BF16`, phiên bản `torch / transformers / trl / peft / bitsandbytes / accelerate`.
- **Cell 3 — `OUT`:** mount Drive, đặt `RUN_NAME`, `OUT`.
- Các bước đánh số → gọi script bằng `!python …` (log `tee` vào `$OUT` để cell báo cáo đọc lại).
- **Cell cuối "## Tạo báo cáo":** in một khối Markdown `## Báo cáo <task> — <ngày> — <AUTHOR>`; **copy nguyên khối** dán vào
  bình luận task ClickUp. Mọi số trong khối được đọc từ file script ghi ra; `n/a` nghĩa là bước đó chưa chạy.

Cell có tag `gpu` (xem *View → Show cell toolbar → Tags* hoặc `metadata.tags` trong JSON) là cell cần GPU hoặc server đang
chạy; các cell còn lại chạy được trên CPU — kiểm tra tự động và review PR dựa vào tag này để chạy notebook không cần GPU.

## Nơi kết quả nằm

```
MyDrive/ChatSystem/runs/<RUN_NAME>/
├── dry_run.log · train_smoke.log · train_full.log · resume.log · vram_*.log
├── smoke/            adapter + log_history.json + training_config.json (200 hàng, 1 epoch)
├── full/             adapter_config.json · adapter_model.safetensors · checkpoint-50/ … checkpoint-300/
│                     log_history.json · training_config.json (resolved.peak_vram_gb, wall_clock_min, …) · loss_curve.png
├── results/public/   base_pred.jsonl · ft_pred.jsonl · base.json · ft.json · base.md · ft.md · bootstrap.md · bootstrap.log
└── vllm_pred.jsonl · vllm_results.json · vllm_results.md · vllm_server.log        (notebook 03)
```

Khi nộp kết quả lên repo: copy các tệp trong `results/public/` vào `results/public/` của repo trong PR (`ft/...`), thêm một dòng
`results/RUNLOG.md` và một hàng `results/INDEX.md` cho **mỗi con số** bạn báo cáo. Không commit checkpoint/adapter
(`runs/`, `*.safetensors`, `checkpoint-*/` đã gitignore) — adapter đưa lên Drive chung theo `docs/serving.md`.

## Lưu ý về cấu hình T4 cố định

- Notebook 01 dùng **`--max-len 2560`** (bằng mặc định hiện tại của script; ghi tường minh để cấu hình T4 không đổi nếu mặc định đổi) ở mọi bước — dry-run, smoke, full, resume.
  Lý do: hàng dài nhất của `data/public/xlam_2k.train.jsonl` là 2426 token (prompt + completion), của `val` là 1276;
  script **từ chối huấn luyện** khi có hàng vượt `--max-len` (không cắt ngầm). Với 2560, dry-run báo `over_limit=0` cho cả
  train và val; 0.5B NF4, `--batch-size 4 --grad-accum 4`, gradient checkpointing vẫn nằm trong 15 GB của T4.
  Nếu dry-run của bạn báo `over_limit > 0` thì dữ liệu trong repo đã đổi: **báo trong bình luận ClickUp kèm id + số token +
  `git HEAD`**, đừng tự xử; tuyệt đối không dùng `--max-rows` để "bỏ" hàng và không hạ `--max-len`.
- **Kaggle** (dùng khi hết quota Colab; 30 GPU-giờ/tuần): Cell 1 tự nhận Kaggle và đọc `GITHUB_TOKEN` từ *Add-ons → Secrets*.
  Kaggle không có Drive: kết quả nằm ở `/kaggle/working/runs/<RUN_NAME>` và **mất khi phiên kết thúc** → tải về hoặc
  *Save Version* trước khi tắt; checkpoint để resume vì vậy chỉ có ý nghĩa trong cùng phiên.
- Đường dẫn Drive `MyDrive/ChatSystem/runs/<RUN_NAME>` không được chứa dấu cách (các dòng `!python … $OUT/…` không quote).

## Lỗi Colab thường gặp và cách xử lý

| Triệu chứng | Nguyên nhân | Xử lý |
|---|---|---|
| `torch.cuda.OutOfMemoryError: CUDA out of memory` khi huấn luyện | batch × độ dài chuỗi quá lớn cho 15 GB | Giảm `--batch-size 2` và tăng `--grad-accum 8` (giữ effective batch = 16); nếu vẫn OOM, thử `--batch-size 1 --grad-accum 16`. **Không** hạ `--max-len`: với dữ liệu hiện tại mọi giá trị dưới 2426 làm script thoát mã 1. Ghi thay đổi vào báo cáo. |
| Phiên bị ngắt giữa lúc huấn luyện (idle, hết quota, "Runtime disconnected") | Colab miễn phí | Kết nối lại, chạy Cell 1 → 2 → 3, rồi chạy lại **cùng lệnh** với `--resume-from-checkpoint $OUT/full/checkpoint-<N>` (N = checkpoint mới nhất trên Drive có đủ `trainer_state.json` + `optimizer.pt`). Notebook 01 Bước 4 diễn tập đúng việc này. |
| `ValueError: Attempting to unscale FP16 gradients` | Tham số LoRA đang ở fp16 thay vì fp32 — nghĩa là `prepare_model_for_kbit_training` không chạy hoặc phiên bản `peft`/`trl` lệch pins | Không sửa trong notebook: bước đó nằm **trong** `training/finetune_qlora.py`. Kiểm tra Cell 2 in đúng phiên bản `requirements-train.txt`; nếu đúng pins mà vẫn lỗi → mở issue kèm log; script được sửa qua PR vào `training/`. |
| `finetune_qlora --dry-run: FAIL … over_limit=N` hoặc script thoát mã 1 với "exceed --max-len" | Có hàng dài hơn `--max-len` (bạn đặt `--max-len` thấp hơn 2426, hoặc dữ liệu trong repo đã đổi) | Kiểm tra `--max-len` ≥ 2426 (notebook dùng 2560, bằng mặc định script); nếu đúng mà vẫn FAIL → dữ liệu trong repo đã đổi, xem *Lưu ý về cấu hình T4 cố định* ở trên, ghi vào comment của task và mở issue. Không dùng `--max-rows`. |
| `assert '<tools>' in prompt` FAIL hoặc `unmasked completion tokens: 0` | Hàng dữ liệu sai định dạng (thiếu `replay_tools`, assistant rỗng) hoặc chat template không render tools | Chạy `python training/validate_dataset.py data/public/xlam_2k.train.jsonl`; báo nhóm Dữ liệu kèm id hàng. |
| `NO CUDA GPU` ở Cell 2 | Runtime chưa bật GPU hoặc hết quota GPU | *Runtime → Change runtime type → T4 GPU*; hết quota → chờ hoặc chuyển Kaggle (30 GPU-giờ/tuần). |
| `GITHUB_TOKEN chưa có trong Secrets` / `git clone` 403 | Chưa tạo secret, chưa bật *Notebook access*, hoặc token thiếu quyền đọc repo | Tạo lại Personal access token (classic) với scope `repo` (tài khoản của bạn phải là collaborator của `thanhhao98/ChatSystem`); bật *Notebook access*; chạy lại Cell 1. |
| `drive.mount` treo hoặc `Permission denied` khi ghi `$OUT` | Chưa chấp nhận quyền Drive, hoặc Drive đầy | Chạy lại Cell 3, chấp nhận quyền; dọn Drive (xóa `checkpoint-*` của lượt cũ). |
| `eval_toolcall.py` thoát mã 2 "header sha256 mismatch" | File dự đoán được tạo trên một phiên bản khác của `xlam_2k.eval.json` | **Không** dùng `--no-header-check` để cho qua. `git pull`, chạy lại dự đoán trên đúng bộ eval; nếu bộ eval đã đổi thì đó là trục đo mới — ghi chú. |
| Sau `pip install vllm`, `import torch` hoặc `transformers` lỗi `undefined symbol` | vLLM kéo `torch` phiên bản khác | Restart session; chỉ dùng vLLM trong phiên riêng; nếu vẫn lỗi → phần *Dự phòng* của notebook 03 (kết quả notebook 02 là đủ). |
| Phiên bản in ở Cell 2 khác `requirements-train.txt` | Colab đổi image (thường là `torch`) | Không tự sửa pins; ghi vào comment của task và mở issue kèm dòng phiên bản — pins được kiểm tra lại và cập nhật qua PR + `CHANGELOG.md`. |
| Notebook chạy xong nhưng cell báo cáo toàn `n/a` | Bước tương ứng chưa chạy, hoặc `RUN_NAME` khác lượt trước nên `$OUT` trống | Kiểm tra `OUT` in ở Cell 3 và thư mục trên Drive. |

## Trước khi commit notebook

```bash
jupyter nbconvert --clear-output --inplace notebooks/finetune/<file>.ipynb
```

Repo không chứa output chạy (và không lỡ chứa token). Kết quả đi vào `results/` + RUNLOG + INDEX như trên.
