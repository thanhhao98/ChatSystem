/**
 * API Client giao tiếp trực tiếp với Backend Chat (app/be/).
 * Hỗ trợ tự động refresh JWT token khi gặp HTTP 401, gửi kèm lịch sử chat,
 * xử lý lỗi chuẩn và giao tiếp dạng Server-Sent Events (SSE) streaming.
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
  success: boolean;
  error?: string;
  duration_ms?: number;
  is_running?: boolean;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system" | "tool";
  content?: string;
  name?: string;
  tool_call_id?: string;
}

export interface ChatResponse {
  success: boolean;
  reply: string;
  tools_executed?: ToolExecutionRecord[];
  token_refreshed?: boolean;
  new_access_token?: string;
  message?: string;
  response_time_ms?: number;
  token_usage?: TokenUsage;
}

export interface StreamCallbacks {
  onStatus?: (statusText: string) => void;
  onToolStart?: (toolName: string, args: Record<string, any>) => void;
  onToolResult?: (record: ToolExecutionRecord) => void;
  onDelta?: (chunk: string) => void;
  onDone?: (res: ChatResponse) => void;
  onError?: (errMessage: string) => void;
}

const BASE_URL = ""; // Đường dẫn tương đối qua Vite Proxy /api -> http://localhost:8000

export function extractErrorMessage(errData: any, status: number): string {
  if (typeof errData?.detail === "string") {
    return errData.detail;
  }
  if (Array.isArray(errData?.detail)) {
    return errData.detail
      .map((e: any) => `${e.loc ? e.loc.slice(-1)[0] + ": " : ""}${e.msg || JSON.stringify(e)}`)
      .join("; ");
  }
  return errData?.message || `Yêu cầu thất bại (HTTP ${status})`;
}

/**
 * Dispatch các sự kiện toàn cục để đồng bộ session giữa API Client và React AuthContext.
 */
function notifyTokenRefreshed(newAccess: string, newRefresh?: string) {
  localStorage.setItem("sgod_access_token", newAccess);
  if (newRefresh) {
    localStorage.setItem("sgod_refresh_token", newRefresh);
  }
  window.dispatchEvent(
    new CustomEvent("sgod:token_refreshed", {
      detail: { accessToken: newAccess, refreshToken: newRefresh },
    })
  );
}

function notifyLogout() {
  localStorage.removeItem("sgod_access_token");
  localStorage.removeItem("sgod_refresh_token");
  localStorage.removeItem("sgod_user_context");
  window.dispatchEvent(new CustomEvent("sgod:logout"));
}

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
    throw new Error(extractErrorMessage(errData, res.status));
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
    const errData = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(errData, res.status));
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
    const errData = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(errData, res.status));
  }

  return await res.json();
}

/**
 * Gửi tin nhắn chat đến backend dạng Server-Sent Events (SSE) Streaming.
 */
