import * as React from "react"
import {
  MessageSquare,
  Pin,
  PinOff,
  MoreHorizontal,
  Pencil,
  Trash2,
  Check,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { ChatSession } from "./ChatWidget"

interface SidebarConversationItemProps {
  session: ChatSession
  isActive: boolean
  isPinned: boolean
  onSelect: (session: ChatSession) => void
  onTogglePin: (sessionId: string) => void
  onRename: (sessionId: string, newTitle: string) => void
  onDelete: (e: React.MouseEvent, sessionId: string) => void
}

export const SidebarConversationItem: React.FC<SidebarConversationItemProps> = React.memo(
  ({
    session,
    isActive,
    isPinned,
    onSelect,
    onTogglePin,
    onRename,
    onDelete,
  }) => {
    const [menuOpen, setMenuOpen] = React.useState(false)
    const [isRenaming, setIsRenaming] = React.useState(false)
    const [draftTitle, setDraftTitle] = React.useState(session.title)

    const menuRef = React.useRef<HTMLDivElement>(null)
    const inputRef = React.useRef<HTMLInputElement>(null)

    React.useEffect(() => {
      if (!isRenaming) {
        setDraftTitle(session.title)
      }
    }, [session.title, isRenaming])

    // Focus input when entering rename mode
    React.useEffect(() => {
      if (isRenaming && inputRef.current) {
        inputRef.current.focus()
        inputRef.current.select()
      }
    }, [isRenaming])

    // Close options menu on outside click or Escape
    React.useEffect(() => {
      if (!menuOpen) return
      const handlePointerDownOutside = (e: MouseEvent) => {
        if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
          setMenuOpen(false)
        }
      }
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          setMenuOpen(false)
        }
      }
      document.addEventListener("mousedown", handlePointerDownOutside)
      document.addEventListener("keydown", handleKeyDown)
      return () => {
        document.removeEventListener("mousedown", handlePointerDownOutside)
        document.removeEventListener("keydown", handleKeyDown)
      }
    }, [menuOpen])

    const handleCommitRename = () => {
      const trimmed = draftTitle.replace(/\s+/g, " ").trim()
      setIsRenaming(false)
      if (trimmed && trimmed !== session.title) {
        onRename(session.id, trimmed)
      } else {
        setDraftTitle(session.title)
      }
    }

    const handleCancelRename = () => {
      setIsRenaming(false)
      setDraftTitle(session.title)
    }

    return (
      <div
        role="button"
        tabIndex={0}
        title={isRenaming ? undefined : session.title}
        onClick={() => {
          if (!isRenaming) {
            onSelect(session)
          }
        }}
        onKeyDown={(e) => {
          if (isRenaming) return
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault()
            onSelect(session)
          }
        }}
        className={cn(
          "group relative flex items-center justify-between gap-1.5 rounded-lg px-2.5 h-9 text-xs sm:text-sm cursor-pointer transition-colors min-w-0 select-none",
          isActive
            ? "bg-accent border-l-2 border-amber-500 text-foreground font-medium shadow-xs"
            : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
        )}
      >
        <div className="flex items-center gap-2 min-w-0 flex-1 overflow-hidden">
          <MessageSquare
            className={cn(
              "h-3.5 w-3.5 shrink-0 transition-colors",
              isActive || isPinned ? "text-amber-500" : "text-amber-500/70",
            )}
          />

          {isRenaming ? (
            <div
              className="flex items-center gap-1 min-w-0 flex-1"
              onClick={(e) => e.stopPropagation()}
            >
              <input
                ref={inputRef}
                type="text"
                value={draftTitle}
                onChange={(e) => setDraftTitle(e.target.value)}
                onKeyDown={(e) => {
                  e.stopPropagation()
                  if (e.key === "Enter") {
                    e.preventDefault()
                    handleCommitRename()
                  } else if (e.key === "Escape") {
                    e.preventDefault()
                    handleCancelRename()
                  }
                }}
                onBlur={handleCommitRename}
                aria-label="Đổi tên cuộc trò chuyện"
                className="w-full min-w-0 bg-background/90 text-foreground text-xs sm:text-sm px-1.5 py-0.5 rounded border border-amber-500/60 focus:outline-none"
              />
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  handleCommitRename()
                }}
                className="p-0.5 text-emerald-500 hover:text-emerald-400 shrink-0"
                title="Lưu tên mới"
              >
                <Check className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  handleCancelRename()
                }}
                className="p-0.5 text-muted-foreground hover:text-foreground shrink-0"
                title="Hủy"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <span
              style={{
                minWidth: 0,
                flex: 1,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {session.title}
            </span>
          )}
        </div>

        {/* Right indicators & actions (Pin indicator + More Options menu) */}
        {!isRenaming && (
          <div
            ref={menuRef}
            className="flex items-center gap-0.5 shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            {isPinned && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onTogglePin(session.id)
                }}
                className="p-1 rounded-md text-amber-500 hover:bg-amber-500/15 transition-colors shrink-0"
                title="Bỏ ghim cuộc trò chuyện"
                aria-label="Bỏ ghim cuộc trò chuyện"
              >
                <Pin className="h-3 w-3 fill-amber-500/25 rotate-45" />
              </button>
            )}

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                setMenuOpen((prev) => !prev)
              }}
              aria-label="Tùy chọn cuộc trò chuyện"
              aria-expanded={menuOpen}
              title="Tùy chọn"
              className={cn(
                "p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-background/60 transition-opacity shrink-0",
                menuOpen
                  ? "opacity-100 bg-background/60 text-foreground"
                  : "opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100",
              )}
            >
              <MoreHorizontal className="h-3.5 w-3.5" />
            </button>

            {menuOpen && (
              <div
                role="menu"
                className="absolute right-2 top-8 z-50 w-44 rounded-xl border border-border bg-popover/95 text-popover-foreground shadow-xl backdrop-blur-xl py-1 text-xs animate-in fade-in zoom-in-95 duration-100"
              >
                <button
                  type="button"
                  role="menuitem"
                  onClick={(e) => {
                    e.stopPropagation()
                    setMenuOpen(false)
                    onTogglePin(session.id)
                  }}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-accent transition-colors text-foreground"
                >
                  {isPinned ? (
                    <>
                      <PinOff className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                      <span>Bỏ ghim</span>
                    </>
                  ) : (
                    <>
                      <Pin className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                      <span>Ghim cuộc trò chuyện</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  role="menuitem"
                  onClick={(e) => {
                    e.stopPropagation()
                    setMenuOpen(false)
                    setIsRenaming(true)
                  }}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-accent transition-colors text-foreground"
                >
                  <Pencil className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <span>Đổi tên</span>
                </button>

                <div className="my-1 border-t border-border/60" />

                <button
                  type="button"
                  role="menuitem"
                  onClick={(e) => {
                    setMenuOpen(false)
                    onDelete(e, session.id)
                  }}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-rose-500/10 text-rose-500 transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5 shrink-0" />
                  <span>Xóa cuộc trò chuyện</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    )
  },
)

SidebarConversationItem.displayName = "SidebarConversationItem"

