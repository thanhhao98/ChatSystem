<!-- Ghi chú trục đo:
     eval=xlam_2k.eval.json,
     scorer=eval_toolcall/1.2 (strict first-call; params >= half of keys; unknown tool = violation),
     axis=strict_accuracy (pass/fail per record), n=200,
     seed_boot=20260625, n_boot=2000, data=first 1000 rows of xlam_2k.train.jsonl,
     epochs=1, seed_train=42, max_len=2560 (T4 config), no_amp=True
-->

# Recipe Grid — xLAM slice (≤6 arms) — 2026-10-03

**Mục tiêu:** So sánh 6 recipe arm trên cùng 1.000 hàng xLAM đầu tiên (seed 42, 1 epoch), chọn 1 recipe làm SGOD default.  
**Môi trường:** Google Colab T4 (15 GB, fp16, no_amp=True). **Notebook:** `notebooks/finetune/04_recipe_grid.ipynb` @ `e2b0d84`.  
**Phiên bản:** transformers 5.12.1, trl 1.13.0, peft 0.20.0, torch 2.11.0+cu130, bitsandbytes 0.50.2.

## Arm-vs-Anchor Table

| arm | strict_acc (%) | 95% CI acc | Δ vs anchor (pp) | 95% CI Δ | McNemar b | c | p | peak VRAM (GB) | wall (min) | quyết định |
|---|---|---|---|---|---|---|---|---|---|---|
| **public_anchor** | **95.5** | [92.5, 98.0] | 0 (điểm neo) | — | — | — | — | 3.24 | 10.88 | ← điểm neo |
| public_r8 | 95.5 | [92.5, 98.0] | +0.0 | [+0.0, +0.0] | 0 | 0 | 1.0000 | 3.23 | 10.87 | GIỮ anchor (bằng điểm, p n.s.) |
| public_lr2e4 | 94.5 | [91.5, 97.5] | +1.0 | [-1.5, +3.5] | 4 | 2 | 0.6875 | 3.24 | 10.96 | GIỮ anchor (p n.s.) |
| public_full_loss | 94.0 | [90.5, 97.0] | +1.5 | [-1.5, +5.0] | 7 | 4 | 0.5488 | 3.24 | 14.30 | **KHÔNG** (never default per spec) |
| public_1p5b | 95.0 | [92.0, 98.0] | +0.5 | [-2.5, +3.5] | 5 | 4 | 1.0000 | 6.20 | 23.92 | GIỮ anchor (p n.s.) |
| public_mask_fn | 94.5 | [91.0, 97.5] | +1.0 | [+0.0, +2.5] | 2 | 0 | 0.5000 | 3.24 | 11.04 | GIỮ anchor (p n.s.) |

> **Quy tắc quyết định (pre-registered):** CI của Δ bao gồm 0 → KHÔNG bác bỏ H0 → GIỮ anchor.  
> Không quyết định trên point estimate. `completion_only=0` loại ngay theo spec F-V1.  
> Δ = acc_anchor − acc_arm (dương = anchor tốt hơn arm).

## Recipe được chọn: `public_anchor`

**Lý do:**
- **r8** (rank=8): bằng anchor điểm (95.5%), CI Δ = [0.0, 0.0] — không mang lại cải thiện; rank 16 đủ capacity, GIỮ anchor.
- **lr2e4** (lr=2e-4): thấp hơn anchor 1.0 pp, CI [-1.5, +3.5] bao gồm 0, p=0.69 — không có ý nghĩa thống kê. LR cao hơn không ổn định với 1 epoch.
- **1p5b** (1.5B): thấp hơn anchor 0.5 pp, CI [-2.5, +3.5], p=1.00 — model lớn hơn không có lợi trên slice 1k; VRAM 6.2 GB (gần gấp đôi) và wall 23.9 min (gấp 2.2×).
- **mask_fn** (mask fn_names 50%): thấp hơn anchor 1.0 pp; đáng chú ý CI Δ = [0.0, +2.5] (cận dưới đúng bằng 0) — anchor vẫn được ưu tiên; giả thuyết tăng param_acc không xác nhận (98.4% vs 98.9% của anchor).
- **full_loss**: loại ngay theo spec F-V1 (`completion_only=0` không bao giờ là default), bất kể kết quả.

---

## Kết quả chi tiết từng arm

### R001 — Anchor (`public_anchor`)

- model: `Qwen/Qwen2.5-0.5B-Instruct`
- lora_rank=16, lora_alpha=32, lr=1e-4, completion_only=1, mask_fn_names=0.0, no_amp=True
- strict_acc: **95.5% [92.5, 98.0]**
- tool_name_acc: 96.5%, param_acc: 98.9%
- train_loss: 0.0938, eval_loss: 0.0506
- steps: 63, wall_clock_min: 10.88, gpu: Tesla T4 (fp16), peak_VRAM: 3.24 GB
- started_at: 2026-10-02T17:49:03

### R002 — r8/α16 (`public_r8`)

