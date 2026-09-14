# `datagen/prompts_eval/` — prompt cho phần **GPT bổ sung của bộ đánh giá** (D Việc 4)

Cùng cấu trúc file với `datagen/prompts/` (`domain_system.md`, `category_<tên>.md`, `label_system.md`,
`arbiter_system.md`, ...). Pipeline dùng thư mục này khi được gọi với `--prompt-dir datagen/prompts_eval`
(hoặc `PROMPT_DIR=datagen/prompts_eval bash datagen/run_pipeline.sh --stage generate,label`).

## Vì sao prompt eval phải **tách rời** prompt huấn luyện

1. **Rò rỉ phân phối (distribution leakage).** Nếu cùng một prompt sinh cả tập huấn luyện và tập đánh giá thì hai tập
   có cùng "giọng", cùng mẫu câu, cùng lỗi hệ thống của model sinh. Mô hình được fine-tune sẽ đạt điểm cao vì nhận ra
   *phong cách* chứ không phải vì gọi tool đúng — và điểm đó **không** chuyển sang người dùng thật. Lọc
   SequenceMatcher < 0.65 chỉ chặn trùng lặp bề mặt, không chặn trùng lặp phân phối.
2. **Tính công bằng của so sánh SLM vs GPT (H1).** GPT baseline chưa thấy tập huấn luyện; nếu eval "giống" tập huấn
   luyện thì SLM có lợi thế không chính đáng và kết luận H1 sai lệch.
3. **Đóng băng.** `eval_v1.json` bị đóng băng ở Điểm đồng bộ 2 và **không đổi** sau đó; prompt huấn luyện còn được
   sửa liên tục đến D Việc 5. Nếu dùng chung prompt, mỗi lần sửa prompt huấn luyện là một lần kéo tập huấn luyện
   lại gần eval hơn.

## Quy tắc

- Người viết prompt eval **không** đọc `datagen/prompts/` trước khi viết (và ngược lại); lõi eval do người viết
  (`eval_human_core.jsonl`, D Việc 2) được viết trước **cả hai** bộ prompt.
- Model arbiter dùng cho alternates/polish của eval (`ARBITER_MODEL`) phải **khác** model GPT được đem ra chấm
  (contract 2, `docs/contracts/eval_metric.md`). Ghi model id vào `docs/eval_v1_card.md`.
- Hàng GPT bổ sung mang `"source": "gpt_aug"`; hàng người viết mang `"source": "human"`; scorer báo cáo hai lát riêng.
- Sau Điểm đồng bộ 2: thư mục này chỉ đổi kèm `eval_v1.1` + errata + sha mới. Mọi hàng huấn luyện sinh sau đó phải
  chống rò rỉ với `eval_v1.json` (`config_sgod.EVAL_SETS_FOR_LEAKAGE`).
- Không few-shot bằng câu trong bất kỳ tập dữ liệu nào của repo; không khoá API, mật khẩu, token.
