/**
 * 面试辅导页面 —— 答案对比 + 维度提升路径 + 整体提升计划
 */

"use client";

import { LoadingSpinner, CollapsibleSection } from "@/components";
import {
  SidebarHeader,
  SidebarNavGroup,
  SidebarDivider,
  SidebarFooter,
} from "@/components/SidebarNav";
import {
  generateCoaching,
  fetchCoaching,
  fetchReport,
  type CoachingResponse,
} from "@/lib/api";
import {
  BookOpen,
  Calendar,
  CheckCircle2,
  GraduationCap,
  Lightbulb,
  Target,
  TrendingUp,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

const DIMENSION_LABELS: Record<string, string> = {
  technical_depth: "技术深度",
  communication: "沟通表达",
  logic_thinking: "逻辑思维",
  project_experience: "项目经验",
  coding_ability: "编程能力",
};

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 80
      ? "bg-emerald-50 text-emerald-700"
      : score >= 60
      ? "bg-amber-50 text-amber-700"
      : "bg-red-50 text-red-600";
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${color}`}>
      {score}分
    </span>
  );
}

function ProgressBar({
  current,
  target,
}: {
  current: number;
  target: number;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-ink-tertiary w-6 text-right">{current}</span>
      <div className="flex-1 h-2 rounded-full bg-black/5 relative">
        <div
          className="h-full rounded-full bg-brand-700/30 absolute"
          style={{ width: `${target}%` }}
        />
        <div
          className="h-full rounded-full bg-brand-700 absolute transition-all duration-700"
          style={{ width: `${current}%` }}
        />
      </div>
      <span className="text-xs text-brand-700 font-medium w-6">{target}</span>
    </div>
  );
}

function CoachingContent() {
  const searchParams = useSearchParams();
  const sessionId = Number(searchParams.get("session_id"));

  const [coaching, setCoaching] = useState<CoachingResponse | null>(null);
  const [reportScore, setReportScore] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sessionId) {
      setError("缺少面试会话ID");
      setIsLoading(false);
      return;
    }

    const load = async () => {
      try {
        // 并行加载报告分数和辅导内容
        const [reportData, coachingData] = await Promise.all([
          fetchReport(sessionId).catch(() => null),
          fetchCoaching(sessionId),
        ]);

        if (reportData) {
          setReportScore((reportData as { overall_score?: number }).overall_score ?? null);
        }

        if (coachingData) {
          setCoaching(coachingData);
        } else {
          // 自动生成
          const generated = await generateCoaching(sessionId);
          setCoaching(generated);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载辅导内容失败");
      } finally {
        setIsLoading(false);
      }
    };

    load();
  }, [sessionId]);

  return (
    <div className="flex h-screen">
      {/* ========== 侧边栏 ========== */}
      <aside className="flex w-[260px] flex-shrink-0 flex-col border-r border-black/5 bg-surface-sidebar">
        <SidebarHeader />
        <SidebarDivider />
        <SidebarNavGroup currentPath="/coaching" />
        <SidebarDivider />

        {/* 会话信息 */}
        {sessionId > 0 && (
          <div className="px-4 py-3">
            <p className="text-[11px] font-medium text-ink-tertiary uppercase tracking-wider mb-2">
              会话信息
            </p>
            <div className="space-y-1.5 text-xs text-ink-secondary">
              <p>会话 #{sessionId}</p>
              {reportScore !== null && (
                <p>
                  面试得分：
                  <span className={`font-semibold ${reportScore >= 80 ? "text-emerald-600" : reportScore >= 60 ? "text-amber-600" : "text-red-500"}`}>
                    {reportScore}
                  </span>
                </p>
              )}
            </div>
          </div>
        )}

        <div className="flex-1" />
        <SidebarFooter />
      </aside>

      {/* ========== 主区域 ========== */}
      <main className="flex-1 overflow-y-auto bg-surface-main">
        {isLoading ? (
          <LoadingSpinner fullPage text="AI 正在生成面试辅导内容..." />
        ) : error ? (
          <div className="flex h-full flex-col items-center justify-center">
            <p className="text-sm text-red-500">{error}</p>
          </div>
        ) : coaching ? (
          <div className="mx-auto max-w-3xl px-8 py-8">
            {/* 页头 */}
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-1">
                <GraduationCap className="h-5 w-5 text-brand-700" />
                <h1 className="text-lg font-semibold text-ink-primary">面试辅导</h1>
              </div>
              <p className="text-xs text-ink-tertiary">
                会话 #{sessionId} · 基于你的面试表现生成个性化辅导
              </p>
            </div>

            {/* ===== 逐题辅导 ===== */}
            {coaching.question_coaching?.length > 0 && (
              <div className="mb-6">
                <h2 className="text-sm font-semibold text-ink-primary mb-3 flex items-center gap-2">
                  <Target className="h-4 w-4 text-brand-700" />
                  逐题辅导
                </h2>
                <div className="space-y-4">
                  {coaching.question_coaching.map((q, i) => (
                    <div
                      key={i}
                      className="rounded-2xl border border-black/5 bg-surface-card overflow-hidden"
                    >
                      {/* 题目 */}
                      <div className="flex items-center justify-between px-5 py-3 border-b border-black/5 bg-black/[0.01]">
                        <p className="text-sm font-medium text-ink-primary flex-1">
                          <span className="text-ink-tertiary mr-2">Q{i + 1}</span>
                          {q.question}
                        </p>
                        <ScoreBadge score={q.score} />
                      </div>

                      {/* 双栏对比 */}
                      <div className="grid grid-cols-2 divide-x divide-black/5">
                        <div className="p-4">
                          <p className="text-[11px] font-medium text-ink-tertiary uppercase tracking-wider mb-2">
                            你的回答
                          </p>
                          <p className="text-xs text-ink-secondary leading-relaxed">
                            {q.user_answer_summary}
                          </p>
                        </div>
                        <div className="p-4 bg-emerald-50/30">
                          <p className="text-[11px] font-medium text-emerald-700 uppercase tracking-wider mb-2">
                            理想答案
                          </p>
                          <p className="text-xs text-ink-secondary leading-relaxed">
                            {q.ideal_answer}
                          </p>
                        </div>
                      </div>

                      {/* 差距分析 + 改进建议 */}
                      <div className="border-t border-black/5 px-5 py-3 space-y-2">
                        <div>
                          <p className="text-[11px] font-medium text-ink-tertiary mb-1">差距分析</p>
                          <p className="text-xs text-ink-secondary">{q.gap_analysis}</p>
                        </div>
                        {q.improvement_tips?.length > 0 && (
                          <div>
                            <p className="text-[11px] font-medium text-ink-tertiary mb-1">改进要点</p>
                            <ul className="space-y-1">
                              {q.improvement_tips.map((tip, j) => (
                                <li key={j} className="flex items-start gap-1.5 text-xs text-ink-secondary">
                                  <Lightbulb className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
                                  {tip}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ===== 维度提升路径 ===== */}
            {coaching.dimension_coaching && (
              <div className="mb-6">
                <h2 className="text-sm font-semibold text-ink-primary mb-3 flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-brand-700" />
                  维度提升路径
                </h2>
                <div className="space-y-2">
                  {Object.entries(coaching.dimension_coaching).map(([key, dim]) => (
                    <CollapsibleSection
                      key={key}
                      title={`${DIMENSION_LABELS[key] || key}  ${dim.current_score} → ${dim.target_score}`}
                      icon={TrendingUp}
                    >
                      <div className="space-y-3">
                        <ProgressBar current={dim.current_score} target={dim.target_score} />

                        {dim.roadmap?.length > 0 && (
                          <div>
                            <p className="text-xs font-medium text-ink-tertiary mb-1.5">学习路径</p>
                            <ul className="space-y-1.5">
                              {dim.roadmap.map((step, j) => (
                                <li key={j} className="flex items-start gap-2 text-xs text-ink-secondary">
                                  <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-brand-700/10 text-[9px] font-bold text-brand-700">
                                    {j + 1}
                                  </span>
                                  {step}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {dim.resources?.length > 0 && (
                          <div>
                            <p className="text-xs font-medium text-ink-tertiary mb-1.5">推荐资源</p>
                            <ul className="space-y-1">
                              {dim.resources.map((r, j) => (
                                <li key={j} className="flex items-start gap-1.5 text-xs text-ink-secondary">
                                  <BookOpen className="h-3.5 w-3.5 text-blue-500 mt-0.5 shrink-0" />
                                  {r}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </CollapsibleSection>
                  ))}
                </div>
              </div>
            )}

            {/* ===== 整体提升计划 ===== */}
            {coaching.overall_improvement_plan && (
              <div>
                <h2 className="text-sm font-semibold text-ink-primary mb-3 flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-brand-700" />
                  整体提升计划
                </h2>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { key: "short_term", label: "短期 (1周)", color: "emerald" },
                    { key: "medium_term", label: "中期 (1个月)", color: "blue" },
                    { key: "long_term", label: "长期 (3个月)", color: "purple" },
                  ].map(({ key, label, color }) => {
                    const items =
                      coaching.overall_improvement_plan[
                        key as keyof typeof coaching.overall_improvement_plan
                      ] || [];
                    return (
                      <div
                        key={key}
                        className="rounded-2xl border border-black/5 bg-surface-card p-4"
                      >
                        <div className="flex items-center gap-1.5 mb-3">
                          <CheckCircle2
                            className={`h-4 w-4 ${
                              color === "emerald"
                                ? "text-emerald-600"
                                : color === "blue"
                                ? "text-blue-600"
                                : "text-purple-600"
                            }`}
                          />
                          <h3 className="text-xs font-semibold text-ink-primary">
                            {label}
                          </h3>
                        </div>
                        <ul className="space-y-1.5">
                          {items.map((item: string, i: number) => (
                            <li
                              key={i}
                              className="text-xs text-ink-secondary leading-relaxed"
                            >
                              {i + 1}. {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </main>
    </div>
  );
}

export default function CoachingPage() {
  return (
    <Suspense fallback={<LoadingSpinner fullPage />}>
      <CoachingContent />
    </Suspense>
  );
}
