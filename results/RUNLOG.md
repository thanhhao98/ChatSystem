# results/RUNLOG.md — nhật ký chạy (append-only)

Mỗi lần chạy huấn luyện / dự đoán / chấm điểm có kết quả nộp lên repo → **một dòng** ở đây, thêm vào cuối,
không sửa dòng cũ. `data@sha8` = 8 hex đầu của sha256 tệp dữ liệu vào (train.jsonl hoặc eval.json).
`kết quả ± CI` viết đúng như số sẽ đưa vào `results/INDEX.md`; nếu chỉ là run thăm dò chưa báo cáo, ghi `—`.

| ngày | ai | nhóm | data@sha8 | recipe | seed | kết quả ± CI | results path |
|---|---|---|---|---|---|---|---|
| 2026-10-03 | vanquyen | F | xlam_2k_train | public_anchor | 42 | 95.5% [92.5, 98.0] | results/public/ft_public_anchor_s42.json |
| 2026-10-03 | vanquyen | F | xlam_2k_train | public_r8 | 42 | 95.5% [92.5, 98.0] | results/public/ft_public_r8_s42.json |
| 2026-10-03 | vanquyen | F | xlam_2k_train | public_lr2e4 | 42 | 94.5% [91.5, 97.5] | results/public/ft_public_lr2e4_s42.json |
| 2026-10-03 | vanquyen | F | xlam_2k_train | public_full_loss | 42 | 94.0% [90.5, 97.0] (quan sát, không chọn) | results/public/ft_public_full_loss_s42.json |
| 2026-10-03 | vanquyen | F | xlam_2k_train | public_1p5b | 42 | 95.0% [92.0, 98.0] | results/public/ft_public_1p5b_s42.json |
| 2026-10-03 | vanquyen | F | xlam_2k_train | public_mask_fn | 42 | 94.5% [91.0, 97.5] | results/public/ft_public_mask_fn_s42.json |
