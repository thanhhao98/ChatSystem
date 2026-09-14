# Hợp đồng 1 — Định dạng hàng huấn luyện (training row format)

| | |
|---|---|
| Phiên bản | v1 (Drop 0, 2026-09-13) |
| Đóng băng | **Điểm đồng bộ 1 — 2026-09-27**. Sau đó mọi thay đổi = phiên bản mới của tài liệu này + PR + `CHANGELOG.md`. |
| Cổng máy | `training/validate_dataset.py` (CPU, stdlib). Mọi tệp `*.jsonl` huấn luyện phải thoát mã 0 trước khi vào PR. |
| Tham chiếu | `datagen/convert_xlam.py` (cài đặt tham chiếu cho hàng công khai), `datagen/build_parity_trainset.py` (hàng SGOD), `training/finetune_qlora.py` (cách render prompt). |

Hàng huấn luyện là đơn vị dữ liệu **duy nhất** mà `training/finetune_qlora.py` nhận. Cùng một định dạng cho
bộ công khai xLAM (`data/public/`) và bộ SGOD (`data/sgod/`); chỉ khác nguồn tool và preamble.

## 1. Hình dạng một hàng

Mỗi dòng của tệp `.jsonl` là một JSON object:

```
{
  "id":           <string, tuỳ chọn nhưng khuyến nghị; "pub-xxxxxxxx" cho bộ công khai, "sgod-tr-000123" cho bộ SGOD>,
  "role":         <string, BẮT BUỘC; thuộc tập vai trò của tools/sgod/roles.json — mặc định {"employee","company_admin","system_admin"}>,
  "messages":     <list, BẮT BUỘC; ĐÚNG 3 phần tử theo thứ tự system → user → assistant>,
  "replay":       <true, tuỳ chọn; có mặt khi và chỉ khi hàng mang "replay_tools">,
  "replay_tools": <list các OpenAI function object, tuỳ chọn; danh mục tool RIÊNG của hàng (bộ công khai)>
}
```

Quy tắc từng trường:

| Trường | Quy tắc |
|---|---|
| `messages[0]` | `role == "system"`; `content.strip()` phải **bằng đúng** preamble của vai trò: `prompts/system_preamble_v0.txt` cho hàng công khai (trung tính, ≤ 300 token, không chứa danh từ nghiệp vụ); `prompts/system_preamble_v1.txt` đã điền ba slot cho hàng SGOD: `{role_vi}` = tên tiếng Việt của `role` theo `tools/sgod/roles.json.role_names_vi`, và ngữ cảnh **generic** `{full_name}` = `Người dùng`, `{user_id}` = `usr-001` (model học cấu trúc, không học id cụ thể; lúc phục vụ backend điền giá trị thật). `datagen/build_parity_trainset.py`, `training/validate_dataset.py` và `tools/sgod/validate_tools.py` dùng cùng một cách điền. |
| `messages[1]` | `role == "user"`; câu hỏi **một lượt** (single-turn). Không có lịch sử hội thoại, không có tool result. |
| `messages[2]` | `role == "assistant"`; nội dung là **một trong ba dạng** ở mục 2. |
| `role` | Vai trò của người hỏi. Quyết định tool nào được render vào prompt (lọc theo `tools/sgod/tool_policy.json`) và câu trả lời từ chối. |
| `replay_tools` | Chỉ hàng công khai. Mỗi phần tử có dạng `{"type":"function","function":{"name","description","parameters"}}`, `parameters` là JSON Schema (`type: object`, `properties`, `required`). Tool gọi trong `messages[2]` phải có trong danh sách này. Hàng không có `replay_tools` lấy tool từ `tools/sgod/sgod_tools.json` lọc theo `role`. |
| Khoá khác | Khoá cấp hàng ngoài danh sách trên (`source`, `meta`, …) được bỏ qua, không gây lỗi. `id` nếu có phải là chuỗi. |

**Tool KHÔNG BAO GIỜ nằm trong text của message.** Danh mục tool được render lúc huấn luyện và lúc phục vụ bởi
`tokenizer.apply_chat_template(messages[:-1], tools=<tools>, tokenize=False, add_generation_prompt=True)`
(mẫu chat của Qwen2.5 sinh khối `<tools>…</tools>` trong lượt system). Đây là sửa lỗi "train/serve parity"
đã cho +18 điểm phần trăm ở hệ thống tham chiếu (POC v1); nhúng tool bằng tay vào system prompt là vi phạm hợp đồng.

## 2. Ba dạng câu trả lời của assistant

1. **Gọi tool** — một hoặc nhiều tag liền nhau, mỗi tag một JSON hợp lệ, không có text nào khác:
   ```
   <tool_call>{"name": "<tên tool>", "arguments": {<tham số>}}</tool_call>
   ```
   `arguments` luôn là object (có thể `{}`), giá trị chỉ lấy từ câu hỏi, không bịa.
