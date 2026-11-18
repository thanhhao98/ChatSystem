"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type FocusEvent,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import { gsap } from "gsap";
import {
  ArrowUp,
  Paperclip,
  X,
  FileText,
  Image as ImageIcon,
  Loader2,
  Sparkles,
} from "lucide-react";

import "./prompt-composer.css";

export interface PromptAttachment {
  id: string;
  file: File;
}

export interface PromptComposerProps {
  placeholder?: string;
  prompts?: string[];

  isLoading?: boolean;
  disabled?: boolean;

  maxFiles?: number;
  maxFileSize?: number;

  onSubmit: (
    message: string,
    files: File[]
  ) => Promise<void> | void;

  onSuggestionClick?: (prompt: string) => void;
  onFocusChange?: (focused: boolean) => void;

  className?: string;
}

const DEFAULT_PROMPTS = [
  "Cho tôi xem danh sách tài sản của tôi...",
  "Tìm kiếm tài sản theo tên hoặc mã tài sản...",
  "Có những địa điểm lưu kho nào?",
  "Xem danh mục phân loại tài sản...",
];

const MAX_HEIGHT = 180;

export default function PromptComposer({
  placeholder = "Nhập câu hỏi tra cứu tài sản...",
  prompts = DEFAULT_PROMPTS,
  isLoading = false,
  disabled = false,
  maxFiles = 4,
  maxFileSize = 10 * 1024 * 1024,
  onSubmit,
  onSuggestionClick,
  onFocusChange,
  className = "",
}: PromptComposerProps) {
  const [message, setMessage] = useState("");
  const [attachments, setAttachments] = useState<
    PromptAttachment[]
  >([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const sendRef = useRef<HTMLButtonElement>(null);

  const busy = isLoading || submitting || disabled;
  const canSend =
    (message.trim().length > 0 || attachments.length > 0) && !busy;

  // Automatically resize textarea
  const resizeTextarea = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";

    textarea.style.height =
      Math.min(textarea.scrollHeight, MAX_HEIGHT) + "px";
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [message, resizeTextarea]);

  // Entrance animation
  useEffect(() => {
    if (!cardRef.current) return;

    gsap.fromTo(
      cardRef.current,
      {
        opacity: 0,
        y: 12,
      },
      {
        opacity: 1,
        y: 0,
        duration: 0.55,
        ease: "power3.out",
      }
    );
  }, []);

  // Send button animation
  useEffect(() => {
    if (!sendRef.current || !canSend) return;

    const tween = gsap.to(sendRef.current, {
      boxShadow:
        "0 0 24px rgba(95,178,242,.42)",
      duration: 1.2,
      repeat: -1,
      yoyo: true,
      ease: "sine.inOut",
    });

    return () => {
      tween.kill();
    };
  }, [canSend]);

  // Liquid glass pointer effect
  const handlePointerMove = (
    e: React.PointerEvent<HTMLDivElement>
  ) => {
    const rect = e.currentTarget.getBoundingClientRect();

    const x =
      ((e.clientX - rect.left) / rect.width) * 100;

    const y =
      ((e.clientY - rect.top) / rect.height) * 100;

    e.currentTarget.style.setProperty("--mouse-x", `${x}%`);
    e.currentTarget.style.setProperty("--mouse-y", `${y}%`);
  };

  // Focus/Blur management for Interactive Lamp
  const handleFocusCapture = () => {
    onFocusChange?.(true);
  };

  const handleBlurCapture = (e: FocusEvent<HTMLDivElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
      onFocusChange?.(false);
    }
  };

  // Add real File objects
  const handleFiles = (e: ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);

    setError("");

    const available = maxFiles - attachments.length;

    if (available <= 0) {
      setError(`Chỉ được đính kèm tối đa ${maxFiles} file.`);
      e.target.value = "";
      return;
    }

    const accepted: PromptAttachment[] = [];

    for (const file of selected.slice(0, available)) {
      if (file.size > maxFileSize) {
        setError(
          `${file.name} vượt quá giới hạn dung lượng cho phép.`
        );
        continue;
      }

      const id =
        typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
          ? crypto.randomUUID()
          : `${Date.now()}_${Math.random().toString(36).slice(2)}`;

      accepted.push({
        id,
        file,
      });
    }

    setAttachments((prev) => [...prev, ...accepted]);

    e.target.value = "";
  };

  const removeFile = (id: string) => {
    setAttachments((prev) =>
      prev.filter((item) => item.id !== id)
    );
  };

  // Submit message
  const handleSubmit = async (
    e?: FormEvent<HTMLFormElement>
  ) => {
    e?.preventDefault();

    const text = message.trim();

    if ((!text && attachments.length === 0) || busy) return;

    setError("");
    setSubmitting(true);

    try {
      await onSubmit(
        text,
        attachments.map((item) => item.file)
      );

      // Clear only after successful submission
      setMessage("");
      setAttachments([]);

      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
        textareaRef.current.focus();
      }
    } catch (err) {
      console.error("Message submission failed:", err);

      setError(
        err instanceof Error
          ? err.message
          : "Không thể gửi tin nhắn. Vui lòng thử lại."
      );

      // Preserve message and attachments on failure
    } finally {
      setSubmitting(false);
    }
  };

  const handleKeyDown = (
    e: KeyboardEvent<HTMLTextAreaElement>
  ) => {
    if (
      e.key === "Enter" &&
      !e.shiftKey &&
      !e.nativeEvent.isComposing
    ) {
      e.preventDefault();
      void handleSubmit();
    }
  };

  const handleSuggestion = (prompt: string) => {
    if (busy) return;

    if (onSuggestionClick) {
      onSuggestionClick(prompt);
      return;
    }

    setMessage(prompt);
    textareaRef.current?.focus();
  };

  const getFileIcon = (file: File) => {
    if (file.type.startsWith("image/")) {
      return <ImageIcon size={14} />;
    }

    return <FileText size={14} />;
  };

  return (
    <div
      className={`sgod-composer-wrapper ${className}`}
    >
      {/* Suggested prompts */}
      {prompts.length > 0 && (
        <div className="sgod-suggestions">
          {prompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              disabled={busy}
              className="sgod-suggestion"
              onClick={() => handleSuggestion(prompt)}
            >
              <Sparkles size={13} />
              <span>{prompt}</span>
            </button>
          ))}
        </div>
      )}

      {/* Liquid Glass Composer */}
      <div
        ref={cardRef}
        className="sgod-glass-card"
        onPointerMove={handlePointerMove}
        onFocusCapture={handleFocusCapture}
        onBlurCapture={handleBlurCapture}
      >
        <div className="sgod-glass-sheen" />

        <form onSubmit={handleSubmit}>
          {/* Textarea */}
          <div className="sgod-input-area">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => {
                setMessage(e.target.value);
                setError("");
              }}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={busy}
              rows={2}
              className="sgod-textarea"
              aria-label="Nhập câu hỏi"
            />
          </div>

          {/* Attached files */}
          {attachments.length > 0 && (
            <div className="sgod-attachments">
              {attachments.map(({ id, file }) => (
                <div key={id} className="sgod-file-chip">
                  {getFileIcon(file)}

                  <span title={file.name}>
                    {file.name}
                  </span>

                  <button
                    type="button"
                    onClick={() => removeFile(id)}
                    disabled={busy}
                    aria-label={`Xóa ${file.name}`}
                  >
                    <X size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Error */}
          {error && (
            <p className="sgod-composer-error" role="alert">
              {error}
            </p>
          )}

          {/* Toolbar */}
          <div className="sgod-toolbar">
            <div className="sgod-toolbar-left">
              <button
                type="button"
                className="sgod-attach-button"
                onClick={() => fileInputRef.current?.click()}
                disabled={busy || attachments.length >= maxFiles}
                aria-label="Đính kèm file"
                title="Đính kèm file"
              >
                <Paperclip size={17} />
              </button>

              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="sgod-hidden-input"
                onChange={handleFiles}
                disabled={busy}
              />

              <span className="sgod-attachment-hint">
                {attachments.length}/{maxFiles} file
              </span>
            </div>

            <div className="sgod-toolbar-right">
              <span className="sgod-keyboard-hint">
                Enter để gửi · Shift + Enter xuống dòng
              </span>

              <button
                ref={sendRef}
                type="submit"
                className="sgod-send-button"
                disabled={!canSend}
                aria-label="Gửi tin nhắn"
              >
                {busy ? (
                  <Loader2
                    size={18}
                    className="sgod-spinner"
                  />
                ) : (
                  <ArrowUp size={19} strokeWidth={2.5} />
                )}
              </button>
            </div>
          </div>
        </form>
      </div>

      <div className="sgod-composer-footer">
        <span>SGOD AI Assistant</span>
        <span>AI có thể đưa ra thông tin chưa chính xác.</span>
      </div>
    </div>
  );
}

