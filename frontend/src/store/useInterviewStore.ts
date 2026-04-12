/**
 * Zustand 面试全局状态管理
 */

import { create } from "zustand";

/** 聊天消息 */
export interface ChatMessage {
  id: string;
  role: "interviewer" | "candidate";
  content: string;
  timestamp: number;
}

/** 重新导出常量，兼容已有导入 */
export { STAGE_LABELS } from "@/lib/constants";

interface InterviewState {
  // ---- 简历相关 ----
  resumeId: number | null;
  resumeFilename: string;

  // ---- 面试会话 ----
  sessionId: number | null;
  currentStage: string;
  isInterviewing: boolean;
  isStreaming: boolean;

  // ---- 对话消息 ----
  messages: ChatMessage[];
  streamingContent: string;

  /** 是否播放面试官语音（TTS） */
  ttsEnabled: boolean;

  // ---- 报告 ----
  report: Record<string, unknown> | null;

  // ---- Actions ----
  setResume: (id: number, filename: string) => void;
  setSession: (id: number) => void;
  setStage: (stage: string) => void;
  setInterviewing: (val: boolean) => void;
  setStreaming: (val: boolean) => void;
  setTtsEnabled: (val: boolean) => void;
  addMessage: (msg: ChatMessage) => void;
  updateMessage: (id: string, content: string) => void;
  appendStreamToken: (token: string) => void;
  commitStreamMessage: () => void;
  setReport: (report: Record<string, unknown>) => void;
  reset: () => void;
}

export const useInterviewStore = create<InterviewState>((set, get) => ({
  // ---- 初始状态 ----
  resumeId: null,
  resumeFilename: "",
  sessionId: null,
  currentStage: "opening",
  isInterviewing: false,
  isStreaming: false,
  messages: [],
  streamingContent: "",
  ttsEnabled: true,
  report: null,

  // ---- Actions ----
  setResume: (id, filename) =>
    set({ resumeId: id, resumeFilename: filename }),

  setSession: (id) => set({ sessionId: id }),

  setStage: (stage) => set({ currentStage: stage }),

  setInterviewing: (val) => set({ isInterviewing: val }),

  setStreaming: (val) => set({ isStreaming: val }),

  setTtsEnabled: (val) => set({ ttsEnabled: val }),

  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  updateMessage: (id, content) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, content } : m
      ),
    })),

  /** 流式追加 token（面试官正在说话时） */
  appendStreamToken: (token) =>
    set((state) => ({ streamingContent: state.streamingContent + token })),

  /** 将流式缓冲区内容提交为一条完整消息 */
  commitStreamMessage: () => {
    const { streamingContent, messages } = get();
    if (streamingContent.trim()) {
      const msg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: "interviewer",
        content: streamingContent,
        timestamp: Date.now(),
      };
      set({ messages: [...messages, msg], streamingContent: "", isStreaming: false });
    }
  },

  setReport: (report) => set({ report }),

  reset: () =>
    set({
      resumeId: null,
      resumeFilename: "",
      sessionId: null,
      currentStage: "opening",
      isInterviewing: false,
      isStreaming: false,
      messages: [],
      streamingContent: "",
      ttsEnabled: true,
      report: null,
    }),
}));
