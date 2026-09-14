# Kiến trúc đích — Chat System pha 2 (SGOD thật)

Pha 1 (hệ thống tham chiếu, POC v1) chứng minh trên backend Flask tự dựng: một Qwen2.5-3B fine-tune (QLoRA, phục vụ bằng vLLM) **ngang**
GPT ở tool-calling trên cùng 37 tool. Pha 2 giữ nguyên bộ khung chat và thay backend đồ chơi bằng **nền tảng SGOD thật**
(`docs/sgod-api-reference.md`): gateway một cổng, ba service `auth` / `asset` / `chat`, hai thông tin xác thực mỗi lời gọi
(`x-api-key` theo service + JWT của người dùng), phong bì `{success, data, message}` trong đó HTTP 200 vẫn có thể là lỗi.

## 1. Sơ đồ

```
Browser ── login (tài khoản SGOD + mật khẩu) ──► ChatSystem backend
                                                 │  POST /sgod-auth/v1/<tier>/sessions → accessToken / refreshToken (theo người dùng)
                                                 │  GET /users/myself + /session/context → user_context; tier → role (docs/contracts/roles.md)
   chat ────────────────────────────────────────►│  router: mode = gpt_only | slm   (cùng tools, cùng preamble, cùng executor)
                                                 │     ├─ GPT qua gateway tương thích OpenAI (OPENAI_BASE_URL / OPENAI_MODEL)
                                                 │     └─ SLM: Qwen2.5 + LoRA trên vLLM (OpenAI-compatible, hermes tool parser)
                                                 │  tool_executor → cổng authz (tools/sgod/tool_policy.json) → SGOD adapter
                                                 │     (x-api-key theo service + Bearer JWT người dùng; rẽ nhánh theo body.success; refresh khi 401)
                                                 └──► <SGOD_BASE_URL>/sgod-{auth,asset,chat}/v1/...
```

Ba bất biến kế thừa từ hệ thống tham chiếu (POC v1):

1. **Hai mode so sánh được.** `gpt_only` và `slm` nhận **cùng** danh mục tool (`tools/sgod/sgod_tools.json` lọc theo vai
   trò), **cùng** preamble (`prompts/system_preamble_v1.txt`), **cùng** executor và cùng cổng authz. Khác nhau duy nhất là
   model sinh `<tool_call>`.
2. **Quyền do mã quyết định, không do LLM.** Mọi tool call đi qua `authorize_tool_call` (đọc `tool_policy.json`) trước khi
   có bất kỳ HTTP request nào; tool ngoài quyền không được render cho model (`model_roles`) và nếu model vẫn gọi thì bị chặn
   (`exec_roles`). JWT của chính người dùng scoping dữ liệu theo tenant (spec §1 "Identity scoping") — vì vậy **không tool
   nào có tham số company/tenant/enterprise id**.
3. **Train/serve parity.** Tool không bao giờ nằm trong text của message; cả huấn luyện và phục vụ render tool bằng
   `apply_chat_template(tools=)` (hợp đồng 1).

## 2. Tái sử dụng nguyên trạng vs. cần bộ chuyển đổi SGOD

| Thành phần (POC v1) | Pha 2 | Ghi chú |
|---|---|---|
| `chat_policy.authorize_tool_call` + audit logger | **giữ nguyên** | nguồn dữ liệu quyền đổi từ `TOOL_POLICY` (Python) sang `tools/sgod/tool_policy.json` (JSON, đọc lúc khởi động); giữ bijection tool ↔ policy |
| `conversation_memory.py` | giữ nguyên | pha 2 một lượt ở dữ liệu/eval; memory chỉ phục vụ UI |
| Vòng lặp GPT (`chat_service.py`) | giữ nguyên | client OpenAI-compatible; tôn trọng `OPENAI_BASE_URL`, `OPENAI_MODEL`; tên model hiển thị lấy từ config, không ghi cứng |
| Vòng lặp SLM + chống ảo giác (`small_model_service.py`) | giữ nguyên | endpoint đổi sang `SLM_BASE_URL` / `SLM_MODEL` |
| Router: dispatch mode + probe SLM TTL (60 s up / 10 s down) | giữ nguyên | bỏ hẳn tầng classifier + rule engine của hybrid (pha 2 chỉ `gpt_only` \| `slm`) |
| Hợp đồng API `/chat` + `ChatWidget.tsx` | giữ nguyên | |
| `tool_executor.py`: `API_BASE`, `TOOL_ROUTES`, header builder, unwrap phong bì, `_resolve_asset_ref` | **SGOD adapter** (S Việc 6) | route đọc từ `x_sgod` trong `sgod_tools.json`; header `x-api-key` theo `x_sgod.service` + `Authorization: Bearer <JWT người dùng>`; rẽ nhánh theo `body.success`, không theo HTTP status; refresh khi 401 rồi gọi lại một lần; chuỗi tên→id gói trong một tool (`x_sgod.resolve`, executor làm suggest→get) |
| Đăng nhập: `api/auth.py`, `AuthContext.tsx`, `LoginPage.tsx`, `client.ts` | **viết lại** (S Việc 7) | `POST /sgod-auth/v1/<tier>/sessions`; giữ access/refresh token theo phiên; không lưu mật khẩu |
| 3 bản `user_context` builder trùng lặp | **gộp thành một**, đọc `tools/sgod/roles.json` | |
| Từ vựng vai trò (`chat_policy.py` L23–25, `system_prompt.py` L57–61) | **ánh xạ từ tier SGOD** (hợp đồng 3, `roles.md`) | `enterprises` → `company_admin`; `enterprise-users`, `sub-enterprises` → `employee`; `system_admin` giữ nhưng không dùng; không bao giờ khoá theo ObjectId vai trò của SGOD |
| `tool_definitions.py` (37 tool Python) | **thay bằng** `tools/sgod/sgod_tools.json` (D Việc 1, ~20 tool chỉ đọc) | schema mô tả tiếng Việt; metadata chỉ nằm dưới `x_sgod`; `validate_tools.py` kiểm ngân sách token |
| `rule_engine.py` + classifier TF-IDF | **loại bỏ** | nguyên nhân chính của khoảng cách Hybrid–GPT trong POC v1; pha 2 đo SLM thuần |
| `config.py` | thêm `SGOD_*`, `SLM_*` | xem `.env.example` |

