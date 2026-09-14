# Hướng dẫn làm việc — repo `thanhhao98/ChatSystem`

Đọc hết tài liệu này trước khi mở task đầu tiên. Mục 2–4 là **quy tắc bắt buộc** (cũng nằm trong list
`Chung — Mốc & Quy tắc` trên ClickUp: `https://app.clickup.com/`, Space: **Chat System**).

1. [Môi trường](#1-môi-trường)
2. [Mô hình truy cập GitHub: nhánh, PR, commit, changelog](#2-mô-hình-truy-cập-github-nhánh-pr-commit-changelog)
3. [Bí mật](#3-bí-mật)
4. [Cách nộp kết quả lên ClickUp](#4-cách-nộp-kết-quả-lên-clickup)
5. [Làm việc với Colab / Kaggle / Google Drive](#5-làm-việc-với-colab--kaggle--google-drive)
6. [Hai bẫy từ hệ thống tham chiếu (POC v1)](#6-hai-bẫy-từ-hệ-thống-tham-chiếu-poc-v1)

## 1. Môi trường

### 1.1 Colab (mặc định cho cả hai nhóm)

Repo là **private**, nên `git clone` cần token. Token nằm trong **Colab Secrets** (biểu tượng chìa khoá ở thanh trái),
không bao giờ nằm trong cell.

1. Tạo **Personal access token (classic)** trên GitHub: *Settings → Developer settings → Personal access tokens →
   Tokens (classic) → Generate new token (classic)*; tick scope **`repo`** (đủ để clone, pull và push nhánh trên repo
   private); hạn ≤ 90 ngày. `thanhhao98/ChatSystem` là repo private thuộc **tài khoản cá nhân** và bạn là collaborator,
   nên token *fine-grained* **không dùng được** ở đây — chỉ token classic mới hoạt động.
2. Colab → Secrets → thêm `GITHUB_TOKEN` (bật "Notebook access"). Thêm `HF_TOKEN` chỉ khi cần dataset/model gated.
3. **Cell 1 — Thiết lập** của mọi notebook là **ô chuẩn trong [`notebooks/_setup_snippet.md`](notebooks/_setup_snippet.md)**
   (đã có sẵn trong từng notebook, copy nguyên văn; không sửa, không viết ô clone riêng). Ô này:
   - **Colab / Kaggle**: đọc `GITHUB_TOKEN` từ Secrets (Colab `google.colab.userdata`; Kaggle `kaggle_secrets`), `git clone`
     repo private (bỏ qua nếu đã có) rồi `chdir` vào `ChatSystem`. Token nằm trong URL remote trong `.git/config` của **VM
     tạm** — nhờ vậy `git pull` / `git push origin` chạy được — và **không bao giờ** được in: không `print`, không
     `!cat .git/config`, không `!git remote -v` vào output notebook. Nếu clone lỗi, thông báo đã được thay token bằng `<token>`.
   - **Local**: đi lên từ thư mục hiện tại đến khi gặp `docs/contracts/cli.md` rồi `chdir` vào gốc repo.
   - Đặt `REPO`, `GIT_SHA`, `IN_COLAB`, `AUTHOR` và hàm `run(cmd)` để gọi script của repo (in lệnh, output, `[exit code = N]`).
   - **Không `pip install` trong ô này.** Notebook fine-tune cài pin ở **Cell 2** (`pip install -q -r requirements-train.txt`)
     rồi in GPU/phiên bản; notebook data chỉ cần stdlib + `matplotlib` + `transformers` (tokenizer) có sẵn trên Colab.

Đẩy nhánh từ Colab (token đã nằm trong remote `origin` của VM tạm, không gõ token vào lệnh):

```python
!git config user.name  "<github-username>"
!git config user.email "<github-username>@users.noreply.github.com"   # KHÔNG dùng email cá nhân
!git checkout -b ft/t1-<github-username>
!jupyter nbconvert --clear-output --inplace notebooks/finetune/01_qlora_sft_colab.ipynb   # xoá output trước khi commit
!git add notebooks/finetune/01_qlora_sft_colab.ipynb CHANGELOG.md
!git commit -m "feat(notebook): [F-T1] chạy QLoRA 0.5B trên xLAM 2k, báo cáo T4"
!git push -q origin HEAD:ft/t1-<github-username>
```

Nếu push lỗi (403 = token thiếu scope `repo`, hoặc tài khoản chưa được thêm làm collaborator), đọc thông báo tại chỗ nhưng
**không dán output** vào ClickUp/issue — nó có thể chứa URL kèm token.

**Cell 2** của notebook fine-tune cài pin rồi in GPU và phiên bản (`nvidia-smi --query-gpu=name,memory.total`, compute
capability, `USE_BF16`, `torch`/`transformers`/`peft`/`trl`/`bitsandbytes`). Trên T4 miễn phí phải thấy
`Tesla T4 · 15 GB · (7,5) · USE_BF16=False → fp16`. Nếu Colab cấp GPU khác (L4/A100), đặt `FORCE_FP16=1` để số đo so sánh
được với bạn cùng nhóm. **Cell 3** mount Google Drive và đặt `RUN_NAME`, `OUT` (mục 5).

### 1.2 Kaggle (khi hết quota Colab; 30 GPU-giờ/tuần, T4×2 — dùng 1 GPU)

- Notebook → *Settings*: Accelerator **GPU T4 x2**, **Internet: On**, *Persistence: Files only*.
- *Add-ons → Secrets*: thêm `GITHUB_TOKEN` (và `HF_TOKEN` nếu cần). **Cell 1 chuẩn tự nhận Kaggle** (biến
  `KAGGLE_KERNEL_RUN_TYPE`) và đọc token bằng `kaggle_secrets.UserSecretsClient` — không sửa gì trong notebook.
- Đường dẫn làm việc là `/kaggle/working/ChatSystem`; Cell 3 đặt `OUT = /kaggle/working/runs/<RUN_NAME>` (được giữ khi
  *Save & Run All*, **mất khi phiên kết thúc**). Kaggle không mount Google Drive: tải adapter về máy rồi đưa lên Drive
  chung, hoặc lưu thành Kaggle Dataset riêng, **trước khi** tắt phiên.

### 1.3 Local (chỉ CPU; để chạy script kiểm định / chấm điểm / viết tài liệu)

```bash
git clone https://github.com/thanhhao98/ChatSystem.git && cd ChatSystem   # git sẽ hỏi username + token (PAT)
python3.11 -m venv .venv && source .venv/bin/activate                      # Python ≥ 3.11
pip install -r requirements.txt            # CPU: openai, requests, numpy, pyyaml
# pip install -r requirements-train.txt    # CHỈ trên máy có GPU; pin == đã được kiểm chứng trên Colab T4
python training/validate_dataset.py data/public/xlam_2k.train.jsonl
```

`requirements-train.txt` ghim `==` cho `transformers`, `peft`, `trl`, `bitsandbytes`, `accelerate`, `datasets`
(không ghim `torch` — dùng torch có sẵn của Colab). **Pin được kiểm lại trên hạ tầng tham chiếu mỗi khi Colab đổi
image/torch**; nếu Cell 2 báo xung đột phiên bản hoặc in phiên bản khác `requirements-train.txt`, mở issue "pins" và không tự
sửa pin trong PR công việc.

`HF_TOKEN` (nếu có) chỉ tồn tại trong Secrets và được nạp bằng `os.environ["HF_TOKEN"] = userdata.get("HF_TOKEN")`
đúng ở cell cần; không `huggingface-cli login` trong notebook đã commit; không in token.

## 2. Mô hình truy cập GitHub: nhánh, PR, commit, changelog

Repo private trên tài khoản cá nhân (gói Free) **không có branch protection** — GitHub không chặn push thẳng lên `main` về
mặt kỹ thuật. Vì vậy kỷ luật nằm ở quy ước chỉ-PR + một workflow gác:

| Quy tắc | Cụ thể |
|---|---|
| Quyền | mọi thực tập sinh là **write collaborator** trên repo private của tài khoản cá nhân (được thêm ở kickoff) |
| Nhánh | tạo từ `main`, tiền tố theo nhóm: `data/<việc>-<tên>`, `ft/<việc>-<tên>`, `sys/<việc>` (epic S). Ví dụ `data/t2-preprocess-anh`. Không commit thẳng lên `main`. |
| Vào `main` | **chỉ qua pull request**; PR được review và merge sau khi CI xanh (người phụ trách merge) — áp dụng cho cả PR của epic S. Squash hay merge commit do người phụ trách merge chọn. |
| Tiêu đề PR | bắt đầu bằng mã việc: `[D-T1]`, `[D-V3]`, `[F-T2]`, `[F-V4]`, `[S-V6]` (D/F/S = nhóm; T = Tuần, V = Việc). Ví dụ `[F-T2] eval base vs ft trên xlam_2k.eval, CI + McNemar`. |
| Commit | conventional commits `type(scope): subject` — `feat`, `fix`, `docs`, `data`, `exp` (thí nghiệm), `chore`, `ci`, `refactor`. Ví dụ `data(sgod): [D-V2] lõi eval người viết 150 câu`. |
| CHANGELOG | `CHANGELOG.md` cập nhật **trong cùng commit** với thay đổi (một dòng, mới nhất ở trên). PR không có dòng changelog sẽ bị trả lại. |
| PR template | điền đủ 5 mục: mã việc & mục tiêu · thay đổi · đã chạy / chưa chạy · số liệu & truy vết · checklist. |
| Force-push | **KHÔNG** `git push --force` lên bất kỳ nhánh chung nào; trên nhánh cá nhân chỉ khi chưa có ai review. Không rebase `main`. |
| Tệp đóng băng | `eval_v1.json`, preamble đã chốt, `roles.json`, `sgod_tools.json` sau tag: không sửa trực tiếp; theo quy trình phiên bản mới trong hợp đồng. |
| Review | ít nhất một người cùng nhóm đọc trước khi merge; sửa theo comment bằng commit mới, không amend. |

**`main-guard.yml`**: chạy ở mỗi push vào `main`. Nếu `github.actor` không phải tài khoản phụ trách merge (chủ sở hữu
repo), workflow **mở một issue** ghi ai push, commit nào, có force-push hay không, và việc cần làm. Đây không phải trừng
phạt — là dấu vết để quyết định giữ hay revert (bằng PR) khi review. Nếu bạn vô tình push lên `main`: **không** tự
revert/force-push; bình luận vào issue và chờ quyết định trong issue đó.

**CI (`ci.yml`)** chạy ở mọi PR: `py_compile`; `prompts/*.txt` không chứa `<!--`; `validate_dataset.py` trên bộ công khai;
`finetune_qlora.py --dry-run --max-len 2560` trên `xlam_2k.train.jsonl` (CPU, chỉ tokenizer) phải `over_limit=0`;
`eval_toolcall.py` + `bootstrap_ci.py` smoke kèm `--md`; `check_provenance.py` trên fixtures **và** trên hai báo cáo vừa sinh;
và **grep bí mật** (thông tin thử nghiệm của SGOD, chuỗi giống khóa API kiểu OpenAI; bỏ qua `data/public/` vì văn bản bên
thứ ba có email mẫu). CI đỏ = chưa được review.

## 3. Bí mật

- **Không bao giờ commit** khóa API, token, mật khẩu, JWT, cookie, hay email cá nhân. Không dán vào notebook output, không
  dán vào ClickUp, không dán vào issue. Bao gồm cả `.env`, `*.ipynb` có output chứa header `Authorization`.
- `docs/sgod-api-reference.md` là **tài liệu API SGOD duy nhất**; mọi khóa và mật khẩu thử trong đó đã là placeholder
  `<SGOD_*_API_KEY>`, `<SGOD_TEST_PASSWORD>`. Giá trị thật chỉ nằm trong `.env` trên hạ tầng tham chiếu (`.env.example` là mẫu).
- `HF_TOKEN`, `GITHUB_TOKEN`: chỉ trong Colab/Kaggle Secrets (mục 1). Token GitHub là classic với scope `repo`, hạn ≤ 90
  ngày, tạo riêng cho việc này (không tái dùng token của dự án khác).
- `OPENAI_API_KEY` **không được chia sẻ** (gateway LLM của hạ tầng tham chiếu). Các bước cần LLM chạy trên hạ tầng tham
  chiếu, đầu ra commit vào repo (mục 4 của `docs/roadmap.md`, S Việc 5).
- Nếu lỡ commit bí mật: ghi vào comment của task và mở issue ngay để **xoay khóa** (rotate) trước; xoá khỏi lịch sử là
  việc sau, thực hiện theo issue đó (không tự force-push).
- Trước khi push, tự kiểm: `git diff --cached | grep -nE "api[_-]?key|token|password|Bearer "` phải không có giá trị thật.

## 4. Cách nộp kết quả lên ClickUp

Mỗi task ClickUp có `Tiêu chí hoàn thành:` — kết quả **dán làm bình luận trong task**, không gửi chat riêng.

1. Chạy notebook đến **cell cuối `## Tạo báo cáo`**. Cell này in đúng khối bình luận (Markdown) gồm: mã việc, ngày,
   git sha, sha256 dữ liệu vào, lệnh đã chạy, các con số, đường dẫn tệp kết quả trong repo, thời gian chạy, GPU. **Copy
   nguyên khối** (không sửa số bằng tay) → dán vào bình luận của task.
2. Nếu có số mới: thêm dòng vào `results/RUNLOG.md` (một dòng/run) và `results/INDEX.md` (một dòng/số báo cáo, `R###`
   tăng dần, cột `lệnh/notebook` là lệnh đầy đủ hoặc `notebook + tên cell`). `python scripts/check_provenance.py <md>` thoát 0.
3. Mở PR theo mục 2; dán **link PR** vào bình luận ClickUp (và link task ClickUp vào mục 1 của PR).
4. Đổi trạng thái task sang **in review**. Bình luận + PR được review và merge, rồi task đổi sang **complete**; nếu cần
   sửa → **update required** kèm bình luận; nếu bị chặn bởi việc khác → **at risk** / **on hold** và ghi rõ chờ gì.
5. Trước hạn mà thấy không kịp: đổi sang **at risk** ngay và bình luận lý do — sớm là tốt, muộn là vấn đề.

Quy tắc số: mọi phần trăm / p-value trong báo cáo, slide, bình luận đều phải có dòng INDEX; báo cáo bắt đầu bằng
`Ghi chú trục đo` (`docs/contracts/eval_metric.md` §6). Không có INDEX = không có số.

## 5. Làm việc với Colab / Kaggle / Google Drive

- **Cache model trên đĩa VM, đầu ra run lên Drive.** **Cell 3** của notebook huấn luyện (`drive.mount`) đặt
  `RUN_NAME` và `OUT = /content/drive/MyDrive/ChatSystem/runs/<RUN_NAME>` (Drive — sống qua phiên); mọi `--output-dir`
  và log đi vào `$OUT/...`. Cache model/tokenizer nằm trên đĩa VM (`~/.cache/huggingface`, mất khi hết phiên — tải lại
  nhanh). Giữ **cùng `RUN_NAME`** ở notebook 01/02/03. Không để checkpoint trên Drive bị `git add` (đã `.gitignore`
  `runs/`, `*.safetensors`).
- **Phiên kết thúc bất ngờ**: Colab miễn phí ngắt sau ~90 phút không tương tác, tối đa ~12 giờ, và có quota ngày. Vì thế
  `finetune_qlora.py` lưu `save_strategy=steps` (`--save-steps 50`) và mọi run dài phải chạy lại được bằng
  `--resume-from-checkpoint <dir>/checkpoint-<n>`. F Tuần 1 yêu cầu **cố ý** ngắt và chứng minh tiếp tục từ bước 101.
- **Kaggle** khi hết quota Colab: 30 GPU-giờ/tuần, T4×2 (script dùng 1 GPU), phiên ≤ 12 giờ, đầu ra trong
  `/kaggle/working`. Ưu tiên Kaggle cho run > 1 giờ (F Việc 1).
- **Không dùng unsloth trên Colab** (xung đột phiên bản với pin của nhóm và khác đường code với `finetune_qlora.py`);
  chỉ `transformers + peft + trl + bitsandbytes` theo `requirements-train.txt`.
- **Không `pip install torch`** trên Colab (dùng torch có sẵn); chỉ cài phần còn lại của `requirements-train.txt`.
- **dtype**: bf16 chỉ khi compute capability ≥ 8; T4 (7,5) → fp16. Script chọn theo compute capability (không theo
  `torch.cuda.is_bf16_supported()` vì hàm này báo sai trên một số cấu hình); `FORCE_FP16=1` ép fp16.
- **Số tái lập**: ghi seed vào mọi lệnh (`--seed`), `temperature 0` khi dự đoán, và sha256 tệp dữ liệu vào header
  dự đoán. Chạy ≥ 3 seed cho số báo cáo (F Việc 4).
- **Tiết kiệm quota**: smoke 200 hàng (`--max-rows 200`) trước mọi run dài; `--dry-run` trước mọi thay đổi dữ liệu;
  tắt runtime khi xong (*Runtime → Disconnect and delete runtime*).

## 6. Hai bẫy từ hệ thống tham chiếu (POC v1)

### 6.1 `max_len` ngắn hơn prompt + completion → loss = 0 mà không báo lỗi

Trong hệ thống tham chiếu (POC v1), `MAX_SEQ_LENGTH = 2048` ngắn hơn lượt system (preamble + 33 tool ≈ 3,4k token). Tokenizer cắt phần **cuối**
— chính là completion. Với completion-only loss, mọi token còn lại đều bị mask → loss = 0, gradient = 0, run "thành công"
với adapter vô dụng. Không có cảnh báo nào.

Pha 2: `training/finetune_qlora.py` **đếm hàng có `prompt + completion > --max-len`, in id và thoát mã 1**. Không có cắt
ngầm. `--dry-run` in prompt render của hàng 0 (phải thấy khối `<tools>`) và `unmasked completion tokens: N > 0`. Nếu bị
thoát 1: tăng `--max-len` (nếu VRAM cho phép), hoặc lọc hàng dài ở bước dữ liệu và **ghi lại** trong báo cáo — không bao giờ
"sửa" bằng cách bỏ kiểm tra hay bằng `--max-rows`.

Tình trạng hiện tại (2026-09-13) của bộ công khai: hàng dài nhất của `xlam_2k.train.jsonl` là **2.426 token** (`val`
1.276), nên chạy với `--max-len 1536` thì dry-run báo `over_limit=5` và thoát 1 — **đúng thiết kế**. Mặc định của script
(`DEFAULT_MAX_LEN = 2560` trong `training/finetune_qlora.py`), notebook 01 và CI đều dùng **`--max-len 2560`** (`over_limit=0`
cho cả train và val). Nếu dry-run của bạn ở 2560 vẫn báo `over_limit > 0`, dữ liệu trong repo đã đổi: báo trong bình luận
ClickUp kèm id, số token và `git HEAD` (xem `notebooks/finetune/README.md`).

### 6.2 `--lora-modules` của vLLM cần đường dẫn tồn tại **bên trong container**

vLLM chạy trong Docker chỉ thấy hệ tệp container. `--lora-modules name=/home/x/adapter` thất bại với
`No such file or directory` dù thư mục có trên host, hoặc tệ hơn: vLLM khởi động với base mà không có adapter, và mọi số
"fine-tune" đo được thực ra là zero-shot. `training/serve_vllm.sh` bind-mount thư mục adapter vào **cùng đường dẫn**
(`-v $ADAPTER:$ADAPTER:ro`). Trước khi đo bất kỳ số nào qua vLLM: `curl /v1/models` phải liệt kê **tên adapter**, và một
request thử phải trả `tool_calls`. Chi tiết: `docs/serving.md` §2–3.
