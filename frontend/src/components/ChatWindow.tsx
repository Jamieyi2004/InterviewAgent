/**
 * 聊天窗口 —— 消息列表 + 流式显示 + 自动滚动（Doubao 风格）
 */

"use client";

import { useInterviewStore } from "@/store/useInterviewStore";
import Image from "next/image";
import { useEffect, useRef } from "react";
import ChatMessageBubble from "./ChatMessage";

export default function ChatWindow() {
  const { messages, streamingContent, isStreaming } = useInterviewStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  return (
    <div className="flex h-full flex-col overflow-y-auto px-6 py-5">
      {messages.length === 0 && !isStreaming && (
        <div className="flex flex-1 items-center justify-center">
          <div className="text-center">
            <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-surface-card">
              <Image src="/logo.png" alt="" width={24} height={24} className="rounded-lg" />
            </div>
            <p className="text-sm text-ink-tertiary">等待面试官开场...</p>
          </div>
        </div>
      )}

      <div className="space-y-5">
        {messages.map((msg) => (
          <ChatMessageBubble key={msg.id} message={msg} />
        ))}
      </div>

      {/* 流式输出 */}
      {isStreaming && streamingContent && (
        <div className="mt-5 flex gap-3 message-enter">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl overflow-hidden">
            <Image src="/logo.png" alt="AI" width={32} height={32} />
          </div>
          <div className="max-w-[70%] rounded-2xl rounded-tl-md bg-surface-card px-4 py-3 text-sm leading-relaxed text-ink-primary">
            <p className="typing-cursor whitespace-pre-wrap">{streamingContent}</p>
          </div>
        </div>
      )}

      {/* 加载动画 */}
      {isStreaming && !streamingContent && (
        <div className="mt-5 flex gap-3 message-enter">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl overflow-hidden">
            <Image src="/logo.png" alt="AI" width={32} height={32} />
          </div>
          <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-md bg-surface-card px-4 py-3.5">
            <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-tertiary" style={{ animationDelay: "0ms" }} />
            <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-tertiary" style={{ animationDelay: "200ms" }} />
            <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-tertiary" style={{ animationDelay: "400ms" }} />
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
