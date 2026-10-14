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

Arm 1.5B (`Qwen/Qwen2.5-1.5B-Instruct`) không chạy trong lượt T4 này (yaml đã bỏ); arm 1.5B có ở lưới lặp lại trên
RTX PRO 6000 (bf16), xem mục *Bổ sung* cuối báo cáo.

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

## Bổ sung (2026-10-14) — lưới lặp lại trên RTX PRO 6000 (bf16), có arm 1.5B và arm tự chọn r32

> **Ghi chú trục đo (phần bổ sung)** — eval: `data/public/xlam_2k.eval.json` @ `6d8c803e` · tools: theo từng bản ghi · preamble: `prompts/system_preamble_v0.txt` @ `ebcae911` · scorer: `training/eval_toolcall.py` (`eval_toolcall/1.2`, strict first-call) @ git `befa395` · sampling: temperature 0 (greedy), `max_new_tokens` 256, dtype bfloat16 · bootstrap percentile 2000 lần, seed 20260625. Cùng trục eval với bảng T4 ở trên; phần cứng và dtype khác, nên mỗi arm dưới đây chỉ so với **anchor của cùng lần chạy**.

**Nguồn và cách kiểm.** Sáu run của @pthao3113 (nhánh `ft/task1-pthao`) theo recipe cố định `max_rows: 1000`, `epochs: 1`, `seed: 42`, trên NVIDIA RTX PRO 6000 (header dự đoán ghi `dtype: bfloat16`). Recipe `public_anchor.yaml`, `recipe_arm_r8.yaml`, `recipe_arm_lr2e4.yaml`, `recipe_arm_comp0.yaml` trùng từng khóa với recipe người chạy đã dùng (trừ `arm`, `notes`); hai recipe mới `recipe_arm_1p5b.yaml` và `recipe_arm_r32.yaml` giữ nguyên giá trị của người chạy (tệp gốc `public_1p5b.yaml`, `public_free_arm.yaml`; chỉ đổi tên tệp và khoá `arm` cho khớp các arm T4). Tên adapter trong header (`public_*_s42`) là tên recipe gốc. Header ghi `git_sha` `befa395`: `training/finetune_qlora.py` ở commit này là bản trước PR #1 (chưa có bước ép tham số LoRA về fp32 và cờ `--no-amp`, hai sửa đổi nhắm vào đường fp16 trên T4). Dự đoán và kết quả nằm ở `results/public/recipe_grid_bf16/`. Chấm lại bằng `training/eval_toolcall.py --preamble prompts/system_preamble_v0.txt`: header khớp và cả sáu tệp kết quả trùng từng byte với tệp đã nộp. Bảng dưới chép từ `results/public/recipe_grid_bf16/bootstrap.md`.

Δ = acc(anchor) − acc(arm) (dương = anchor tốt hơn); McNemar b = anchor đúng & arm sai, c = ngược lại.

| arm | recipe | accuracy (%) | 95% CI | Δ vs anchor (pp) | 95% CI Δ (pp) | McNemar b | c | p |
|---|---|---|---|---|---|---|---|---|
| anchor | `public_anchor.yaml` | 95.5 | [92.5, 98.0] | — | — | — | — | — |
| r8 | `recipe_arm_r8.yaml` | 95.5 | [92.5, 98.0] | +0.0 | [+0.0, +0.0] | 0 | 0 | 1.0000 |
| lr2e4 | `recipe_arm_lr2e4.yaml` | 94.5 | [91.5, 97.5] | +1.0 | [-1.0, +3.0] | 3 | 1 | 0.6250 |
| comp0 (full loss, chỉ quan sát) | `recipe_arm_comp0.yaml` | 94.0 | [90.5, 97.0] | +1.5 | [-1.5, +4.5] | 6 | 3 | 0.5078 |
| **1p5b** (Qwen2.5-1.5B-Instruct) | `recipe_arm_1p5b.yaml` | 95.0 | [92.0, 98.0] | +0.5 | [-2.5, +3.5] | 5 | 4 | 1.0000 |
| r32 (tự chọn, r32/α64) | `recipe_arm_r32.yaml` | 94.5 | [91.5, 97.5] | +1.0 | [-1.0, +3.0] | 3 | 1 | 0.6250 |

