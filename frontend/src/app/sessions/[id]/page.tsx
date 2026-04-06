/**
 * 会话详情 —— 对话回放 + 评估摘要 + 洞察分析
 *
 * 布局：左侧栏 (260px) + 右侧滚动内容
 */

"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  BarChart3,
  FileText,
  Clock,
  MessageSquare,
  Zap,
  Brain,
  Target,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Quote,
} from "lucide-react";

import {
  fetchSessionDetail,
  fetchEvaluation,
  fetchInsights,
  fetchTokenUsage,
  type SessionDetail,
} from "@/lib/api";
import { SidebarHeader, SidebarNavGroup, SidebarDivider, SidebarFooter } from "@/components/SidebarNav";
import StatusBadge from "@/components/StatusBadge";
import CollapsibleSection from "@/components/CollapsibleSection";
import ConversationReplay from "@/components/ConversationReplay";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = Number(params.id);

  const [detail, setDetail] = useState<SessionDetail | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [evaluation, setEvaluation] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [insights, setInsights] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [tokenUsage, setTokenUsage] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    Promise.all([
      fetchSessionDetail(sessionId),
      fetchEvaluation(sessionId).catch(() => null),
      fetchInsights(sessionId).catch(() => null),
      fetchTokenUsage(sessionId).catch(() => null),
    ])
      .then(([d, e, i, t]) => {
        setDetail(d);
        setEvaluation(e);
        setInsights(i);
        setTokenUsage(t);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return <LoadingSpinner fullPage text="加载会话详情..." />;
  if (error || !detail) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-sm text-red-500">{error || "会话不存在"}</p>
      </div>
    );
  }

  const { session, messages, report } = detail;
  const duration =
    session.created_at && session.ended_at
      ? Math.round(
          (new Date(session.ended_at).getTime() - new Date(session.created_at).getTime()) / 60000
        )
      : null;

  return (
    <div className="flex h-screen">
      {/* 侧边栏 */}
      <aside className="flex w-[260px] flex-shrink-0 flex-col border-r border-black/5 bg-surface-sidebar">
        <SidebarHeader />
        <SidebarDivider />

        {/* 返回按钮 */}
        <div className="px-3 py-1">
          <button
            onClick={() => router.push("/sessions")}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-ink-secondary transition-all hover:bg-surface-hover"
          >
            <ArrowLeft className="h-4 w-4" />
            返回会话列表
          </button>
        </div>

        <SidebarDivider />

        {/* 会话信息 */}
        <div className="flex-1 overflow-y-auto px-4 py-3">
          <p className="mb-3 text-xs font-medium text-ink-tertiary">会话信息</p>
          <div className="flex flex-col gap-3">
            <InfoRow label="候选人" value={session.candidate_name} />
            <InfoRow label="目标岗位" value={session.position} />
            <InfoRow
              label="状态"
              value={<StatusBadge status={session.status} />}
            />
            {duration !== null && (
              <InfoRow label="面试时长" value={`${duration} 分钟`} />
            )}
            <InfoRow label="消息数" value={`${messages.length} 条`} />
            {report && (
              <InfoRow
                label="综合评分"
                value={
                  <span
                    className={`text-sm font-semibold ${
                      report.overall_score >= 80
                        ? "text-emerald-600"
                        : report.overall_score >= 60
                        ? "text-amber-600"
                        : "text-red-500"
                    }`}
                  >
                    {report.overall_score}
                  </span>
                }
              />
            )}
            <InfoRow
              label="创建时间"
              value={
                session.created_at
                  ? new Date(session.created_at).toLocaleString("zh-CN")
                  : "—"
              }
            />
          </div>

          <div className="mt-6 flex flex-col gap-2">
            <button
              onClick={() => router.push(`/dashboard?session_id=${sessionId}`)}
              className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-ink-secondary transition-all hover:bg-surface-hover"
            >
              <BarChart3 className="h-4 w-4" />
              数据分析仪表盘
            </button>
            {report && (
              <button
                onClick={() => router.push(`/report?session_id=${sessionId}`)}
                className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-ink-secondary transition-all hover:bg-surface-hover"
              >
                <FileText className="h-4 w-4" />
                查看评估报告
              </button>
            )}
          </div>
        </div>

        <SidebarFooter />
      </aside>

      {/* 主区域 */}
      <main className="flex flex-1 flex-col overflow-auto bg-surface-main">
        {/* 顶部 */}
        <div className="border-b border-black/5 px-8 py-5">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-ink-primary">
              {session.candidate_name} — {session.position}
            </h2>
            <StatusBadge status={session.status} />
          </div>
          <div className="mt-1.5 flex items-center gap-4 text-xs text-ink-tertiary">
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {session.created_at
                ? new Date(session.created_at).toLocaleString("zh-CN")
                : "—"}
            </span>
            <span className="flex items-center gap-1">
              <MessageSquare className="h-3.5 w-3.5" />
              {messages.length} 条消息
            </span>
            {duration !== null && (
              <span className="flex items-center gap-1">
                <Zap className="h-3.5 w-3.5" />
                {duration} 分钟
              </span>
            )}
          </div>
        </div>

        {/* 内容区 */}
        <div className="mx-auto w-full max-w-4xl px-8 py-6">
          <div className="flex flex-col gap-5">
            {/* 对话回放 */}
            <CollapsibleSection title="对话回放" icon={MessageSquare} defaultOpen={true}>
              <ConversationReplay messages={messages} />
            </CollapsibleSection>

            {/* 评估摘要 */}
            {evaluation && evaluation.summary && (
              <CollapsibleSection title="实时评估摘要" icon={Target} defaultOpen={false}>
                <div className="flex flex-col gap-4">
                  <div className="flex items-center gap-6">
                    <div>
                      <p className="text-xs text-ink-tertiary">平均分</p>
                      <p className="text-2xl font-bold text-ink-primary">
                        {evaluation.summary.average_score?.toFixed(1) || "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-ink-tertiary">最新评语</p>
                      <p className="text-sm font-medium text-ink-primary">
                        {evaluation.summary.latest_verdict || "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-ink-tertiary">评估轮次</p>
                      <p className="text-sm font-medium text-ink-primary">
                        {evaluation.summary.turns_evaluated || 0}
                      </p>
                    </div>
                  </div>

                  {evaluation.summary.all_strengths?.length > 0 && (
                    <div>
                      <p className="mb-2 text-xs font-medium text-emerald-600 flex items-center gap-1">
                        <CheckCircle2 className="h-3.5 w-3.5" /> 优势
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {evaluation.summary.all_strengths.map((s: string, i: number) => (
                          <span key={i} className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs text-emerald-700">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {evaluation.summary.all_weaknesses?.length > 0 && (
                    <div>
                      <p className="mb-2 text-xs font-medium text-amber-600 flex items-center gap-1">
                        <AlertTriangle className="h-3.5 w-3.5" /> 不足
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {evaluation.summary.all_weaknesses.map((w: string, i: number) => (
                          <span key={i} className="rounded-full bg-amber-50 px-2.5 py-1 text-xs text-amber-700">
                            {w}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CollapsibleSection>
            )}

            {/* Token 用量 */}
            {tokenUsage && tokenUsage.summary && (
              <CollapsibleSection title="Token 消耗" icon={Zap} defaultOpen={false}>
                <div className="grid grid-cols-4 gap-4">
                  <MiniStat label="总 Token" value={tokenUsage.summary.total_tokens?.toLocaleString() || "0"} />
                  <MiniStat label="API 调用" value={tokenUsage.summary.total_api_calls || 0} />
                  <MiniStat
                    label="总费用"
                    value={`$${tokenUsage.summary.total_cost_usd?.toFixed(4) || "0"}`}
                  />
                  <MiniStat
                    label="耗时"
                    value={`${(tokenUsage.summary.duration_seconds / 60)?.toFixed(1) || "0"} 分钟`}
                  />
                </div>
              </CollapsibleSection>
            )}

            {/* 候选人洞察 */}
            {insights && insights.insights && (
              <CollapsibleSection title="候选人洞察" icon={Brain} defaultOpen={false}>
                <div className="flex flex-col gap-4">
                  <InsightGroup
                    icon={TrendingUp}
                    title="技术信号"
                    items={insights.insights.technical_signals}
                    tagClass="bg-blue-50 text-blue-700"
                  />
                  <InsightGroup
                    icon={AlertTriangle}
                    title="知识盲区"
                    items={insights.insights.knowledge_gaps}
                    tagClass="bg-red-50 text-red-600"
                  />
                  <InsightGroup
                    icon={Brain}
                    title="思维模式"
                    items={insights.insights.thinking_patterns}
                    tagClass="bg-purple-50 text-purple-700"
                  />
                  <InsightGroup
                    icon={MessageSquare}
                    title="沟通风格"
                    items={insights.insights.communication_style}
                    tagClass="bg-cyan-50 text-cyan-700"
                  />

                  {insights.insights.notable_quotes?.length > 0 && (
                    <div>
                      <p className="mb-2 text-xs font-medium text-ink-secondary flex items-center gap-1">
                        <Quote className="h-3.5 w-3.5" /> 候选人原话
                      </p>
                      <div className="flex flex-col gap-2">
                        {insights.insights.notable_quotes.map((q: string, i: number) => (
                          <blockquote
                            key={i}
                            className="border-l-2 border-brand-700/30 pl-3 text-sm italic text-ink-secondary"
                          >
                            &ldquo;{q}&rdquo;
                          </blockquote>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CollapsibleSection>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

/* ---------- 辅助组件 ---------- */

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-ink-tertiary">{label}</span>
      <span className="text-xs text-ink-primary">{value}</span>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl bg-surface-card p-3 text-center">
      <p className="text-lg font-semibold text-ink-primary">{value}</p>
      <p className="text-[10px] text-ink-tertiary">{label}</p>
    </div>
  );
}

function InsightGroup({
  icon: Icon,
  title,
  items,
  tagClass,
}: {
  icon: typeof TrendingUp;
  title: string;
  items: string[];
  tagClass: string;
}) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <p className="mb-2 text-xs font-medium text-ink-secondary flex items-center gap-1">
        <Icon className="h-3.5 w-3.5" /> {title}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, i) => (
          <span key={i} className={`rounded-full px-2.5 py-1 text-xs ${tagClass}`}>
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