- trục thay đổi: lora_rank=8 (↓ từ 16), lora_alpha=16
- strict_acc: **95.5% [92.5, 98.0]** | Δ vs anchor: **+0.0 pp [+0.0, +0.0]**
- tool_name_acc: 96.5%, param_acc: 98.9%
- train_loss: 0.0989, eval_loss: 0.0503
- steps: 63, wall_clock_min: 10.87, peak_VRAM: 3.23 GB
- McNemar: b=0, c=0, p=1.0000 (n.s.)

### R003 — lr=2e-4 (`public_lr2e4`)

- trục thay đổi: lr=2.0e-4 (↑ từ 1e-4)
- strict_acc: **94.5% [91.5, 97.5]** | Δ vs anchor: **+1.0 pp [-1.5, +3.5]**
- tool_name_acc: 95.5%, param_acc: 98.9%
- train_loss: 0.0896, eval_loss: 0.0509
- steps: 63, wall_clock_min: 10.96, peak_VRAM: 3.24 GB
- McNemar: b=4, c=2, p=0.6875 (n.s.)

### R004 — full_loss (`public_full_loss`) — chỉ quan sát

- trục thay đổi: completion_only=0 (loss trên toàn sequence)
- strict_acc: **94.0% [90.5, 97.0]** | Δ vs anchor: **+1.5 pp [-1.5, +5.0]**
- tool_name_acc: 95.0%, param_acc: 98.9%
- train_loss: 0.7936 (cao hơn nhiều vì loss trên cả prompt), eval_loss: 0.5266
- steps: 63, wall_clock_min: 14.30, peak_VRAM: 3.24 GB
- McNemar: b=7, c=4, p=0.5488 (n.s.)
- **Ghi chú:** KHÔNG chọn làm default theo spec F-V1 (bất kể kết quả)

### R005 — 1.5B (`public_1p5b`)

- trục thay đổi: model=Qwen2.5-1.5B-Instruct (↑ từ 0.5B, ~4.7× params)
- strict_acc: **95.0% [92.0, 98.0]** | Δ vs anchor: **+0.5 pp [-2.5, +3.5]**
- tool_name_acc: 95.5%, param_acc: 99.5%
- train_loss: 0.0807, eval_loss: 0.0363
- steps: 63, wall_clock_min: 23.92, peak_VRAM: 6.20 GB
- McNemar: b=5, c=4, p=1.0000 (n.s.)

### R006 — mask_fn=0.5 (`public_mask_fn`) — free arm

- trục thay đổi: mask_fn_names=0.5 (50% train rows có fn name bị đổi ngẫu nhiên — Hammer arXiv:2410.04587)
- lý do chọn arm: buộc model học ngữ nghĩa param, không chỉ nhớ tên tool → giả thuyết tăng param_acc
- strict_acc: **94.5% [91.0, 97.5]** | Δ vs anchor: **+1.0 pp [+0.0, +2.5]**
- tool_name_acc: 96.0%, param_acc: 98.4% (thấp hơn anchor 98.9% → giả thuyết không xác nhận ở quy mô 1k)
- train_loss: 0.0926, eval_loss: 0.0508
- steps: 63, wall_clock_min: 11.04, peak_VRAM: 3.24 GB
- McNemar: b=2, c=0, p=0.5000 (n.s.)

---

## RUNLOG

| ngày | ai | nhóm | data@sha8 | recipe | seed | kết quả ± CI | results path |
|---|---|---|---|---|---|---|---|
| 2026-10-03 | vanquyen | F | xlam_2k_train | public_anchor | 42 | 95.5% [92.5, 98.0] | results/public/ft_public_anchor_s42.json |
| 2026-10-03 | vanquyen | F | xlam_2k_train | public_r8 | 42 | 95.5% [92.5, 98.0] | results/public/ft_public_r8_s42.json |
| 2026-10-03 | vanquyen | F | xlam_2k_train | public_lr2e4 | 42 | 94.5% [91.5, 97.5] | results/public/ft_public_lr2e4_s42.json |
| 2026-10-03 | vanquyen | F | xlam_2k_train | public_full_loss | 42 | 94.0% [90.5, 97.0] (quan sát, không chọn) | results/public/ft_public_full_loss_s42.json |
| 2026-10-03 | vanquyen | F | xlam_2k_train | public_1p5b | 42 | 95.0% [92.0, 98.0] | results/public/ft_public_1p5b_s42.json |
| 2026-10-03 | vanquyen | F | xlam_2k_train | public_mask_fn | 42 | 94.5% [91.0, 97.5] | results/public/ft_public_mask_fn_s42.json |

---

## INDEX (R### — mọi số phải có dòng này)

