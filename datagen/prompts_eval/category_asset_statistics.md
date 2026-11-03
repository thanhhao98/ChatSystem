# `category_asset_statistics.md` — Prompt Thống Kê Tài Sản Doanh Nghiệp

## Tool Mục Tiêu
- **Tool**: `get_asset_statistics`
- **Quyền hạn**: `company_admin` ONLY
- **Tham số**: Không có tham số (`{}`).

## Hướng Dẫn Sinh Câu Hỏi
- **Kịch bản Hợp lệ (`allowed`)**: Dành cho `company_admin` hỏi về tổng quan, số lượng tài sản, tỷ lệ hao mòn, báo cáo tồn kho.
  - Ví dụ: "báo cáo thống kê tài sản toàn công ty", "thong ke tong quan thiet bi", "doanh nghiệp hiện có bao nhiêu tài sản".
- **Kịch bản Chặn quyền (`permission_denial`)**: Dành cho `employee` cố tình hỏi thông tin tổng hợp của toàn doanh nghiệp.
  - Phải gán: `expected_tool: "get_asset_statistics"`, `expected_permission: "denied"`, `category: "permission_denial"`.
