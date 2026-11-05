import * as React from "react"
import {
  Send,
  Sun,
  Moon,
  Plus,
  MessageSquare,
  Trash2,
  LogOut,
  Sparkles,
  Wrench,
  CheckCircle2,
  XCircle,
  PanelLeftClose,
  PanelLeftOpen,
  Bot,
  User as UserIcon,
  ChevronDown,
  ChevronUp,
  Clock,
  Zap,
  Cpu,
  FileText,
} from "lucide-react"
import { useAuth } from "../context/AuthContext"
import {
  ChatMessage,
  TokenUsage,
  ToolExecutionRecord,
  sendChatApiStream,
} from "../services/client"
import { Hero } from "@/components/ui/hero"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export interface MessageItem {
  id: string
  sender: "user" | "assistant"
  text: string
  tools?: ToolExecutionRecord[]
  timestamp: string
  responseTimeMs?: number
  outputTokens?: number
  tokensPerSec?: number
  tokenUsage?: TokenUsage
  isStreaming?: boolean
  statusMessage?: string
}

export interface ChatSession {
  id: string
  title: string
  messages: MessageItem[]
  updatedAt: string
}

const SUGGESTIONS = [
  "Cho tôi xem danh sách tài sản của tôi",
  "Có những địa điểm lưu kho nào?",
  "Xem danh mục phân loại tài sản",
  "Thông tin hồ sơ doanh nghiệp là gì?",
]

