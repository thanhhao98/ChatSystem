# Phục vụ adapter bằng vLLM — hợp đồng bàn giao (F Việc 5) và cách chạy trên hạ tầng tham chiếu (S Việc 10)

## 1. Gói bàn giao adapter (nhóm F → hạ tầng tham chiếu)

Một adapter được nhận khi **thư mục** sau nạp được bằng `peft.PeftModel.from_pretrained(base, <dir>)` mà không cần
sửa gì, và số của nó tái lập được trong `notebooks/finetune/02_eval_toolcalling.ipynb`.

```
<served-name>/                         ví dụ: sgod-1.5b-v1-s42/
├── adapter_config.json                PEFT LoRA; base_model_name_or_path = id Hugging Face CHÍNH XÁC của base
│                                      (ví dụ "Qwen/Qwen2.5-1.5B-Instruct"); r ≤ 16 (nếu khác phải ghi rõ trong README);
│                                      target_modules = q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj
├── adapter_model.safetensors          trọng số LoRA (không kèm base, không merge)
├── training_config.json               do finetune_qlora.py ghi: mọi flag, seed, max_len, dtype, phiên bản thư viện
├── log_history.json                   đường loss / lr theo bước
└── README.md                          xem mẫu bên dưới
```

`README.md` trong thư mục adapter (điền đủ, tiếng Việt):

```markdown
# <served-name>
- Base: Qwen/Qwen2.5-1.5B-Instruct · LoRA r16/α32 · completion-only · lr 1e-4 · 2 epoch · seed 42
- Dữ liệu: data/sgod/train.jsonl @ <sha8> (+ val.jsonl @ <sha8>) · preamble v1 @ <sha8> · tools-v1 @ <sha8>
- Repo: git <sha7> · recipe: training/recipes/sgod_v1.yaml
- Số đã báo cáo: INDEX R0xx (strict acc trên eval_v1), RUNLOG dòng <ngày>
- Cách tái lập: notebooks/finetune/02_eval_toolcalling.ipynb, cell "Nạp adapter từ zip"
- Yêu cầu phục vụ: --max-lora-rank 16 · --max-model-len 8192 · --dtype half nếu T4
```

Quy trình nộp:

1. Zip đúng thư mục trên: `zip -r <served-name>_<YYYY-MM-DD>.zip <served-name>/` → tải lên **Drive chung** của nhóm
   (thư mục `ChatSystem/adapters/`); dán vào task ClickUp: link Drive, `sha256sum` của zip, tên phục vụ, và **một**
   request `chat.completions` mẫu (mục 4) kèm phản hồi.
2. Commit vào repo **chỉ** `adapter_config.json`, `training_config.json`, `log_history.json`, `README.md` dưới
   `results/adapters/<served-name>/` (không commit `.safetensors` — đã bị `.gitignore`).
3. Một thành viên **khác** của nhóm F nạp lại zip trong notebook 02 và tái lập số trong INDEX (sai lệch cho phép: 0 khi
   `temperature 0` cùng backend; nếu khác backend transformers ↔ vLLM, ghi cả hai số, cùng trục đo).

Tên phục vụ: `sgod-<size>-<recipe>-s<seed>` (ví dụ `sgod-0.5b-v1-s42`, `sgod-1.5b-v1-s7`), chữ thường, không dấu cách.
Tên này là `served-model-name` trong vLLM, là `model` trong header dự đoán và là cột `model` trong INDEX — **không đổi tên
giữa các nơi**.

## 2. Phục vụ trên hạ tầng tham chiếu bằng `training/serve_vllm.sh` (S Việc 10)

`training/serve_vllm.sh` là bản của `serve_slm.sh` (hệ thống tham chiếu, POC v1) bỏ phần SSH tới máy GPU từ xa; chạy vLLM OpenAI server **tại chỗ**
(Docker hoặc `python -m vllm.entrypoints.openai.api_server`). Biến môi trường:

| Biến | Mặc định | Nghĩa |
|---|---|---|
| `MODEL` | `Qwen/Qwen2.5-0.5B-Instruct` | base Hugging Face (phải **bằng** `base_model_name_or_path` của adapter; script cảnh báo nếu khác) |
| `ADAPTER` | (trống = không LoRA) | thư mục adapter PEFT (script đổi sang đường dẫn tuyệt đối và kiểm `adapter_config.json` tồn tại) |
| `SERVED` | `qwen2.5-0.5b` | tên phục vụ; với LoRA = tên trong `--lora-modules`; container tên `vllm-$SERVED` |
| `PORT` | `8000` | cổng OpenAI-compatible → `http://localhost:$PORT/v1` |
| `MAX_LEN` | `8192` | `--max-model-len` (preamble v1 + tool ≤ 3.400 token; 8192 đủ) |
| `DTYPE` | `auto` | `auto` \| `half` \| `bfloat16` \| `float16`; `auto` đọc compute capability qua `nvidia-smi`: < 8 → `half`, ≥ 8 → để vLLM tự chọn (bf16) |
| `MAX_LORA_RANK` | `16` | `--max-lora-rank`; tăng nếu adapter r > 16 |
| `GPU` | `0` | chỉ số CUDA device |
| `GPU_MEM_UTIL` | `0.85` | `--gpu-memory-utilization` |
| `HF_CACHE` | `~/.cache/huggingface` | cache Hugging Face của host, mount vào container để không tải lại base |
| `HF_TOKEN` | (trống) | chuyển vào container khi đặt (model gated); không ghi ra đâu |
| `IMAGE` / `IMAGE_TAG` | `vllm/vllm-openai:v0.22.0` | image Docker; đổi tag qua `IMAGE_TAG` |

```bash
# base + một adapter
MODEL=Qwen/Qwen2.5-1.5B-Instruct ADAPTER=/data/adapters/sgod-1.5b-v1-s42 SERVED=sgod-1.5b-v1-s42 \
  bash training/serve_vllm.sh

# kiểm tra
curl -s http://localhost:8000/v1/models | python -m json.tool     # phải thấy "id": "sgod-1.5b-v1-s42"

# dừng
docker rm -f vllm-sgod-1.5b-v1-s42
```

Script chờ `/v1/models` trả 200 (tối đa `HEALTH_TRIES` × 5 s), in danh sách model đã phục vụ, rồi in sẵn lệnh smoke-test
`curl` và lệnh `predict_toolcall.py --backend openai` trỏ vào server. Không có Docker (Colab/Kaggle) → dùng phần
"pip alternative" ở cuối script.

Cờ vLLM mà script sinh ra (để đọc log / chạy tay khi cần):

```
--model $MODEL --served-model-name $SERVED --max-model-len $MAX_LEN --dtype $DTYPE
--gpu-memory-utilization 0.85
--enable-auto-tool-choice --tool-call-parser hermes
--enable-lora --max-lora-rank $MAX_LORA_RANK --lora-modules $SERVED=$ADAPTER      # chỉ khi có ADAPTER
```

Nhiều adapter cùng base trong **một** phiên (S Việc 9: 3B zero-shot + 3B SFT): lặp `--lora-modules a=/p/a b=/p/b`;
request với `model: "<base served name>"` là zero-shot, `model: "a"` là adapter. Không cần nạp lại base.

### Bẫy đã gặp ở hệ thống tham chiếu (POC v1): đường dẫn `--lora-modules` phải tồn tại **bên trong container**

vLLM chạy trong Docker chỉ thấy hệ tệp của container. `--lora-modules name=/home/x/adapter` sẽ báo
`No such file or directory` dù thư mục tồn tại trên host. `serve_vllm.sh` bind-mount thư mục adapter vào **cùng
đường dẫn** (`-v $ADAPTER:$ADAPTER:ro`) để cờ resolve được; nếu chạy Docker tay thì phải tự thêm `-v`. Cache Hugging Face
cũng mount (`-v ~/.cache/huggingface:/root/.cache/huggingface`) để không tải lại base.

## 3. vLLM parse tool call như thế nào (hermes)

