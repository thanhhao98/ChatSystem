# Hợp đồng dòng lệnh (CLI contract) — mọi script và notebook phải tuân theo

Các script dưới `training/`, `datagen/`, `tools/sgod/`, `scripts/` là giao diện chung của hai nhóm.
Notebook chỉ **gọi** các script này (qua `!python …` hoặc `subprocess`), không tự cài đặt lại logic chấm điểm hay
định dạng dữ liệu. Thay đổi cờ (flag) là thay đổi hợp đồng: cần PR riêng, cập nhật tài liệu này và CHANGELOG.

Tất cả script: `--help` đầy đủ; thoát mã 0 khi thành công, khác 0 khi lỗi; in một dòng tóm tắt cuối cùng;
không cần GPU trừ khi ghi rõ; không đọc biến môi trường bí mật nào ngoài `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `HF_TOKEN`.

## training/validate_dataset.py  (CPU, không tải model)
```
python training/validate_dataset.py <rows.jsonl> [<rows.jsonl> ...]
    [--preamble prompts/system_preamble_v0.txt]   # nội dung messages[0] phải BẰNG file này (sau strip)
    [--no-preamble-check]
    [--tools tools/sgod/sgod_tools.json]          # bắt buộc cho hàng KHÔNG có replay_tools; kiểm tra tên tool + tham số theo schema
    [--roles tools/sgod/roles.json]               # tập giá trị hợp lệ của "role"; mặc định {"employee","company_admin","system_admin"}
    [--fixed-replies prompts/fixed_replies.json]
    [--max-rows N]
```
Kiểm tra từng hàng theo `docs/contracts/training_row_format.md`; in số hàng lỗi theo loại; mã thoát 1 nếu có lỗi.

## training/finetune_qlora.py  (GPU cho huấn luyện; `--dry-run` chạy CPU)
```
python training/finetune_qlora.py
    --data data/public/xlam_2k.train.jsonl [--val data/public/xlam_2k.val.jsonl]
    [--tools tools/sgod/sgod_tools.json]     # dùng cho hàng không có replay_tools; lọc theo role của hàng qua tool_policy.json cùng thư mục
    [--model Qwen/Qwen2.5-0.5B-Instruct] [--output-dir runs/<name>]
    [--epochs 2] [--lr 1e-4] [--batch-size 4] [--grad-accum 4] [--max-len 2560]
    [--lora-rank 16] [--lora-alpha <2*rank>] [--lora-dropout 0.05]
    [--completion-only 1] [--mask-fn-names 0.0] [--max-rows N] [--seed 42]
    [--save-steps 50] [--logging-steps 10] [--resume-from-checkpoint <dir>]
    [--dry-run]                              # render hàng 0, in prompt, assert "<tools>" có trong prompt và số token completion không bị mask > 0; đếm hàng bị cắt; không tải model
    [--recipe training/recipes/<tên>.yaml]   # tùy chọn: khóa yaml = tên cờ (dạng gạch dưới) → giá trị mặc định; cờ gõ trên CLI ghi đè
```
Định dạng prompt: `tokenizer.apply_chat_template(messages[:-1], tools=<tools>, tokenize=False, add_generation_prompt=True)`;
completion = `messages[-1].content + eos`. dtype: bf16 nếu compute capability ≥ 8, ngược lại fp16 (biến `FORCE_FP16=1` để ép fp16).
Kết quả trong `--output-dir`: `adapter_config.json`, `adapter_model.safetensors`, `log_history.json`, `training_config.json`, `checkpoint-*/`.
Hàng nào có prompt+completion dài hơn `--max-len` → in id và **thoát mã 1** (không cắt ngầm).

## training/predict_toolcall.py  (một lượt, không thực thi tool)
```
python training/predict_toolcall.py --eval <eval.json> --out <predictions.jsonl>
    --backend openai --base-url http://localhost:8000/v1 --model <served-name> [--api-key-env OPENAI_API_KEY]
  | --backend transformers --model-path Qwen/Qwen2.5-0.5B-Instruct [--adapter <dir>] [--batch-size 8] [--max-new-tokens 256]
    [--tools tools/sgod/sgod_tools.json]     # bỏ qua khi bản ghi eval có trường "tools" riêng (bộ công khai)
    [--system prompts/system_preamble_v0.txt] [--temperature 0] [--limit N]
```
Dòng đầu file ra là header `{"header": true, ...}` (xem `docs/contracts/eval_metric.md`), sau đó mỗi bản ghi eval một dòng.

## training/eval_toolcall.py  (CPU)
```
python training/eval_toolcall.py --gold <eval.json> --pred <predictions.jsonl> --out <results.json>
    [--tools tools/sgod/sgod_tools.json] [--policy tools/sgod/tool_policy.json] [--preamble <file>]
    [--group-by source] [--no-header-check] [--md <results.md>]
```
Từ chối chấm nếu sha256 trong header khác file cục bộ (trừ khi `--no-header-check`). Ghi `results.json` theo schema kết quả.

## training/bootstrap_ci.py  (CPU)
```
python training/bootstrap_ci.py --run base=results/base.json --run ft=results/ft.json [--run ...]
    [--pair base ft] [--pair ...] [--paired-diff-margin 5] [--n-boot 2000] [--seed 20260625] [--md <out.md>]
```
In điểm ước lượng + CI 95% cho mỗi run; với mỗi cặp: CI của hiệu (paired bootstrap), kết luận theo margin, McNemar (b, c, p).

## datagen/convert_xlam.py · scripts/recover_xlam_raw.py
Xem docstring đầu file. Đầu ra phải tái lập bit-for-bit với cùng `--seed`.

## tools/sgod/validate_tools.py  (CPU; tải tokenizer Qwen để đếm token)
```
python tools/sgod/validate_tools.py [--tools tools/sgod/sgod_tools.json] [--policy tools/sgod/tool_policy.json]
    [--roles tools/sgod/roles.json] [--spec docs/sgod-api-reference.md] [--preamble prompts/system_preamble_v1.txt]
    [--max-preamble-tokens 1000] [--max-system-tokens 3400]
```

## scripts/check_provenance.py  (CPU)
```
python scripts/check_provenance.py <report.md> [--index results/INDEX.md]
```
Mã thoát 1 nếu có phần trăm hoặc `p = …` trong báo cáo không có dòng tương ứng trong INDEX (bỏ qua dòng có `<!-- no-prov -->`).

## Định dạng chung
- Kết quả chấm điểm `results.json`: `{"model", "eval_set", "eval_sha256", "n", "passed", "by_reason", "results": [{"id", "pass", "reason", "expected_tool", "actual_tool", "source", "user_role"}]}`.
- Mọi tệp dự đoán/kết quả nộp lên repo nằm dưới `results/` và có dòng trong `results/RUNLOG.md`.
