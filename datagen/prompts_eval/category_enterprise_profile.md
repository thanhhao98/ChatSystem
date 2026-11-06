# `category_enterprise_profile.md` — Prompt Hồ Sơ Doanh Nghiệp

## Tool Mục Tiêu
- **Tool**: `get_enterprise_profile`
- **Quyền hạn**: `company_admin` ONLY
- **Tham số**: Không có tham số (`{}`).
- **Alternates**: `get_my_profile` (khi ngữ cảnh hỏi mơ hồ thông tin tài khoản doanh nghiệp).

## Hướng Dẫn Sinh Câu Hỏi
- **Kịch bản Hợp lệ**: `company_admin` hỏi "thông tin doanh nghiệp", "hồ sơ công ty", "mã số thuế và địa chỉ công ty".
- **Kịch bản Chặn quyền (`denied`)**: `employee` cố tình hỏi thông tin pháp lý doanh nghiệp -> `expected_tool: "get_enterprise_profile"`, `expected_permission: "denied"`.
