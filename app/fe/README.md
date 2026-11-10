# Hướng dẫn Phát triển Frontend ChatSystem (`app/fe`)

> **Dành cho:** Frontend Developer (Phương Thảo)
> **Phiên bản:** 1.0 (Scaffold & Architecture Integration)
> **Stack:** React 18 + TypeScript + Vite

---

## 1. Giới thiệu & Kiến trúc

Thư mục `app/fe` chứa mã nguồn giao diện cho hệ thống Chatbot Hỗ trợ Doanh nghiệp SGOD.
Frontend giao tiếp trực tiếp với Backend FastAPI (`app/be`) thông qua Vite reverse proxy tại đường dẫn `/api/`.

```
app/fe/
├── index.html                  # HTML entry point
├── package.json                # Dependencies & scripts
├── tsconfig.json               # Cấu hình TypeScript
├── vite.config.ts              # Cấu hình Vite & Proxy tới http://localhost:8000
├── src/
│   ├── main.tsx                # Mount ứng dụng & bọc AuthProvider
│   ├── App.tsx                 # Điều hướng hiển thị (Login vs ChatWidget)
│   ├── context/
│   │   └── AuthContext.tsx     # Context quản lý phiên đăng nhập, JWT token, user info
│   ├── services/
│   │   └── client.ts           # Service API giao tiếp với Backend (/api/auth, /api/chat, /api/tools)
│   └── components/
│       ├── LoginPage.tsx       # Màn hình đăng nhập mẫu
│       └── ChatWidget.tsx      # Giao diện khung chat mẫu có kết nối Gemini Agentic Tool Calling
└── README.md                   # Tài liệu hướng dẫn này
```

---

## 2. Hướng dẫn Chạy Thử (Quick Start)

### Bước 1: Khởi động Backend (`app/be`)

Đảm bảo Backend đã được kích hoạt và đang chạy trên cổng `8000`:

```bash
# Từ thư mục gốc dự án ChatSystem:
source .venv/bin/activate
cd app/be
python -m uvicorn main:app --reload --port 8000
```

Backend Swagger kiểm tra: [http://localhost:8000/docs](http://localhost:8000/docs)

### Bước 2: Khởi động Frontend (`app/fe`)

Mở một terminal mới:

```bash
cd app/fe
npm install
npm run dev
```

Trình duyệt sẽ mở tại: **[http://localhost:5173](http://localhost:5173)**

---

## 3. Tài khoản Test Mẫu (SGOD Live Gateway)

Hệ thống đã kết nối sẵn với Gateway SGOD thực tế:

- **Email / Credential:** `thuongpx2007@gmail.com`
- **Mật khẩu:** `PasswordStrong123@`
- **Tier:** `enterprises` (Doanh nghiệp)
- **Quyền hạn (Role):** `company_admin` (Quản trị viên công ty, sở hữu quyền gọi toàn bộ danh mục tài sản, phòng ban, danh mục).

---

## 4. Đặc tả API Backend (`app/be`)

Frontend giao tiếp với Backend thông qua các endpoints đã được chuẩn hóa tại `src/services/client.ts`:

### 4.1. Đăng nhập (`POST /api/auth/login`)

- **Body:**
  ```json
  {
    "credential": "thuongpx2007@gmail.com",
    "password": "PasswordStrong123@",
    "tier": "enterprises"
  }
  ```
- **Response:**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "...",
    "token_type": "bearer",
    "user_id": "usr_...",
    "role": "company_admin",
    "email": "thuongpx2007@gmail.com"
  }
  ```

### 4.2. Lấy thông tin người dùng (`GET /api/auth/me`)

- **Headers:** `Authorization: Bearer <access_token>`
- **Response:** Thông tin hồ sơ doanh nghiệp / người dùng từ SGOD.

### 4.3. Lấy danh sách công cụ được cấp quyền (`GET /api/tools/`)

- **Headers:** `Authorization: Bearer <access_token>`
- **Response:** Trả về danh sách các tool mà tài khoản hiện tại được phép gọi (ví dụ: `list_my_assets`, `get_asset`, `list_categories`, `list_locations`,...).

### 4.4. Trò chuyện với Trợ lý ảo AI (`POST /api/chat/`)

- **Headers:** `Authorization: Bearer <access_token>`
- **Body:**
  ```json
  {
    "message": "Tôi đang có những tài sản nào?",
    "history": []
  }
  ```
- **Response:**
  ```json
  {
    "reply": "Bạn hiện có 3 tài sản: 1. Màn hình Dell 001...",
    "tools_called": [
      {
        "name": "list_my_assets",
        "arguments": {}
      }
    ]
  }
  ```

---

## 5. Nhiệm vụ Tiếp theo cho Frontend (Phương Thảo)

1. **Thiết kế & Hoàn thiện UI/UX:**
   - Thay thế style inline hiện tại bằng CSS Framework (TailwindCSS, Ant Design hoặc MUI tùy chọn).
   - Thiết kế giao diện Chat chuyên nghiệp: sidebar lịch sử chat, avatar bot/user, bong bóng chat (chat bubbles).
2. **Hiển thị Markdown & Rich UI:**
   - Cài đặt thư viện như `react-markdown` để render câu trả lời dạng bảng, danh sách, in đậm từ AI.
   - Hiển thị badge trực quan khi AI kích hoạt một tool (ví dụ: `🔧 Đã thực thi công cụ: list_my_assets`).
3. **Xử lý UX khi gọi API:**
   - Loading skeleton hoặc typing animation ("Bot đang suy nghĩ...").
   - Hiển thị thông báo Toast khi đăng nhập thất bại hoặc hết hạn phiên làm việc (tự động logout khi 401).
