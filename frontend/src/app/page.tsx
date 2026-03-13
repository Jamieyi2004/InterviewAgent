/**
 * 首页 —— 华中师大 AI 面试官（豆包/ChatGPT 风格）
 *
 * 布局：左侧栏 (260px) + 右侧主区域
 * 空状态：中央 Avatar + 建议卡片网格
 * 底部：悬浮输入框
 */

"use client";

import ResumeUploader from "@/components/ResumeUploader";
import { startInterview } from "@/lib/api";
import { useInterviewStore } from "@/store/useInterviewStore";
import {
    Briefcase,
    ChevronRight,
    FileText,
    GraduationCap,
    MessageSquare,
    Plus,
    Settings,
    Sparkles,
    User
} from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";

const POSITION_OPTIONS = [
  "Java后端开发工程师",
  "前端开发工程师",
  "Python开发工程师",
  "全栈开发工程师",
  "数据分析师",
  "算法工程师",
];

const SUGGESTION_CARDS = [
  {
    icon: Sparkles,
    title: "开始模拟面试",
    desc: "上传简历，AI 面试官实时对话",
    action: "start",
  },
  {
    icon: GraduationCap,
    title: "面试技巧指导",
    desc: "了解面试流程与应答策略",
    action: "tips",
  },
  {
    icon: FileText,
    title: "简历优化建议",
    desc: "AI 分析简历亮点与不足",
    action: "resume",
  },
  {
    icon: MessageSquare,
    title: "常见面试问题",
    desc: "八股文高频考点速览",
    action: "faq",
  },
];

