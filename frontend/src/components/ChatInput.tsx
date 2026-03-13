/**
 * 聊天输入框 —— 悬浮输入栏（Doubao 风格）
 */

"use client";

import { ArrowUp } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface Props {
  onSend: (content: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({
  onSend,
  disabled = false,
  placeholder = "输入你的回答...",
}: Props) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
    }
  }, [input]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const hasContent = input.trim().length > 0;

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="flex items-end gap-2 rounded-3xl border border-black/6 bg-surface-elevated px-4 py-2.5 shadow-input transition-all focus-within:border-brand-700/20 focus-within:shadow-float">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none bg-transparent px-1 py-1 text-sm text-ink-primary outline-none placeholder:text-ink-tertiary disabled:opacity-40"
        />
        <button
          onClick={handleSend}
          disabled={disabled || !hasContent}
          className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl transition-all ${
            hasContent && !disabled
              ? "bg-brand-700 text-white shadow-sm hover:bg-brand-800 active:scale-95"
              : "bg-ink-disabled/30 text-ink-disabled"
          }`}
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </div>
      <p className="mt-1.5 text-center text-[11px] text-ink-disabled">
        AI 面试官可能会产生不准确的信息，仅供参考
      </p>
    </div>
  );
}
