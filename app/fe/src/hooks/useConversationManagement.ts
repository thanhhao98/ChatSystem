import * as React from "react"

/**
 * Chuẩn hóa chuỗi tiếng Việt phục vụ tìm kiếm không dấu & không phân biệt hoa thường.
 * Giữ nguyên chuỗi gốc khi hiển thị trên UI.
 */
export function normalizeVietnameseText(input: string): string {
  if (!input) return ""
  return input
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "d")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim()
}

/**
 * Kiểm tra tiêu đề hội thoại có khớp với từ khóa tìm kiếm (hỗ trợ cả có dấu và không dấu).
 */
export function matchesConversationSearch(title: string, rawQuery: string): boolean {
  const trimmedQuery = rawQuery.trim()
  if (!trimmedQuery) return true
  if (!title) return false

  // Kiểm tra khớp trực tiếp (lowercase NFC)
  const lowerTitle = title.toLocaleLowerCase("vi").replace(/\s+/g, " ").trim()
  const lowerQuery = trimmedQuery.toLocaleLowerCase("vi").replace(/\s+/g, " ").trim()
  if (lowerTitle.includes(lowerQuery)) {
    return true
  }

  // Kiểm tra khớp không dấu (NFD stripped + đ->d)
  const normTitle = normalizeVietnameseText(title)
  const normQuery = normalizeVietnameseText(trimmedQuery)
  if (!normQuery) return true

  return normTitle.includes(normQuery)
}

/**
 * Tạo khóa localStorage lưu danh sách ID hội thoại đã ghim,
 * cô lập theo từng user_id và enterprise/tier.
 */
export function buildPinnedStorageKey(
  userId?: string | null,
  enterpriseName?: string | null,
  tier?: string | null,
): string {
  const safeUser = (userId || "guest").trim()
  const safeEnterprise = (enterpriseName || tier || "default")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_")
  return `sgod_pinned_conversations_${safeUser}_${safeEnterprise}`
}

interface UsePinnedConversationsOptions {
  userId?: string | null
  enterpriseName?: string | null
  tier?: string | null
  validSessionIds: string[]
}

export function usePinnedConversations({
  userId,
  enterpriseName,
  tier,
  validSessionIds,
}: UsePinnedConversationsOptions) {
  const pinnedStorageKey = React.useMemo(
    () => buildPinnedStorageKey(userId, enterpriseName, tier),
    [userId, enterpriseName, tier],
  )

  const readPinnedFromStorage = React.useCallback((key: string): string[] => {
    try {
      const raw = localStorage.getItem(key)
      if (!raw) return []
      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed)) return []
      return Array.from(
        new Set(parsed.filter((id): id is string => typeof id === "string" && id.length > 0)),
      )
    } catch {
      return []
    }
  }, [])

  const [pinnedIds, setPinnedIds] = React.useState<string[]>(() =>
    readPinnedFromStorage(pinnedStorageKey),
  )

  // Tải lại danh sách ghim khi đổi tài khoản hoặc doanh nghiệp
  React.useEffect(() => {
    setPinnedIds(readPinnedFromStorage(pinnedStorageKey))
  }, [pinnedStorageKey, readPinnedFromStorage])

  // Tự động dọn dẹp các ID đã bị xóa khỏi danh sách hội thoại
  React.useEffect(() => {
    if (validSessionIds.length === 0) return
    const validSet = new Set(validSessionIds)
    setPinnedIds((prev) => {
      const filtered = prev.filter((id) => validSet.has(id))
      if (filtered.length === prev.length) return prev
      try {
        localStorage.setItem(pinnedStorageKey, JSON.stringify(filtered))
      } catch {
        // Ignore quota errors
      }
      return filtered
    })
  }, [validSessionIds, pinnedStorageKey])

  const persistPinnedIds = React.useCallback(
    (updater: (prev: string[]) => string[]) => {
      setPinnedIds((prev) => {
        const next = Array.from(new Set(updater(prev)))
        try {
          localStorage.setItem(pinnedStorageKey, JSON.stringify(next))
        } catch {
          // Ignore quota errors
        }
        return next
      })
    },
    [pinnedStorageKey],
  )

  const togglePin = React.useCallback(
    (sessionId: string) => {
      persistPinnedIds((prev) =>
        prev.includes(sessionId)
          ? prev.filter((id) => id !== sessionId)
          : [sessionId, ...prev],
      )
    },
    [persistPinnedIds],
  )

  const pinConversation = React.useCallback(
    (sessionId: string) => {
      persistPinnedIds((prev) => (prev.includes(sessionId) ? prev : [sessionId, ...prev]))
    },
    [persistPinnedIds],
  )

  const unpinConversation = React.useCallback(
    (sessionId: string) => {
      persistPinnedIds((prev) => prev.filter((id) => id !== sessionId))
    },
    [persistPinnedIds],
  )

  const pinnedSet = React.useMemo(() => new Set(pinnedIds), [pinnedIds])

  return {
    pinnedIds,
    pinnedSet,
    togglePin,
    pinConversation,
    unpinConversation,
  }
}