export const ChatWidget: React.FC = () => {
  const { user, token, refreshToken, logout, updateAccessToken } = useAuth()

  const storageKey = React.useMemo(
    () => `sgod_chat_history_${user?.user_id || "guest"}`,
    [user?.user_id],
  )

  // Theme state (default to dark mode to showcase the interactive spotlight lamp)
  const [theme, setTheme] = React.useState<"dark" | "light">(() => {
    const saved = localStorage.getItem("sgod_theme")
    return saved === "light" || saved === "dark" ? saved : "dark"
  })

  React.useEffect(() => {
    const root = document.documentElement
    if (theme === "dark") {
      root.classList.add("dark")
    } else {
      root.classList.remove("dark")
    }
    localStorage.setItem("sgod_theme", theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"))
  }

  // Interactive Lamp focus state
  const [isChatFocused, setIsChatFocused] = React.useState(false)

  // Sidebar & Chat History state
  const [sidebarOpen, setSidebarOpen] = React.useState<boolean>(true)
  const [sessions, setSessions] = React.useState<ChatSession[]>(() => {
    try {
      const raw = localStorage.getItem(`sgod_chat_history_${user?.user_id || "guest"}`)
      return raw ? JSON.parse(raw) : []
    } catch {
      return []
    }
  })
  const [activeSessionId, setActiveSessionId] = React.useState<string | null>(null)
  const [messages, setMessages] = React.useState<MessageItem[]>([])
  const [input, setInput] = React.useState("")
  const [sending, setSending] = React.useState(false)
  const [expandedTools, setExpandedTools] = React.useState<Record<string, boolean>>({})

  const toggleToolExpand = (key: string) => {
    setExpandedTools((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  // Typewriter buffer refs for buttery smooth streaming
  const textBufferRef = React.useRef<string>("")
  const displayedLengthRef = React.useRef<number>(0)
  const isStreamActiveRef = React.useRef<boolean>(false)
  const typingIntervalRef = React.useRef<any>(null)

  const stopTypewriter = () => {
    if (typingIntervalRef.current) {
      clearInterval(typingIntervalRef.current)
      typingIntervalRef.current = null
    }
  }

  const startTypewriter = (botId: string) => {
    stopTypewriter()
    typingIntervalRef.current = setInterval(() => {
      const buffer = textBufferRef.current
      const currentLen = displayedLengthRef.current
      const remaining = buffer.length - currentLen

      if (remaining > 0) {
        // Tốc độ thích ứng: nhả từ 1-3 ký tự mỗi nhịp (20ms) để tốc độ đều và mượt như gõ phím.
        // Nếu buffer bị dồn nhiều do mạng (remaining > 35), tăng tốc dần để theo kịp
        const step = Math.max(1, Math.min(Math.ceil(remaining / 6), 14))
        const nextLen = Math.min(currentLen + step, buffer.length)
        displayedLengthRef.current = nextLen
        const textToDisplay = buffer.slice(0, nextLen)

        setMessages((prev) =>
          prev.map((m) =>
            m.id === botId
              ? { ...m, text: textToDisplay, statusMessage: undefined }
              : m
          )
        )
      } else if (!isStreamActiveRef.current && remaining === 0) {
        stopTypewriter()
      }
    }, 20)
  }

  React.useEffect(() => {
    return () => {
      stopTypewriter()
    }
  }, [])

  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  // Load sessions when user changes
  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey)
      const parsed: ChatSession[] = raw ? JSON.parse(raw) : []
      setSessions(parsed)
    } catch {
      setSessions([])
    }
  }, [storageKey])

  // Persist sessions to localStorage
  const saveSessions = React.useCallback(
    (updated: ChatSession[]) => {
      setSessions(updated)
      try {
        localStorage.setItem(storageKey, JSON.stringify(updated))
      } catch {
        // Ignore quota errors
      }
    },
    [storageKey],
  )

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, sending])

  // Auto-resize textarea height
  React.useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [input, messages.length])

  // Focus management on composer container to prevent flicker between textarea & send button
  const handleComposerFocusCapture = () => {
    setIsChatFocused(true)
  }

  const handleComposerBlurCapture = (e: React.FocusEvent<HTMLFormElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
      setIsChatFocused(false)
    }
  }

  const handleNewChat = () => {
    setActiveSessionId(null)
    setMessages([])
    setInput("")
  }

  const handleSelectSession = (session: ChatSession) => {
    setActiveSessionId(session.id)
    setMessages(session.messages)
  }

  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation()
    const filtered = sessions.filter((s) => s.id !== sessionId)
    saveSessions(filtered)
    if (activeSessionId === sessionId) {
      setActiveSessionId(null)
      setMessages([])
    }
  }

  const syncSessionMessages = (nextMessages: MessageItem[], firstUserText?: string) => {
    const nowStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    if (!activeSessionId) {
      const newId = `session_${Date.now()}`
      const newSession: ChatSession = {
        id: newId,
        title: (firstUserText || "Cuộc trò chuyện mới").slice(0, 48),
        messages: nextMessages,
        updatedAt: nowStr,
      }
      setActiveSessionId(newId)
      saveSessions([newSession, ...sessions])
    } else {
      const updated = sessions.map((s) =>
        s.id === activeSessionId
          ? { ...s, messages: nextMessages, updatedAt: nowStr }
          : s,
      )
      saveSessions(updated)
    }
  }

  const handleSend = async (customText?: string) => {
    const textToSend = (customText ?? input).trim()
    if (!textToSend || sending || !token) return

    const userMsg: MessageItem = {
      id: String(Date.now()),
      sender: "user",
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    }

    // Chuẩn bị 8 tin nhắn gần nhất làm lịch sử ngữ cảnh
    const historyPayload: ChatMessage[] = messages
      .filter((m) => !m.text.startsWith("⚠️"))
      .slice(-8)
      .map((m) => ({
        role: m.sender === "user" ? "user" : "assistant",
        content: m.text,
      }))

    const updatedWithUser = [...messages, userMsg]
    const botMsgId = String(Date.now() + 1)
    const initialBotMsg: MessageItem = {
      id: botMsgId,
      sender: "assistant",
      text: "",
      tools: [],
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      isStreaming: true,
      statusMessage: "Đang phân tích yêu cầu...",
    }

    const currentTurnMessages = [...updatedWithUser, initialBotMsg]
    setMessages(currentTurnMessages)
    syncSessionMessages(updatedWithUser, textToSend)

    if (!customText) setInput("")
    setSending(true)

    // Khởi tạo bộ đệm nhả chữ mượt mà & bấm giờ client
    const reqStartTime = performance.now()
    textBufferRef.current = ""
    displayedLengthRef.current = 0
    isStreamActiveRef.current = true
    startTypewriter(botMsgId)

    try {
      await sendChatApiStream(
        textToSend,
        token,
        historyPayload,
        refreshToken || undefined,
        {
          onStatus: (statusText) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botMsgId
                  ? { ...m, statusMessage: statusText }
                  : m
              )
            )
          },
          onToolStart: (toolName, args) => {
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== botMsgId) return m
                const existing = m.tools || []
                const newRecord: ToolExecutionRecord = {
                  tool_name: toolName,
                  arguments: args,
                  result: null,
                  success: false,
                  is_running: true,
                }
                return {
                  ...m,
                  tools: [...existing, newRecord],
                  statusMessage: `Đang thực thi công cụ SGOD: ${toolName}...`,
                }
              })
            )
          },
          onToolResult: (record) => {
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== botMsgId) return m
                const existing = m.tools || []
                const updated = existing.map((t) =>
                  t.tool_name === record.tool_name && t.is_running
                    ? { ...record, is_running: false }
                    : t
                )
                if (!updated.some((t) => t.tool_name === record.tool_name)) {
                  updated.push({ ...record, is_running: false })
                }
                return {
                  ...m,
                  tools: updated,
                  statusMessage: `Đã hoàn thành ${record.tool_name}`,
                }
              })
            )
          },
          onDelta: (chunk) => {
            // Đẩy vào hàng đợi đệm để nhả chữ mượt mà
            textBufferRef.current += chunk
          },
          onDone: (res) => {
            isStreamActiveRef.current = false
            const reqEndTime = performance.now()
            // Thời gian Client hoàn tất toàn bộ request với Backend
            const clientResponseTimeMs = Math.round(reqEndTime - reqStartTime)

            if (res.reply && res.reply.length > textBufferRef.current.length) {
              textBufferRef.current = res.reply
            }
            const finalFullText = textBufferRef.current || res.reply || ""

            // Đếm số lượng từ / token thực tế xuất hiện trong câu trả lời
            const tokenCount = finalFullText.trim() ? finalFullText.trim().split(/\s+/).length : 0
            const durationSec = Math.max(clientResponseTimeMs / 1000, 0.05)
            // Tốc độ nhả chữ: token (từ) trên giây
            const tokPerSec = Number((tokenCount / durationSec).toFixed(1))

            // Xả hết nội dung còn lại trong buffer lập tức
            stopTypewriter()
            displayedLengthRef.current = finalFullText.length

            setMessages((prev) => {
              const updated = prev.map((m) =>
                m.id === botMsgId
                  ? {
                      ...m,
                      text: finalFullText,
                      tools: res.tools_executed || m.tools,
                      responseTimeMs: clientResponseTimeMs,
                      outputTokens: tokenCount,
                      tokensPerSec: tokPerSec,
                      tokenUsage: res.token_usage,
                      isStreaming: false,
                      statusMessage: undefined,
                    }
                  : m
              )
              syncSessionMessages(updated, textToSend)
              return updated
            })
            if (res.new_access_token) {
              updateAccessToken(res.new_access_token)
            }
          },
          onError: (errMsg) => {
            isStreamActiveRef.current = false
            stopTypewriter()
            setMessages((prev) => {
              const updated = prev.map((m) =>
                m.id === botMsgId
                  ? {
                      ...m,
                      text: m.text ? `${m.text}\n\n⚠️ Lỗi: ${errMsg}` : `⚠️ Lỗi: ${errMsg}`,
                      isStreaming: false,
                      statusMessage: undefined,
                    }
                  : m
              )
              syncSessionMessages(updated, textToSend)
              return updated
            })
            if (
              errMsg.toLowerCase().includes("hết hạn") ||
              errMsg.toLowerCase().includes("expired") ||
              errMsg.includes("401")
            ) {
              setTimeout(() => {
                logout()
              }, 2500)
            }
          },
        },
        updateAccessToken
      )
    } catch (err: any) {
      isStreamActiveRef.current = false
      stopTypewriter()
      const errMsg = err.message || "Không thể nhận phản hồi từ máy chủ"
      setMessages((prev) => {
        const updated = prev.map((m) =>
          m.id === botMsgId
            ? { ...m, text: `⚠️ Lỗi: ${errMsg}`, isStreaming: false, statusMessage: undefined }
            : m
        )
        syncSessionMessages(updated, textToSend)
        return updated
      })
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const hasConversation = messages.length > 0

  const renderComposer = (variant: "welcome" | "bottom") => (
    <form
      onFocusCapture={handleComposerFocusCapture}
      onBlurCapture={handleComposerBlurCapture}
      onSubmit={(e) => {
        e.preventDefault()
        handleSend()
      }}
      className={cn(
        "relative z-30 w-full transition-all duration-300",
        variant === "welcome" ? "max-w-2xl mx-auto" : "max-w-4xl mx-auto",
      )}
    >
      <div
        className={cn(
          "flex items-end gap-2 rounded-2xl border px-4 py-3 transition-all duration-300",
          "bg-white dark:bg-card/90 backdrop-blur-md",
          isChatFocused
            ? "border-[#D4A13B] dark:border-primary/60 ring-2 ring-[#F2C65D]/35 dark:ring-primary/20 shadow-[0_0_30px_-5px_rgba(242,198,93,0.4)] dark:shadow-[0_0_35px_-5px_hsl(var(--primary)/0.25)]"
            : "border-border shadow-md",
        )}
      >
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Nhập câu hỏi tra cứu tài sản (ví dụ: 'Tìm tài sản Màn hình Dell')..."
          disabled={sending}
          aria-label="Nhập câu hỏi tra cứu tài sản"
          className="max-h-40 min-h-[28px] flex-1 resize-none bg-transparent text-sm sm:text-base text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
        />
        <Button
          type="submit"
          size="sm"
          disabled={sending || !input.trim()}
          className="h-9 rounded-xl px-4 font-semibold shrink-0 transition-transform active:scale-95"
        >
          <Send className="h-4 w-4 mr-1.5" />
          <span>Gửi</span>
        </Button>
      </div>
    </form>
  )

  const renderSuggestions = (variant: "welcome" | "bottom") => (
    <div
      className={cn(
        "relative z-30 flex flex-wrap gap-2",
        variant === "welcome"
          ? "justify-center max-w-2xl mx-auto mt-4"
          : "justify-start max-w-4xl mx-auto mb-3 overflow-x-auto pb-1",
      )}
    >
      {SUGGESTIONS.map((s, idx) => (
        <button
          key={idx}
          type="button"
          disabled={sending}
          onClick={() => handleSend(s)}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border border-border bg-[#FAFAFA] dark:bg-secondary/60 px-3.5 py-1.5 text-xs sm:text-sm text-secondary-foreground transition-all",
            "hover:bg-accent hover:border-[#D4A13B]/50 dark:hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50",
          )}
        >
          <Sparkles className="h-3.5 w-3.5 text-[#D4A13B] dark:text-muted-foreground shrink-0" />
          <span>{s}</span>
        </button>
      ))}
    </div>
  )

  return (
    <div className="flex h-screen w-full overflow-hidden bg-white dark:bg-background text-foreground">
      {/* Sidebar History */}
      <aside
        aria-label="Lịch sử trò chuyện"
        className={cn(
          "z-40 flex flex-col border-r border-border bg-[#FAFAFA] dark:bg-card/60 backdrop-blur-sm transition-all duration-300 shrink-0",
          sidebarOpen ? "w-64 sm:w-72" : "w-0 overflow-hidden border-r-0",
        )}
      >
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2 font-semibold text-sm">
            <Bot className="h-5 w-5 text-primary" />
            <span className="truncate">SGOD ChatSystem</span>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(false)}
            className="h-8 w-8"
            title="Thu gọn thanh bên"
          >
            <PanelLeftClose className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-3">
          <Button
            type="button"
            variant="outline"
            onClick={handleNewChat}
            className="w-full justify-start gap-2 rounded-xl border-dashed"
          >
            <Plus className="h-4 w-4" />
            <span>Cuộc trò chuyện mới</span>
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-1 space-y-1">
          <div className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Lịch sử tra cứu
          </div>
          {sessions.length === 0 ? (
            <p className="px-2 py-4 text-xs text-muted-foreground">
              Chưa có lịch sử hội thoại.
            </p>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                role="button"
                tabIndex={0}
                onClick={() => handleSelectSession(session)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault()
                    handleSelectSession(session)
                  }
                }}
                className={cn(
                  "group flex items-center justify-between rounded-lg px-3 py-2 text-xs sm:text-sm cursor-pointer transition-colors",
                  activeSessionId === session.id
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                )}
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{session.title}</span>
                </div>
                <button
                  type="button"
                  onClick={(e) => handleDeleteSession(e, session.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-muted-foreground hover:text-destructive transition-opacity"
                  title="Xóa hội thoại"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))
          )}
        </div>

        <div className="border-t border-border p-3 text-xs text-muted-foreground">
          <div className="font-medium text-foreground truncate">{user?.full_name}</div>
          <div className="truncate">
            {user?.enterprise_name || "SGOD Enterprise"} • {user?.tier}
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="relative flex flex-1 flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="relative z-40 flex items-center justify-between border-b border-border bg-white/95 dark:bg-background/80 backdrop-blur-md px-4 sm:px-6 py-3">
          <div className="flex items-center gap-3 min-w-0">
            {!sidebarOpen && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => setSidebarOpen(true)}
                className="h-8 w-8 shrink-0"
                title="Mở thanh bên"
              >
                <PanelLeftOpen className="h-4 w-4" />
              </Button>
            )}
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Bot className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm sm:text-base truncate">
                    {user?.full_name || "Trợ lý SGOD"}
                  </span>
                  <span className="inline-flex items-center rounded-full bg-primary/15 px-2.5 py-0.5 text-[11px] font-semibold text-primary shrink-0">
                    {user?.role_vi || user?.role}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground truncate">
                  {user?.enterprise_name || "SGOD Enterprise Platform"} • Tier: {user?.tier}
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={toggleTheme}
              aria-label={theme === "dark" ? "Chuyển sang chế độ sáng" : "Chuyển sang chế độ tối"}
              title={theme === "dark" ? "Chuyển sang Light Mode" : "Chuyển sang Dark Mode"}
              className="h-9 w-9 rounded-lg"
            >
              {theme === "dark" ? (
                <Sun className="h-4 w-4 text-amber-400" />
              ) : (
                <Moon className="h-4 w-4 text-slate-700" />
              )}
            </Button>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={logout}
              title="Đăng xuất"
              className="gap-1.5 rounded-lg"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Đăng xuất</span>
            </Button>
          </div>
        </header>

        {/* Body: Welcome Screen with Interactive Lamp OR Active Conversation */}
        {!hasConversation ? (
          <div className="relative flex-1 flex flex-col overflow-y-auto overflow-x-hidden">
            <Hero
              isChatFocused={isChatFocused}
              title={`Xin chào ${user?.full_name || "bạn"}!`}
              subtitle="Tôi là trợ lý AI kết nối trực tiếp với nền tảng quản lý tài sản SGOD. Bạn có thể hỏi tôi bất kỳ thông tin nào về tài sản, lịch bảo trì hoặc vị trí lưu kho."
              className="min-h-full flex-1 rounded-none"
              titleClassName="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight"
              subtitleClassName="text-sm sm:text-base md:text-lg max-w-2xl"
              contentClassName="w-full max-w-4xl mx-auto pt-32 pb-12"
            >
              <div className="w-full mt-2 space-y-4">
                {renderComposer("welcome")}
                {renderSuggestions("welcome")}
              </div>
            </Hero>
          </div>
        ) : (
          <>
            {/* Active Conversation Area (Lamp minimized/hidden for readability) */}
            <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-4 bg-background">
              <div className="max-w-4xl mx-auto space-y-5">
                {messages.map((m) => (
                  <div
                    key={m.id}
                    className={cn(
                      "flex items-start gap-3",
                      m.sender === "user" ? "justify-end" : "justify-start",
                    )}
                  >
                    {m.sender === "assistant" && (
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary mt-0.5">
                        <Bot className="h-4 w-4" />
                      </div>
                    )}

                    <div
                      className={cn(
                        "max-w-[82%] sm:max-w-[75%] rounded-2xl px-4 py-3 shadow-sm",
                        m.sender === "user"
                          ? "bg-primary text-primary-foreground rounded-br-xs"
                          : "bg-card text-card-foreground border border-border rounded-bl-xs",
                      )}
                    >
                      {/* Tool Execution Cards */}
                      {m.tools && m.tools.length > 0 && (
                        <div className="mb-3 flex flex-col gap-2">
                          {m.tools.map((t, idx) => {
                            const toolKey = `${m.id}_tool_${idx}`
                            const isExpanded = !!expandedTools[toolKey]
                            return (
                              <div
                                key={idx}
                                className="rounded-xl border border-border bg-muted/40 dark:bg-secondary/40 text-xs overflow-hidden transition-all shadow-xs"
                              >
                                <div
                                  className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-muted/70 transition-colors select-none"
                                  onClick={() => toggleToolExpand(toolKey)}
                                >
                                  <div className="flex items-center gap-2 min-w-0">
                                    <div className="p-1 rounded-md bg-primary/10 text-primary">
                                      <Wrench className="h-3.5 w-3.5" />
                                    </div>
                                    <span className="font-medium text-foreground truncate">
                                      {t.tool_name}
                                    </span>
                                    {t.is_running ? (
                                      <span className="inline-flex items-center gap-1 text-amber-500 font-medium">
                                        <Clock className="h-3 w-3 animate-spin" />
                                        <span>Đang thực thi...</span>
                                      </span>
                                    ) : t.success ? (
                                      <span className="inline-flex items-center gap-1 text-emerald-500 font-semibold">
                                        <CheckCircle2 className="h-3 w-3" />
                                        <span>Thành công</span>
                                      </span>
                                    ) : (
                                      <span className="inline-flex items-center gap-1 text-rose-500 font-semibold">
                                        <XCircle className="h-3 w-3" />
                                        <span>Thất bại</span>
                                      </span>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-2 shrink-0 text-muted-foreground ml-2">
                                    {typeof t.duration_ms === "number" && (
                                      <span className="inline-flex items-center gap-0.5 rounded-md bg-background px-1.5 py-0.5 text-[10px] font-mono border border-border">
                                        <Zap className="h-2.5 w-2.5 text-amber-500" />
                                        {t.duration_ms}ms
                                      </span>
                                    )}
                                    {isExpanded ? (
                                      <ChevronUp className="h-3.5 w-3.5" />
                                    ) : (
                                      <ChevronDown className="h-3.5 w-3.5" />
                                    )}
                                  </div>
                                </div>

                                {isExpanded && (
                                  <div className="border-t border-border px-3 py-2.5 bg-background/50 space-y-2 text-[11px] font-mono">
                                    <div>
                                      <div className="text-muted-foreground font-semibold mb-1">
                                        Tham số (Arguments):
                                      </div>
                                      <pre className="p-2 rounded-lg bg-muted text-foreground overflow-x-auto max-h-36 whitespace-pre-wrap break-all">
                                        {JSON.stringify(t.arguments, null, 2)}
                                      </pre>
                                    </div>
                                    {t.result !== undefined && t.result !== null && (
                                      <div>
                                        <div className="text-muted-foreground font-semibold mb-1">
                                          Kết quả SGOD (Result):
                                        </div>
                                        <pre className="p-2 rounded-lg bg-muted text-foreground overflow-x-auto max-h-48 whitespace-pre-wrap break-all">
                                          {typeof t.result === "string"
                                            ? t.result
                                            : JSON.stringify(t.result, null, 2)}
                                        </pre>
                                      </div>
                                    )}
                                    {t.error && (
                                      <div className="text-rose-500">
                                        <strong>Lỗi:</strong> {t.error}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      )}

                      {/* Status badge when streaming and no text yet */}
                      {m.isStreaming && m.statusMessage && !m.text && (
                        <div className="flex items-center gap-2 py-1 text-xs text-muted-foreground animate-pulse">
                          <Sparkles className="h-3.5 w-3.5 text-primary" />
                          <span>{m.statusMessage}</span>
                        </div>
                      )}

                      {/* Text content with blinking cursor while streaming */}
                      {m.text && (
                        <div className="text-sm sm:text-base leading-relaxed whitespace-pre-wrap">
                          {m.text}
                          {m.isStreaming && (
                            <span className="inline-block w-1.5 h-4 ml-1 bg-primary animate-pulse align-middle" />
                          )}
                        </div>
                      )}

                      {/* Footer: Response Time, Word Count (Token nhả), Speed (Token/s), Timestamp */}
                      <div className="mt-2.5 pt-1.5 border-t border-border/40 flex flex-wrap items-center justify-between gap-2 text-[10px] text-muted-foreground">
                        <div className="flex flex-wrap items-center gap-2">
                          {typeof m.responseTimeMs === "number" && (
                            <span
                              className="inline-flex items-center gap-1 font-mono font-medium rounded-md bg-muted/60 px-1.5 py-0.5"
                              title="Thời gian từ lúc client gửi request đến khi nhận xong toàn bộ phản hồi"
                            >
                              <Clock className="h-3 w-3 text-amber-500" />
                              {(m.responseTimeMs / 1000).toFixed(2)}s
                            </span>
                          )}
                          {typeof m.outputTokens === "number" && (
                            <span
                              className="inline-flex items-center gap-1 font-mono rounded-md bg-muted/60 px-1.5 py-0.5"
                              title="Số lượng từ được sinh ra trong câu trả lời"
                            >
                              <FileText className="h-3 w-3 text-sky-500" />
                              {m.outputTokens} từ
                            </span>
                          )}
                          {typeof m.tokensPerSec === "number" && (
                            <span
                              className="inline-flex items-center gap-1 font-mono rounded-md bg-muted/60 px-1.5 py-0.5"
                              title="Tốc độ sinh chữ trung bình (từ / giây)"
                            >
                              <Zap className="h-3 w-3 text-emerald-500" />
                              {m.tokensPerSec} từ/s
                            </span>
                          )}
                          {m.tokenUsage && (
                            <span
                              className="inline-flex items-center gap-1 font-mono text-[9px] opacity-70 rounded-md bg-muted/40 px-1 py-0.5"
                              title={`Gemini API Tokens - Prompt: ${m.tokenUsage.prompt_tokens} • Completion: ${m.tokenUsage.completion_tokens}`}
                            >
                              <Cpu className="h-2.5 w-2.5" />
                              {m.tokenUsage.total_tokens} gemini tk
                            </span>
                          )}
                        </div>
                        <span className="opacity-75">{m.timestamp}</span>
                      </div>
                    </div>

                    {m.sender === "user" && (
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground mt-0.5">
                        <UserIcon className="h-4 w-4" />
                      </div>
                    )}
                  </div>
                ))}

                {sending && !messages.some((m) => m.isStreaming) && (
                  <div className="flex items-start gap-3 justify-start">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary mt-0.5">
                      <Bot className="h-4 w-4" />
                    </div>
                    <div className="flex items-center gap-2 rounded-2xl border border-border bg-card px-4 py-3 text-xs sm:text-sm text-muted-foreground">
                      <span className="inline-flex gap-1">
                        <span className="h-2 w-2 rounded-full bg-primary/60 animate-bounce" />
                        <span className="h-2 w-2 rounded-full bg-primary/60 animate-bounce [animation-delay:0.15s]" />
                        <span className="h-2 w-2 rounded-full bg-primary/60 animate-bounce [animation-delay:0.3s]" />
                      </span>
                      <span>Đang xử lý & gọi dữ liệu SGOD...</span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Bottom Composer Bar when conversation is active */}
            <div className="border-t border-border bg-background/90 backdrop-blur-md px-4 sm:px-6 py-3">
              {renderSuggestions("bottom")}
              {renderComposer("bottom")}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