## 3. Hình dạng danh mục tool (hợp đồng 4, tóm tắt)

```
tools/sgod/sgod_tools.json  = [ {"type":"function",
                                 "function": {"name", "description" (VN), "parameters" (JSON Schema)},
                                 "x_sgod": {"service": "asset", "method": "GET", "path": "/assets/{id}",
                                            "jwt_scoped": true, "allowed_roles": [...], "writes": false,
                                            "id_params": ["id"], "resolve": "assets/suggest?q="}} , ... ]
tools/sgod/tool_policy.json = { "<tool>": {"writes": false, "roles": ["employee", "company_admin"]} }
tools/sgod/roles.json       = ánh xạ tier SGOD → vai trò chat (máy đọc của docs/contracts/roles.md)
```

Luật: không tham số kiểu company/tenant/enterprise id; endpoint hỏng ở spec §4 và mọi tool `/sgod-chat/v1` cho vai trò
không phải owner nằm trong blocklist; pha 2 chỉ tool **chỉ đọc** (`writes: false`). `tools/sgod/validate_tools.py`
kiểm tất cả + ngân sách token (preamble ≤ 1.000, lượt system với vai trò nhiều tool nhất ≤ 3.400 token Qwen).

## 4. Dòng dữ liệu và đo lường

```
docs/sgod-api-reference.md ─► D Việc 1: sgod_tools.json (+ fixtures S Việc 2) ─► S Việc 4 xác minh, tag tools-v1
                                        │
       D Việc 2: eval_human_core (người viết, ≥150)    D Việc 3: prompt sinh (datagen/prompts) ─► run_pipeline.sh (hạ tầng tham chiếu)
                                        └────────────► D Việc 4: eval_v1.json (đóng băng, sha256) ◄──────────┘
                                                                  │  chống rò rỉ SequenceMatcher < 0.65
                                                       D Việc 5: train/val.jsonl (build_parity_trainset, preamble v1)
                                                                  │
   F: finetune_qlora.py (T4: 0.5B/1.5B, ≥3 seed) · hạ tầng tham chiếu: finetune_multi.py (GPU, 3B)  ─► adapter (PEFT)
                                                                  │
            predict_toolcall.py (vLLM / gateway / transformers) ─► *.predictions.jsonl (header sha256)
                                                                  │
            eval_toolcall.py ─► results.json ─► bootstrap_ci.py (CI, hiệu ghép đôi, McNemar) ─► H1 giữ / không giữ
                                                                  │
                                            results/INDEX.md + RUNLOG.md ◄─ scripts/check_provenance.py
```

Thứ tự bắt buộc: **eval trước dữ liệu huấn luyện** (eval_v1 đóng băng 10-25 trước khi sinh hàng SGOD nào), và mọi hàng
huấn luyện được sàng rò rỉ với eval_v1.

## 5. Mô hình phục vụ

- **GPT**: gateway tương thích OpenAI; `OPENAI_BASE_URL`, `OPENAI_MODEL`, `OPENAI_API_KEY` (chỉ trên hạ tầng tham chiếu).
- **SLM**: vLLM `--enable-auto-tool-choice --tool-call-parser hermes --enable-lora --lora-modules <served>=<adapter>`,
  cùng một base Qwen2.5 cho nhiều adapter; chi tiết và hợp đồng bàn giao adapter ở `docs/serving.md`.
- Backend gọi cả hai qua **một** client OpenAI-compatible với `tools=` — đúng cách predictor (`training/predict_toolcall.py`)
  gọi lúc đánh giá, nên số đo offline và hành vi online là cùng một đường.
