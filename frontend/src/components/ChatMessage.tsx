/**
 * 单条消息气泡 —— 面试官（左）/ 候选人（右）
 */

import type { ChatMessage } from "@/store/useInterviewStore";
import { User } from "lucide-react";
import Image from "next/image";

interface Props {
  message: ChatMessage;
}

export default function ChatMessageBubble({ message }: Props) {
  const isInterviewer = message.role === "interviewer";

  return (
    <div
      className={`flex gap-3 message-enter ${
        isInterviewer ? "flex-row" : "flex-row-reverse"
      }`}
    >
      {/* 头像 */}
      {isInterviewer ? (
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl overflow-hidden">
          <Image src="/logo.png" alt="面试官" width={32} height={32} />
        </div>
      ) : (
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl bg-brand-700/10">
          <User className="h-4 w-4 text-brand-700" />
        </div>
      )}

      {/* 气泡 */}
      <div
        className={`max-w-[70%] px-4 py-3 text-sm leading-relaxed ${
          isInterviewer
            ? "rounded-2xl rounded-tl-md bg-surface-card text-ink-primary"
            : "rounded-2xl rounded-tr-md bg-brand-700 text-white"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}
