# Báo cáo mẫu (fixture) — mọi con số đều có trong INDEX

> **Ghi chú trục đo** — eval: `data/public/xlam_2k.eval.json` @ `6d8c803e` · tools: theo từng bản ghi (bộ công khai) · preamble: `prompts/system_preamble_v0.txt` @ `ebcae911` · scorer: `training/eval_toolcall.py` @ `abc1234`.

| Arm | Strict accuracy | 95% CI |
|---|---|---|
| base (zero-shot) | 48.0% | — |
| ft (fixture-adapter) | 61.5% | [54.5%, 68.0%] |

McNemar exact hai phía base vs ft: p = 0.0021.

Dòng này có một số không truy vết nhưng được đánh dấu bỏ qua: 12.3% <!-- no-prov -->

<!-- no-prov-start -->
```
$ python training/bootstrap_ci.py --run ft=results/reference/fixture_ft.json
ft   77.7%  [70.1, 84.2]  (n=200)
```
<!-- no-prov-end -->
