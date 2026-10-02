# Bootstrap CI + McNemar — Recipe Grid Search (xLAM 2k)

> **Ghi chú trục đo**: percentile bootstrap, 2000 resamples, seed 20260625; margin H1 = 5pp; McNemar exact two-sided. Chỉ so sánh các run chấm trên cùng eval/tools/preamble sha256.

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
| anchor | arm_lr2e4 | 200 | +0.5pp | [-1.5, +2.5] | GIỮ | H1 giữ | 3 | 2 | 1.0000 | trong nhiễu (n.s.) |
| anchor | arm_comp0 | 200 | +2.0 | [-1.0, +5.0] | GIỮ | H1 giữ | 7 | 3 | 0.3438 | trong nhiễu (n.s.) |
| anchor | arm_free | 200 | +0.0 | [+0.0, +0.0] | GIỮ | H1 giữ | 0 | 0 | 1.0000 | trong nhiễu (n.s.) |

## Kết luận chọn Recipe Mặc định (Default Recipe)

Tất cả các Arm thử nghiệm (`r8`, `lr2e4`, `comp0`, `free`) đều cho khoảng tin cậy CI của độ chênh lệch chứa số 0 (p-value lớn, trong nhiễu). Theo đúng nguyên tắc của dự án (*CI covers 0 → KEEP anchor*), **giữ nguyên Anchor (`public_anchor.yaml`) làm Recipe Mặc định cho bộ dữ liệu SGOD**.

