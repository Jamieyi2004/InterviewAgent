/**
 * 聊天输入框 —— 悬浮输入栏（Doubao 风格）
 * 支持文字发送与麦克风语音（二选一）
 */

"use client";

import { VoiceRecorder } from "@/audioRecorder";
import { ArrowUp, Mic } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface Props {
  onSend: (content: string) => void;
  /** 语音：16kHz PCM Base64，由父组件经 WebSocket 发送 */
  onSendVoice?: (audioBase64: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({
  onSend,
  onSendVoice,
  disabled = false,
  placeholder = "输入你的回答...",
}: Props) {
  const [input, setInput] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const voiceRef = useRef(new VoiceRecorder());

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
    }
  }, [input]);

  useEffect(() => {
    if (disabled && voiceRef.current.getState() === "recording") {
      voiceRef.current.cancel();
      setIsRecording(false);
    }
  }, [disabled]);

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
  const voiceEnabled = Boolean(onSendVoice) && !disabled;

  const toggleRecording = async () => {
    if (!onSendVoice || disabled) return;
    const vr = voiceRef.current;
    if (vr.getState() === "recording") {
      try {
        const b64 = await vr.stop();
        if (b64.length > 0) {
          onSendVoice(b64);
        }
      } catch (e) {
        console.error("[Voice]", e);
      }
      setIsRecording(false);
      return;
    }
    try {
      await vr.start();
      setIsRecording(true);
    } catch (e) {
      console.error("[Voice] 麦克风", e);
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="flex items-end gap-2 rounded-3xl border border-black/6 bg-surface-elevated px-4 py-2.5 shadow-input transition-all focus-within:border-brand-700/20 focus-within:shadow-float">
        <button
          type="button"
          onClick={() => void toggleRecording()}
          disabled={!voiceEnabled}
          title={isRecording ? "点击结束录音并发送" : "点击开始语音回答"}
          className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl transition-all ${
            !voiceEnabled
              ? "text-ink-disabled"
              : isRecording
                ? "bg-brand-700 text-white shadow-sm animate-pulse hover:bg-brand-800"
                : "bg-brand-700/12 text-brand-700 hover:bg-brand-700/20"
          }`}
        >
          <Mic className="h-4 w-4" />
        </button>
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
        {onSendVoice
          ? "文字或语音二选一作答；语音点击左侧麦克风开始/结束录音"
          : null}
        {onSendVoice ? " · " : ""}
        AI 面试官可能会产生不准确的信息，仅供参考
      </p>
    </div>
  );
}