1. Client gửi `chat.completions` với `tools=[…]` (OpenAI function object) và `messages=[system, user]`.
2. vLLM áp **chat template của Qwen2.5** lên messages + tools → lượt system chứa khối
   `<tools>[{"type":"function","function":{…}}, …]</tools>` và hướng dẫn trả lời bằng
   `<tool_call>{"name":…,"arguments":{…}}</tool_call>`. Đây chính là prompt `finetune_qlora.py` dùng khi huấn luyện
   (`apply_chat_template(tools=)`), nên **không có** lệch train/serve.
3. Model sinh text `<tool_call>{…}</tool_call>` (một hoặc nhiều tag).
4. `--tool-call-parser hermes` nhận dạng tag, parse JSON, và trả về theo chuẩn OpenAI:
   `choices[0].message.tool_calls = [{"id": "...", "type": "function", "function": {"name": "...", "arguments": "<json string>"}}]`,
   `finish_reason = "tool_calls"`. Text không nằm trong tag đi vào `message.content`.
5. `--enable-auto-tool-choice` cho phép `tool_choice="auto"` (mặc định của client OpenAI) — không có nó vLLM từ chối
   request có `tools`.
6. JSON hỏng trong tag → hermes bỏ qua, text nằm lại trong `content`; `predict_toolcall.py` do đó **cũng** parse
   `raw_text` để đếm `json_valid` (hợp đồng 2 §4), không chỉ tin `tool_calls`.

Ghi chú: `arguments` từ API là **chuỗi JSON**; predictor phải `json.loads` về dict trước khi ghi `predicted_tool_calls`.

## 4. Request mẫu (dán vào task cùng phản hồi)

```python
from openai import OpenAI
import json
client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
tools = json.load(open("tools/sgod/sgod_tools.json"))
# lọc theo vai trò như executor làm: chỉ tool mà tool_policy.json cho phép user_role này
policy = json.load(open("tools/sgod/tool_policy.json"))
role = "employee"
tools = [t for t in tools if role in policy[t["function"]["name"]]["roles"]]
# Qwen chỉ nhận đúng object function chuẩn — bỏ x_sgod trước khi gửi
tools = [{"type": "function", "function": t["function"]} for t in tools]
# điền 3 slot của preamble v1 đúng như lúc huấn luyện (ngữ cảnh generic; backend điền giá trị thật khi phục vụ người dùng)
roles_cfg = json.load(open("tools/sgod/roles.json"))
preamble = open("prompts/system_preamble_v1.txt", encoding="utf-8").read().strip().format(
    full_name="Người dùng", role_vi=roles_cfg["role_names_vi"][role], user_id="usr-001")

r = client.chat.completions.create(
    model="sgod-1.5b-v1-s42",
    messages=[{"role": "system", "content": preamble},
              {"role": "user", "content": "Tôi đang giữ những tài sản nào?"}],
    tools=tools, tool_choice="auto", temperature=0, max_tokens=256)
m = r.choices[0].message
print(r.choices[0].finish_reason)            # tool_calls
for tc in m.tool_calls or []:
    print(tc.function.name, json.loads(tc.function.arguments))
```

Phản hồi mong đợi: `finish_reason == "tool_calls"`, đúng một `tool_calls[0].function.name` nằm trong danh mục của vai
trò, `arguments` parse được. Backend ChatSystem gọi cùng endpoint này (`SLM_BASE_URL`, `SLM_MODEL`) — vì vậy số đo offline
của `predict_toolcall.py --backend openai` và hành vi online là một.

## 5. Chạy vLLM trên Colab T4 (tuỳ chọn, `03_serve_vllm_colab.ipynb`)

- Bắt buộc `--dtype half` (T4 không có bf16), `--max-model-len 4096`, `--gpu-memory-utilization 0.85`; 0.5B/1.5B vừa
  15 GB; 3B fp16 + KV cache thường không vừa cùng adapter.
- Chạy server nền (`nohup … &`), chờ `/v1/models` trả 200 rồi mới gửi request; đo p50 latency trên ≥ 30 request.
- Phiên Colab kết thúc là mất server — không dùng cho số báo cáo chính (số chính đo qua `predict_toolcall.py` với
  backend transformers hoặc vLLM trên hạ tầng tham chiếu, ghi rõ backend trong header và INDEX).
