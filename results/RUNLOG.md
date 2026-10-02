# results/RUNLOG.md — nhật ký chạy (append-only)

Mỗi lần chạy huấn luyện / dự đoán / chấm điểm có kết quả nộp lên repo → **một dòng** ở đây, thêm vào cuối,
không sửa dòng cũ. `data@sha8` = 8 hex đầu của sha256 tệp dữ liệu vào (train.jsonl hoặc eval.json).
`kết quả ± CI` viết đúng như số sẽ đưa vào `results/INDEX.md`; nếu chỉ là run thăm dò chưa báo cáo, ghi `—`.

| ngày | ai | nhóm | data@sha8 | recipe | seed | kết quả ± CI | results path |
|---|---|---|---|---|---|---|---|
| 2026-09-25 | thanhlong | F | 6d8c803e | base zero-shot | 42 | strict 95.0% [92.0, 98.0] | results/public/base.json |
| 2026-09-25 | thanhlong | F | 6d8c803e | qlora 0.5b full sft | 42 | strict 96.0% [93.0, 98.5] | results/public/ft.json |
| 2026-10-02 | thanhlong | F | 6d8c803e | public_anchor | 42 | strict 95.5% [92.5, 98.0] | results/public/anchor_results.json |
| 2026-10-02 | thanhlong | F | 6d8c803e | recipe_arm_r8 | 42 | strict 95.5% [92.5, 98.0] | results/public/recipe_arm_r8_results.json |
| 2026-10-02 | thanhlong | F | 6d8c803e | recipe_arm_lr2e4 | 42 | strict 95.0% [92.0, 98.0] | results/public/recipe_arm_lr2e4_results.json |
| 2026-10-02 | thanhlong | F | 6d8c803e | recipe_arm_comp0 | 42 | strict 93.5% [90.0, 96.5] | results/public/recipe_arm_comp0_results.json |
| 2026-10-02 | thanhlong | F | 6d8c803e | recipe_arm_free | 42 | strict 95.5% [92.5, 98.0] | results/public/recipe_arm_free_results.json |
