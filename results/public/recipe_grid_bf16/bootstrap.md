# Bootstrap CI + McNemar

> **Ghi chú trục đo**: percentile bootstrap, 2000 resamples, seed 20260625; margin H1 = 5pp; McNemar exact two-sided. Chỉ so sánh các run chấm trên cùng eval/tools/preamble sha256.

## Từng run

| run | accuracy (%) | 95% CI | n |
|---|---|---|---|
| anchor | 95.5 | [92.5, 98.0] | 200 |
| arm_r8 | 95.5 | [92.5, 98.0] | 200 |
| arm_lr2e4 | 94.5 | [91.5, 97.5] | 200 |
| arm_comp0 | 94.0 | [90.5, 97.0] | 200 |
| arm_1p5b | 95.0 | [92.0, 98.0] | 200 |
| arm_r32 | 94.5 | [91.5, 97.5] | 200 |

## Từng cặp (paired)

| A | B | n paired | diff (pp) | 95% CI diff | A không thấp hơn B quá margin | H1 | McNemar b (A thắng) | c (B thắng) | p | kết luận |
|---|---|---|---|---|---|---|---|---|---|---|
| anchor | arm_r8 | 200 | +0.0 | [+0.0, +0.0] | GIỮ | H1 giữ | 0 | 0 | 1.0000 | trong nhiễu (n.s.) |
| anchor | arm_lr2e4 | 200 | +1.0 | [-1.0, +3.0] | GIỮ | H1 giữ | 3 | 1 | 0.6250 | trong nhiễu (n.s.) |
| anchor | arm_comp0 | 200 | +1.5 | [-1.5, +4.5] | GIỮ | H1 giữ | 6 | 3 | 0.5078 | trong nhiễu (n.s.) |
| anchor | arm_1p5b | 200 | +0.5 | [-2.5, +3.5] | GIỮ | H1 giữ | 5 | 4 | 1.0000 | trong nhiễu (n.s.) |
| anchor | arm_r32 | 200 | +1.0 | [-1.0, +3.0] | GIỮ | H1 giữ | 3 | 1 | 0.6250 | trong nhiễu (n.s.) |

_Lệnh_: `python training/bootstrap_ci.py --run anchor=results/public/recipe_grid_bf16/anchor_results.json --run arm_r8=results/public/recipe_grid_bf16/recipe_arm_r8_results.json --run arm_lr2e4=results/public/recipe_grid_bf16/recipe_arm_lr2e4_results.json --run arm_comp0=results/public/recipe_grid_bf16/recipe_arm_comp0_results.json --run arm_1p5b=results/public/recipe_grid_bf16/recipe_arm_1p5b_results.json --run arm_r32=results/public/recipe_grid_bf16/recipe_arm_r32_results.json --pair anchor arm_r8 --pair anchor arm_lr2e4 --pair anchor arm_comp0 --pair anchor arm_1p5b --pair anchor arm_r32 --paired-diff-margin 5 --n-boot 2000 --seed 20260625`
