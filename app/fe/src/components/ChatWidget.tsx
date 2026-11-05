import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { ChatMessage, ToolExecutionRecord, sendChatApi } from "../services/client";

interface MessageItem {
  id: string;
  sender: "user" | "assistant";
  text: string;
  tools?: ToolExecutionRecord[];
  timestamp: string;
}

export const ChatWidget: React.FC = () => {
  const { user, token, refreshToken, logout, updateAccessToken } = useAuth();
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: `Xin chào ${user?.full_name || "bạn"}! Tôi là trợ lý AI kết nối trực tiếp với nền tảng quản lý tài sản SGOD. Bạn có thể hỏi tôi bất kỳ thông tin nào về tài sản, lịch bảo trì hoặc vị trí lưu kho.`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const handleSend = async (customText?: string) => {
    const textToSend = customText || input;
    if (!textToSend.trim() || sending || !token) return;

    const userMsg: MessageItem = {
      id: String(Date.now()),
      sender: "user",
      text: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    // Chuẩn bị 8 tin nhắn gần nhất làm lịch sử ngữ cảnh
    const historyPayload: ChatMessage[] = messages
      .filter((m) => m.id !== "welcome" && !m.text.startsWith("⚠️"))
      .slice(-8)
      .map((m) => ({
        role: m.sender === "user" ? "user" : "assistant",
        content: m.text,
      }));

    setMessages((prev) => [...prev, userMsg]);
    if (!customText) setInput("");
    setSending(true);

    try {
      const res = await sendChatApi(
        textToSend.trim(),
        token,
        historyPayload,
        refreshToken || undefined,
        updateAccessToken
      );
      if (res.new_access_token) {
        updateAccessToken(res.new_access_token);
      }

      const botMsg: MessageItem = {
        id: String(Date.now() + 1),
        sender: "assistant",
        text: res.reply || "Đã xử lý xong yêu cầu.",
        tools: res.tools_executed,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      const errMsg = err.message || "Không thể nhận phản hồi từ máy chủ";
      const errorMsg: MessageItem = {
        id: String(Date.now() + 1),
        sender: "assistant",
        text: `⚠️ Lỗi: ${errMsg}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);

      // Nếu lỗi phiên đăng nhập không thể refresh -> Tự động logout về trang login
      if (errMsg.toLowerCase().includes("hết hạn") || errMsg.toLowerCase().includes("expired") || errMsg.includes("401")) {
        setTimeout(() => {
          logout();
        }, 2500);
      }
    } finally {
      setSending(false);
    }
  };

  const suggestions = [
    "Cho tôi xem danh sách tài sản của tôi",
    "Có những địa điểm lưu kho nào?",
    "Xem danh mục phân loại tài sản",
    "Thông tin hồ sơ doanh nghiệp là gì?",
  ];

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.userInfo}>
          <div style={styles.avatar}>🤖</div>
          <div>
            <div style={styles.userName}>
              {user?.full_name}
              <span style={styles.roleBadge}>
                {user?.role_vi || user?.role}
              </span>
            </div>
            <div style={styles.enterpriseText}>
              {user?.enterprise_name || "SGOD Enterprise Platform"} • Tier: {user?.tier}
            </div>
          </div>
        </div>
        <button onClick={logout} style={styles.logoutBtn} title="Đăng xuất">
          Đăng xuất ➔
        </button>
      </div>

      {/* Message Area */}
      <div style={styles.messageArea}>
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              ...styles.messageRow,
              justifyContent: m.sender === "user" ? "flex-end" : "flex-start",
            }}
          >
            {m.sender === "assistant" && <div style={styles.botAvatar}>🤖</div>}
            <div style={m.sender === "user" ? styles.userBubble : styles.assistantBubble}>
              {/* Tool Execution Badges if any */}
              {m.tools && m.tools.length > 0 && (
                <div style={styles.toolsContainer}>
                  {m.tools.map((t, idx) => (
                    <div key={idx} style={styles.toolBadge}>
                      <span style={styles.toolIcon}>🛠️</span>
                      <span>Đã gọi API SGOD: <strong>{t.tool_name}</strong></span>
                      <span style={{ color: t.success ? "#16a34a" : "#dc2626", fontWeight: "bold" }}>
                        {t.success ? "✓ Thành công" : "✗ Thất bại"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <div style={styles.bubbleText}>{m.text}</div>
              <div style={styles.bubbleTime}>{m.timestamp}</div>
            </div>
          </div>
        ))}

        {sending && (
          <div style={{ ...styles.messageRow, justifyContent: "flex-start" }}>
            <div style={styles.botAvatar}>🤖</div>
            <div style={styles.loadingBubble}>
              <span style={styles.dot}>•</span>
              <span style={styles.dot}>•</span>
              <span style={styles.dot}>•</span>
              <span style={{ marginLeft: "8px", fontSize: "13px", color: "#6b7280" }}>
                Đang xử lý & gọi dữ liệu SGOD...
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Suggestions */}
      <div style={styles.suggestionsContainer}>
        {suggestions.map((s, idx) => (
          <button
            key={idx}
            disabled={sending}
            onClick={() => handleSend(s)}
            style={styles.suggestionChip}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        style={styles.inputBar}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Nhập câu hỏi tra cứu tài sản (ví dụ: 'Tìm tài sản Màn hình Dell')..."
          disabled={sending}
          style={styles.chatInput}
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          style={{
            ...styles.sendBtn,
            opacity: sending || !input.trim() ? 0.6 : 1,
            cursor: sending || !input.trim() ? "not-allowed" : "pointer",
          }}
        >
          Gửi
        </button>
      </form>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    maxWidth: "960px",
    margin: "0 auto",
    backgroundColor: "#ffffff",
    boxShadow: "0 0 20px rgba(0, 0, 0, 0.05)",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "16px 24px",
    backgroundColor: "#ffffff",
    borderBottom: "1px solid #e5e7eb",
  },
  userInfo: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },
  avatar: {
    fontSize: "28px",
  },
  userName: {
    fontSize: "16px",
    fontWeight: "700",
    color: "#111827",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  roleBadge: {
    fontSize: "11px",
    fontWeight: "600",
    backgroundColor: "#dbeafe",
    color: "#1d4ed8",
    padding: "2px 8px",
    borderRadius: "12px",
  },
  enterpriseText: {
    fontSize: "12px",
    color: "#6b7280",
    marginTop: "2px",
  },
  logoutBtn: {
    backgroundColor: "transparent",
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    padding: "6px 12px",
    fontSize: "13px",
    color: "#4b5563",
    cursor: "pointer",
  },
  messageArea: {
    flex: 1,
    overflowY: "auto",
    padding: "20px 24px",
    backgroundColor: "#f9fafb",
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  messageRow: {
    display: "flex",
    alignItems: "flex-start",
    gap: "8px",
  },
  botAvatar: {
    fontSize: "22px",
    marginTop: "2px",
  },
  userBubble: {
    maxWidth: "75%",
    backgroundColor: "#2563eb",
    color: "#ffffff",
    padding: "12px 16px",
    borderRadius: "16px 16px 2px 16px",
    boxShadow: "0 1px 3px rgba(0, 0, 0, 0.1)",
  },
  assistantBubble: {
    maxWidth: "75%",
    backgroundColor: "#ffffff",
    color: "#1f2937",
    padding: "14px 18px",
    borderRadius: "16px 16px 16px 2px",
    border: "1px solid #e5e7eb",
    boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
  },
  loadingBubble: {
    backgroundColor: "#ffffff",
    padding: "12px 16px",
    borderRadius: "16px",
    border: "1px solid #e5e7eb",
    display: "flex",
    alignItems: "center",
  },
  dot: {
    fontSize: "18px",
    color: "#9ca3af",
    marginRight: "2px",
  },
  toolsContainer: {
    marginBottom: "10px",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  toolBadge: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    backgroundColor: "#f3f4f6",
    border: "1px solid #e5e7eb",
    borderRadius: "6px",
    padding: "4px 8px",
    fontSize: "12px",
    color: "#374151",
  },
  toolIcon: {
    fontSize: "13px",
  },
  bubbleText: {
    fontSize: "14px",
    lineHeight: "1.5",
    whiteSpace: "pre-wrap",
  },
  bubbleTime: {
    fontSize: "11px",
    opacity: 0.7,
    marginTop: "4px",
    textAlign: "right",
  },
  suggestionsContainer: {
    display: "flex",
    gap: "8px",
    padding: "10px 24px",
    backgroundColor: "#ffffff",
    overflowX: "auto",
    borderTop: "1px solid #f3f4f6",
  },
  suggestionChip: {
    backgroundColor: "#f3f4f6",
    border: "1px solid #e5e7eb",
    borderRadius: "16px",
    padding: "6px 12px",
    fontSize: "12px",
    color: "#374151",
    cursor: "pointer",
    whiteSpace: "nowrap",
  },
  inputBar: {
    display: "flex",
    gap: "10px",
    padding: "16px 24px",
    backgroundColor: "#ffffff",
    borderTop: "1px solid #e5e7eb",
  },
  chatInput: {
    flex: 1,
    padding: "12px 16px",
    fontSize: "14px",
    border: "1px solid #d1d5db",
    borderRadius: "24px",
    outline: "none",
  },
  sendBtn: {
    backgroundColor: "#2563eb",
    color: "#ffffff",
    border: "none",
    borderRadius: "24px",
    padding: "0 24px",
    fontSize: "14px",
    fontWeight: "600",
  },
};
