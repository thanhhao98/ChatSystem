# Notebooks — hướng dẫn nhanh

Mỗi notebook tương ứng **một task ClickUp** và kết thúc bằng ô `## Tạo báo cáo` in ra khối Markdown để dán vào comment của task.
Notebook chỉ **gọi** các script trong `datagen/`, `training/`, `tools/sgod/` (cờ cố định trong `docs/contracts/cli.md`),
không cài đặt lại logic chấm điểm hay định dạng dữ liệu.

| Notebook | Task ClickUp | Tạo ra gì | Runtime | Thời gian dự kiến |
|---|---|---|---|---|
| `data/01_explore_public_dataset.ipynb` | D Tuần 1 — Dựng môi trường và khám phá bộ dữ liệu công khai xLAM (2k hàng gốc) | Thống kê lát 2k (rows, tools/row, calls/row, args/call, độ dài query, top-20 tool, số hàng answers parse JSON), 2 biểu đồ, 3 ví dụ; khối báo cáo | CPU (Colab hoặc local; không cần token) | ~2 phút |
| `data/02_preprocess_to_chatml.ipynb` | D Tuần 2 — Tiền xử lý về định dạng hàng huấn luyện (parity, `<tool_call>`) và chia train/val/test | `/tmp/xlam_2k.{train,val,test}.jsonl` + `/tmp/xlam_2k.eval.json` tái tạo từ raw; sha256 id khớp bản commit; 0 tool-set dùng chung; exit code `validate_dataset.py`; 1 prompt render có `<tools>`; histogram token + `% > 2560` (`--max-len` của F Tuần 1); khối báo cáo | CPU (tải tokenizer Qwen 0.5B, vài MB) | ~3–5 phút |
| `data/03_validate_dataset.ipynb` | Tiện ích cho D Tuần 2 và D Việc 5 (hàng SGOD) | Chạy `training/validate_dataset.py` trên danh sách file tự điền; số hàng, exit code, 3 hàng lỗi đầu, giải thích loại lỗi; khối báo cáo | CPU (chỉ stdlib, không cần pip) | < 1 phút |
| `finetune/01_qlora_sft_colab.ipynb` | F Tuần 1 — Dựng môi trường Colab và chạy QLoRA SFT nhẹ (Qwen2.5-0.5B-Instruct) trên lát xLAM 2k | Adapter LoRA trên Drive, `log_history.json`, loss curve, peak VRAM, 1 lần sinh `<tool_call>`; khối báo cáo | GPU T4 (Colab/Kaggle) | điền sau lần chạy kiểm chứng trên Colab T4 |
| `finetune/02_eval_toolcalling.ipynb` | F Tuần 2 — Đánh giá pretrained vs fine-tuned trên test công khai | `results/{base,ft}_pred.jsonl`, `results.json`, bảng accuracy + CI 95% + McNemar; khối báo cáo | GPU T4 | điền sau lần chạy kiểm chứng trên Colab T4 |
| `finetune/03_serve_vllm_colab.ipynb` (tuỳ chọn) | F Tuần 2 — bước nâng cao | vLLM `--dtype half` + LoRA, 1 request `chat.completions` với `tools=`, p50 latency | GPU T4 | điền sau lần chạy kiểm chứng trên Colab T4 |

## Cách mở trên Colab

1. Tạo **Personal access token (classic)** trên GitHub (*Settings → Developer settings → Personal access tokens →
   Tokens (classic) → Generate new token (classic)*), tick scope **`repo`**, hạn ≤ 90 ngày. `thanhhao98/ChatSystem` là repo
   **private thuộc tài khoản cá nhân** và bạn là *collaborator*, nên chỉ token classic mới clone/push được (token chi tiết
   theo repo không hoạt động với collaborator). Không in token ra output, không dán vào cell, không commit.
2. Colab → biểu tượng chìa khoá (**Secrets**) → *Add new secret*: Name `GITHUB_TOKEN`, Value = token; bật **Notebook access**.
   (Token Hugging Face, nếu cần cho bước nâng cao, cũng để ở đây với tên `HF_TOKEN`.)
3. Mở notebook: *File → Open notebook → GitHub*, tick **Include private repos**, chọn `thanhhao98/ChatSystem` và file;
   hoặc *Upload* file `.ipynb` từ bản clone trên máy.
4. `Runtime → Run all`. Ô thiết lập tự clone repo vào `/content/ChatSystem`. Ô cuối in khối báo cáo → dán vào ClickUp.

Kaggle: thêm `GITHUB_TOKEN` trong *Add-ons → Secrets* và bật cho notebook; ô thiết lập tự đọc bằng `kaggle_secrets`
(xem `_setup_snippet.md`).

## Cách chạy trên máy cá nhân

```bash
git clone https://github.com/thanhhao98/ChatSystem && cd ChatSystem
python -m pip install -r requirements.txt matplotlib transformers jupyter
jupyter lab notebooks/data/01_explore_public_dataset.ipynb
```

`requirements.txt` cố ý chỉ giữ pins tối thiểu cho CI (`openai`, `requests`, `numpy`, `pyyaml`); notebook data cần thêm
`matplotlib` (biểu đồ ở 01/02), `transformers` (tokenizer Qwen ở 02 — **không cần torch**) và `jupyter` để chạy local,
nên cài kèm như dòng trên. Notebook `03` chỉ dùng stdlib. Trên Colab ba thư viện này đã có sẵn.
Pins GPU (torch, peft, trl, bitsandbytes…) nằm ở `requirements-train.txt` và chỉ cài trong notebook `finetune/`.

Ô thiết lập tự tìm gốc repo (`docs/contracts/cli.md`) nên mở notebook từ thư mục con nào cũng được.

## Quy tắc

- **Không commit output.** Trước khi commit: `jupyter nbconvert --clear-output --inplace notebooks/<track>/<file>.ipynb`.
  Notebook còn output sẽ bị từ chối khi review PR (có thể chứa token hoặc kết quả chạy không truy vết).
- **Không sửa cờ của script trong notebook**; nếu cần cờ mới → PR sửa script + `docs/contracts/cli.md` + `CHANGELOG.md`.
- **Mọi con số dán lên ClickUp** phải kèm `git HEAD` (ô thiết lập in ra) và tên notebook — quy tắc truy vết trong
  `Quy tắc bắt buộc — Mọi con số phải truy vết được`.
- Notebook mới phải dùng đúng ô thiết lập trong `_setup_snippet.md` và kết thúc bằng ô `## Tạo báo cáo`.
- File tạm ghi ra `/tmp/` (Colab) hoặc Google Drive (kết quả huấn luyện); không ghi đè `data/public/`.
