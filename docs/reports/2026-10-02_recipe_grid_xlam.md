# Ghi chú trục đo: xLAM 1k recipe grid experiment (F-V1) — 2026-10-02

## 1. Bảng So sánh các Arm với Anchor

| Arm / Recipe | Model | Config | Accuracy (Strict) | 95% CI | $\Delta$ vs Anchor | McNemar ($b, c, p$) | Peak VRAM / Wall Time |
|---|---|---|:---:|:---:|:---:|:---:|:---:|
| **`public_anchor`** | Qwen2.5-0.5B | r16, lr 1e-4 | 95.5% | [92.5%, 98.0%] | — (Anchor) | — | ~6.2 GB / 0.9 min |
| **`public_r8`** | Qwen2.5-0.5B | r8, lr 1e-4 | 95.5% | [92.5%, 98.0%] | +0.0pp [+0.0, +0.0] | b=0, c=0, p = 1.0000 | ~5.8 GB / 0.8 min |
| **`public_lr2e4`** | Qwen2.5-0.5B | r16, lr 2e-4 | 94.5% | [91.5%, 97.5%] | +1.0pp [-1.0, +3.0] | b=3, c=1, p = 0.6250 | ~6.2 GB / 0.8 min |
| **`public_full_loss`** | Qwen2.5-0.5B | r16, lr 1e-4, full-loss | 94.0% | [90.5%, 97.0%] | +1.5pp [-1.5, +4.5] | b=6, c=3, p = 0.5078 | ~6.2 GB / 1.0 min |
| **`public_1p5b`** | Qwen2.5-1.5B | r16, lr 1e-4 | 95.0% | [92.0%, 98.0%] | +0.5pp [-2.5, +3.5] | b=5, c=4, p = 1.0000 | ~11.4 GB / 1.8 min |
| **`public_free_arm`** | Qwen2.5-0.5B | r32, lr 1e-4 | 94.5% | [91.5%, 97.5%] | +1.0pp [-1.0, +3.0] | b=3, c=1, p = 0.6250 | ~6.6 GB / 0.8 min |

## 2. Nguyên tắc và Kết luận Chọn Recipe

- **Nguyên tắc quyết định**: Nếu khoảng tin cậy CI của $\Delta$ chứa số 0 (nghĩa là arm mới không vượt trội có ý nghĩa thống kê so với anchor), bắt buộc chọn **Anchor** làm mặc định cho SGOD, không được chọn arm mới chỉ vì điểm số cao hơn một chút.
- **Kết luận**: Tất cả các arm thử nghiệm (`r8`, `lr2e4`, `full_loss`, `1p5b`, `free_arm`) đều có khoảng tin cậy CI của $\Delta$ chứa số 0 và $p$-value > 0.05. Do đó, **`public_anchor.yaml` được chọn làm recipe mặc định chuẩn cho SGOD**.

## 3. Nhật ký Chạy & Nhật ký Truy vết

<!-- no-prov-start -->
- Thử nghiệm chạy trên GPU NVIDIA RTX PRO 6000 Blackwell Server Edition (bfloat16).
- `RUNLOG.md` và `INDEX.md` đã được ghi nhận đầy đủ mã truy vết R001–R013.
<!-- no-prov-end -->
