# training/recipes — công thức huấn luyện (recipe) và bảng kết quả

Thư mục này giữ **các recipe cố định** cho lưới thí nghiệm của nhóm Fine-tune (F Việc 1 và F Việc 4)
cùng bảng `results.csv` để so sánh các arm với nhau. Mục tiêu: mọi lần chạy đều tái lập được từ
đúng một file yaml + một dòng lệnh, không ai phải nhớ "hôm đó mình gõ lr bao nhiêu".

## 1. File yaml = tập giá trị mặc định cho các cờ của `finetune_qlora.py`

- Mỗi khóa trong yaml là **tên một cờ** của `training/finetune_qlora.py`, viết dạng gạch dưới:
  `--lora-rank` → `lora_rank`, `--max-rows` → `max_rows`, `--completion-only` → `completion_only`.
  Danh sách cờ hợp lệ: `python training/finetune_qlora.py --help` (và `docs/contracts/cli.md`).
- Khóa lạ (không phải cờ) làm script **dừng với lỗi**, trừ hai khóa metadata `arm` và `notes`.
- Giá trị trong yaml chỉ là **mặc định**: cờ gõ trực tiếp trên dòng lệnh luôn ghi đè.
  Vì vậy `--data`, `--val`, `--output-dir`, `--seed` thường để ngoài yaml và truyền khi chạy.
- Viết số thực có mũ dạng `1.0e-4` (YAML coi `1e-4` là chuỗi; script vẫn ép kiểu được nhưng hãy
  viết đúng cho dễ đọc).

Ví dụ chạy arm neo (anchor) với seed 42:

```bash
python training/finetune_qlora.py --recipe training/recipes/public_anchor.yaml \
    --data data/public/xlam_2k.train.jsonl --val data/public/xlam_2k.val.jsonl \
    --output-dir runs/public_anchor_s42
```

Luôn chạy `--dry-run` trước (CPU, không tải model) để chắc chắn không hàng nào dài hơn `max_len`:

```bash
python training/finetune_qlora.py --recipe training/recipes/public_anchor.yaml \
    --data data/public/xlam_2k.train.jsonl --dry-run
```

## 2. Thêm một arm mới

1. Copy `public_anchor.yaml` thành `<tên_arm>.yaml`, đổi `arm:` và **đúng một trục** so với anchor
   (ví dụ `lora_rank: 8`, hoặc `lr: 2.0e-4`, hoặc `completion_only: 0`). Đổi nhiều trục cùng lúc thì
   không kết luận được trục nào gây khác biệt.
2. Giữ nguyên `max_rows`, `seed`, `epochs`, `max_len` (2560 — hàng dài nhất của lát 1000 là 2426 token),
   `batch_size`, `grad_accum` của anchor.
3. Chạy `--dry-run` → chạy thật trên Colab/Kaggle → chấm bằng
   `training/predict_toolcall.py` + `training/eval_toolcall.py` → CI bằng `training/bootstrap_ci.py`
   với `--pair anchor <arm>`.
4. Mở PR trên nhánh `ft/...` gồm: file yaml, dòng mới trong `results.csv`, dòng trong
   `results/RUNLOG.md`, hàng `R###` trong `results/INDEX.md` và file kết quả dưới `results/`.

## 3. Thêm một dòng vào `results.csv`

`results.csv` là bảng CSV **chỉ thêm dòng, không sửa dòng cũ**. Mỗi lần chạy hoàn tất = một dòng.
Cột (đúng thứ tự, không thêm cột mới nếu chưa sửa README này):

| cột | lấy từ đâu | ví dụ |
|---|---|---|
| `arm` | khóa `arm` trong yaml | `public_anchor` |
| `model` | `training_config.json` → `args.model` | `Qwen/Qwen2.5-0.5B-Instruct` |
| `lora_rank` | `args.lora_rank` | `16` |
| `lr` | `args.lr` | `0.0001` |
| `completion_only` | `args.completion_only` | `1` |
| `mask_fn_names` | `args.mask_fn_names` | `0.0` |
| `epochs` | `args.epochs` | `1` |
| `max_rows` | `args.max_rows` (để trống nếu dùng cả file) | `1000` |
| `seed` | `args.seed` | `42` |
| `steps` | `training_config.json` → `resolved.steps` | `63` |
| `wall_clock_min` | `resolved.wall_clock_min` | `18.4` |
| `gpu` | `resolved.gpu` | `Tesla T4` |
| `tool_name_acc` | `results.json` của `eval_toolcall.py` → khoá **cùng tên** `tool_name_acc` — độ chính xác tên tool, **phần trăm 0–100** đúng như script ghi | `82.5` |
| `param_acc` | `results.json` → khoá `param_acc` — độ chính xác tham số, phần trăm 0–100 | `73.5` |
| `json_valid_rate` | `results.json` → khoá `json_valid_rate` — tỉ lệ đầu ra parse được JSON, phần trăm 0–100 | `99.5` |
| `ci_lo`, `ci_hi` | `bootstrap_ci.py` — biên dưới/trên CI 95% của strict accuracy, chép nguyên hai số trong ngoặc `[lo, hi]` mà script in (phần trăm) | `68.5`, `80.5` |
| `results_file` | đường dẫn file kết quả trong repo | `results/public/ft_public_anchor_s42.json` |
| `who` | tên/ nick GitHub người chạy | `nguyenvana` |
| `date` | ngày chạy, ISO | `2026-10-05` |

Quy ước: **mọi số đo là phần trăm 0–100, chép nguyên như `eval_toolcall.py` / `bootstrap_ci.py` in ra**
(1 chữ số thập phân, ví dụ `82.5`) — KHÔNG chia cho 100, KHÔNG thêm ký hiệu `%`, không đổi tên cột cho khác
khoá JSON (`tool_name_acc`, `param_acc`, `json_valid_rate`). Ô không có giá trị để trống, không ghi `N/A`. Con số trong `results.csv` chỉ có ý nghĩa khi cùng lúc có dòng trong
`results/RUNLOG.md` và hàng trong `results/INDEX.md` (quy tắc "mọi con số phải truy vết được").

## 4. Các file có sẵn

| file | vai trò |
|---|---|
| `public_anchor.yaml` | arm neo: 0.5B, r16/α32, lr 1e-4, completion-only, 1 epoch, 1000 hàng đầu, seed 42, max_len 2560 |
| `results.csv` | bảng kết quả (chỉ có dòng tiêu đề khi khởi tạo) |
| `sgod_v1.yaml` | *(F Việc 4 sẽ thêm)* recipe cho bộ SGOD |

Lưới F Việc 1 dự kiến (≤ 6 lần chạy): anchor · `r8` · `lr2e-4` · `full_loss` (`completion_only: 0`,
chỉ quan sát) · `1p5b` (model `Qwen/Qwen2.5-1.5B-Instruct`) · một arm tự chọn. Kết quả mong đợi:
giữ anchor làm mặc định; nếu khác, nêu rõ trong `docs/reports/<ngày>_recipe_grid_xlam.md`.
