/**
 * API Client giao tiếp trực tiếp với Backend Chat (app/be/).
 * Mọi request đều gọi qua proxy /api để tránh vấn đề CORS và giấu kín API key.
 */

export interface UserContext {
  user_id: string;
  full_name: string;
  role: "company_admin" | "employee" | "system_admin";
  tier: "enterprises" | "enterprise-users" | "sub-enterprises";
  role_vi?: string;
  enterprise_name?: string;
}

export interface LoginResponse {
  success: boolean;
  access_token?: string;
  refresh_token?: string;
  user_context?: UserContext;
  message?: string;
}

export interface RefreshResponse {
  success: boolean;
  access_token?: string;
  refresh_token?: string;
  message?: string;
}

export interface MeResponse {
  success: boolean;
  user_context?: UserContext;
  message?: string;
}

export interface ToolExecutionRecord {
  tool_name: string;
  arguments: Record<string, any>;
  result: any;
  success: bool;
  error?: string;
}

export interface ChatResponse {
  success: boolean;
  reply: string;
  tools_executed?: ToolExecutionRecord[];
  token_refreshed?: boolean;
  new_access_token?: string;
  message?: string;
}

const BASE_URL = ""; // Sử dụng đường dẫn tương đối để tận dụng Vite Proxy /api -> http://localhost:8000

export async function loginApi(
  credential: string,
  password: string,
  tier?: string
): Promise<LoginResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential, password, tier: tier || undefined }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || errData.message || `Đăng nhập thất bại (HTTP ${res.status})`);
  }

  return await res.json();
}

export async function refreshApi(refreshToken: string): Promise<RefreshResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!res.ok) {
    throw new Error("Làm mới token thất bại");
  }

  return await res.json();
}

export async function getMeApi(accessToken: string): Promise<MeResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/me`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok) {
    throw new Error("Phiên làm việc hết hạn hoặc không hợp lệ");
  }

  return await res.json();
}

export async function sendChatApi(
  message: string,
  accessToken: string
): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/api/chat/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || errData.message || `Gửi tin nhắn thất bại (HTTP ${res.status})`);
  }

  return await res.json();
}

export async function getToolsApi(accessToken: string): Promise<{ role: string; count: number; tools: any[] }> {
  const res = await fetch(`${BASE_URL}/api/tools/`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok) {
    throw new Error("Không thể tải danh mục công cụ");
  }

  return await res.json();
}
