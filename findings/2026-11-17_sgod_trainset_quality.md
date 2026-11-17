# Báo cáo Chất lượng Bộ dữ liệu Huấn luyện SGOD (Track B Trainset)

> **Ghi chú trục đo** — eval: `data/sgod/eval_v1.json` @ `1f5bd32` · tools: `tools/sgod/sgod_tools.json` @ `4d9abda` · preamble: `prompts/system_preamble_v1.txt` @ `d3fe548` · leakage_threshold: 0.65 · yield_budget: 0.58.

---

## 1. Mục tiêu & Bối cảnh Thực hiện

- **Mã công việc:** `[D-V5]` (Task ID ClickUp: `z8rzdfntre`)
- **Nhóm thực hiện:** Nhóm D — Data (`Thehy-IT` - Lead, `BaoMyTH` - Member 1, `Hồ Văn Dinh` - Member 2)
- **Nhánh tính năng:** `data/v5-thehy` (Target PR: `dev`)
- **Bàn giao hạ nguồn:** Nhóm F Task 4 (`[F-V4]` — Fine-tuning SLM) & Nhóm S Task 9 (`[S-V9]` — Serving GPU vLLM).

---

## 2. Thống kê Quy mô qua từng Công đoạn (Rows per Stage)

| Công đoạn (Stage) | Tệp dữ liệu đầu ra | Số lượng records | Tỷ lệ cơ cấu | Ghi chú |
| :--- | :--- | :---: | :---: | :--- |
| **Stage 1 (Generate)** | `data/sgod/raw.json` | 4.709 | - | Sinh từ `TRACKB_BUCKET_PLAN` (Scale 7.5, raw ≈ N/0.58) |
| **Stage 2 (Label)** | `data/sgod/labeled.json` | 4.709 | - | Đồng thuận đa mô hình (Consensus Qwen2.5-3B) |
| **Stage 3 (Verify)** | `data/sgod/verified.json` (raw) | 4.537 | - | Vượt qua bộ lọc schema, RBAC và semantics |
| **Stage 4 (Quarantine Triage)** | `data/sgod/salvage_baomy.json` | +127 | - | Cứu chữa 127/171 ca lỗi thiếu `maintenanceScheduleId` |
| **Domain Verified Final** | `data/sgod/verified.json` (merged) | 4.663 | - | Tỷ lệ Yield: **99,02%** (4.663 / 4.709) |
| **Stage 5 (Irrelevance)** | `data/sgod/irrelevance.json` | 500 | 10.0% | No-call / chitchat / out-of-scope / procedure |
| **Stage 6 (Replay Buffer)** | `data/sgod/replay.train.jsonl` | 1.750 | 35.0% | Public xLAM 2k (1.600 train + 150 val bù thiếu) |
| **Stage 7 (Assemble - Train)** | `data/sgod/train.jsonl` | **4.863** | - | 2.613 domain + 1.750 replay + 500 irrelevance |
| **Stage 7 (Assemble - Val)** | `data/sgod/val.jsonl` | **137** | - | Trích xuất 5% chỉ từ luồng Domain SGOD verified |
| **Tổng quy mô bàn giao** | `train` + `val` | **5.000** | 100% | Khớp chính xác `MIX_TARGETS.final_target = 5000` |

---

## 3. Các Chỉ số Chất lượng Cốt lõi & Kiểm định Gác cổng

### 3.1 Tỷ lệ Năng suất (Yield Rate)
- **Kỳ vọng thiết kế:** $\approx 58\%$
- **Sàn kỹ thuật bắt buộc:** $\ge 45\%$
- **Thực tế đạt được:** $4.663 / 4.709 = \mathbf{99{,}02\%}$ $\rightarrow$ **PASS ✅ (Vượt xa kỳ vọng)**.