2. **Từ chối vì quyền** — đúng chuỗi `REFUSAL_VI` trong `prompts/fixed_replies.json`:
   `Xin lỗi, bạn không có quyền thực hiện thao tác này. Vui lòng liên hệ quản trị viên.`
3. **Ngoài phạm vi** — đúng chuỗi `DEFLECT_VI` trong `prompts/fixed_replies.json`:
   `Xin lỗi, tôi chỉ hỗ trợ các tác vụ quản lý tài sản. Bạn vui lòng nêu yêu cầu liên quan nhé.`

So khớp hai chuỗi cố định sau `.strip()`; không chấp nhận biến thể. Hai chuỗi này được sao từ
`build_parity_trainset.py` (L26–27) của hệ thống tham chiếu (POC v1) và **không đổi** trong pha 2.

## 3. Ví dụ

### 3a. Hàng công khai (từ `data/public/xlam_2k.train.jsonl`, id `pub-06aecb40`, rút gọn còn 1 trong 3 tool)

```json
{"id": "pub-06aecb40", "role": "employee", "replay": true,
 "replay_tools": [
   {"type": "function", "function": {"name": "email",
     "description": "Checks if a given email address is disposable using the MailCheck3 API.",
     "parameters": {"type": "object",
       "properties": {"email": {"description": "The email address to be checked.", "type": "str", "default": "email@example.com"}},
       "required": []}}}
 ],
 "messages": [
   {"role": "system", "content": "Bạn là trợ lý AI hỗ trợ gọi công cụ (tool calling). Khi người dùng đưa ra yêu cầu, hãy chọn đúng công cụ trong danh sách công cụ được cung cấp và điền tham số chính xác, chỉ dùng thông tin có trong yêu cầu, không tự bịa giá trị. Nếu yêu cầu không thuộc phạm vi các công cụ, hãy trả lời ngắn gọn bằng tiếng Việt rằng bạn không hỗ trợ được."},
   {"role": "user", "content": "Is user@temp-mail.org a disposable email?"},
   {"role": "assistant", "content": "<tool_call>{\"name\": \"email\", \"arguments\": {\"email\": \"user@temp-mail.org\"}}</tool_call>"}
 ]}
```

Ghi chú: xLAM ghi kiểu tham số là `"str"`, `"int, optional"`… (không phải JSON Schema chuẩn). Validator chỉ
kiểm tra hình dạng (`type: object` + `properties` + `required`), không kiểm kiểu; tool schema SGOD phải dùng kiểu
JSON Schema chuẩn (`string`, `integer`, …) — `tools/sgod/validate_tools.py` kiểm điều đó.

### 3b. Hàng SGOD với REFUSAL (minh hoạ; tên tool và preamble v1 chốt tại Điểm đồng bộ 1)

```json
{"id": "sgod-tr-000123", "role": "employee",
 "messages": [
   {"role": "system", "content": "<prompts/system_preamble_v1.txt với {role_vi}=Nhân viên, {full_name}=Người dùng, {user_id}=usr-001>"},
   {"role": "user", "content": "Cho tôi danh sách toàn bộ nhân viên trong công ty kèm email và số điện thoại."},
   {"role": "assistant", "content": "Xin lỗi, bạn không có quyền thực hiện thao tác này. Vui lòng liên hệ quản trị viên."}
 ]}
```

Hàng SGOD không có `replay_tools`: lúc huấn luyện, `finetune_qlora.py --tools tools/sgod/sgod_tools.json` render
đúng các tool mà `tool_policy.json` cho phép vai trò `employee` — giống hệt lúc phục vụ. Một hàng REFUSAL chỉ hợp lệ
khi tool cần thiết **không** nằm trong tập tool của vai trò đó (labeler và `validate_dataset.py --tools --roles` kiểm).

### 3c. Hàng SGOD gọi tool (minh hoạ)

```json
{"id": "sgod-tr-000124", "role": "company_admin",
 "messages": [
   {"role": "system", "content": "<preamble v1 với {role_vi}=Quản trị viên doanh nghiệp, ngữ cảnh generic>"},
   {"role": "user", "content": "Liệt kê các lịch bảo trì đang hiệu lực."},
   {"role": "assistant", "content": "<tool_call>{\"name\": \"list_maintenance_schedules\", \"arguments\": {\"status\": \"active\"}}</tool_call>"}
 ]}
```

## 4. Độ dài và cắt ngắn

- `MAX_SEQ_LENGTH` chuẩn là **4096** token (arm 3B trên máy GPU của hạ tầng tham chiếu). Mặc định của `finetune_qlora.py`
  là `--max-len 2560` (`DEFAULT_MAX_LEN`); trên T4 miễn phí, notebook 01 và CI dùng đúng **`--max-len 2560`** cho bộ công khai
  vì hàng dài nhất của `data/public/xlam_2k.train.jsonl` là 2.426 token (prompt + completion; `val` 1.276) — với giá trị
  thấp hơn như 1536, 5 hàng vượt giới hạn và script thoát mã 1 (`over_limit=5`), đúng hành vi mong muốn. CI chạy dry-run
  ở 2560 và đòi `over_limit=0`. Bộ SGOD dùng giá trị theo dry-run nếu VRAM cho phép. Quy tắc: **không hạ `--max-len` dưới hàng dài nhất và không dùng `--max-rows`
  để "bỏ" hàng**; lọc hàng dài là việc của bước dữ liệu và phải ghi vào báo cáo.
