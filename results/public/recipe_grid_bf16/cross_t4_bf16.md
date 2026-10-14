# Bootstrap CI + McNemar

> **Ghi chú trục đo**: percentile bootstrap, 2000 resamples, seed 20260625; margin H1 = 5pp; McNemar exact two-sided. Chỉ so sánh các run chấm trên cùng eval/tools/preamble sha256.

## Từng run

| run | accuracy (%) | 95% CI | n |
|---|---|---|---|
| t4_anchor | 95.5 | [92.5, 98.0] | 200 |
| bf16_anchor | 95.5 | [92.5, 98.0] | 200 |
| t4_r8 | 95.5 | [92.5, 98.0] | 200 |
| bf16_r8 | 95.5 | [92.5, 98.0] | 200 |
| t4_lr2e4 | 95.0 | [92.0, 98.0] | 200 |
| bf16_lr2e4 | 94.5 | [91.5, 97.5] | 200 |
| t4_comp0 | 93.5 | [90.0, 96.5] | 200 |
| bf16_comp0 | 94.0 | [90.5, 97.0] | 200 |

## Từng cặp (paired)

| A | B | n paired | diff (pp) | 95% CI diff | A không thấp hơn B quá margin | H1 | McNemar b (A thắng) | c (B thắng) | p | kết luận |
|---|---|---|---|---|---|---|---|---|---|---|
| t4_anchor | bf16_anchor | 200 | +0.0 | [+0.0, +0.0] | GIỮ | H1 giữ | 0 | 0 | 1.0000 | trong nhiễu (n.s.) |
| t4_r8 | bf16_r8 | 200 | +0.0 | [+0.0, +0.0] | GIỮ | H1 giữ | 0 | 0 | 1.0000 | trong nhiễu (n.s.) |
| t4_lr2e4 | bf16_lr2e4 | 200 | +0.5 | [-1.0, +2.5] | GIỮ | H1 giữ | 2 | 1 | 1.0000 | trong nhiễu (n.s.) |
| t4_comp0 | bf16_comp0 | 200 | -0.5 | [-1.5, +0.0] | GIỮ | H1 giữ | 0 | 1 | 1.0000 | trong nhiễu (n.s.) |

_Lệnh_: `python training/bootstrap_ci.py --run t4_anchor=results/public/anchor_results.json --run bf16_anchor=results/public/recipe_grid_bf16/anchor_results.json --run t4_r8=results/public/recipe_arm_r8_results.json --run bf16_r8=results/public/recipe_grid_bf16/recipe_arm_r8_results.json --run t4_lr2e4=results/public/recipe_arm_lr2e4_results.json --run bf16_lr2e4=results/public/recipe_grid_bf16/recipe_arm_lr2e4_results.json --run t4_comp0=results/public/recipe_arm_comp0_results.json --run bf16_comp0=results/public/recipe_grid_bf16/recipe_arm_comp0_results.json --pair t4_anchor bf16_anchor --pair t4_r8 bf16_r8 --pair t4_lr2e4 bf16_lr2e4 --pair t4_comp0 bf16_comp0 --paired-diff-margin 5 --n-boot 2000 --seed 20260625`
