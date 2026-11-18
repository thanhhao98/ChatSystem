import * as React from "react"
import {
  Sun,
  Moon,
  Plus,
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
  ChevronRight,
  Pin,
  X,
  Clock,
  Zap,
  Cpu,
  FileText,
  Warehouse,
  Package,
  Layers,
  Building2,
  Maximize2,
  Minimize2,
  Copy,
  Check,
  Search,
  CornerDownLeft,
  Send,
} from "lucide-react"
import { useAuth } from "../context/AuthContext"
import { useTheme } from "../context/ThemeContext"
import {
  ChatMessage,
  TokenUsage,
  ToolExecutionRecord,
  getHealthApi,
  sendChatApiStream,
} from "../services/client"
import { Hero } from "@/components/ui/hero"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { AssistantMarkdown } from "./AssistantMarkdown"
import { SidebarConversationItem } from "./SidebarConversationItem"
import {
  matchesConversationSearch,
  usePinnedConversations,
} from "../hooks/useConversationManagement"

export interface MessageAttachmentMeta {
  name: string
  size: number
  type: string
}

export interface MessageItem {
  id: string
  sender: "user" | "assistant"
  text: string
  model?: string
  attachments?: MessageAttachmentMeta[]
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

const SIDEBAR_DEFAULT_WIDTH = 288
const SIDEBAR_MIN_WIDTH = 220
const SIDEBAR_MAX_WIDTH = 480
const SIDEBAR_MAX_VIEWPORT_RATIO = 0.4
const SIDEBAR_WIDTH_STORAGE_KEY = "sgod_sidebar_width"

function getEffectiveMaxSidebarWidth(viewportWidth?: number): number {
  const vw =
    viewportWidth ??
    (typeof window !== "undefined" ? window.innerWidth : 1280)
  const ratioMax = Math.floor(vw * SIDEBAR_MAX_VIEWPORT_RATIO)
  return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, ratioMax))
}

function clampSidebarWidth(width: number, viewportWidth?: number): number {
  const vw =
    viewportWidth ??
    (typeof window !== "undefined" ? window.innerWidth : 1280)
  const ratioMax = Math.floor(vw * SIDEBAR_MAX_VIEWPORT_RATIO)
  const maxAllowed = Math.min(SIDEBAR_MAX_WIDTH, ratioMax)
  const minAllowed = Math.min(SIDEBAR_MIN_WIDTH, maxAllowed)
  return Math.min(Math.max(Math.round(width), minAllowed), maxAllowed)
}

const ENTERPRISE_PROMPTS = [
  {
    title: "Vị trí & Kho bãi",
    desc: "Tra cứu tất cả địa điểm kho, vị trí lưu trữ hiện có",
    prompt: "Có những địa điểm lưu kho nào trong hệ thống?",
    icon: Warehouse,
    badge: "Kho bãi",
  },
  {
    title: "Danh sách Tài sản",
    desc: "Kiểm tra danh mục tài sản, tình trạng và phân bổ",
    prompt: "Cho tôi xem danh sách tài sản của tôi",
    icon: Package,
    badge: "Tài sản",
  },
  {
    title: "Phân loại Danh mục",
    desc: "Xem cấu trúc phân loại thiết bị và nhóm tài sản",
    prompt: "Xem danh mục phân loại tài sản",
    icon: Layers,
    badge: "Danh mục",
  },
  {
    title: "Hồ sơ Doanh nghiệp",
    desc: "Tra cứu thông tin pháp lý, chi nhánh và hồ sơ",
    prompt: "Thông tin hồ sơ doanh nghiệp là gì?",
    icon: Building2,
    badge: "Hồ sơ",
  },
]

