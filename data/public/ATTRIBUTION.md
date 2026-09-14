# Ghi công và nguồn gốc bộ dữ liệu công khai `data/public/`

## Nguồn

- **Bộ dữ liệu**: Salesforce **xlam-function-calling-60k** — `https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k`
- **Giấy phép**: **CC-BY-4.0** (Creative Commons Attribution 4.0). Repo này phân phối lại một lát 2.000 hàng đã biến đổi;
  yêu cầu ghi công được đáp ứng bởi tệp này và `NOTICE.md`. Bản gốc trên Hugging Face là **gated** (cần đồng ý điều khoản
  và `HF_TOKEN`); lát trong repo không cần token.
- **Bài báo**: Zuxin Liu, Thai Hoang, Jianguo Zhang, Ming Zhu, Tian Lan, Shirley Kokane, Juntao Tan, Weiran Yao, Zhiwei Liu,
  Yihao Feng, Rithesh Murthy, Liangwei Yang, Silvio Savarese, Juan Carlos Niebles, Huan Wang, Shelby Heinecke, Caiming Xiong.
  *APIGen: Automated PIpeline for Generating Verifiable and Diverse Function-Calling Datasets.* NeurIPS 2024.
  arXiv:2406.18518 — `https://arxiv.org/abs/2406.18518`

```bibtex
@article{liu2024apigen,
  title   = {APIGen: Automated Pipeline for Generating Verifiable and Diverse Function-Calling Datasets},
  author  = {Liu, Zuxin and Hoang, Thai and Zhang, Jianguo and Zhu, Ming and Lan, Tian and Kokane, Shirley and
             Tan, Juntao and Yao, Weiran and Liu, Zhiwei and Feng, Yihao and Murthy, Rithesh and Yang, Liangwei and
             Savarese, Silvio and Niebles, Juan Carlos and Wang, Huan and Heinecke, Shelby and Xiong, Caiming},
  journal = {arXiv preprint arXiv:2406.18518},
  year    = {2024}
}
```

## Lát 2.000 hàng được tạo thế nào

Hai bước, đều tất định với `--seed 20260913`:

1. **`scripts/recover_xlam_raw.py`** (chạy một lần, offline, trên hạ tầng tham chiếu). Đầu vào là 6.500 hàng xLAM đã được
   hệ thống tham chiếu (POC v1) chuẩn hoá về định dạng hàng huấn luyện (tool trong `replay_tools`, câu trả lời trong tag `<tool_call>`). Script **đảo
   ngược** phép chuẩn hoá để lấy lại `{id, query, tools, answers}` giống bản gốc, lọc: đúng **1** lời gọi tool, **1–4** tool
   trong danh mục, tool được gọi có trong danh mục, câu hỏi không trùng; rồi lấy mẫu **phân tầng theo số tool**
   (tỷ lệ theo tầng, làm tròn phần dư lớn nhất), seed `20260913` → `xlam_raw_2k.jsonl` (2.000 hàng).
   Phân bố theo số tool: 1 tool: 644 · 2 tool: 372 · 3 tool: 465 · 4 tool: 519.
2. **`datagen/convert_xlam.py`** (stdlib; nhóm D chạy lại được trong Tuần 2). Đổi tham số xLAM sang JSON Schema
   (`type: object` + `properties` + `required` = tham số không có `default`), thêm preamble
   `prompts/system_preamble_v0.txt` làm `messages[0]`, câu trả lời thành `<tool_call>{…}</tool_call>`, chia
   **80/10/10 theo nhóm tập-tool** (cả nhóm vào một split; **0** tập tool chung giữa các split), seed `20260913`
   → `xlam_2k.{train,val,test}.jsonl` (1600/200/200) và `xlam_2k.eval.json` (200 bản ghi từ test, mỗi bản ghi mang `tools` riêng).

Lệnh tái lập (đầu ra phải **bit-for-bit** giống bản đã commit):

```bash
python datagen/convert_xlam.py --in data/public/xlam_raw_2k.jsonl --out-prefix /tmp/xlam_2k \
    --system-file prompts/system_preamble_v0.txt --seed 20260913
cmp /tmp/xlam_2k.train.jsonl data/public/xlam_2k.train.jsonl && echo identical
```

## Biến đổi so với bản gốc

- `id` **không** phải id gốc của xLAM: `xlam-<sha1(query + answers)[:8]>` ở bước 1, đổi tiền tố thành `pub-` ở bước 2.
- Kiểu tham số giữ nguyên chuỗi của xLAM (`"str"`, `"int, optional"`, …) — không phải kiểu JSON Schema chuẩn.
- Thêm hai trường không có trong bản gốc: `role: "employee"` (mọi hàng) và preamble hệ thống tiếng Việt.
- Câu hỏi và mô tả tool là **tiếng Anh** như bản gốc; các địa chỉ email / tên trong dữ liệu là giá trị mẫu do APIGen sinh,
  không phải dữ liệu cá nhân của nhóm.
- Chỉ giữ hàng có đúng một lời gọi tool (bản gốc có hàng nhiều lời gọi).

## Mã băm (sha256) — dùng để đối chiếu trong notebook Tuần 2 và header dự đoán

Danh sách id nối bằng `\n` (đúng cách `convert_xlam.py::sha256_ids` tính), và sha256 của cả tệp:

| Tệp | Số hàng | sha256(danh sách id) | sha256(tệp) |
|---|---|---|---|
| `xlam_raw_2k.jsonl` | 2000 | `2a44b1824acebb31c46fc1951f082ca0aeda19837abd14550374b85038b8ef5b` | `0928dfa2ba06ee056585c53be074311ec2a10cc4afcce3c56c07737761f91477` |
| `xlam_2k.train.jsonl` | 1600 | `e016357a2443008f08c1c1d077493efbc0a7e51e1f72f616c648572c170015e1` | `933c4ecd30601adf570938901c6a9d48b4eca24ad5abdbdb81b58792c5349e31` |
| `xlam_2k.val.jsonl` | 200 | `75c24b8f3d5af2852736abc69556ae404d9c22feb0867ad6ab09c66159aefd09` | `fa85bbc8aef5dc96f73cf378b19b2efdf8fc8171849f3983079cf8403553eae6` |
| `xlam_2k.test.jsonl` | 200 | `0c862665ffb18f4643168d27a285044f05378cf204094e947eb8ba6fed799459` | `9f75cea06192eb3d754195d15bd7beca445073523d8d74e8f290857fb6e837c7` |
| `xlam_2k.eval.json` | 200 | `0c862665ffb18f4643168d27a285044f05378cf204094e947eb8ba6fed799459` (cùng id với test) | `6d8c803e5b05ea1ddfe1412eda8d3d006d2b05cfd97af170e0c314792b653a67` |

Preamble v0 (`prompts/system_preamble_v0.txt`, sau `.strip()`): sha256 `ebcae91113cd2d4cec962f9405bb1f8ed4e261c25d71d8bc58f155e9484ad147`.
`convert_xlam.py` in 16 hex đầu của các giá trị trên (`ids_sha256=e016357a2443008f`, …) — notebook Tuần 2 so 16 hex này.

`eval@sha8` cho bộ công khai trong `results/INDEX.md` là **`6d8c803e`** (8 hex đầu của sha256 tệp `xlam_2k.eval.json`).

## Cách trích dẫn trong báo cáo

> Bộ dữ liệu công khai dùng để khởi động và ablation là lát 2.000 hàng của xlam-function-calling-60k (Liu et al., 2024,
> CC-BY-4.0), chia theo nhóm tập-tool 1600/200/200 (`data/public/ATTRIBUTION.md`).
