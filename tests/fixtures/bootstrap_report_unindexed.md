# Bootstrap CI + McNemar

> **Ghi chú trục đo**: percentile bootstrap, 2000 resamples, seed 20260625; margin H1 = 5pp; McNemar exact two-sided. Chỉ so sánh các run chấm trên cùng eval/tools/preamble sha256.

## Từng run

| run | accuracy (%) | 95% CI | n |
|---|---|---|---|
| a | 74.5 | [68.5, 80.5] | 200 |
| b | 68.0 | [61.5, 74.5] | 200 |

## Từng cặp (paired)

| A | B | n paired | diff (pp) | 95% CI diff | A không thấp hơn B quá margin | H1 | McNemar b (A thắng) | c (B thắng) | p | kết luận |
|---|---|---|---|---|---|---|---|---|---|---|
| a | b | 200 | +6.5 | [-3.5, +15.5] | GIỮ | H1 giữ | 49 | 36 | 0.1928 | trong nhiễu (n.s.) |

_Lệnh_: `python training/bootstrap_ci.py --run a=/tmp/r.json --run b=/tmp/rb.json --pair a b --paired-diff-margin 5 --n-boot 2000 --seed 20260625`