export const ChatWidget: React.FC = () => {
  const { user, token, refreshToken, logout, updateAccessToken } = useAuth()
  const { theme, toggleTheme } = useTheme()

  const storageKey = React.useMemo(
    () => `sgod_chat_history_${user?.user_id || "guest"}`,
    [user?.user_id],
  )

  // Desktop Wide View mode
  const [isWideView, setIsWideView] = React.useState<boolean>(false)

  // Copy feedback state
  const [copiedId, setCopiedId] = React.useState<string | null>(null)

  // Search in session history
  const [searchHistory, setSearchHistory] = React.useState<string>("")
  const [debouncedSearch, setDebouncedSearch] = React.useState<string>("")
  const searchInputRef = React.useRef<HTMLInputElement>(null)
  const [isPinnedSectionOpen, setIsPinnedSectionOpen] = React.useState<boolean>(true)

  // Light debounce (80ms) for smooth real-time search on large lists; instant when cleared
  React.useEffect(() => {
    if (!searchHistory.trim()) {
      setDebouncedSearch("")
      return
    }
    const timer = window.setTimeout(() => {
      setDebouncedSearch(searchHistory)
    }, 80)
    return () => window.clearTimeout(timer)
  }, [searchHistory])

  // Keyboard shortcut Cmd+K (macOS) / Ctrl+K (Windows/Linux) to focus conversation search
  React.useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        const activeEl = document.activeElement as HTMLElement | null
        if (activeEl) {
          const tag = activeEl.tagName
          const isEditable =
            tag === "TEXTAREA" ||
            tag === "INPUT" ||
            tag === "SELECT" ||
            activeEl.isContentEditable
          if (isEditable && activeEl !== searchInputRef.current) {
            return
          }
        }
        e.preventDefault()
        setSidebarOpen(true)
        window.requestAnimationFrame(() => {
          searchInputRef.current?.focus()
          searchInputRef.current?.select()
        })
      }
    }
    window.addEventListener("keydown", handleGlobalKeyDown)
    return () => {
      window.removeEventListener("keydown", handleGlobalKeyDown)
    }
  }, [])

  // Active AI model fetched from backend API (/api/health & stream done event)
  const [activeModel, setActiveModel] = React.useState<string>("")

  React.useEffect(() => {
    let mounted = true
    getHealthApi()
      .then((res) => {
        if (mounted && res.gemini_model) {
          setActiveModel(res.gemini_model)
        }
      })
      .catch(() => {
        // Fallback silently if health endpoint is unreachable
      })
    return () => {
      mounted = false
    }
  }, [])

  // Liquid Mercury Blobs Data for Ambient Background
  const blobsData = React.useMemo(() => {
    return Array.from({ length: 5 }).map(() => ({
      size: Math.random() * 260 + 200,
      left: Math.random() * 80 + 10,
      top: Math.random() * 75 + 10,
      animationDelay: Math.random() * -20,
      animationDuration: Math.random() * 18 + 18,
    }))
  }, [])
  const blobRefs = React.useRef<(HTMLDivElement | null)[]>([])

  // Mouse Parallax for Liquid Glass Background
  React.useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)")
    if (mediaQuery.matches) return

    let rafId: number | null = null
    const handleMouseMove = (e: MouseEvent) => {
      if (rafId !== null) return
      rafId = window.requestAnimationFrame(() => {
        const x = e.clientX / window.innerWidth
        const y = e.clientY / window.innerHeight

        blobRefs.current.forEach((blob, index) => {
          if (blob) {
            const speed = (index + 1) * 12
            blob.style.transform = `translate3d(${x * speed}px, ${y * speed}px, 0)`
          }
        })
        rafId = null
      })
    }

    document.addEventListener("mousemove", handleMouseMove, { passive: true })
    return () => {
      document.removeEventListener("mousemove", handleMouseMove)
      if (rafId !== null) window.cancelAnimationFrame(rafId)
    }
  }, [])

  // Interactive Lamp focus state (for Welcome Screen)
  const [isChatFocused, setIsChatFocused] = React.useState(false)

  // Sidebar & Chat History state
  const [sidebarOpen, setSidebarOpen] = React.useState<boolean>(true)
  const [viewportWidth, setViewportWidth] = React.useState<number>(() =>
    typeof window !== "undefined" ? window.innerWidth : 1280,
  )
  const [sidebarWidth, setSidebarWidth] = React.useState<number>(() => {
    try {
      const saved = localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY)
      if (saved !== null) {
        const parsed = Number(saved)
        if (Number.isFinite(parsed) && parsed > 0) {
          return clampSidebarWidth(parsed)
        }
      }
    } catch {
      // Ignore storage access errors
    }
    return clampSidebarWidth(SIDEBAR_DEFAULT_WIDTH)
  })
  const [isResizingSidebar, setIsResizingSidebar] = React.useState<boolean>(false)
  const resizeCleanupRef = React.useRef<(() => void) | null>(null)

  // Persist clamped sidebar width to localStorage
  React.useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(sidebarWidth))
    } catch {
      // Ignore storage quota errors
    }
  }, [sidebarWidth])

  // Re-clamp sidebar width when viewport size changes
  React.useEffect(() => {
    const handleViewportResize = () => {
      const vw = window.innerWidth
      setViewportWidth(vw)
      setSidebarWidth((prev) => clampSidebarWidth(prev, vw))
    }
    window.addEventListener("resize", handleViewportResize, { passive: true })
    return () => {
      window.removeEventListener("resize", handleViewportResize)
    }
  }, [])

  // Cleanup active drag listeners & body styles on unmount
  React.useEffect(() => {
    return () => {
      if (resizeCleanupRef.current) {
        resizeCleanupRef.current()
        resizeCleanupRef.current = null
      }
    }
  }, [])

  const handleStartResizeSidebar = React.useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (e.button !== 0) return
      e.preventDefault()
      e.stopPropagation()

      if (resizeCleanupRef.current) {
        resizeCleanupRef.current()
      }

      setIsResizingSidebar(true)
      const prevCursor = document.body.style.cursor
      const prevUserSelect = document.body.style.userSelect
      document.body.style.cursor = "col-resize"
      document.body.style.userSelect = "none"

      const handlePointerMove = (moveEvent: PointerEvent) => {
        const nextWidth = clampSidebarWidth(moveEvent.clientX, window.innerWidth)
        setSidebarWidth(nextWidth)
      }

      const cleanup = () => {
        window.removeEventListener("pointermove", handlePointerMove)
        window.removeEventListener("pointerup", handlePointerUp)
        window.removeEventListener("pointercancel", handlePointerUp)
        document.body.style.cursor = prevCursor
        document.body.style.userSelect = prevUserSelect
        setIsResizingSidebar(false)
        resizeCleanupRef.current = null
      }

      const handlePointerUp = () => {
        cleanup()
      }

      resizeCleanupRef.current = cleanup
      window.addEventListener("pointermove", handlePointerMove)
      window.addEventListener("pointerup", handlePointerUp)
      window.addEventListener("pointercancel", handlePointerUp)
    },
    [],
  )

  const handleSidebarResizerKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      const step = 16
      if (e.key === "ArrowRight") {
        e.preventDefault()
        setSidebarWidth((prev) => clampSidebarWidth(prev + step, window.innerWidth))
      } else if (e.key === "ArrowLeft") {
        e.preventDefault()
        setSidebarWidth((prev) => clampSidebarWidth(prev - step, window.innerWidth))
      } else if (e.key === "Home") {
        e.preventDefault()
        setSidebarWidth(clampSidebarWidth(SIDEBAR_MIN_WIDTH, window.innerWidth))
      } else if (e.key === "End") {
        e.preventDefault()
        setSidebarWidth(clampSidebarWidth(SIDEBAR_MAX_WIDTH, window.innerWidth))
      }
    },
    [],
  )

  const normalizeSessions = React.useCallback((rawList: unknown): ChatSession[] => {
    if (!Array.isArray(rawList)) return []
    return rawList
      .filter((item): item is ChatSession => Boolean(item && typeof item === "object" && "id" in item))
      .map((s) => {
        const validMessages = Array.isArray(s.messages) ? s.messages : []
        const firstUserText = validMessages
          .find((m) => m.sender === "user" && m.text)
          ?.text?.replace(/\s+/g, " ")
          .trim()
        const isLegacySlicedTitle =
          Boolean(s.title && s.title.length === 48 && firstUserText && firstUserText.length > 48 && firstUserText.startsWith(s.title))
        const resolvedTitle =
          !s.title || isLegacySlicedTitle
            ? firstUserText || s.title
            : s.title
        if (validMessages.length === 0 && resolvedTitle) {
          const fallbackTime =
            s.updatedAt || new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
          return {
            ...s,
            title: resolvedTitle,
            messages: [
              {
                id: `user_${s.id}`,
                sender: "user" as const,
                text: resolvedTitle,
                timestamp: fallbackTime,
              },
            ],
          }
        }
        return {
          ...s,
          title: resolvedTitle || "Cuộc trò chuyện mới",
          messages: validMessages,
        }
      })
  }, [])

  const [sessions, setSessions] = React.useState<ChatSession[]>(() => {
    try {
      const raw = localStorage.getItem(`sgod_chat_history_${user?.user_id || "guest"}`)
      return raw ? normalizeSessions(JSON.parse(raw)) : []
    } catch {
      return []
    }
  })
  const [activeSessionId, setActiveSessionId] = React.useState<string | null>(null)
  const activeSessionIdRef = React.useRef<string | null>(null)
  React.useEffect(() => {
    activeSessionIdRef.current = activeSessionId
  }, [activeSessionId])

  const [messages, setMessages] = React.useState<MessageItem[]>([])
  const [input, setInput] = React.useState("")
  const [sending, setSending] = React.useState(false)
  const [expandedTools, setExpandedTools] = React.useState<Record<string, boolean>>({})
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  const toggleToolExpand = (key: string) => {
    setExpandedTools((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const handleCopyMessage = (text: string, id: string) => {
    if (!text) return
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => {
      setCopiedId((prev) => (prev === id ? null : prev))
    }, 2000)
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

  // Load sessions when user changes
  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey)
      const parsed = raw ? normalizeSessions(JSON.parse(raw)) : []
      setSessions(parsed)
      localStorage.setItem(storageKey, JSON.stringify(parsed))
    } catch {
      setSessions([])
    }
  }, [storageKey, normalizeSessions])

  // If a session is currently active but messages state is empty (e.g. after HMR or repaired session), sync its messages
  React.useEffect(() => {
    if (!activeSessionId || messages.length > 0) return
    const current = sessions.find((s) => s.id === activeSessionId)
    if (current && current.messages && current.messages.length > 0) {
      setMessages(current.messages)
    }
  }, [activeSessionId, messages.length, sessions])

  // Persist sessions to localStorage
  const saveSessions = React.useCallback(
    (updated: ChatSession[]) => {
      const normalized = normalizeSessions(updated)
      setSessions(normalized)
      try {
        localStorage.setItem(storageKey, JSON.stringify(normalized))
      } catch {
        // Ignore quota errors
      }
    },
    [storageKey, normalizeSessions],
  )

  const upsertSession = React.useCallback(
    (sessionId: string, nextMessages: MessageItem[], titleFallback?: string) => {
      const nowStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      const cleanFallback = (titleFallback || nextMessages[0]?.text || "Cuộc trò chuyện mới")
        .replace(/\s+/g, " ")
        .trim()
      setSessions((prevSessions) => {
        const existingSession = prevSessions.find((s) => s.id === sessionId)
        let updated: ChatSession[]
        if (existingSession) {
          const updatedSession: ChatSession = {
            ...existingSession,
            title: existingSession.title || cleanFallback,
            messages: nextMessages,
            updatedAt: nowStr,
          }
          updated = [
            updatedSession,
            ...prevSessions.filter((s) => s.id !== sessionId),
          ]
        } else {
          const newSession: ChatSession = {
            id: sessionId,
            title: cleanFallback,
            messages: nextMessages,
            updatedAt: nowStr,
          }
          updated = [newSession, ...prevSessions]
        }
        try {
          localStorage.setItem(storageKey, JSON.stringify(updated))
        } catch {
          // Ignore quota errors
        }
        return updated
      })
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

  // Focus management on composer container
  const handleComposerFocusCapture = () => {
    setIsChatFocused(true)
  }

  const handleComposerBlurCapture = (e: React.FocusEvent<HTMLFormElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
      setIsChatFocused(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleNewChat = () => {
    stopTypewriter()
    activeSessionIdRef.current = null
    setActiveSessionId(null)
    setMessages([])
  }

  const handleSelectSession = (session: ChatSession) => {
    stopTypewriter()
    const latestSession = sessions.find((s) => s.id === session.id) || session
    const sessionMessages =
      Array.isArray(latestSession.messages) && latestSession.messages.length > 0
        ? latestSession.messages
        : [
            {
              id: `user_${latestSession.id}`,
              sender: "user" as const,
              text: latestSession.title || "Cuộc trò chuyện",
              timestamp:
                latestSession.updatedAt ||
                new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            },
          ]
    activeSessionIdRef.current = latestSession.id
    setActiveSessionId(latestSession.id)
    setMessages(sessionMessages)
  }

  const validSessionIds = React.useMemo(() => sessions.map((s) => s.id), [sessions])
  const { pinnedSet, togglePin, unpinConversation } = usePinnedConversations({
    userId: user?.user_id,
    enterpriseName: user?.enterprise_name,
    tier: user?.tier,
    validSessionIds,
  })

  const handleRenameSession = React.useCallback(
    (sessionId: string, newTitle: string) => {
      const cleanTitle = newTitle.replace(/\s+/g, " ").trim()
      if (!cleanTitle) return
      setSessions((prevSessions) => {
        const updated = prevSessions.map((s) =>
          s.id === sessionId ? { ...s, title: cleanTitle } : s,
        )
        try {
          localStorage.setItem(storageKey, JSON.stringify(updated))
        } catch {
          // Ignore quota errors
        }
        return updated
      })
    },
    [storageKey],
  )

  const handleDeleteSession = React.useCallback(
    (e: React.MouseEvent, sessionId: string) => {
      e.stopPropagation()
      unpinConversation(sessionId)
      const filtered = sessions.filter((s) => s.id !== sessionId)
      saveSessions(filtered)
      if (activeSessionId === sessionId) {
        stopTypewriter()
        activeSessionIdRef.current = null
        setActiveSessionId(null)
        setMessages([])
      }
    },
    [sessions, saveSessions, activeSessionId, unpinConversation],
  )

  const handleSend = async (overrideText?: string) => {
    const textToSend = (overrideText ?? input).trim()
    if (!textToSend || sending) return

    if (!token) {
      alert("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
      logout()
      return
    }

    const now = new Date()
    const timeStr = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })

    const targetSessionId = activeSessionIdRef.current || `session_${Date.now()}`
    if (!activeSessionIdRef.current) {
      activeSessionIdRef.current = targetSessionId
      setActiveSessionId(targetSessionId)
    }

    const userMsg: MessageItem = {
      id: `user_${Date.now()}`,
      sender: "user",
      text: textToSend,
      timestamp: timeStr,
    }

    const botMsgId = `assistant_${Date.now() + 1}`
    const botMsg: MessageItem = {
      id: botMsgId,
      sender: "assistant",
      text: "",
      timestamp: timeStr,
      isStreaming: true,
      statusMessage: "Đang kết nối trí tuệ nhân tạo Gemini...",
    }

    let turnMessages: MessageItem[] = [...messages, userMsg, botMsg]
    setMessages(turnMessages)
    upsertSession(targetSessionId, turnMessages, textToSend)
    setInput("")
    setSending(true)

    textBufferRef.current = ""
    displayedLengthRef.current = 0
    isStreamActiveRef.current = true
    startTypewriter(botMsgId)

    const historyPayload: ChatMessage[] = messages.map((m) => ({
      role: m.sender,
      content: m.text,
    }))

    const reqStartTime = performance.now()

    try {
      await sendChatApiStream(
        textToSend,
        token,
        historyPayload,
        refreshToken || undefined,
        {
          onStatus: (statusText) => {
            turnMessages = turnMessages.map((m) =>
              m.id === botMsgId ? { ...m, statusMessage: statusText } : m,
            )
            if (activeSessionIdRef.current === targetSessionId) {
              setMessages(turnMessages)
            }
          },
          onToolStart: (toolName, args) => {
            turnMessages = turnMessages.map((m) => {
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
            upsertSession(targetSessionId, turnMessages, textToSend)
            if (activeSessionIdRef.current === targetSessionId) {
              setMessages(turnMessages)
            }
          },
          onToolResult: (record) => {
            turnMessages = turnMessages.map((m) => {
              if (m.id !== botMsgId) return m
              const existing = m.tools || []
              const updated = existing.map((t) =>
                t.tool_name === record.tool_name && t.is_running
                  ? { ...record, is_running: false }
                  : t,
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
            upsertSession(targetSessionId, turnMessages, textToSend)
            if (activeSessionIdRef.current === targetSessionId) {
              setMessages(turnMessages)
            }
          },
          onDelta: (chunk) => {
            textBufferRef.current += chunk
          },
          onDone: (res) => {
            isStreamActiveRef.current = false
            const reqEndTime = performance.now()
            const clientResponseTimeMs = Math.round(reqEndTime - reqStartTime)

            if (res.reply && res.reply.length > textBufferRef.current.length) {
              textBufferRef.current = res.reply
            }
            const finalFullText = textBufferRef.current || res.reply || ""

            const tokenCount = finalFullText.trim() ? finalFullText.trim().split(/\s+/).length : 0
            const durationSec = Math.max(clientResponseTimeMs / 1000, 0.05)
            const tokPerSec = Number((tokenCount / durationSec).toFixed(1))

            stopTypewriter()
            displayedLengthRef.current = finalFullText.length

            if (res.model) {
              setActiveModel(res.model)
            }

            turnMessages = turnMessages.map((m) =>
              m.id === botMsgId
                ? {
                    ...m,
                    text: finalFullText,
                    model: res.model || activeModel || m.model,
                    tools: res.tools_executed || m.tools,
                    responseTimeMs: clientResponseTimeMs,
                    outputTokens: tokenCount,
                    tokensPerSec: tokPerSec,
                    tokenUsage: res.token_usage,
                    isStreaming: false,
                    statusMessage: undefined,
                  }
                : m,
            )
            upsertSession(targetSessionId, turnMessages, textToSend)
            if (activeSessionIdRef.current === targetSessionId) {
              setMessages(turnMessages)
            }
            if (res.new_access_token) {
              updateAccessToken(res.new_access_token)
            }
          },
          onError: (errMsg) => {
            isStreamActiveRef.current = false
            stopTypewriter()
            turnMessages = turnMessages.map((m) =>
              m.id === botMsgId
                ? {
                    ...m,
                    text: m.text ? `${m.text}\n\n⚠️ Lỗi: ${errMsg}` : `⚠️ Lỗi: ${errMsg}`,
                    isStreaming: false,
                    statusMessage: undefined,
                  }
                : m,
            )
            upsertSession(targetSessionId, turnMessages, textToSend)
            if (activeSessionIdRef.current === targetSessionId) {
              setMessages(turnMessages)
            }
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
        updateAccessToken,
      )
    } catch (err: any) {
      isStreamActiveRef.current = false
      stopTypewriter()
      const errMsg = err.message || "Không thể nhận phản hồi từ máy chủ"
      turnMessages = turnMessages.map((m) =>
        m.id === botMsgId
          ? { ...m, text: `⚠️ Lỗi: ${errMsg}`, isStreaming: false, statusMessage: undefined }
          : m,
      )
      upsertSession(targetSessionId, turnMessages, textToSend)
      if (activeSessionIdRef.current === targetSessionId) {
        setMessages(turnMessages)
      }
    } finally {
      setSending(false)
    }
  }

  const hasConversation = messages.length > 0

  const isSearching = debouncedSearch.trim().length > 0

  const { matchedSessions, pinnedSessions, regularSessions } = React.useMemo(() => {
    const matched = sessions.filter((s) =>
      matchesConversationSearch(s.title, debouncedSearch),
    )
    const pinned: ChatSession[] = []
    const regular: ChatSession[] = []
    for (const s of matched) {
      if (pinnedSet.has(s.id)) {
        pinned.push(s)
      } else {
        regular.push(s)
      }
    }
    return {
      matchedSessions: matched,
      pinnedSessions: pinned,
      regularSessions: regular,
    }
  }, [sessions, debouncedSearch, pinnedSet])

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
        variant === "welcome"
          ? "max-w-3xl mx-auto"
          : isWideView
          ? "max-w-6xl mx-auto"
          : "max-w-4xl mx-auto",
      )}
    >
      <div
        className={cn(
          "flex items-end gap-2 rounded-2xl px-4 py-3 transition-all duration-300 liquid-glass-composer",
          isChatFocused ? "liquid-glass-composer-focused" : "",
        )}
      >
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Nhập câu hỏi tra cứu tài sản hoặc vị trí kho (ví dụ: 'Tìm danh sách máy in tại kho A')..."
          disabled={sending}
          aria-label="Nhập câu hỏi tra cứu tài sản"
          className="max-h-40 min-h-[28px] flex-1 resize-none bg-transparent text-sm sm:text-base text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
        />
        <Button
          type="submit"
          size="sm"
          disabled={sending || !input.trim()}
          className="h-9 rounded-xl px-4 font-semibold shrink-0 transition-transform active:scale-95 bg-[#f2c65d] hover:bg-[#e0b54d] text-zinc-950 font-bold shadow-md hover:shadow-amber-500/25"
        >
          <Send className="h-4 w-4 mr-1.5" />
          <span>Gửi</span>
        </Button>
      </div>

      <div className="hidden sm:flex items-center justify-between mt-2 px-2 text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1 opacity-75">
          <CornerDownLeft className="h-3 w-3" />
          <span>Nhấn <strong>Enter</strong> để gửi • <strong>Shift + Enter</strong> để xuống dòng</span>
        </span>
        {activeModel && (
          <span className="opacity-70 font-mono">{activeModel}</span>
        )}
      </div>
    </form>
  )

  const renderWelcomeFeatureCards = () => (
    <div className="w-full max-w-4xl mx-auto mt-6">
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5 text-amber-500" />
          <span>Tác vụ thường dùng (Desktop Enterprise Quickstart)</span>
        </div>
        <span className="text-[11px] text-muted-foreground">Chọn để tra cứu tức thì</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {ENTERPRISE_PROMPTS.map((item, idx) => {
          const IconComp = item.icon
          return (
            <button
              key={idx}
              type="button"
              disabled={sending}
              onClick={() => handleSend(item.prompt)}
              className="group flex flex-col text-left p-4 rounded-xl cursor-pointer text-foreground disabled:opacity-50 liquid-glass-card"
            >
              <div className="flex items-center justify-between w-full mb-3">
                <div className="p-2 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 group-hover:scale-110 transition-transform">
                  <IconComp className="h-4 w-4" />
                </div>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-muted border border-border text-foreground group-hover:border-amber-500/40 group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
                  {item.badge}
                </span>
              </div>
              <div className="font-semibold text-xs sm:text-sm text-foreground mb-1 group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
                {item.title}
              </div>
              <p className="text-[11px] leading-relaxed text-muted-foreground line-clamp-2">
                {item.desc}
              </p>
            </button>
          )
        })}
      </div>
    </div>
  )

  const renderBottomSuggestions = () => (
    <div
      className={cn(
        "relative z-30 flex items-center gap-2 mb-2.5 overflow-x-auto pb-1 mx-auto transition-all duration-300",
        isWideView ? "max-w-6xl" : "max-w-4xl",
      )}
    >
      <span className="text-[11px] text-muted-foreground shrink-0 flex items-center gap-1 font-medium mr-1">
        <Sparkles className="h-3 w-3 text-amber-500" />
        <span>Gợi ý:</span>
      </span>
      {ENTERPRISE_PROMPTS.map((item, idx) => (
        <button
          key={idx}
          type="button"
          disabled={sending}
          onClick={() => handleSend(item.prompt)}
          className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs transition-all shrink-0 border border-border bg-card/60 hover:bg-accent hover:border-amber-500/40 text-foreground backdrop-blur-md disabled:opacity-50"
        >
          <span>{item.title}</span>
        </button>
      ))}
    </div>
  )

  return (
    <div className="chat-liquid-root relative flex h-screen w-full overflow-hidden text-foreground font-sans">
      <style>{`
        /* Liquid Glass Design System Styles - Dual Theme */
        html.dark .chat-liquid-root,
        :root:not(.light) .chat-liquid-root {
          --chat-bg: #07070a;
          --chat-vignette: radial-gradient(circle at 50% 35%, rgba(7, 7, 10, 0.15) 0%, rgba(7, 7, 10, 0.75) 100%);
          --chat-blob-grad: linear-gradient(135deg, #e0e0e0, #71717a);
          --chat-blob-opacity: 0.22;
          --sidebar-bg: rgba(12, 12, 17, 0.75);
          --sidebar-border: rgba(255, 255, 255, 0.08);
          --header-bg: rgba(10, 10, 15, 0.78);
          --header-border: rgba(255, 255, 255, 0.08);
          --assistant-bg: rgba(18, 18, 24, 0.86);
          --assistant-border: rgba(255, 255, 255, 0.11);
          --assistant-text: #f4f4f5;
          --user-bg: linear-gradient(135deg, rgba(212, 161, 59, 0.35), rgba(180, 130, 30, 0.5));
          --user-border: rgba(242, 198, 93, 0.45);
          --user-text: #fffbeb;
          --composer-bg: rgba(16, 16, 22, 0.84);
          --composer-border: rgba(255, 255, 255, 0.13);
          --card-bg: rgba(18, 18, 24, 0.68);
          --card-border: rgba(255, 255, 255, 0.09);
          --tool-bg: rgba(10, 10, 14, 0.65);
          --tool-border: rgba(255, 255, 255, 0.09);
          background-color: var(--chat-bg);
          color: #f4f4f5;
        }

        html.light .chat-liquid-root {
          --chat-bg: #f4f6f9;
          --chat-vignette: radial-gradient(circle at 50% 35%, rgba(255, 255, 255, 0.1) 0%, rgba(240, 243, 248, 0.75) 100%);
          --chat-blob-grad: linear-gradient(135deg, #f2c65d, #d1d5db);
          --chat-blob-opacity: 0.20;
          --sidebar-bg: rgba(255, 255, 255, 0.88);
          --sidebar-border: rgba(0, 0, 0, 0.08);
          --header-bg: rgba(255, 255, 255, 0.90);
          --header-border: rgba(0, 0, 0, 0.08);
          --assistant-bg: rgba(255, 255, 255, 0.95);
          --assistant-border: rgba(0, 0, 0, 0.09);
          --assistant-text: #09090b;
          --user-bg: linear-gradient(135deg, rgba(255, 251, 235, 0.96), rgba(254, 243, 199, 0.88));
          --user-border: rgba(245, 158, 11, 0.35);
          --user-text: #18181b;
          --composer-bg: rgba(255, 255, 255, 0.94);
          --composer-border: rgba(0, 0, 0, 0.12);
          --card-bg: rgba(255, 255, 255, 0.84);
          --card-border: rgba(0, 0, 0, 0.08);
          --tool-bg: rgba(244, 244, 246, 0.92);
          --tool-border: rgba(0, 0, 0, 0.08);
          background-color: var(--chat-bg);
          color: #0f172a;
        }

        .chat-liquid-stage {
          position: fixed;
          inset: 0;
          width: 100%;
          height: 100%;
          z-index: 0;
          pointer-events: none;
          overflow: hidden;
          opacity: var(--chat-blob-opacity);
          filter: url('#chat-gooey');
        }

        .chat-liquid-blob {
          position: absolute;
          background: var(--chat-blob-grad);
          border-radius: 50%;
          filter: blur(35px);
          animation: chat-blob-float 24s infinite alternate ease-in-out;
          box-shadow:
            inset -10px -10px 20px rgba(0, 0, 0, 0.3),
            10px 10px 30px rgba(255, 255, 255, 0.2);
          transition: transform 0.15s ease-out;
          pointer-events: none;
          will-change: transform;
        }

        @keyframes chat-blob-float {
          0% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(8vw, 12vh) scale(1.15); }
          66% { transform: translate(-6vw, 6vh) scale(0.9); }
          100% { transform: translate(5vw, -8vh) scale(1.1); }
        }

        .chat-ambient-vignette {
          position: fixed;
          inset: 0;
          pointer-events: none;
          z-index: 1;
          background: var(--chat-vignette);
        }

        /* Liquid Glass Sidebar */
        .liquid-glass-sidebar {
          background: var(--sidebar-bg) !important;
          backdrop-filter: blur(28px) saturate(170%);
          -webkit-backdrop-filter: blur(28px) saturate(170%);
          border-right: 1px solid var(--sidebar-border) !important;
          box-shadow: 10px 0 30px -10px rgba(0, 0, 0, 0.15);
        }

        /* Liquid Glass Header */
        .liquid-glass-header {
          background: var(--header-bg) !important;
          backdrop-filter: blur(28px) saturate(170%);
          -webkit-backdrop-filter: blur(28px) saturate(170%);
          border-bottom: 1px solid var(--header-border) !important;
          box-shadow: 0 8px 24px -6px rgba(0, 0, 0, 0.08);
        }

        /* Liquid Glass Quickstart Cards */
        .liquid-glass-card {
          background: var(--card-bg);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid var(--card-border);
          border-radius: 14px;
          box-shadow: inset 0 1px 1px 0 rgba(255, 255, 255, 0.1), 0 12px 28px -8px rgba(0, 0, 0, 0.1);
          transition: transform 0.25s, border-color 0.25s, background 0.25s, box-shadow 0.25s;
        }

        .liquid-glass-card:hover {
          border-color: rgba(242, 198, 93, 0.5);
          transform: translateY(-2px);
          box-shadow: inset 0 1px 1px 0 rgba(255, 255, 255, 0.2), 0 16px 36px -8px rgba(242, 198, 93, 0.2);
        }

        /* Liquid Glass Composer (Input) */
        .liquid-glass-composer {
          background: var(--composer-bg);
          backdrop-filter: blur(24px) saturate(180%);
          -webkit-backdrop-filter: blur(24px) saturate(180%);
          border: 1px solid var(--composer-border);
          box-shadow: inset 0 1px 1px 0 rgba(255, 255, 255, 0.1), 0 16px 40px -10px rgba(0, 0, 0, 0.15);
        }

        .liquid-glass-composer-focused {
          border-color: rgba(242, 198, 93, 0.65) !important;
          box-shadow:
            inset 0 1px 1px 0 rgba(255, 255, 255, 0.2),
            0 0 35px -5px rgba(242, 198, 93, 0.4),
            0 20px 50px -10px rgba(0, 0, 0, 0.2) !important;
        }

        /* High Legibility Liquid Glass Assistant Message */
        .liquid-glass-assistant {
          background: var(--assistant-bg);
          backdrop-filter: blur(24px) saturate(160%);
          -webkit-backdrop-filter: blur(24px) saturate(160%);
          border: 1px solid var(--assistant-border);
          box-shadow:
            inset 0 1px 0 0 rgba(255, 255, 255, 0.12),
            0 16px 36px -12px rgba(0, 0, 0, 0.15);
          color: var(--assistant-text);
        }

        /* Liquid Glass User Message */
        .liquid-glass-user {
          background: var(--user-bg);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid var(--user-border);
          box-shadow:
            inset 0 1px 1px 0 rgba(255, 255, 255, 0.25),
            0 10px 28px -6px rgba(0, 0, 0, 0.15);
          color: var(--user-text);
        }

        /* Tool cards within chat: crisp glass */
        .liquid-glass-tool {
          background: var(--tool-bg);
          border: 1px solid var(--tool-border);
          backdrop-filter: blur(12px);
        }

        @media (prefers-reduced-motion: reduce) {
          .chat-liquid-blob {
            animation: none;
            transition: none;
          }
          .liquid-glass-card {
            transition: none;
          }
        }
      `}</style>

      {/* SVG Gooey Filter for Liquid Mercury */}
      <svg className="absolute w-0 h-0 pointer-events-none" aria-hidden="true">
        <defs>
          <filter id="chat-gooey">
            <feGaussianBlur in="SourceGraphic" stdDeviation="14" result="blur" />
            <feColorMatrix
              in="blur"
              mode="matrix"
              values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 19 -9"
              result="goo"
            />
            <feComposite in="SourceGraphic" in2="goo" operator="atop" />
          </filter>
        </defs>
      </svg>

      {/* Ambient Liquid Stage behind all workspace elements */}
      <div className="chat-liquid-stage" aria-hidden="true">
        {blobsData.map((data, index) => (
          <div
            key={index}
            ref={(el) => {
              blobRefs.current[index] = el
            }}
            className="chat-liquid-blob"
            style={{
              width: `${data.size}px`,
              height: `${data.size}px`,
              left: `${data.left}%`,
              top: `${data.top}%`,
              animationDelay: `${data.animationDelay}s`,
              animationDuration: `${data.animationDuration}s`,
            }}
          />
        ))}
      </div>

      {/* Ambient Vignette Overlay for Crisp Contrast */}
      <div className="chat-ambient-vignette" aria-hidden="true" />

      {/* Sidebar History (Liquid Glass - Resizable) */}
      <aside
        aria-label="Lịch sử trò chuyện"
        style={{
          width: sidebarOpen ? `${sidebarWidth}px` : "0px",
        }}
        className={cn(
          "relative z-40 flex flex-col shrink-0 liquid-glass-sidebar",
          isResizingSidebar ? "transition-none select-none" : "transition-[width] duration-300 ease-out",
          !sidebarOpen && "w-0 overflow-hidden border-r-0",
        )}
      >
        <div className="flex items-center justify-between gap-2 p-4 border-b border-border/60 min-w-0">
          <div className="flex items-center gap-2 font-semibold text-sm min-w-0 flex-1">
            <div className="p-1.5 rounded-lg bg-amber-500/15 text-amber-500 border border-amber-500/20 shrink-0">
              <Bot className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <span className="truncate block font-bold text-sm tracking-tight text-foreground">SGOD Asset AI</span>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(false)}
            className="h-8 w-8 shrink-0 text-muted-foreground hover:text-foreground hover:bg-accent"
            title="Thu gọn thanh bên"
          >
            <PanelLeftClose className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-3 space-y-2 min-w-0">
          <Button
            type="button"
            variant="outline"
            onClick={handleNewChat}
            className="w-full min-w-0 justify-start gap-2 rounded-xl border-dashed border-border bg-card/60 hover:bg-accent hover:border-amber-500/60 text-foreground"
          >
            <Plus className="h-4 w-4 shrink-0 text-amber-500" />
            <span className="font-semibold text-xs sm:text-sm min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-left">
              Cuộc trò chuyện mới
            </span>
          </Button>

          {/* Search Input (Always visible) */}
          <div className="relative min-w-0">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Tìm kiếm cuộc trò chuyện..."
              aria-label="Tìm kiếm cuộc trò chuyện"
              value={searchHistory}
              onChange={(e) => setSearchHistory(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape" && searchHistory) {
                  e.preventDefault()
                  setSearchHistory("")
                }
              }}
              className="w-full pl-8 pr-8 py-1.5 text-xs rounded-lg border border-border/80 bg-card/60 hover:border-amber-500/30 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/20 transition-colors"
            />
            {searchHistory ? (
              <button
                type="button"
                onClick={() => {
                  setSearchHistory("")
                  searchInputRef.current?.focus()
                }}
                title="Xóa từ khóa tìm kiếm"
                aria-label="Xóa từ khóa tìm kiếm"
                className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            ) : (
              <kbd className="hidden sm:inline-flex items-center gap-0.5 absolute right-2 top-1/2 -translate-y-1/2 px-1 py-0.5 text-[9px] font-mono text-muted-foreground/70 bg-muted/60 border border-border/60 rounded pointer-events-none">
                ⌘K
              </kbd>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-1 space-y-3 min-w-0">
          {sessions.length === 0 ? (
            <p className="px-2 py-6 text-xs text-muted-foreground text-center">
              Chưa có lịch sử hội thoại.
            </p>
          ) : matchedSessions.length === 0 ? (
            <div className="px-2 py-6 text-center space-y-2.5">
              <p className="text-xs text-muted-foreground">
                Không tìm thấy cuộc trò chuyện phù hợp.
              </p>
              <button
                type="button"
                onClick={() => {
                  setSearchHistory("")
                  searchInputRef.current?.focus()
                }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 px-2.5 py-1 text-[11px] font-medium text-amber-600 dark:text-amber-400 transition-colors"
              >
                <X className="h-3 w-3" />
                <span>Xóa từ khóa</span>
              </button>
            </div>
          ) : (
            <>
              {/* Pinned Conversations Section (ĐÃ GHIM) */}
              {pinnedSessions.length > 0 && (
                <div className="space-y-1 min-w-0">
                  <button
                    type="button"
                    onClick={() => setIsPinnedSectionOpen((prev) => !prev)}
                    className="w-full flex items-center justify-between gap-2 px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400 hover:text-amber-500 transition-colors min-w-0"
                  >
                    <span className="flex items-center gap-1.5 min-w-0 truncate">
                      {isPinnedSectionOpen || isSearching ? (
                        <ChevronDown className="h-3 w-3 shrink-0" />
                      ) : (
                        <ChevronRight className="h-3 w-3 shrink-0" />
                      )}
                      <Pin className="h-3 w-3 shrink-0 fill-amber-500/25 rotate-45" />
                      <span className="truncate">Đã ghim</span>
                    </span>
                    <span className="font-mono text-[10px] px-1.5 py-0.2 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-600 dark:text-amber-400 shrink-0">
                      {pinnedSessions.length}
                    </span>
                  </button>

                  {(isPinnedSectionOpen || isSearching) && (
                    <div className="space-y-0.5 min-w-0">
                      {pinnedSessions.map((session) => (
                        <SidebarConversationItem
                          key={session.id}
                          session={session}
                          isActive={activeSessionId === session.id}
                          isPinned={true}
                          onSelect={handleSelectSession}
                          onTogglePin={togglePin}
                          onRename={handleRenameSession}
                          onDelete={handleDeleteSession}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Regular Conversations Section (LỊCH SỬ TRA CỨU) */}
              {regularSessions.length > 0 && (
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground min-w-0">
                    <span className="truncate">Lịch sử tra cứu</span>
                    <span className="font-mono text-[10px] text-amber-500/80 shrink-0">
                      {regularSessions.length}
                    </span>
                  </div>

                  <div className="space-y-0.5 min-w-0">
                    {regularSessions.map((session) => (
                      <SidebarConversationItem
                        key={session.id}
                        session={session}
                        isActive={activeSessionId === session.id}
                        isPinned={false}
                        onSelect={handleSelectSession}
                        onTogglePin={togglePin}
                        onRename={handleRenameSession}
                        onDelete={handleDeleteSession}
                      />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className="border-t border-border/60 p-3 text-xs text-muted-foreground bg-card/20 min-w-0">
          <div className="font-semibold text-foreground truncate">{user?.full_name}</div>
          <div className="truncate text-[11px] text-muted-foreground">
            {[user?.enterprise_name, user?.tier ? `Tier: ${user.tier}` : null]
              .filter(Boolean)
              .join(" • ")}
          </div>
        </div>

        {/* Right-edge Drag Resize Handle */}
        {sidebarOpen && (
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Kéo để thay đổi chiều rộng thanh bên"
            aria-valuemin={SIDEBAR_MIN_WIDTH}
            aria-valuemax={getEffectiveMaxSidebarWidth(viewportWidth)}
            aria-valuenow={sidebarWidth}
            tabIndex={0}
            title="Kéo để điều chỉnh độ rộng thanh bên (Nhấp đúp để đặt lại mặc định)"
            onPointerDown={handleStartResizeSidebar}
            onKeyDown={handleSidebarResizerKeyDown}
            onDoubleClick={() =>
              setSidebarWidth(clampSidebarWidth(SIDEBAR_DEFAULT_WIDTH, window.innerWidth))
            }
            className="group/resizer absolute top-0 -right-1 bottom-0 z-50 w-2.5 cursor-col-resize select-none touch-none flex items-center justify-center focus:outline-none"
          >
            <div
              className={cn(
                "h-full w-[2px] rounded-full transition-all duration-150",
                isResizingSidebar
                  ? "bg-amber-500 w-[3px] shadow-[0_0_12px_rgba(245,158,11,0.75)]"
                  : "bg-transparent group-hover/resizer:bg-amber-500/60 group-focus-visible/resizer:bg-amber-500/80",
              )}
            />
          </div>
        )}
      </aside>

      {/* Main Workspace Area (Transparent over Liquid Stage) */}
      <div className="relative z-10 flex flex-1 flex-col min-w-0 overflow-hidden">
        {/* Top Header (Liquid Glass) */}
        <header className="relative z-40 flex items-center justify-between px-4 sm:px-6 py-2.5 liquid-glass-header">
          <div className="flex items-center gap-3 min-w-0">
            {!sidebarOpen && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => setSidebarOpen(true)}
                className="h-8 w-8 shrink-0 text-muted-foreground hover:text-foreground hover:bg-accent"
                title="Mở thanh bên"
              >
                <PanelLeftOpen className="h-4 w-4" />
              </Button>
            )}

            <div className="flex items-center gap-3 min-w-0">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-500/15 text-amber-500 font-bold border border-amber-500/30">
                <Bot className="h-5 w-5" />
              </div>

              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm sm:text-base truncate text-foreground">
                    SGOD Asset Copilot
                  </span>
                  {(user?.role_vi || user?.role) && (
                    <span className="inline-flex items-center rounded-full bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 text-[10px] font-semibold text-amber-600 dark:text-amber-400 shrink-0">
                      {user?.role_vi || user?.role}
                    </span>
                  )}
                </div>
                {(user?.enterprise_name || user?.full_name) && (
                  <div className="hidden sm:block text-[11px] text-muted-foreground truncate">
                    {[user?.enterprise_name, user?.full_name]
                      .filter(Boolean)
                      .join(" • ")}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">

            {/* Desktop Wide View Mode Toggle */}
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={() => setIsWideView((prev) => !prev)}
              aria-label={isWideView ? "Thu gọn giao diện" : "Mở rộng không gian làm việc"}
              title={isWideView ? "Thu gọn giao diện (Tiêu chuẩn)" : "Mở rộng giao diện (Toàn màn hình)"}
              className="h-9 w-9 rounded-lg hidden sm:flex border-border bg-card/60 hover:bg-accent text-foreground"
            >
              {isWideView ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>

            {/* Dark / Light Toggle */}
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={toggleTheme}
              aria-label={theme === "dark" ? "Chuyển sang chế độ sáng" : "Chuyển sang chế độ tối"}
              title={theme === "dark" ? "Chuyển sang Light Mode" : "Chuyển sang Dark Mode"}
              className="h-9 w-9 rounded-lg border-border bg-card/60 hover:bg-accent"
            >
              {theme === "dark" ? (
                <Sun className="h-4 w-4 text-amber-400" />
              ) : (
                <Moon className="h-4 w-4 text-slate-700" />
              )}
            </Button>

            {/* Logout */}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={logout}
              title="Đăng xuất"
              className="gap-1.5 rounded-lg border-border bg-card/60 hover:bg-accent text-foreground"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Đăng xuất</span>
            </Button>
          </div>
        </header>

        {/* Body: Welcome Screen with Lamp OR Active Conversation */}
        {!hasConversation ? (
          <div className="relative flex-1 flex flex-col overflow-y-auto overflow-x-hidden">
            <Hero
              isChatFocused={isChatFocused}
              title={`Xin chào, ${user?.full_name || "bạn"}!`}
              subtitle="Trợ lý AI tích hợp trực tiếp với cơ sở dữ liệu SGOD Asset Management. Bạn có thể tra cứu thông tin tài sản, kiểm tra kho bãi hoặc tra cứu danh mục tự động."
              className="min-h-full flex-1 rounded-none px-4"
              titleClassName="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-foreground"
              subtitleClassName="text-sm sm:text-base md:text-lg max-w-2xl text-muted-foreground"
              contentClassName="w-full max-w-5xl mx-auto pt-24 pb-12"
            >
              <div className="w-full mt-4 space-y-4">
                {renderComposer("welcome")}
                {renderWelcomeFeatureCards()}
              </div>
            </Hero>
          </div>
        ) : (
          <>
            {/* Active Conversation Area */}
            <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-4">
              <div
                className={cn(
                  "mx-auto space-y-6 transition-all duration-300",
                  isWideView ? "max-w-6xl" : "max-w-4xl",
                )}
              >
                {messages.map((m) => (
                  <div
                    key={m.id}
                    className={cn(
                      "flex items-start gap-3 group",
                      m.sender === "user" ? "justify-end" : "justify-start",
                    )}
                  >
                    {m.sender === "assistant" && (
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-500/15 text-amber-500 mt-0.5 border border-amber-500/30">
                        <Bot className="h-5 w-5" />
                      </div>
                    )}

                    <div
                      className={cn(
                        "rounded-2xl px-5 py-4 transition-all",
                        m.sender === "user"
                          ? "max-w-[85%] sm:max-w-[70%] rounded-br-xs liquid-glass-user"
                          : "min-w-0 w-full max-w-full sm:max-w-[92%] rounded-bl-xs liquid-glass-assistant",
                      )}
                    >
                      {/* Assistant Header with Model Pill & Quick Copy Button */}
                      {m.sender === "assistant" && (
                        <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-border/60 text-xs">
                          <div className="flex items-center gap-1.5 text-muted-foreground font-medium">
                            <span className="font-semibold text-foreground">SGOD Copilot</span>
                            {(m.model || activeModel) && (
                              <>
                                <span>•</span>
                                <span className="text-[10px] font-mono bg-accent text-amber-600 dark:text-amber-400 px-1.5 py-0.5 rounded border border-border">
                                  {m.model || activeModel}
                                </span>
                              </>
                            )}
                          </div>

                          <div className="flex items-center gap-1">
                            <button
                              type="button"
                              onClick={() => handleCopyMessage(m.text, m.id)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                              title="Sao chép câu trả lời"
                            >
                              {copiedId === m.id ? (
                                <>
                                  <Check className="h-3 w-3 text-emerald-500" />
                                  <span className="text-emerald-500 font-medium">Đã sao chép</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="h-3 w-3" />
                                  <span>Sao chép</span>
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Tool Execution Cards */}
                      {m.tools && m.tools.length > 0 && (
                        <div className="mb-3 flex flex-col gap-2">
                          {m.tools.map((t, idx) => {
                            const toolKey = `${m.id}_tool_${idx}`
                            const isExpanded = !!expandedTools[toolKey]
                            return (
                              <div
                                key={idx}
                                className="rounded-xl border border-border liquid-glass-tool text-xs overflow-hidden transition-all shadow-xs"
                              >
                                <div
                                  className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-accent/40 transition-colors select-none"
                                  onClick={() => toggleToolExpand(toolKey)}
                                >
                                  <div className="flex items-center gap-2 min-w-0">
                                    <div className="p-1 rounded-md bg-amber-500/15 text-amber-500">
                                      <Wrench className="h-3.5 w-3.5" />
                                    </div>
                                    <span className="font-medium text-foreground truncate">
                                      {t.tool_name}
                                    </span>
                                    {t.is_running ? (
                                      <span className="inline-flex items-center gap-1 text-amber-500 font-medium">
                                        <Clock className="h-3 w-3 animate-spin" />
                                        <span>Đang gọi API SGOD...</span>
                                      </span>
                                    ) : t.success ? (
                                      <span className="inline-flex items-center gap-1 text-emerald-500 font-semibold">
                                        <CheckCircle2 className="h-3 w-3" />
                                        <span>Thành công</span>
                                        {t.status_code && (
                                          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                                            HTTP {t.status_code}
                                          </span>
                                        )}
                                      </span>
                                    ) : (
                                      <span className="inline-flex items-center gap-1 text-rose-500 font-semibold">
                                        <XCircle className="h-3 w-3" />
                                        <span>Thất bại</span>
                                        {t.status_code && (
                                          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                                            HTTP {t.status_code}
                                          </span>
                                        )}
                                      </span>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-2 shrink-0 text-muted-foreground ml-2">
                                    {typeof t.duration_ms === "number" && (
                                      <span className="inline-flex items-center gap-0.5 rounded-md bg-accent px-1.5 py-0.5 text-[10px] font-mono border border-border text-amber-600 dark:text-amber-300">
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
                                  <div className="border-t border-border px-3 py-2.5 bg-black/40 dark:bg-black/60 space-y-2 text-[11px] font-mono">
                                    <div>
                                      <div className="text-zinc-400 font-semibold mb-1">
                                        Tham số (Arguments):
                                      </div>
                                      <pre className="p-2 rounded-lg bg-black/50 text-emerald-400 overflow-x-auto max-h-36 whitespace-pre-wrap break-all border border-border/50">
                                        {JSON.stringify(t.arguments, null, 2)}
                                      </pre>
                                    </div>
                                    {t.result !== undefined && t.result !== null && (
                                      <div>
                                        <div className="text-zinc-400 font-semibold mb-1">
                                          Kết quả SGOD (Result):
                                        </div>
                                        <pre className="p-2 rounded-lg bg-black/50 text-zinc-200 overflow-x-auto max-h-48 whitespace-pre-wrap break-all border border-border/50">
                                          {typeof t.result === "string"
                                            ? t.result
                                            : JSON.stringify(t.result, null, 2)}
                                        </pre>
                                      </div>
                                    )}
                                    {/* ONLY show error block if tool call failed AND has error text */}
                                    {!t.success && t.error && (
                                      <div className="text-rose-500 font-semibold">
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
                        <div className="flex items-center gap-2 py-1 text-xs text-amber-500 animate-pulse">
                          <Sparkles className="h-3.5 w-3.5" />
                          <span>{m.statusMessage}</span>
                        </div>
                      )}

                      {/* Text content with blinking cursor while streaming */}
                      {m.text && (
                        m.sender === "assistant" ? (
                          <AssistantMarkdown
                            content={m.text}
                            isStreaming={m.isStreaming}
                          />
                        ) : (
                          <div className="text-sm sm:text-base leading-relaxed whitespace-pre-wrap font-normal">
                            {m.text}
                          </div>
                        )
                      )}

                      {/* Footer: Metrics */}
                      <div
                        className={cn(
                          "mt-3 pt-2.5 border-t flex flex-wrap items-center justify-between gap-2 text-[10px]",
                          m.sender === "user"
                            ? "border-amber-500/25 text-amber-950/70 dark:text-amber-100/75"
                            : "border-border/60 text-muted-foreground",
                        )}
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          {typeof m.responseTimeMs === "number" && (
                            <span
                              className="inline-flex items-center gap-1 font-mono font-medium rounded-md bg-accent border border-border px-1.5 py-0.5 text-foreground"
                              title="Thời gian phản hồi"
                            >
                              <Clock className="h-3 w-3 text-amber-500" />
                              {(m.responseTimeMs / 1000).toFixed(2)}s
                            </span>
                          )}
                          {typeof m.outputTokens === "number" && (
                            <span
                              className="inline-flex items-center gap-1 font-mono rounded-md bg-accent border border-border px-1.5 py-0.5 text-foreground"
                              title="Số lượng từ sinh ra"
                            >
                              <FileText className="h-3 w-3 text-sky-500" />
                              {m.outputTokens} từ
                            </span>
                          )}
                          {typeof m.tokensPerSec === "number" && (
                            <span
                              className="inline-flex items-center gap-1 font-mono rounded-md bg-accent border border-border px-1.5 py-0.5 text-foreground"
                              title="Tốc độ sinh chữ trung bình (từ / giây)"
                            >
                              <Zap className="h-3 w-3 text-emerald-500" />
                              {m.tokensPerSec} từ/s
                            </span>
                          )}
                          {m.tokenUsage && (
                            <span
                              className="inline-flex items-center gap-1 font-mono text-[9px] opacity-75 rounded-md bg-accent border border-border px-1.5 py-0.5 text-foreground"
                              title={`Gemini Tokens - Prompt: ${m.tokenUsage.prompt_tokens} • Output: ${m.tokenUsage.completion_tokens}`}
                            >
                              <Cpu className="h-2.5 w-2.5 text-amber-500" />
                              {m.tokenUsage.total_tokens} tk
                            </span>
                          )}
                        </div>
                        <span className="opacity-70 font-mono text-[10px]">{m.timestamp}</span>
                      </div>
                    </div>

                    {m.sender === "user" && (
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-500/20 text-amber-600 dark:text-amber-300 mt-0.5 border border-amber-500/40 font-semibold">
                        <UserIcon className="h-4 w-4" />
                      </div>
                    )}
                  </div>
                ))}

                {sending && !messages.some((m) => m.isStreaming) && (
                  <div className="flex items-start gap-3 justify-start">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-500/15 text-amber-500 mt-0.5 border border-amber-500/30">
                      <Bot className="h-5 w-5" />
                    </div>
                    <div className="flex items-center gap-2 rounded-2xl border border-border bg-card/70 px-4 py-3 text-xs sm:text-sm text-foreground shadow-md backdrop-blur-md">
                      <span className="inline-flex gap-1">
                        <span className="h-2 w-2 rounded-full bg-amber-500 animate-bounce" />
                        <span className="h-2 w-2 rounded-full bg-amber-500 animate-bounce [animation-delay:0.15s]" />
                        <span className="h-2 w-2 rounded-full bg-amber-500 animate-bounce [animation-delay:0.3s]" />
                      </span>
                      <span>Đang kết nối Gemini và tra cứu dữ liệu SGOD...</span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Bottom Composer Bar (Liquid Glass) */}
            <div className="border-t border-border/60 bg-card/80 backdrop-blur-2xl px-4 sm:px-6 py-3">
              {renderBottomSuggestions()}
              {renderComposer("bottom")}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