| id | số | metric | results file | lệnh/notebook | git sha7 | eval@sha8 | tools@sha8 | model | ngày | ai |
|---|---|---|---|---|---|---|---|---|---|---|
| R001 | 95.5% [92.5, 98.0] | strict accuracy, public eval (n=200), anchor | results/public/ft_public_anchor_s42.json | `notebooks/finetune/04_recipe_grid.ipynb` @ `e2b0d84` | e2b0d84 | — | — | Qwen/Qwen2.5-0.5B-Instruct + public_anchor | 2026-10-03 | vanquyen |
| R002 | 95.5% [92.5, 98.0] | strict accuracy, public eval (n=200), r8 | results/public/ft_public_r8_s42.json | `notebooks/finetune/04_recipe_grid.ipynb` @ `e2b0d84` | e2b0d84 | — | — | Qwen/Qwen2.5-0.5B-Instruct + public_r8 | 2026-10-03 | vanquyen |
| R003 | +0.0 pp [+0.0, +0.0] | diff (pp) anchor − r8 | results/public/ft_public_r8_s42.json | `python training/bootstrap_ci.py --run anchor=... --run r8=... --pair anchor r8` | e2b0d84 | — | — | — | 2026-10-03 | vanquyen |
| R004 | p = 1.0000 | McNemar anchor vs r8 (b=0, c=0) | results/public/ft_public_r8_s42.json | *(same bootstrap_ci.py)* | e2b0d84 | — | — | — | 2026-10-03 | vanquyen |
| R005 | 94.5% [91.5, 97.5] | strict accuracy, public eval (n=200), lr2e4 | results/public/ft_public_lr2e4_s42.json | `notebooks/finetune/04_recipe_grid.ipynb` @ `e2b0d84` | e2b0d84 | — | — | Qwen/Qwen2.5-0.5B-Instruct + public_lr2e4 | 2026-10-03 | vanquyen |
| R006 | +1.0 pp [-1.5, +3.5] | diff (pp) anchor − lr2e4 | results/public/ft_public_lr2e4_s42.json | `python training/bootstrap_ci.py --run anchor=... --run lr2e4=... --pair anchor lr2e4` | e2b0d84 | — | — | — | 2026-10-03 | vanquyen |
| R007 | p = 0.6875 | McNemar anchor vs lr2e4 (b=4, c=2) | results/public/ft_public_lr2e4_s42.json | *(same)* | e2b0d84 | — | — | — | 2026-10-03 | vanquyen |
| R008 | 94.0% [90.5, 97.0] | strict accuracy, public eval (n=200), full_loss | results/public/ft_public_full_loss_s42.json | `notebooks/finetune/04_recipe_grid.ipynb` @ `e2b0d84` | e2b0d84 | — | — | Qwen/Qwen2.5-0.5B-Instruct + public_full_loss | 2026-10-03 | vanquyen |
| R009 | +1.5 pp [-1.5, +5.0] | diff (pp) anchor − full_loss | results/public/ft_public_full_loss_s42.json | `python training/bootstrap_ci.py --run anchor=... --run full_loss=... --pair anchor full_loss` | e2b0d84 | — | — | — | 2026-10-03 | vanquyen |
| R010 | p = 0.5488 | McNemar anchor vs full_loss (b=7, c=4) | results/public/ft_public_full_loss_s42.json | *(same)* | e2b0d84 | — | — | — | 2026-10-03 | vanquyen |
| R011 | 95.0% [92.0, 98.0] | strict accuracy, public eval (n=200), 1p5b | results/public/ft_public_1p5b_s42.json | `notebooks/finetune/04_recipe_grid.ipynb` @ `e2b0d84` | e2b0d84 | — | — | Qwen/Qwen2.5-1.5B-Instruct + public_1p5b | 2026-10-03 | vanquyen |
| R012 | +0.5 pp [-2.5, +3.5] | diff (pp) anchor − 1p5b | results/public/ft_public_1p5b_s42.json | `python training/bootstrap_ci.py --run anchor=... --run 1p5b=... --pair anchor 1p5b` | e2b0d84 | — | — | — | 2026-10-03 | vanquyen |
| R013 | p = 1.0000 | McNemar anchor vs 1p5b (b=5, c=4) | results/public/ft_public_1p5b_s42.json | *(same)* | e2b0d84 | — | — | — | 2026-10-03 | vanquyen |
| R014 | 94.5% [91.0, 97.5] | strict accuracy, public eval (n=200), mask_fn | results/public/ft_public_mask_fn_s42.json | `notebooks/finetune/04_recipe_grid.ipynb` @ `e2b0d84` | e2b0d84 | — | — | Qwen/Qwen2.5-0.5B-Instruct + public_mask_fn | 2026-10-03 | vanquyen |
| R015 | +1.0 pp [+0.0, +2.5] | diff (pp) anchor − mask_fn | results/public/ft_public_mask_fn_s42.json | `python training/bootstrap_ci.py --run anchor=... --run mask_fn=... --pair anchor mask_fn` | e2b0d84 | — | — | — | 2026-10-03 | vanquyen |
| R016 | p = 0.5000 | McNemar anchor vs mask_fn (b=2, c=0) | results/public/ft_public_mask_fn_s42.json | *(same)* | e2b0d84 | — | — | — | 2026-10-03 | vanquyen |
