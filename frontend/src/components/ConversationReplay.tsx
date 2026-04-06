"use client";

import Image from "next/image";
import { STAGE_LABELS } from "@/lib/constants";
import type { SessionMessage } from "@/lib/api";

export default function ConversationReplay({ messages }: { messages: SessionMessage[] }) {
  let lastStage = "";

  return (
    <div className="flex flex-col gap-3">
      {messages.map((msg) => {
        const showDivider = msg.stage && msg.stage !== lastStage;
        if (msg.stage) lastStage = msg.stage;
        const isInterviewer = msg.role === "interviewer";

        return (
          <div key={msg.id}>
            {showDivider && (
              <div className="flex items-center gap-3 py-3">
                <div className="flex-1 border-t border-black/5" />
                <span className="text-xs font-medium text-ink-tertiary">
                  {STAGE_LABELS[msg.stage] || msg.stage}
                </span>
                <div className="flex-1 border-t border-black/5" />
              </div>
            )}
            <div className={`flex gap-3 ${isInterviewer ? "" : "flex-row-reverse"}`}>
              {isInterviewer ? (
                <Image
                  src="/logo.png"
                  alt="interviewer"
                  width={32}
                  height={32}
                  className="h-8 w-8 flex-shrink-0 rounded-full"
                />
              ) : (
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-brand-700 text-white text-xs font-medium">
                  候
                </div>
              )}
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  isInterviewer
                    ? "rounded-tl-md bg-surface-card text-ink-primary"
                    : "rounded-tr-md bg-brand-700 text-white"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.created_at && (
                  <p className={`mt-1 text-[10px] ${isInterviewer ? "text-ink-tertiary" : "text-white/60"}`}>
                    {new Date(msg.created_at).toLocaleTimeString("zh-CN")}
                  </p>
                )}
              </div>
            </div>
          </div>
        );
      })}
      {messages.length === 0 && (
        <div className="py-12 text-center text-sm text-ink-tertiary">暂无对话记录</div>
      )}
    </div>
  );
}