### 3.2 Kiểm toán Chống rò rỉ Dữ liệu Tuyệt đối (Zero Data Leakage)
Toàn bộ câu hỏi người dùng được đối soát SequenceMatcher độc lập so với 650 câu benchmark cấm (500 câu `eval_v1.json` + 150 câu `eval_human_core.jsonl`) theo ngưỡng $\text{Sim} < 0.65$:
- `verified.json` (4.663 câu): Max Similarity = **0.6496** $\rightarrow$ **0 vi phạm (PASS ✅)**
- `irrelevance.json` (500 câu): Max Similarity = **0.6226** $\rightarrow$ **0 vi phạm (PASS ✅)**
- `train.jsonl` (4.863 câu): Max Similarity = **0.6496** $\rightarrow$ **0 vi phạm (PASS ✅)**
- `val.jsonl` (137 câu): Max Similarity = **0.6408** $\rightarrow$ **0 vi phạm (PASS ✅)**

### 3.3 Kiểm toán Tính tương thích API (API Catalogue Alignment)
- Script: `datagen/audit_trainset_vs_api.py`
- Kết quả: `3250/3250 domain rows align with the current catalogue (0 misaligned)` $\rightarrow$ **PASS ✅**.

### 3.4 Kiểm định Cú pháp & Preamble Nghiêm ngặt (Strict Validation Gate)
- Script: `training/validate_dataset.py` (chạy trên domain train 3.113 dòng + val 137 dòng)
- Tham số bắt buộc: `--preamble prompts/system_preamble_v1.txt --tools tools/sgod/sgod_tools.json --roles tools/sgod/roles.json` (Tuyệt đối không dùng `--no-preamble-check`).
- Kết quả: `validate_dataset: PASS files=2 rows=3250 errors=0` $\rightarrow$ **Exit Code 0 (PASS ✅)**.

---

## 4. Phân bổ Cơ cấu & Định dạng Dữ liệu

### 4.1 Cơ cấu Targets trong tập `train.jsonl`
- **Tool Calling (`<tool_call>`):** 3.861 dòng (79,4%)
- **Deflect (Từ chối lịch sử / ngoài phạm vi):** 760 dòng (15,6%)
- **Refusal (Chặn quyền hạn RBAC):** 242 dòng (5,0%)

### 4.2 Cơ cấu Stream
- **Domain Verified SGOD:** 2.613 dòng train + 137 dòng val = 2.750 dòng (55,0%)
- **Replay xLAM (Public):** 1.750 dòng train (35,0%)
- **Irrelevance (No-call):** 500 dòng train (10,0%)

---

## 5. Mã Băm Xác thực Dữ liệu (Git-stream SHA256)

Mã băm được tính toán thông qua luồng byte chuẩn LF từ Git database (`git show HEAD:<path> | sha256sum`), bảo đảm miễn nhiễm hoàn toàn với lỗi xuống dòng CRLF trên Windows:

```text
train.jsonl: bed2022596cd1200381fa8157a14b38d829be25a5c1ba82cbcb71c05faae9b20
val.jsonl:   d71df9124faa05edb3acbb063c403e0becfd6aee374c9221b6f888378cc2ed67
```

---

## 6. Biên bản Bàn giao Hạ nguồn (Handoff)

- **Bàn giao Nhóm F Task 4 (`[F-V4]` — Fine-tuning SLM):**
  - Tập huấn luyện: `data/sgod/train.jsonl` (4.863 dòng, định dạng Parity format với Preamble v1 & placeholders).
  - Tập dev/val: `data/sgod/val.jsonl` (137 dòng, 100% domain SGOD).
  - Tỷ lệ targets: 79,4% Tool calling, 15,6% Deflect, 5,0% Refusal.
- **Bàn giao Nhóm S Task 9 (`[S-V9]` — Serving GPU vLLM):**
  - Hệ thống nhãn: 22 SGOD tools đã căn chỉnh 100% với `tools/sgod/sgod_tools.json`.
  - Không có rò rỉ thông tin so với benchmark `eval_v1`.
