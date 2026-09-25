# Bootstrap CI + McNemar

> **Ghi chú trục đo**: percentile bootstrap, 2000 resamples, seed 20260625; margin H1 = 5pp; McNemar exact two-sided. Chỉ so sánh các run chấm trên cùng eval/tools/preamble sha256.

## Từng run

| run | accuracy (%) | 95% CI | n |
|---|---|---|---|
| base | 95.0 | [92.0, 98.0] | 200 |
| ft | 96.0 | [93.0, 98.5] | 200 |

## Từng cặp (paired)

| A | B | n paired | diff (pp) | 95% CI diff | A không thấp hơn B quá margin | H1 | McNemar b (A thắng) | c (B thắng) | p | kết luận |
|---|---|---|---|---|---|---|---|---|---|---|
| base | ft | 200 | -1.0 | [-3.0, +1.0] | GIỮ | H1 giữ | 1 | 3 | 0.6250 | trong nhiễu (n.s.) |

_Lệnh_: `python training/bootstrap_ci.py --run base=/content/drive/MyDrive/ChatSystem/runs/xlam2k_qwen05b/results/public/base.json --run ft=/content/drive/MyDrive/ChatSystem/runs/xlam2k_qwen05b/results/public/ft.json --pair base ft --paired-diff-margin 5 --n-boot 2000 --seed 20260625`