export default function HomePage() {
  const router = useRouter();
  const { resumeId, setSession, setInterviewing } = useInterviewStore();
  const [position, setPosition] = useState(POSITION_OPTIONS[0]);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState("");
  const [showSetup, setShowSetup] = useState(false);

  const handleStart = async () => {
    if (!resumeId) {
      setShowSetup(true);
      return;
    }

    setError("");
    setIsStarting(true);

    try {
      const result = await startInterview(resumeId, position);
      setSession(result.session_id);
      setInterviewing(true);
      router.push("/interview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建面试失败");
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div className="flex h-screen">
      {/* ========== 左侧栏 ========== */}
      <aside className="flex w-[260px] flex-shrink-0 flex-col border-r border-black/5 bg-surface-sidebar">
        {/* Logo 区域 */}
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

        {/* 新建面试按钮 */}
        <div className="px-3 mb-2">
          <button
            onClick={() => setShowSetup(true)}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-ink-primary transition-all hover:bg-surface-hover active:scale-[0.98]"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-700 text-white">
              <Plus className="h-3.5 w-3.5" />
            </div>
            新建面试
          </button>
        </div>

        {/* 分割线 */}
        <div className="mx-4 border-t border-black/5" />

        {/* 历史记录区 —— 空状态 */}
        <div className="flex-1 overflow-y-auto px-3 py-3">
          <p className="px-2 pb-2 text-[11px] font-medium uppercase tracking-wider text-ink-tertiary">
            历史记录
          </p>
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-2xl bg-surface-hover">
              <MessageSquare className="h-4.5 w-4.5 text-ink-tertiary" />
            </div>
            <p className="text-xs text-ink-tertiary">暂无面试记录</p>
            <p className="text-[11px] text-ink-disabled">开始一场面试吧</p>
          </div>
        </div>

        {/* 底部用户信息 */}
        <div className="border-t border-black/5 p-3">
          <div className="flex items-center gap-2.5 rounded-xl px-2.5 py-2 transition-colors hover:bg-surface-hover cursor-pointer">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-700/10">
              <User className="h-4 w-4 text-brand-700" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-ink-primary truncate">候选人</p>
              <p className="text-[11px] text-ink-tertiary">免费体验中</p>
            </div>
            <Settings className="h-4 w-4 text-ink-tertiary" />
          </div>
        </div>
      </aside>

      {/* ========== 右侧主区域 ========== */}
      <main className="flex flex-1 flex-col bg-surface-main">
        {/* 主区域：空状态 / 设置面板 */}
        <div className="flex flex-1 flex-col items-center justify-center px-8">
          {!showSetup ? (
            /* ===== 空状态（中心欢迎页）===== */
            <div className="w-full max-w-2xl animate-fade-in">
              {/* Avatar 区域 */}
              <div className="mb-8 flex flex-col items-center">
                <div className="relative mb-4">
                  <Image
                    src="/logo.png"
                    alt="AI 面试官"
                    width={80}
                    height={80}
                    className="animate-float rounded-3xl shadow-float"
                  />
                  {/* 在线状态小圆点 */}
                  <div className="absolute -bottom-0.5 -right-0.5 h-4 w-4 rounded-full border-2 border-white bg-emerald-400" />
                </div>
                <h2 className="mb-1.5 text-xl font-semibold text-ink-primary">
                  你好，我是小华
                </h2>
                <p className="text-sm text-ink-secondary">
                  华中师大 AI 面试官，帮你模拟真实面试场景
                </p>
              </div>

              {/* 建议卡片网格 */}
              <div className="grid grid-cols-2 gap-3">
                {SUGGESTION_CARDS.map((card) => (
                  <button
                    key={card.title}
                    onClick={() => {
                      if (card.action === "start") {
                        setShowSetup(true);
                      }
                    }}
                    className="group flex items-start gap-3 rounded-2xl border border-black/5 bg-surface-card p-4 text-left transition-all hover:border-brand-700/15 hover:shadow-card-hover active:scale-[0.98]"
                  >
                    <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-brand-700/8 text-brand-700 transition-colors group-hover:bg-brand-700/12">
                      <card.icon className="h-4.5 w-4.5" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink-primary">
                        {card.title}
                      </p>
                      <p className="mt-0.5 text-xs text-ink-tertiary leading-relaxed">
                        {card.desc}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* ===== 面试设置面板 ===== */
            <div className="w-full max-w-lg animate-slide-up">
              {/* 返回空状态 */}
              <button
                onClick={() => setShowSetup(false)}
                className="mb-6 flex items-center gap-1 text-sm text-ink-tertiary transition-colors hover:text-ink-primary"
              >
                ← 返回
              </button>

              <h2 className="mb-6 text-xl font-semibold text-ink-primary">
                准备开始面试
              </h2>

              {/* 步骤一：上传简历 */}
              <div className="mb-4 rounded-2xl border border-black/5 bg-surface-card p-5 transition-shadow hover:shadow-card">
                <div className="mb-3 flex items-center gap-2.5">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-700 text-[12px] font-bold text-white">
                    1
                  </div>
                  <h3 className="text-sm font-semibold text-ink-primary">
                    上传你的简历
                  </h3>
                </div>
                <ResumeUploader />
              </div>

              {/* 步骤二：选择岗位 */}
              <div className="mb-6 rounded-2xl border border-black/5 bg-surface-card p-5 transition-shadow hover:shadow-card">
                <div className="mb-3 flex items-center gap-2.5">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-700 text-[12px] font-bold text-white">
                    2
                  </div>
                  <h3 className="text-sm font-semibold text-ink-primary">
                    选择目标岗位
                  </h3>
                </div>
                <div className="flex items-center gap-2.5">
                  <Briefcase className="h-4 w-4 text-ink-tertiary" />
                  <select
                    value={position}
                    onChange={(e) => setPosition(e.target.value)}
                    className="flex-1 rounded-xl border border-black/8 bg-white px-3.5 py-2.5 text-sm text-ink-primary outline-none transition-colors focus:border-brand-700/40 focus:ring-2 focus:ring-brand-700/8"
                  >
                    {POSITION_OPTIONS.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* 开始面试按钮 */}
              <button
                onClick={handleStart}
                disabled={!resumeId || isStarting}
                className="flex w-full items-center justify-center gap-2 rounded-2xl bg-brand-700 py-3.5 text-sm font-semibold text-white shadow-float transition-all hover:bg-brand-800 hover:shadow-float-lg active:scale-[0.98] disabled:bg-ink-disabled disabled:shadow-none disabled:text-white/60"
              >
                {isStarting ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    正在准备面试...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    开始模拟面试
                    <ChevronRight className="h-4 w-4" />
                  </>
                )}
              </button>

              {error && (
                <p className="mt-3 text-center text-sm text-red-500">{error}</p>
              )}
            </div>
          )}
        </div>

        {/* 底部悬浮装饰输入框（首页装饰，不实际输入） */}
        {!showSetup && (
          <div className="px-8 pb-6">
            <div
              onClick={() => setShowSetup(true)}
              className="mx-auto flex max-w-2xl cursor-pointer items-center gap-3 rounded-3xl border border-black/6 bg-surface-elevated px-5 py-3.5 shadow-input transition-all hover:border-brand-700/20 hover:shadow-float"
            >
              <Sparkles className="h-4.5 w-4.5 text-ink-tertiary" />
              <span className="flex-1 text-sm text-ink-tertiary">
                上传简历，开始你的模拟面试...
              </span>
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-700 text-white transition-colors hover:bg-brand-800">
                <ChevronRight className="h-4 w-4" />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
