<!-- Tiêu đề PR phải mang mã việc ClickUp: "[D-V1] …", "[F-T2] …", "[S-V3] …" (D/F/S = nhóm, T = Tuần, V = Việc). -->

## 1. Mã việc và mục tiêu
- ClickUp: <!-- dán link task, ví dụ https://app.clickup.com/t/... --> 
- Mục tiêu của PR này (1–2 câu):

## 2. Thay đổi
<!-- Liệt kê tệp / thư mục chính và điều gì đổi. Nếu đổi flag của script trong docs/contracts/cli.md → nói rõ và cập nhật cli.md + CHANGELOG trong cùng PR. -->
- 

## 3. Đã chạy / chưa chạy
<!-- Lệnh đã chạy và kết quả (dán 1–3 dòng cuối). Ghi rõ những gì CHƯA chạy và vì sao (không có GPU, thiếu dữ liệu, …). -->
- Đã chạy:
  - `…`
- Chưa chạy:
  - 

## 4. Số liệu và truy vết
<!-- Mọi con số mới xuất hiện trong PR (README, docs/reports, results, notebook) cần một dòng trong results/INDEX.md và một dòng trong results/RUNLOG.md. Nếu PR không có số → ghi "không có số mới". -->
- Dòng INDEX: 
- Dòng RUNLOG: 
- Ghi chú trục đo (eval@sha8 · tools@sha8 · preamble): 

## 5. Kiểm tra trước khi xin review
- [ ] Nhánh có tiền tố đúng nhóm (`data/`, `ft/`, `sys/`) và PR nhắm vào `main`
- [ ] Tiêu đề PR mang mã việc; commit theo conventional commits (`type(scope): subject`)
- [ ] `CHANGELOG.md` được cập nhật **trong cùng commit** với thay đổi
- [ ] Mọi con số mới có dòng `results/INDEX.md` (+ `results/RUNLOG.md`); `python scripts/check_provenance.py <report.md>` thoát 0
- [ ] Nếu đổi `tools/sgod/*.json`: dán đầu ra `python tools/sgod/validate_tools.py` (kèm số token)
- [ ] Nếu đổi dữ liệu huấn luyện: `python training/validate_dataset.py <rows.jsonl>` thoát 0
- [ ] Không có khóa / token / mật khẩu / email cá nhân trong diff (`git grep` sạch)
- [ ] Không force-push; không sửa tệp đã đóng băng (`eval_v1.json`, preamble đã chốt, `roles.json`) ngoài quy trình phiên bản mới
- [ ] Đã đặt ClickUp task sang **in review** và dán link PR vào task
