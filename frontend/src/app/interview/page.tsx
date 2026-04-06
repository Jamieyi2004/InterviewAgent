/**
 * 面试对话页面（豆包/ChatGPT 风格）
 *
 * 布局：左侧栏 + 右侧对话区
 * 对话区：顶部进度条 + 中间消息流 + 底部悬浮输入
 */

"use client";

import ChatInput from "@/components/ChatInput";
import ChatWindow from "@/components/ChatWindow";
import CodeEditor from "@/components/CodeEditor";
import InterviewProgress from "@/components/InterviewProgress";
import { CodingProblem, endInterview, fetchProblem } from "@/lib/api";
import { InterviewWebSocket } from "@/lib/websocket";
import { feLogger } from "@/logger";
import { useInterviewStore } from "@/store/useInterviewStore";
import { TtsPlayer } from "@/ttsPlayer";
import {
    BarChart3,
    ChevronLeft,
    PhoneOff,
    Volume2,
    VolumeX
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

export default function InterviewPage() {
  const router = useRouter();
  const wsRef = useRef<InterviewWebSocket | null>(null);

  const [roundStartAt, setRoundStartAt] = useState<number | null>(null);
  const [codingProblem, setCodingProblem] = useState<CodingProblem | null>(null);

  // 文字缓冲队列
  const textBufferRef = useRef<string>("");
  const displayTimerRef = useRef<NodeJS.Timeout | null>(null);
  const pendingDoneRef = useRef<{ stage: string } | null>(null);
  const pendingFinishedRef = useRef<number | null>(null);

  const {
    sessionId,
    currentStage,
    isInterviewing,
    isStreaming,
    ttsEnabled,
    setStage,
    setStreaming,
    setInterviewing,
    setTtsEnabled,
    addMessage,
    appendStreamToken,
    commitStreamMessage,
  } = useInterviewStore();

  const CHAR_DELAY = 150;
  const FIRST_CHAR_DELAY = 3500;
  const firstCharDelayRef = useRef<NodeJS.Timeout | null>(null);

  const startDisplayTimer = useCallback(() => {
    if (displayTimerRef.current) return;

    displayTimerRef.current = setInterval(() => {
      if (textBufferRef.current.length > 0) {
        const char = textBufferRef.current[0];
        textBufferRef.current = textBufferRef.current.slice(1);
        appendStreamToken(char);
      } else {
        if (pendingDoneRef.current) {
          const { stage } = pendingDoneRef.current;
          pendingDoneRef.current = null;
          commitStreamMessage();
          setStage(stage);
          stopDisplayTimer();
        } else if (pendingFinishedRef.current !== null) {
          const sid = pendingFinishedRef.current;
          pendingFinishedRef.current = null;
          commitStreamMessage();
          setInterviewing(false);
          stopDisplayTimer();
          router.push(`/report?session_id=${sid}`);
        }
      }
    }, CHAR_DELAY);
  }, [appendStreamToken, commitStreamMessage, setStage, setInterviewing, router]);

  const startDisplayWithDelay = useCallback(() => {
    if (firstCharDelayRef.current || displayTimerRef.current) return;

    firstCharDelayRef.current = setTimeout(() => {
      firstCharDelayRef.current = null;
      startDisplayTimer();
    }, FIRST_CHAR_DELAY);
  }, [startDisplayTimer]);

  const stopDisplayTimer = useCallback(() => {
    if (firstCharDelayRef.current) {
      clearTimeout(firstCharDelayRef.current);
      firstCharDelayRef.current = null;
    }
    if (displayTimerRef.current) {
      clearInterval(displayTimerRef.current);
      displayTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopDisplayTimer();
  }, [stopDisplayTimer]);

  useEffect(() => {
    if (currentStage === "coding" && sessionId && !codingProblem) {
      fetchProblem(sessionId).then((problem) => {
        if (problem) setCodingProblem(problem);
      });
    }
  }, [currentStage, sessionId, codingProblem]);

  const handleToken = useCallback(
    (token: string) => {
      setStreaming(true);
      textBufferRef.current += token;
      startDisplayWithDelay();
    },
    [setStreaming, startDisplayWithDelay]
  );

  const handleDone = useCallback(
    (stage: string) => {
      if (textBufferRef.current.length > 0) {
        pendingDoneRef.current = { stage };
      } else {
        commitStreamMessage();
        setStage(stage);
        stopDisplayTimer();
      }

      if (roundStartAt != null) {
        const now = performance.now();
        feLogger.info("round done (text)", {
          ms_from_send_to_done: now - roundStartAt,
          stage,
        });
      }
    },
    [commitStreamMessage, setStage, stopDisplayTimer, roundStartAt]
  );

  const handleFinished = useCallback(
    (sid: number) => {
      if (textBufferRef.current.length > 0) {
        pendingFinishedRef.current = sid;
      } else {
        commitStreamMessage();
        setInterviewing(false);
        stopDisplayTimer();
        router.push(`/report?session_id=${sid}`);
      }
    },
    [commitStreamMessage, setInterviewing, stopDisplayTimer, router]
  );

  const handleError = useCallback(
    (error: string) => {
      feLogger.error("[Interview] WS error", { error });
      setStreaming(false);
      stopDisplayTimer();
    },
    [setStreaming, stopDisplayTimer]
  );

  const currentRoundIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      router.push("/");
      return;
    }

    const ws = new InterviewWebSocket(sessionId, {
      onToken: handleToken,
      onDone: handleDone,
      onTtsSegment: ({ audioBase64, segmentIndex, text, roundId }) => {
        if (ttsEnabled && roundId) {
          if (currentRoundIdRef.current !== roundId) {
            currentRoundIdRef.current = roundId;
            TtsPlayer.startRound(sessionId, roundId);
          }
          TtsPlayer.enqueueSegment(sessionId, roundId, segmentIndex, audioBase64);
        }
        if (roundStartAt != null) {
          const now = performance.now();
          feLogger.info("round tts segment", {
            segmentIndex,
            textLength: text.length,
            ms_from_send_to_tts_segment: now - roundStartAt,
          });
        }
      },
      onFinished: handleFinished,
      onError: handleError,
    });

    ws.connect();
    wsRef.current = ws;
    setStreaming(true);

    return () => {
      ws.close();
      TtsPlayer.stopAll();
    };
  }, [sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSend = (content: string) => {
    textBufferRef.current = "";
    pendingDoneRef.current = null;
    pendingFinishedRef.current = null;
    stopDisplayTimer();

    addMessage({
      id: `msg-${Date.now()}`,
      role: "candidate",
      content,
      timestamp: Date.now(),
    });

    wsRef.current?.send(content);
    setStreaming(true);
    setRoundStartAt(performance.now());
    feLogger.info("round start", { contentLength: content.length });
  };

  const handleCodeSubmit = (code: string) => {
    addMessage({
      id: `msg-${Date.now()}`,
      role: "candidate",
      content: "【已提交代码】",
      timestamp: Date.now(),
    });

    const message = `【代码提交】\n\`\`\`cpp\n${code}\n\`\`\``;
    wsRef.current?.send(message);
    setStreaming(true);
    setRoundStartAt(performance.now());
  };

  const handleEnd = async () => {
    if (!sessionId) return;
    try {
      await endInterview(sessionId);
      wsRef.current?.close();
      setInterviewing(false);
      router.push(`/report?session_id=${sessionId}`);
    } catch (err) {
      feLogger.error("结束面试失败", err);
    }
  };

  return (
    <div className="flex h-screen">
      {/* ========== 左侧栏 ========== */}
      <aside className="flex w-[260px] flex-shrink-0 flex-col border-r border-black/5 bg-surface-sidebar">
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 py-5">
          <Image
            src="/logo.png"
            alt="华中师大 AI 面试官"
            width={36}
            height={36}
            className="rounded-xl"
          />
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-ink-primary leading-tight">
              AI 面试官
            </h1>
            <p className="text-[11px] text-ink-tertiary">华中师范大学</p>
          </div>
        </div>

        {/* 返回首页 */}
        <div className="px-3 mb-2">
          <button
            onClick={() => router.push("/")}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-ink-secondary transition-all hover:bg-surface-hover"
          >
            <ChevronLeft className="h-4 w-4" />
            返回首页
          </button>
        </div>

        <div className="mx-4 border-t border-black/5" />

        {/* 面试阶段信息 */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          <p className="mb-3 text-[11px] font-medium uppercase tracking-wider text-ink-tertiary">
            面试进度
          </p>
          <InterviewProgress currentStage={currentStage} />

          {/* 面试操作 */}
          <div className="mt-6 space-y-2">
            <button
              type="button"
              onClick={() => setTtsEnabled(!ttsEnabled)}
              className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm transition-all ${
                ttsEnabled
                  ? "bg-brand-700/8 text-brand-700"
                  : "text-ink-tertiary hover:bg-surface-hover"
              }`}
            >
              {ttsEnabled ? (
                <Volume2 className="h-4 w-4" />
              ) : (
                <VolumeX className="h-4 w-4" />
              )}
              {ttsEnabled ? "语音已开启" : "语音已关闭"}
            </button>

            {sessionId && (
              <Link
                href={`/dashboard?session_id=${sessionId}`}
                className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm text-ink-tertiary transition-all hover:bg-surface-hover"
              >
                <BarChart3 className="h-4 w-4" />
                实时数据仪表盘
              </Link>
            )}
          </div>
        </div>

        {/* 底部：结束面试按钮 */}
        <div className="border-t border-black/5 p-3">
          <button
            onClick={handleEnd}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-red-200 py-2.5 text-sm font-medium text-red-500 transition-all hover:bg-red-50 active:scale-[0.98]"
          >
            <PhoneOff className="h-4 w-4" />
            结束面试
          </button>
        </div>
      </aside>

      {/* ========== 右侧对话区域 ========== */}
      <main className="flex flex-1 flex-col bg-surface-main">
        {/* 顶部状态栏 */}
        <header className="flex items-center justify-between border-b border-black/5 px-6 py-3">
          <div className="flex items-center gap-2.5">
            <div className="relative">
              <Image
                src="/logo.png"
                alt="AI"
                width={32}
                height={32}
                className="rounded-xl"
              />
              <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-[1.5px] border-white bg-emerald-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-ink-primary">小华</p>
              <p className="text-[11px] text-ink-tertiary">
                {isStreaming ? "正在输入..." : "在线"}
              </p>
            </div>
          </div>
        </header>

        {/* 消息流 */}
        <div className="flex-1 overflow-hidden">
          <ChatWindow />
        </div>

        {/* 算法题编辑器 */}
        {currentStage === "coding" && (
          <div className="border-t border-black/5">
            <CodeEditor problem={codingProblem} onSubmit={handleCodeSubmit} disabled={isStreaming} />
          </div>
        )}

        {/* 底部悬浮输入框 */}
        <div className="px-6 pb-5 pt-2">
          <ChatInput
            onSend={handleSend}
            disabled={isStreaming}
            placeholder={
              currentStage === "coding"
                ? "如有问题可在此提问，或直接在上方编辑器提交代码..."
                : isStreaming
                ? "面试官正在思考..."
                : "输入你的回答...（Enter 发送）"
            }
          />
        </div>
      </main>
    </div>
  );
}
