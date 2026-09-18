# Báo cáo mẫu (fixture) — có số KHÔNG truy vết được

> **Ghi chú trục đo** — eval: `data/public/xlam_2k.eval.json` @ `6d8c803e` · tools: theo từng bản ghi · preamble: `prompts/system_preamble_v0.txt` @ `ebcae911` · scorer: `training/eval_toolcall.py` @ `abc1234`.

| Arm | Strict accuracy |
|---|---|
| base (zero-shot) | 48.0% |
| ft (fixture-adapter) | 63.2% |

McNemar exact hai phía base vs ft: p = 0.41.

Số 99.9% dưới đây chỉ có ở dòng "ví dụ" của INDEX nên vẫn phải bị báo thiếu: 99.9%.