**Kết luận phần bổ sung.**

1. CI của Δ chứa 0 ở cả năm arm và không cặp nào có McNemar có ý nghĩa → **giữ `public_anchor.yaml` làm recipe mặc định**, cùng kết luận với bảng T4 ở trên; không chọn arm theo điểm ước lượng.
2. **Arm 1.5B** (bắt buộc trong lưới, bảng T4 chưa có): trên lát 1.000 hàng, 1.5B không hơn anchor 0.5B (Δ +0.5 pp, CI [-2.5, +3.5]), nên chưa có lý do đổi kích cỡ ở bước này; so sánh kích cỡ trên bộ SGOD thuộc F Việc 4.
3. **Arm tự chọn r32/α64** (giữ α = 2r): tăng hạng LoRA không cải thiện (Δ +1.0 pp, CI [-1.0, +3.0]); cùng với r8 bằng anchor, hạng LoRA không phải trục quyết định ở quy mô này. Arm tự chọn của hai lần chạy khác trục (T4: `recipe_arm_free.yaml`, `lora_dropout` 0.1; bf16: `recipe_arm_r32.yaml`), nên không đối chiếu chéo.
4. Điểm kiểm tra của task: anchor bf16 95.5% [92.5, 98.0] nằm trong CI của run tuần 2 (R002: 96.0% [93.0, 98.5]).
5. Lần chạy bf16 không nộp log huấn luyện hay `training_config.json`, nên peak VRAM, thời gian chạy và tệp train thực dùng không kiểm được và không báo cáo ở đây; cột `wall_clock_min` và `gpu` của `training/recipes/results.csv` chép từ bảng của người chạy.

### Đối chiếu chéo cùng recipe: T4 fp16 (bảng trên) ↔ RTX PRO 6000 bf16

Δ = acc(T4) − acc(bf16); McNemar b = T4 đúng & bf16 sai, c = ngược lại. Nguồn: `results/public/recipe_grid_bf16/cross_t4_bf16.md`.

| recipe | T4 accuracy (%) | bf16 accuracy (%) | Δ T4 − bf16 (pp) | 95% CI Δ (pp) | McNemar b | c | p |
|---|---|---|---|---|---|---|---|
| `public_anchor.yaml` | 95.5 | 95.5 | +0.0 | [+0.0, +0.0] | 0 | 0 | 1.0000 |
| `recipe_arm_r8.yaml` | 95.5 | 95.5 | +0.0 | [+0.0, +0.0] | 0 | 0 | 1.0000 |
| `recipe_arm_lr2e4.yaml` | 95.0 | 94.5 | +0.5 | [-1.0, +2.5] | 2 | 1 | 1.0000 |
| `recipe_arm_comp0.yaml` | 93.5 | 94.0 | -0.5 | [-1.5, +0.0] | 0 | 1 | 1.0000 |

Anchor và r8 cho cùng pass/fail trên toàn bộ 200 bản ghi ở hai phần cứng; lr2e4 lệch 3 bản ghi, comp0 lệch 1 bản ghi. Đổi phần cứng và dtype (T4 fp16 → bf16) không làm đổi kết luận nào ở trên.

<!-- no-prov-start -->
**Lần lặp thứ ba (không tính số).** @wynn187z cũng chạy lưới này trên Colab T4 (fp16, `--no-amp`; nhánh `ft/v1-recipe-grid-vanquyen` @ `b8d4640`, notebook `notebooks/finetune/04_recipe_grid.ipynb`, arm tự chọn `mask_fn_names: 0.5`) và báo cáo trên ClickUp với cùng kết luận giữ anchor. Tệp dự đoán và kết quả (`results/public/ft_public_*_s42.*`) không được commit và notebook đã xoá output, nên không có số nào của lần chạy này trong báo cáo này hay trong `results/INDEX.md`.
<!-- no-prov-end -->
