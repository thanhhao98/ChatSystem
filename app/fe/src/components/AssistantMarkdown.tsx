import * as React from "react"
import ReactMarkdown, { Components } from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"

interface AssistantMarkdownProps {
  content: string
  isStreaming?: boolean
}

type BadgeVariant = "active" | "inactive" | "important" | "normal"

const STATUS_BADGE_MAP: Record<string, BadgeVariant> = {
  "đang hoạt động": "active",
  "ngừng hoạt động": "inactive",
  "quan trọng": "important",
  "bình thường": "normal",
}

const BADGE_STYLES: Record<BadgeVariant, { container: string; dot: string }> = {
  active: {
    container:
      "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 shadow-[0_0_10px_-3px_rgba(16,185,129,0.25)]",
    dot: "bg-emerald-500 dark:bg-emerald-400",
  },
  inactive: {
    container:
      "bg-zinc-500/15 text-zinc-600 dark:text-zinc-400 border-zinc-500/30",
    dot: "bg-zinc-400 dark:bg-zinc-500",
  },
  important: {
    container:
      "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/35 shadow-[0_0_10px_-3px_rgba(245,158,11,0.25)]",
    dot: "bg-amber-500 dark:bg-amber-400",
  },
  normal: {
    container:
      "bg-slate-500/15 text-slate-600 dark:text-slate-300 border-slate-500/30",
    dot: "bg-slate-400 dark:bg-slate-400",
  },
}

function extractSingleTextValue(node: React.ReactNode): string | null {
  if (typeof node === "string") {
    return node
  }
  if (typeof node === "number") {
    return String(node)
  }
  if (Array.isArray(node)) {
    if (node.length === 1) {
      return extractSingleTextValue(node[0])
    }
    const parts: string[] = []
    for (const child of node) {
      const val = extractSingleTextValue(child)
      if (val === null) return null
      parts.push(val)
    }
    return parts.join("")
  }
  if (React.isValidElement(node)) {
    const type = node.type
    if (type === "strong" || type === "em" || type === "span") {
      return extractSingleTextValue(node.props.children)
    }
  }
  return null
}

export const AssistantMarkdown: React.FC<AssistantMarkdownProps> = React.memo(
  ({ content, isStreaming }) => {
    const components = React.useMemo<Components>(
      () => ({
        p: ({ children }) => (
          <p className="mb-3 last:mb-0 leading-relaxed text-sm sm:text-[15px] text-inherit">
            {children}
          </p>
        ),
        h1: ({ children }) => (
          <h1 className="text-lg sm:text-xl font-bold tracking-tight mt-4 mb-2.5 first:mt-0 text-foreground border-b border-border/50 pb-1.5">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-base sm:text-lg font-bold tracking-tight mt-4 mb-2 first:mt-0 text-foreground">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-sm sm:text-base font-semibold mt-3 mb-1.5 first:mt-0 text-foreground">
            {children}
          </h3>
        ),
        h4: ({ children }) => (
          <h4 className="text-sm font-semibold mt-2.5 mb-1 first:mt-0 text-foreground">
            {children}
          </h4>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-foreground">{children}</strong>
        ),
        em: ({ children }) => <em className="italic opacity-95">{children}</em>,
        ul: ({ children }) => (
          <ul className="my-2.5 ml-5 list-disc space-y-1.5 text-sm sm:text-[15px] leading-relaxed marker:text-amber-500/80">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="my-2.5 ml-5 list-decimal space-y-1.5 text-sm sm:text-[15px] leading-relaxed marker:text-amber-500/80 marker:font-mono marker:text-xs">
            {children}
          </ol>
        ),
        li: ({ children }) => <li className="pl-1 leading-relaxed">{children}</li>,
        blockquote: ({ children }) => (
          <blockquote className="my-3 border-l-2 border-amber-500/60 bg-amber-500/5 pl-3.5 py-1.5 italic text-muted-foreground rounded-r-lg">
            {children}
          </blockquote>
        ),
        hr: () => <hr className="my-4 border-border/60" />,
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-amber-600 dark:text-amber-400 underline underline-offset-4 decoration-amber-500/40 hover:decoration-amber-500 transition-colors break-words"
          >
            {children}
          </a>
        ),
        pre: ({ children }) => (
          <pre className="my-3 w-full overflow-x-auto rounded-[10px] border border-border/80 bg-zinc-950/90 dark:bg-black/60 p-3.5 text-xs sm:text-[13px] font-mono text-zinc-100 leading-relaxed shadow-inner">
            {children}
          </pre>
        ),
        code: ({ className, children, ...props }) => {
          const isBlock = Boolean(className && className.startsWith("language-"))
          if (isBlock) {
            return (
              <code className={cn("font-mono text-xs sm:text-[13px]", className)} {...props}>
                {children}
              </code>
            )
          }
          return (
            <code
              className="rounded-md border border-border/80 bg-black/[0.06] dark:bg-white/[0.08] px-1.5 py-0.5 font-mono text-[12.5px] text-amber-700 dark:text-amber-300 break-words"
              {...props}
            >
              {children}
            </code>
          )
        },
        table: ({ children }) => (
          <div className="my-3.5 w-full max-w-full overflow-x-auto rounded-[10px] border border-black/10 dark:border-white/[0.12] bg-black/[0.02] dark:bg-white/[0.02] shadow-sm backdrop-blur-md">
            <table className="w-full border-collapse text-left text-[13px] leading-normal">
              {children}
            </table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-slate-200/70 dark:bg-black/50 border-b border-black/10 dark:border-white/[0.12] text-foreground select-none">
            {children}
          </thead>
        ),
        tbody: ({ children }) => (
          <tbody className="divide-y divide-black/[0.06] dark:divide-white/[0.07]">
            {children}
          </tbody>
        ),
        tr: ({ children }) => (
          <tr className="transition-colors hover:bg-black/[0.035] dark:hover:bg-white/[0.045]">
            {children}
          </tr>
        ),
        th: ({ children, style }) => (
          <th
            style={style}
            className="px-3.5 py-2.5 font-semibold text-[12.5px] tracking-wide text-slate-800 dark:text-zinc-100 whitespace-nowrap"
          >
            {children}
          </th>
        ),
        td: ({ children, style }) => {
          const rawText = extractSingleTextValue(children)
          const normalized = rawText ? rawText.trim().toLowerCase() : ""
          const badgeVariant = normalized ? STATUS_BADGE_MAP[normalized] : undefined

          if (badgeVariant && rawText) {
            const badgeStyle = BADGE_STYLES[badgeVariant]
            return (
              <td
                style={style}
                className="px-3.5 py-2.5 align-middle text-[13px] whitespace-nowrap"
              >
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11.5px] font-medium leading-tight",
                    badgeStyle.container,
                  )}
                >
                  <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", badgeStyle.dot)} />
                  <span>{rawText.trim()}</span>
                </span>
              </td>
            )
          }

          return (
            <td
              style={style}
              className="px-3.5 py-2.5 align-middle text-[13px] text-slate-700 dark:text-zinc-200"
            >
              {children}
            </td>
          )
        },
      }),
      [],
    )

    return (
      <div className="assistant-markdown-body w-full min-w-0 max-w-full overflow-hidden break-words">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
          {content}
        </ReactMarkdown>
        {isStreaming && (
          <span className="inline-block w-1.5 h-4 ml-1 bg-amber-500 animate-pulse align-middle" />
        )}
      </div>
    )
  },
)

AssistantMarkdown.displayName = "AssistantMarkdown"