export async function sendChatApiStream(
  message: string,
  accessToken: string,
  history: ChatMessage[] = [],
  refreshToken?: string,
  callbacks: StreamCallbacks = {},
  onTokenRefreshed?: (newToken: string) => void
): Promise<void> {
  let currentToken = accessToken || localStorage.getItem("sgod_access_token") || "";
  const currentRefresh = refreshToken || localStorage.getItem("sgod_refresh_token") || "";

  const doStreamRequest = async (tokenToUse: string): Promise<Response> => {
    return await fetch(`${BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${tokenToUse}`,
      },
      body: JSON.stringify({
        message,
        history,
        refresh_token: currentRefresh || undefined,
      }),
    });
  };

  let res = await doStreamRequest(currentToken);

  // Nếu gặp 401 Unauthorized -> Tự động refresh token và thử lại
  if (res.status === 401 && currentRefresh) {
    try {
      const refRes = await refreshApi(currentRefresh);
      if (refRes.success && refRes.access_token) {
        currentToken = refRes.access_token;
        notifyTokenRefreshed(refRes.access_token, refRes.refresh_token);
        if (onTokenRefreshed) {
          onTokenRefreshed(refRes.access_token);
        }
        res = await doStreamRequest(currentToken);
      } else {
        notifyLogout();
        callbacks.onError?.("Phiên đăng nhập đã hết hạn");
        return;
      }
    } catch {
      notifyLogout();
      callbacks.onError?.("Làm mới phiên làm việc thất bại");
      return;
    }
  }

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    const errText = extractErrorMessage(errData, res.status);
    callbacks.onError?.(errText);
    throw new Error(errText);
  }

  if (!res.body) {
    callbacks.onError?.("Trình duyệt không hỗ trợ đọc dữ liệu stream");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) {
        currentEvent = "";
        continue;
      }
      if (trimmed.startsWith("event: ")) {
        currentEvent = trimmed.slice(7).trim();
      } else if (trimmed.startsWith("data: ")) {
        const rawJson = trimmed.slice(6).trim();
        try {
          const payload = JSON.parse(rawJson);
          if (currentEvent === "status") {
            callbacks.onStatus?.(payload.message || "");
          } else if (currentEvent === "tool_start") {
            callbacks.onToolStart?.(payload.tool_name, payload.arguments || {});
          } else if (currentEvent === "tool_result") {
            callbacks.onToolResult?.(payload);
          } else if (currentEvent === "delta") {
            callbacks.onDelta?.(payload.content || "");
          } else if (currentEvent === "done") {
            if (payload.token_refreshed && payload.new_access_token) {
              notifyTokenRefreshed(payload.new_access_token);
              if (onTokenRefreshed) {
                onTokenRefreshed(payload.new_access_token);
              }
            }
            callbacks.onDone?.(payload);
          } else if (currentEvent === "error") {
            callbacks.onError?.(payload.error || "Lỗi xử lý mô hình AI");
          }
        } catch {
          // ignore malformed JSON chunk
        }
      }
    }
  }
}

/**
 * Gửi tin nhắn chat đến backend (chế độ blocking HTTP).
 */
export async function sendChatApi(
  message: string,
  accessToken: string,
  history: ChatMessage[] = [],
  refreshToken?: string,
  onTokenRefreshed?: (newToken: string) => void
): Promise<ChatResponse> {
  let currentToken = accessToken || localStorage.getItem("sgod_access_token") || "";
  const currentRefresh = refreshToken || localStorage.getItem("sgod_refresh_token") || "";

  const doRequest = async (tokenToUse: string): Promise<Response> => {
    return await fetch(`${BASE_URL}/api/chat/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${tokenToUse}`,
      },
      body: JSON.stringify({
        message,
        history,
        refresh_token: currentRefresh || undefined,
      }),
    });
  };

  let res = await doRequest(currentToken);

  if (res.status === 401 && currentRefresh) {
    try {
      const refRes = await refreshApi(currentRefresh);
      if (refRes.success && refRes.access_token) {
        currentToken = refRes.access_token;
        notifyTokenRefreshed(refRes.access_token, refRes.refresh_token);
        if (onTokenRefreshed) {
          onTokenRefreshed(refRes.access_token);
        }
        res = await doRequest(currentToken);
      } else {
        notifyLogout();
      }
    } catch {
      notifyLogout();
    }
  }

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(errData, res.status));
  }

  const result: ChatResponse = await res.json();
  if (result.token_refreshed && result.new_access_token) {
    notifyTokenRefreshed(result.new_access_token);
    if (onTokenRefreshed) {
      onTokenRefreshed(result.new_access_token);
    }
  }

  return result;
}

export async function getToolsApi(accessToken: string): Promise<{ role: string; count: number; tools: any[] }> {
  let currentToken = accessToken || localStorage.getItem("sgod_access_token") || "";
  let res = await fetch(`${BASE_URL}/api/tools/`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${currentToken}`,
    },
  });

  if (res.status === 401) {
    const currentRefresh = localStorage.getItem("sgod_refresh_token");
    if (currentRefresh) {
      try {
        const refRes = await refreshApi(currentRefresh);
        if (refRes.success && refRes.access_token) {
          notifyTokenRefreshed(refRes.access_token, refRes.refresh_token);
          res = await fetch(`${BASE_URL}/api/tools/`, {
            method: "GET",
            headers: {
              Authorization: `Bearer ${refRes.access_token}`,
            },
          });
        }
      } catch {
        notifyLogout();
      }
    }
  }

  if (!res.ok) {
    throw new Error("Không thể tải danh mục công cụ");
  }

  return await res.json();
}
