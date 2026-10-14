# Lưới recipe F Việc 1 trên lát xLAM công khai — Bootstrap CI + McNemar (anchor vs từng arm)

> **Ghi chú trục đo** — eval: `data/public/xlam_2k.eval.json` @ `6d8c803e` · tools: theo từng bản ghi · preamble: `ebcae911` · scorer: `eval_toolcall/1.2 (strict first-call; params >= half of keys; unknown tool = violation)` · sampling: greedy, temperature 0, max_new_tokens 256, fp16, batch 8 (backend transformers) · bootstrap: percentile, 2000 resamples, seed 20260625; margin H1 = 5pp; McNemar exact two-sided. Chỉ so sánh các run chấm trên cùng eval/tools/preamble sha256; không so sánh với bảng ở trục khác.

## Cấu hình chung của 5 lượt huấn luyện

- Base `Qwen/Qwen2.5-0.5B-Instruct`, QLoRA qua `training/finetune_qlora.py --recipe <yaml>`; dữ liệu: 1000 hàng đầu
  (`max_rows: 1000`) của `data/public/xlam_2k.train.jsonl` @ `933c4ecd`, val `data/public/xlam_2k.val.jsonl`.
- 1 epoch = 63 bước (batch 4 × grad-accum 4), seed 42, `max_len` 2560, `save_steps` 50 — giống hệt `public_anchor.yaml`.
- Cả 5 lượt chạy trên Tesla T4 với cờ `--no-amp` (tắt fp16 AMP/GradScaler) — dùng nhất quán cho anchor và mọi arm.
- Adapter được huấn luyện ngày 2026-10-02 (lưu trên Drive). Dự đoán + chấm điểm có trong repo được chạy lại ngày
  2026-10-07 @ `b803e0c` từ đúng các adapter đó: `sampling.adapter` trong header của từng `results/public/*_pred.jsonl`
  ghi thư mục adapter tương ứng (cột cuối bảng dưới).

| run (`--run`) | yaml | trục đổi so với anchor | thư mục adapter |
|---|---|---|---|
| anchor | `training/recipes/public_anchor.yaml` | — | `public_anchor_s42` |
| arm_r8 | `training/recipes/recipe_arm_r8.yaml` | `lora_rank` 16 → 8, giữ `lora_alpha` = 2 × rank (32 → 16) | `recipe_arm_r8_s42` |
| arm_lr2e4 | `training/recipes/recipe_arm_lr2e4.yaml` | `lr` 1.0e-4 → 2.0e-4 | `recipe_arm_lr2e4_s42` |
| arm_comp0 | `training/recipes/recipe_arm_comp0.yaml` | `completion_only` 1 → 0 (full loss — chỉ quan sát) | `recipe_arm_comp0_s42` |
| arm_free | `training/recipes/recipe_arm_free.yaml` | `lora_dropout` 0.05 → 0.1 (arm tự chọn) | `recipe_arm_free_s42` |

Arm 1.5B (`Qwen/Qwen2.5-1.5B-Instruct`) không chạy trong lượt này (yaml đã bỏ).

## Từng run

| run | accuracy (%) | 95% CI | n |
|---|---|---|---|
| anchor | 95.5 | [92.5, 98.0] | 200 |
| arm_r8 | 95.5 | [92.5, 98.0] | 200 |
| arm_lr2e4 | 95.0 | [92.0, 98.0] | 200 |
| arm_comp0 | 93.5 | [90.0, 96.5] | 200 |
| arm_free | 95.5 | [92.5, 98.0] | 200 |

## Từng cặp (paired)

| A | B | n paired | diff (pp) | 95% CI diff | A không thấp hơn B quá margin | H1 | McNemar b (A thắng) | c (B thắng) | p | kết luận |
|---|---|---|---|---|---|---|---|---|---|---|
| anchor | arm_r8 | 200 | +0.0 | [+0.0, +0.0] | GIỮ | H1 giữ | 0 | 0 | 1.0000 | trong nhiễu (n.s.) |
| anchor | arm_lr2e4 | 200 | +0.5 | [-1.5, +2.5] | GIỮ | H1 giữ | 3 | 2 | 1.0000 | trong nhiễu (n.s.) |
| anchor | arm_comp0 | 200 | +2.0 | [-1.0, +5.0] | GIỮ | H1 giữ | 7 | 3 | 0.3438 | trong nhiễu (n.s.) |
| anchor | arm_free | 200 | +0.0 | [+0.0, +0.0] | GIỮ | H1 giữ | 0 | 0 | 1.0000 | trong nhiễu (n.s.) |

Δ = acc_anchor − acc_arm (cột `diff (pp)`): Δ dương nghĩa là anchor tốt hơn arm.

_Lệnh_: `python training/bootstrap_ci.py --run anchor=results/public/anchor_results.json --run arm_r8=results/public/recipe_arm_r8_results.json --run arm_lr2e4=results/public/recipe_arm_lr2e4_results.json --run arm_comp0=results/public/recipe_arm_comp0_results.json --run arm_free=results/public/recipe_arm_free_results.json --pair anchor arm_r8 --pair anchor arm_lr2e4 --pair anchor arm_comp0 --pair anchor arm_free --paired-diff-margin 5 --n-boot 2000 --seed 20260625`

## Kết luận

1. **Recipe mặc định: giữ anchor (`public_anchor.yaml`).** Với cả ba arm ứng viên (`arm_r8`, `arm_lr2e4`, `arm_free`),
   CI của hiệu ghép đôi chứa 0 và McNemar trong nhiễu, nên không có arm nào thay được anchor ở n = 200 / 63 bước.
2. **`arm_comp0` (full loss) chỉ là quan sát** theo thiết kế lưới (`training/recipes/README.md` §4), không phải ứng viên
   mặc định: điểm thấp hơn anchor nhưng CI của hiệu vẫn chứa 0.
3. **`arm_r8`**: pass/fail giống anchor trên 200/200 bản ghi (b = c = 0) dù raw output khác ở 23/200 id — ở cỡ mẫu
   này metric strict không phân biệt được r8 với r16.
4. **`arm_free` (`lora_dropout` 0.05 → 0.1) không cho thông tin.** Pass/fail giống anchor 200/200 (b = c = 0) và tên tool
   dự đoán giống 200/200; raw output chỉ khác ở 2/200 id (`pub-886927c1`: cả hai sai `wrong_tool`; `pub-a41b846a`: cả hai
   đúng, khác tham số). Dropout chỉ tác động lúc huấn luyện (lúc dự đoán mô hình ở chế độ `eval()` nên dropout tắt), và với
   63 bước, lr 1.0e-4, đổi 0.05 → 0.1 gần như không làm đầu ra khác đi — trong khi cùng 63 bước, `arm_r8` đổi raw output
   ở 23/200 id. Giữ arm này trong bảng như một quan sát,
   không dùng để kết luận.