- Nếu `prompt + completion` của một hàng dài hơn `--max-len`, `finetune_qlora.py` **in id hàng và thoát mã 1**.
  Không bao giờ cắt ngầm: sự cố ở hệ thống tham chiếu (POC v1, `finetune_multi.py` L50–51) là 2048 token cắt mất phần completion →
  completion-only loss che toàn bộ → loss = 0 mà không báo lỗi. `--dry-run` phải in `unmasked completion tokens: N > 0`
  và số hàng bị cắt = 0.
- Ngân sách token của preamble v1 và của lượt system đã render (preamble + tool của vai trò nhiều tool nhất) do
  `tools/sgod/validate_tools.py` kiểm: preamble ≤ 1.000 token Qwen, lượt system ≤ 3.400 token.

## 5. Nguồn tool và preamble theo loại hàng

| Loại hàng | `role` | `replay_tools` | Preamble (`messages[0]`) | Ai tạo |
|---|---|---|---|---|
| Công khai (xLAM) | luôn `employee` | có, tool riêng của hàng | `system_preamble_v0.txt` (đã đóng băng, sha256 `ebcae911…`) | `datagen/convert_xlam.py` (D Tuần 2) |
| SGOD | theo persona của câu hỏi | không | `system_preamble_v1.txt` với `{role_vi}` theo vai trò + `{full_name}`/`{user_id}` generic | `datagen/build_parity_trainset.py` (D Việc 5) |
| Replay trộn khi huấn luyện SGOD | `employee` | có | v0 | `datagen/assemble_trackb_trainset.py` (tỷ lệ ~1,4× ở arm 3B) |

## 6. Ai đóng băng gì, khi nào

| Hạng mục | Việc / nguồn | Khi | Sau khi đóng băng |
|---|---|---|---|
| Tài liệu này (hợp đồng 1) | Drop 0 → Điểm đồng bộ 1 | Điểm đồng bộ 1 — 2026-09-27 | đổi = phiên bản mới + PR + CHANGELOG; `validate_dataset.py` cập nhật cùng PR |
| `prompts/system_preamble_v0.txt` | Drop 0 | đã đóng băng (Drop 0) | không đổi trong pha 2 |
| `prompts/system_preamble_v1.txt` | S Việc 3 | văn bản nền chốt 09-27; **quy tắc chọn tool có thể bổ sung đến 2026-10-11**; sau đó đóng băng | đổi = trục đo mới (xem hợp đồng 2). Tệp prompt là **văn bản thuần cho model**: không chú thích HTML (`<!-- -->`), không ghi chú trạng thái/TODO — chúng sẽ lọt vào `messages[0]` của mọi hàng SGOD và vào ngân sách token. Ghi chú trạng thái nằm ở `prompts/README.md`; CI thất bại nếu `prompts/*.txt` chứa `<!--`. |
| `prompts/fixed_replies.json` | Drop 0 | đã đóng băng (Drop 0) | không đổi |
| `docs/contracts/roles.md` + `tools/sgod/roles.json` | S Việc 3 | 2026-09-27 | đổi → phải gán nhãn lại toàn bộ dữ liệu |
| `tools/sgod/sgod_tools.json` + `tool_policy.json` | D Việc 1, xác minh S Việc 4 | tag `tools-v1`, 2026-10-08 | đổi = tag mới + trục đo mới |

## 7. Danh sách kiểm tra của `training/validate_dataset.py`

1. Mỗi dòng là JSON object; `messages` đúng 3 phần tử với thứ tự role `system`, `user`, `assistant`.
2. `messages[0].content.strip()` bằng preamble (`--preamble`, hoặc bỏ qua bằng `--no-preamble-check`).
3. `messages[2].content` là chuỗi `<tool_call>…</tool_call>` hợp lệ (JSON parse được, có `name` + `arguments` object) **hoặc** đúng `REFUSAL_VI` / `DEFLECT_VI`.
4. `role` thuộc tập vai trò (`--roles`).
5. Nếu có `replay_tools`: hình dạng OpenAI function; `replay == true`; tool trong `<tool_call>` có trong `replay_tools`.
6. Nếu không có `replay_tools`: cần `--tools`; tool trong `<tool_call>` có trong danh mục, tham số có trong `parameters.properties`, và vai trò được phép theo `tool_policy.json` cùng thư mục.
7. In số hàng lỗi theo loại; **mã thoát 1 nếu có bất kỳ lỗi**.
