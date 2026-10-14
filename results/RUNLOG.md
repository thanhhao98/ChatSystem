# results/RUNLOG.md — nhật ký chạy (append-only)

Mỗi lần chạy huấn luyện / dự đoán / chấm điểm có kết quả nộp lên repo → **một dòng** ở đây, thêm vào cuối,
không sửa dòng cũ. `data@sha8` = 8 hex đầu của sha256 tệp dữ liệu vào (train.jsonl hoặc eval.json).
`kết quả ± CI` viết đúng như số sẽ đưa vào `results/INDEX.md`; nếu chỉ là run thăm dò chưa báo cáo, ghi `—`.

| ngày | ai | nhóm | data@sha8 | recipe | seed | kết quả ± CI | results path |
|---|---|---|---|---|---|---|---|
| 2026-09-25 | thanhlong | F | 6d8c803e | base zero-shot | 42 | strict 95.0% [92.0, 98.0] | results/public/base.json |
| 2026-09-25 | thanhlong | F | 6d8c803e | qlora 0.5b full sft | 42 | strict 96.0% [93.0, 98.5] | results/public/ft.json |
| 2026-10-02 (dự đoán 2026-10-07) | thanhlong | F | 933c4ecd | public_anchor | 42 | strict 95.5% [92.5, 98.0] | results/public/anchor_results.json |
| 2026-10-02 (dự đoán 2026-10-07) | thanhlong | F | 933c4ecd | recipe_arm_r8 | 42 | strict 95.5% [92.5, 98.0] | results/public/recipe_arm_r8_results.json |
| 2026-10-02 (dự đoán 2026-10-07) | thanhlong | F | 933c4ecd | recipe_arm_lr2e4 | 42 | strict 95.0% [92.0, 98.0] | results/public/recipe_arm_lr2e4_results.json |
| 2026-10-02 (dự đoán 2026-10-07) | thanhlong | F | 933c4ecd | recipe_arm_comp0 | 42 | strict 93.5% [90.0, 96.5] | results/public/recipe_arm_comp0_results.json |
| 2026-10-02 (dự đoán 2026-10-07) | thanhlong | F | 933c4ecd | recipe_arm_free | 42 | strict 95.5% [92.5, 98.0] | results/public/recipe_arm_free_results.json |
| 2026-10-02 | pthao3113 | F | 933c4ecd | public_anchor — RTX PRO 6000, bf16 | 42 | strict 95.5% [92.5, 98.0] | results/public/recipe_grid_bf16/anchor_results.json |
| 2026-10-02 | pthao3113 | F | 933c4ecd | recipe_arm_r8 — RTX PRO 6000, bf16 | 42 | strict 95.5% [92.5, 98.0] | results/public/recipe_grid_bf16/recipe_arm_r8_results.json |
| 2026-10-02 | pthao3113 | F | 933c4ecd | recipe_arm_lr2e4 — RTX PRO 6000, bf16 | 42 | strict 94.5% [91.5, 97.5] | results/public/recipe_grid_bf16/recipe_arm_lr2e4_results.json |
| 2026-10-02 | pthao3113 | F | 933c4ecd | recipe_arm_comp0 — RTX PRO 6000, bf16 | 42 | strict 94.0% [90.5, 97.0] | results/public/recipe_grid_bf16/recipe_arm_comp0_results.json |
| 2026-10-02 | pthao3113 | F | 933c4ecd | recipe_arm_1p5b — RTX PRO 6000, bf16 | 42 | strict 95.0% [92.0, 98.0] | results/public/recipe_grid_bf16/recipe_arm_1p5b_results.json |
| 2026-10-02 | pthao3113 | F | 933c4ecd | recipe_arm_r32 — RTX PRO 6000, bf16 | 42 | strict 94.5% [91.5, 97.5] | results/public/recipe_grid_bf16/recipe_arm_r32_results.json |
| 2026-10-14 | thanhhao98 | F | 6d8c803e | bootstrap_ci: anchor vs 5 arm, lưới bf16 (6 tệp kết quả ở trên) | 20260625 | xem R037–R046 | results/public/recipe_grid_bf16/bootstrap.md |
| 2026-10-14 | thanhhao98 | F | 6d8c803e | bootstrap_ci: T4 fp16 vs bf16 cùng recipe (anchor, r8, lr2e4, comp0) | 20260625 | xem R047–R054 | results/public/recipe_grid_bf16/cross_t4_bf16.md |
