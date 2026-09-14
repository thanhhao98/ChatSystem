# ChatSystem — trợ lý chat tiếng Việt cho quản lý tài sản trên nền tảng SGOD

Repo làm việc của chương trình thực tập **Chat System pha 2** (6 thực tập sinh, 2 nhóm) — `https://github.com/thanhhao98/ChatSystem` (private).
Quản lý công việc trên ClickUp: `https://app.clickup.com/` (Space: **Chat System**).

**Mục lục**

1. [Giới thiệu](#1-giới-thiệu)
2. [Mục tiêu cuối](#2-mục-tiêu-cuối)
3. [Kiến trúc đích](#3-kiến-trúc-đích)
4. [Hai nhóm và bốn hợp đồng](#4-hai-nhóm-và-bốn-hợp-đồng)
5. [Bắt đầu ở đâu](#5-bắt-đầu-ở-đâu)
6. [Cấu trúc thư mục](#6-cấu-trúc-thư-mục)
7. [Kiểm thử](#7-kiểm-thử)
8. [Tài liệu](#8-tài-liệu)
9. [Hạn chế đã biết](#9-hạn-chế-đã-biết)
10. [Ghi công dữ liệu](#10-ghi-công-dữ-liệu)

## 1. Giới thiệu

Hệ thống tham chiếu (POC v1) xây một chatbot quản lý tài sản tiếng Việt với hai mode so sánh được trên cùng 37 tool và
cùng backend: **GPT** (function calling qua gateway tương thích OpenAI) và **SLM** (Qwen2.5-3B fine-tune QLoRA, phục vụ
bằng vLLM). Kết luận: ở tầng tool-calling thuần, SLM **ngang** GPT; khoảng cách còn lại nằm ở tầng luật/NER thủ công.
<!-- no-prov -->

Pha 2 chuyển hệ sang **nền tảng SGOD thật** (`docs/sgod-api-reference.md`): gateway một cổng, ba service
`auth` / `asset` / `chat`, hai thông tin xác thực mỗi lời gọi, phong bì `{success, data, message}`. Câu hỏi nghiên cứu
giữ nguyên: *một mô hình nhỏ, tự phục vụ, có ngang GPT ở tool-calling trên API thật không?* — nhưng lần này dữ liệu,
bộ đánh giá, harness và mô hình do **nhóm thực tập** xây theo bốn hợp đồng cố định, và mọi con số phải truy vết được.

## 2. Mục tiêu cuối

Người dùng đăng nhập bằng **tài khoản SGOD + mật khẩu**, chat bằng tiếng Việt, và nhận câu trả lời qua **SLM fine-tune
của nhóm** hoặc **GPT** — cùng tool, cùng preamble, cùng executor, cùng cổng phân quyền — với số đo so sánh được:

- **H1 (đăng ký trước)**: strict accuracy của SLM trên `eval_v1` không thấp hơn GPT quá **5 điểm phần trăm**
  (CI bootstrap ghép đôi 95 %, 2.000 lần, seed 20260625; McNemar kèm theo). Xem `docs/contracts/eval_metric.md` §5.
- Đầu ra kỹ thuật: `tools/sgod/sgod_tools.json` (~20 tool chỉ đọc), `data/sgod/eval_v1.json` (đóng băng, sha256),
  `data/sgod/{train,val}.jsonl`, adapter LoRA (0.5B/1.5B trên T4; 3B trên máy GPU của hạ tầng tham chiếu) phục vụ bằng vLLM, bảng 4 arm
  có CI + McNemar + kết luận `H1 giữ / không giữ`, demo end-to-end (Điểm đồng bộ 3, 2026-11-22).

## 3. Kiến trúc đích

```
Browser ── login (tài khoản SGOD) ──► ChatSystem backend
                                      │  POST /sgod-auth/v1/<tier>/sessions → JWT người dùng; tier → role (docs/contracts/roles.md)
   chat ─────────────────────────────►│  router: mode = gpt_only | slm   (cùng tools, cùng preamble, cùng executor)
                                      │     ├─ GPT qua gateway tương thích OpenAI
                                      │     └─ SLM: Qwen2.5 + LoRA trên vLLM (hermes tool parser)
                                      │  tool_executor → cổng authz (tools/sgod/tool_policy.json) → SGOD adapter
                                      └──► <SGOD_BASE_URL>/sgod-{auth,asset,chat}/v1/...
```

Chi tiết, bảng "giữ nguyên / cần adapter" và dòng dữ liệu–đo lường: `docs/architecture.md`.

## 4. Hai nhóm và bốn hợp đồng

| Nhóm | Người | Việc | List ClickUp | Nhánh |
|---|---|---|---|---|
| **D — Dữ liệu** | 3 | danh mục tool SGOD, lõi eval người viết, prompt sinh, `eval_v1`, dữ liệu huấn luyện chống rò rỉ | `D — Dữ liệu` | `data/…` |
| **F — Huấn luyện & Phục vụ** | 3 | QLoRA trên T4, harness dự đoán/chấm, lưới recipe, bảng 4 arm + H1, gói adapter | `F — Huấn luyện & Phục vụ` | `ft/…` |
| **S — Hệ thống & hạ tầng tham chiếu** | — | OpenAPI/fixtures, đăng nhập SGOD, adapter executor, các bước LLM của pipeline, baseline GPT, arm 3B, phục vụ, demo — chạy trên hạ tầng tham chiếu, đầu ra commit vào repo (`results/`, `fixtures/`, `docs/sgod/`, `data/sgod/`) | `S — Hệ thống & hạ tầng tham chiếu` | `sys/…` |

Hai nhóm gặp nhau ở **bốn hợp đồng** (`docs/contracts/`), soạn trong epic S và đóng băng tại các Điểm đồng bộ:

| # | Hợp đồng | Tệp | Đóng băng | Cổng máy |
|---|---|---|---|---|
| 1 | Định dạng hàng huấn luyện | `docs/contracts/training_row_format.md` | Điểm đồng bộ 1 — 2026-09-27 | `training/validate_dataset.py` |
| 2 | Bộ eval, thước đo, schema dự đoán/kết quả, H1 | `docs/contracts/eval_metric.md` | Điểm đồng bộ 2 — 2026-10-25 | `training/eval_toolcall.py`, `training/bootstrap_ci.py` |
| 3 | Ánh xạ tier SGOD → vai trò chat | `docs/contracts/roles.md` (epic S, 09-27) + `tools/sgod/roles.json` | 2026-09-27 | đọc bởi datagen, labeler, executor |
| 4 | Hình dạng danh mục tool | `tools/sgod/sgod_tools.json` + `tool_policy.json` (D Việc 1, S Việc 4 xác minh) | tag `tools-v1` — 2026-10-08 | `tools/sgod/validate_tools.py` |

Mọi script là giao diện chung và có dòng lệnh cố định: `docs/contracts/cli.md`. Notebook chỉ **gọi** script, không cài
đặt lại logic.

## 5. Bắt đầu ở đâu

Đọc theo thứ tự: `HUONG_DAN_LAM_VIEC.md` (môi trường, nhánh/PR, bí mật, nộp kết quả) → `docs/onboarding_slides.pdf` →
hợp đồng của nhóm mình → hai task onboarding dưới đây (đã ở trạng thái **to do** trên ClickUp; phần còn lại là `planning`).

### Nhóm D — Dữ liệu

| Task | Hạn | Notebook | Kết quả nộp |
|---|---|---|---|
| **Tuần 1 — Dựng môi trường và khám phá bộ dữ liệu công khai xLAM (2k hàng gốc)** | 2026-09-20 | [`notebooks/data/01_explore_public_dataset.ipynb`](notebooks/data/01_explore_public_dataset.ipynb) | chạy trên Colab từ `data/public/xlam_raw_2k.jsonl` (không tải, không token); dán khối `## Tạo báo cáo` (số hàng, tool/hàng, call/hàng, tham số/call, độ dài câu hỏi, top-20 tool, số JSON parse được) làm bình luận ClickUp |
| **Tuần 2 — Tiền xử lý về định dạng hàng huấn luyện (parity, `<tool_call>`) và chia train/val/test** | 2026-09-27 | [`notebooks/data/02_preprocess_to_chatml.ipynb`](notebooks/data/02_preprocess_to_chatml.ipynb) | chạy `datagen/convert_xlam.py` → 1600/200/200 (0 tập tool chung); `training/validate_dataset.py` thoát 0; một prompt render có khối `<tools>`; sha256 danh sách id khớp `data/public/ATTRIBUTION.md` |

### Nhóm F — Huấn luyện & Phục vụ

| Task | Hạn | Notebook | Kết quả nộp |
|---|---|---|---|
| **Tuần 1 — Dựng môi trường Colab và chạy QLoRA SFT nhẹ (Qwen2.5-0.5B-Instruct) trên lát xLAM 2k** | 2026-09-20 | [`notebooks/finetune/01_qlora_sft_colab.ipynb`](notebooks/finetune/01_qlora_sft_colab.ipynb) | cell GPU in `Tesla T4 · 15 GB · (7,5) · USE_BF16=False → fp16`; `--dry-run` xanh; smoke 200 hàng rồi 3 epoch trên 1.6k; ngắt kết nối + `--resume-from-checkpoint` tiếp từ bước 101; báo cáo VRAM đỉnh, thời gian, loss, `ls` adapter, một `<tool_call>` greedy |
| **Tuần 2 — Đánh giá pretrained vs fine-tuned trên test công khai (tool-name, args, JSON validity, bootstrap CI, McNemar)** | 2026-09-27 | [`notebooks/finetune/02_eval_toolcalling.ipynb`](notebooks/finetune/02_eval_toolcalling.ipynb) | `results/{base,ft}_pred.jsonl` → `training/eval_toolcall.py` → `training/bootstrap_ci.py --run base=… --run ft=… --pair base ft`; dán bảng + CI 95 % + McNemar (b, c, p) |

Lộ trình đầy đủ (Việc 1–5, Đầu ra cuối kỳ, epic S, ba Điểm đồng bộ): `docs/roadmap.md`.

## 6. Cấu trúc thư mục

```
README.md · HUONG_DAN_LAM_VIEC.md · CHANGELOG.md · NOTICE.md · .env.example · requirements.txt · requirements-train.txt
docs/
  contracts/         cli.md · training_row_format.md · eval_metric.md · roles.md (epic S, 09-27)
  architecture.md · roadmap.md · serving.md · personas_sgod.md (stub, epic S 09-27)
  sgod-api-reference.md (spec, bí mật đã thay placeholder) · sgod/ (openapi-*.json, query_params.md — S Việc 1)
  onboarding_slides.pdf · reports/ (D_final.md, F_final.md)
prompts/             system_preamble_v0.txt (đóng băng) · system_preamble_v1.txt (09-27) · fixed_replies.json
data/
  public/            xlam_raw_2k.jsonl · xlam_2k.{train,val,test}.jsonl · xlam_2k.eval.json · sample_pred.jsonl · ATTRIBUTION.md
  sgod/              eval_human_core.jsonl · eval_v1.json (+ .sha256) · {raw,labeled,verified,quarantine}.json · {train,val}.jsonl
fixtures/sgod/       phản hồi thật đã che PII (S Việc 2)
tools/sgod/          sgod_tools.json · tool_policy.json · roles.json · validate_tools.py · tool_api_mapping.md (sinh)
datagen/             convert_xlam.py (stdlib) · generate/label/polish/verify/build_parity_trainset · config_sgod.py · run_pipeline.sh · prompts/ · prompts_eval/
training/            validate_dataset.py · finetune_qlora.py · predict_toolcall.py · eval_toolcall.py · bootstrap_ci.py · serve_vllm.sh · recipes/
notebooks/           data/01,02,03 · finetune/01,02,03 · _setup_snippet.md — mỗi notebook: cell 1 thiết lập chuẩn (clone/chdir, `_setup_snippet.md`), cell 2 pin + probe GPU/phiên bản, cell cuối "## Tạo báo cáo"
results/             INDEX.md (sổ truy vết số) · RUNLOG.md (nhật ký run) · reference/ · public/ · sgod_eval_v1/ · adapters/
scripts/             recover_xlam_raw.py (chạy một lần trên hạ tầng tham chiếu) · make_sample_pred.py · check_provenance.py · verify_on_gpu*.sh (hạ tầng tham chiếu)
tests/fixtures/      report_ok.md · report_bad.md · eval_report_ok.md · bootstrap_report_unindexed.md · index_fixture.md (cho CI của check_provenance)
.github/             workflows/ci.yml · workflows/main-guard.yml · PULL_REQUEST_TEMPLATE.md
```

## 7. Kiểm thử

CI (`.github/workflows/ci.yml`) chạy trên mọi pull request và mọi push vào `main`, Python 3.11, chỉ CPU. Chạy tại chỗ
trước khi mở PR:

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# biên dịch mọi script
find datagen training tools scripts -name '*.py' -print0 | xargs -0 python -m py_compile

# hợp đồng 1: mọi hàng huấn luyện công khai hợp lệ
python training/validate_dataset.py data/public/xlam_2k.train.jsonl data/public/xlam_2k.val.jsonl data/public/xlam_2k.test.jsonl

# hợp đồng 2: chấm mẫu + CI
python training/eval_toolcall.py --gold data/public/xlam_2k.eval.json --pred data/public/sample_pred.jsonl --out /tmp/r.json
python training/bootstrap_ci.py --run a=/tmp/r.json

# truy vết số: fixture ok → 0, fixture bad → 1; báo cáo thật do eval_toolcall --md sinh → 0; bảng bootstrap chưa có INDEX → 1
python scripts/check_provenance.py tests/fixtures/report_ok.md  --index tests/fixtures/index_fixture.md
python scripts/check_provenance.py tests/fixtures/report_bad.md --index tests/fixtures/index_fixture.md   # phải thoát 1
python scripts/check_provenance.py tests/fixtures/eval_report_ok.md --index tests/fixtures/index_fixture.md
python scripts/check_provenance.py tests/fixtures/bootstrap_report_unindexed.md --index tests/fixtures/index_fixture.md   # phải thoát 1

# hợp đồng 1 (huấn luyện): dry-run CPU, chỉ tải tokenizer (CI cài thêm `transformers==5.12.1 jinja2`, không cần torch)
python training/finetune_qlora.py --dry-run --data data/public/xlam_2k.train.jsonl --max-len 2560
#   → phải in `assert '<tools>' in prompt: OK`, `unmasked completion tokens: N > 0` và `over_limit=0`

# prompt là văn bản thuần cho model: không chú thích HTML
grep -n '<!--' prompts/*.txt        # phải rỗng

# bí mật: phải rỗng (mẫu viết sao cho không chứa chuỗi bí mật nào; bỏ qua data/public/ — văn bản bên thứ ba có email mẫu)
git grep -nIE "Sgod(2025|123)|sk-[A-Za-z0-9]{20}|SmartGeneration(of)Digital" -- . ':!data/public'
```

Khi đổi tool: `python tools/sgod/validate_tools.py` (tải tokenizer Qwen để đếm token). Khi đổi dữ liệu:
`python datagen/convert_xlam.py … --seed 20260913` phải tái lập bit-for-bit (xem `data/public/ATTRIBUTION.md`).
Huấn luyện: mặc định của script (`DEFAULT_MAX_LEN = 2560` trong `training/finetune_qlora.py`), notebook 01 và CI đều dùng
**`--max-len 2560`** cho bộ công khai — hàng dài nhất của `xlam_2k.train.jsonl` là 2.426 token; nếu hạ xuống 1536, 5 hàng
vượt giới hạn nên dry-run báo `over_limit=5` và thoát mã 1 (đúng thiết kế: không cắt ngầm). Chi tiết và cách báo khi dry-run
của bạn khác: `notebooks/finetune/README.md` § *Lưu ý về cấu hình T4 cố định*.

## 8. Tài liệu

| Tệp | Nội dung |
|---|---|
| `HUONG_DAN_LAM_VIEC.md` | môi trường Colab/Kaggle/local, mô hình truy cập GitHub, bí mật, nộp kết quả lên ClickUp, thực hành Colab/Drive, hai bẫy từ hệ thống tham chiếu (POC v1) |
| `docs/onboarding_slides.pdf` | bộ slide onboarding (đọc tuần 1) |
| `docs/contracts/cli.md` | dòng lệnh cố định của mọi script |
| `docs/contracts/training_row_format.md` · `eval_metric.md` · `roles.md` | hợp đồng 1 · 2 · 3 |
| `docs/architecture.md` · `docs/roadmap.md` · `docs/serving.md` · `docs/personas_sgod.md` | kiến trúc đích · lộ trình · bàn giao/phục vụ adapter · persona |
| `docs/sgod-api-reference.md` | **tài liệu API SGOD duy nhất** (placeholder thay bí mật) |
| `results/INDEX.md` · `results/RUNLOG.md` | sổ truy vết số · nhật ký run |
| `data/public/ATTRIBUTION.md` · `NOTICE.md` | ghi công dữ liệu · giấy phép và phạm vi sử dụng |
| `CHANGELOG.md` | thay đổi theo ngày, cùng commit với thay đổi |

## 9. Hạn chế đã biết

- **Thực tập sinh không có quyền gọi SGOD trực tiếp.** Làm việc từ spec + `fixtures/sgod/`; lời gọi thật chạy trên hạ
  tầng tham chiếu và artefact được commit vào repo (`fixtures/sgod/`, `docs/sgod/`). Mọi bước cần LLM trong pipeline dữ
  liệu (sinh / gán nhãn / kiểm định) cũng chạy trên hạ tầng tham chiếu từ PR của nhóm D (`datagen/run_pipeline.sh`);
  đầu ra được commit vào `data/sgod/` trong ≤ 2 ngày làm việc.
- **Không có branch protection** (repo private trên tài khoản cá nhân, gói Free). Quy ước chỉ-PR + `main-guard.yml` thay
  thế — về mặt kỹ thuật không có gì ngăn push thẳng; xem `HUONG_DAN_LAM_VIEC.md` §2.
- **Chỉ một lượt (single-turn)** ở dữ liệu và eval pha 2; đa lượt ngoài phạm vi.
- **Compute của thực tập sinh là Colab/Kaggle T4 miễn phí**: fp16 (không bf16), 0.5B/1.5B, phiên kết thúc bất ngờ →
  bắt buộc `--save-steps` + `--resume-from-checkpoint`, đầu ra lên Drive. Arm 3B chạy trên máy GPU của hạ tầng tham
  chiếu; kết quả commit vào `results/`.
- **Spec §4**: một số endpoint SGOD hỏng (dashboard summary, một số GET của asset, mọi endpoint chat cho tài khoản không
  phải owner) → nằm trong blocklist của danh mục tool.
- **Bẫy đã gặp ở hệ thống tham chiếu (POC v1)**: `max_len` ngắn hơn prompt+completion từng làm loss = 0 âm thầm (nay script thoát 1);
  `--lora-modules` của vLLM cần đường dẫn tồn tại **trong container**. Chi tiết: `HUONG_DAN_LAM_VIEC.md` §6.
- **5 hàng của `xlam_2k.train.jsonl` dài hơn 1536 token** (dài nhất 2.426): chạy với `--max-len 1536` làm dry-run thoát 1;
  mặc định của script (`DEFAULT_MAX_LEN = 2560`), notebook 01 và CI đều dùng `--max-len 2560`. Lọc/không lọc hàng dài là
  quyết định của nhóm D ở bước dữ liệu.
- **Preamble v1 còn là bản nháp** đến Điểm đồng bộ 1 (văn bản nền) và 2026-10-11 (quy tắc chọn tool); trạng thái ở
  `prompts/README.md`, không ghi trong tệp prompt.
- Trục đo **không trộn**: đổi eval / tools / preamble / scorer là trục mới; bảng chỉ so số cùng trục
  (`docs/contracts/eval_metric.md` §6).

## 10. Ghi công dữ liệu

Bộ dữ liệu công khai là lát 2.000 hàng của **Salesforce/xlam-function-calling-60k** (APIGen, Liu et al. 2024,
arXiv:2406.18518), giấy phép **CC-BY-4.0**; cách tạo lát, biến đổi và sha256 ở `data/public/ATTRIBUTION.md`. Mô hình nền
Qwen2.5 (Apache-2.0 cho 0.5B/1.5B; Qwen Research License cho 3B). Phạm vi sử dụng và các giấy phép khác: `NOTICE.md`.
