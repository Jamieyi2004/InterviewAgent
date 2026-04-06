/**
 * 管理后台 — 数据分析仪表盘（从 /dashboard 移入）
 */

"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Zap, Target, Brain, TrendingUp, AlertTriangle, CheckCircle2,
  DollarSign, Activity, Hash, MessageSquare, Quote,
} from "lucide-react";
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  LineChart, Line, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ResponsiveContainer, Legend,
} from "recharts";

import { fetchTokenUsage, fetchEvaluation, fetchInsights } from "@/lib/api";
import { SidebarHeader, AdminSidebarNavGroup, SidebarDivider, SidebarFooter } from "@/components/SidebarNav";
import AdminGuard from "@/components/AdminGuard";
import LoadingSpinner from "@/components/LoadingSpinner";
import { STAGE_LABELS } from "@/lib/constants";

const PIE_COLORS = ["#005A4E", "#10B981", "#34D399", "#6EE7B7", "#A7F3D0", "#D1FAE5"];

function DashboardContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const sessionId = Number(searchParams.get("session_id"));

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [tokenData, setTokenData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [evalData, setEvalData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [insightData, setInsightData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sessionId) { setError("缺少 session_id 参数"); setLoading(false); return; }
    setLoading(true);
    Promise.all([fetchTokenUsage(sessionId), fetchEvaluation(sessionId), fetchInsights(sessionId)])
      .then(([t, e, i]) => { setTokenData(t); setEvalData(e); setInsightData(i); if (!t && !e && !i) setError("该会话暂无分析数据（仅活跃会话可用）"); })
      .catch((err) => setError(err instanceof Error ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, [sessionId]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const stagePieData = tokenData?.stage_breakdown ? Object.entries(tokenData.stage_breakdown).map(([stage, data]: [string, any]) => ({ name: STAGE_LABELS[stage] || stage, value: data.total_tokens, cost: data.cost_usd })) : [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const callerBarData = tokenData?.caller_breakdown ? Object.entries(tokenData.caller_breakdown).map(([caller, data]: [string, any]) => ({ name: caller, input: data.input_tokens, output: data.output_tokens })) : [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const scoreLineData = evalData?.evaluations ? evalData.evaluations.map((e: any) => ({ turn: `第${e.turn}轮`, score: e.score, stage: STAGE_LABELS[e.stage] || e.stage })) : [];
  const DIMENSION_LABELS: Record<string, string> = { "Technical Accuracy": "技术准确性", "Answer Completeness": "回答完整度", "Expression Clarity": "表达清晰度", "Thinking Depth": "思维深度" };
  const latestEval = evalData?.evaluations?.[evalData.evaluations.length - 1];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const radarData = latestEval?.dimensions ? latestEval.dimensions.map((d: any) => ({ dimension: DIMENSION_LABELS[d.dimension] || d.dimension, score: d.score, fullMark: 100 })) : [];

  return (
    <AdminGuard>
    <div className="flex h-screen">
      <aside className="flex w-[260px] flex-shrink-0 flex-col border-r border-black/5 bg-surface-sidebar">
        <SidebarHeader />
        <SidebarDivider />
        <AdminSidebarNavGroup currentPath="/admin/dashboard" />
        <SidebarDivider />
        <div className="flex-1 overflow-y-auto px-4 py-3">
          {sessionId > 0 && (
            <>
              <p className="mb-3 text-xs font-medium text-ink-tertiary">当前会话</p>
              <div className="rounded-xl bg-white p-3 text-center shadow-card">
                <p className="text-lg font-bold text-brand-700">#{sessionId}</p>
                <p className="text-xs text-ink-tertiary">面试会话 ID</p>
              </div>
              <div className="mt-4 flex flex-col gap-1">
                <button onClick={() => router.push(`/admin/sessions/${sessionId}`)} className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs text-ink-secondary hover:bg-surface-hover">
                  <MessageSquare className="h-3.5 w-3.5" /> 查看对话记录
                </button>
              </div>
            </>
          )}
        </div>
        <SidebarFooter />
      </aside>

      <main className="flex flex-1 flex-col overflow-auto bg-surface-main">
        <div className="border-b border-black/5 px-8 py-5">
          <h2 className="text-lg font-semibold text-ink-primary">数据分析仪表盘</h2>
          <p className="mt-0.5 text-xs text-ink-tertiary">会话 #{sessionId} 的面试数据分析</p>
        </div>

        <div className="flex-1 px-8 py-6">
          {loading ? (
            <LoadingSpinner text="加载分析数据..." />
          ) : error && !tokenData && !evalData && !insightData ? (
            <div className="flex flex-col items-center justify-center py-20">
              <Activity className="mb-3 h-12 w-12 text-ink-disabled" />
              <p className="text-sm text-ink-tertiary">{error}</p>
              <button onClick={() => router.push("/admin/sessions")} className="mt-4 rounded-xl bg-brand-700 px-4 py-2 text-sm text-white hover:bg-brand-800">返回会话列表</button>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-5">
              {/* Token 消耗 */}
              <div className="rounded-2xl border border-black/5 bg-white p-5">
                <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink-primary"><Zap className="h-4 w-4 text-amber-500" /> Token 消耗分析</h3>
                {tokenData?.summary ? (<>
                  <div className="mb-4 grid grid-cols-3 gap-3">
                    <MiniCard icon={Hash} label="总 Token" value={tokenData.summary.total_tokens?.toLocaleString() || "0"} color="text-blue-600" />
                    <MiniCard icon={DollarSign} label="总费用" value={`$${tokenData.summary.total_cost_usd?.toFixed(4) || "0"}`} color="text-emerald-600" />
                    <MiniCard icon={Activity} label="API 调用" value={tokenData.summary.total_api_calls || 0} color="text-purple-600" />
                  </div>
                  {stagePieData.length > 0 && (<div className="mb-4"><p className="mb-2 text-xs text-ink-tertiary">阶段 Token 分布</p><ResponsiveContainer width="100%" height={200}><PieChart><Pie data={stagePieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`} labelLine={false} fontSize={11}>{stagePieData.map((_, idx) => (<Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />))}</Pie><Tooltip formatter={(v: any) => v?.toLocaleString()} /></PieChart></ResponsiveContainer></div>)}
                  {callerBarData.length > 0 && (<div><p className="mb-2 text-xs text-ink-tertiary">模块调用分布</p><ResponsiveContainer width="100%" height={180}><BarChart data={callerBarData} layout="vertical"><CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" /><XAxis type="number" fontSize={10} /><YAxis type="category" dataKey="name" fontSize={10} width={90} /><Tooltip /><Bar dataKey="input" stackId="a" fill="#005A4E" name="输入" /><Bar dataKey="output" stackId="a" fill="#34D399" name="输出" /><Legend fontSize={11} /></BarChart></ResponsiveContainer></div>)}
                </>) : <EmptyPanel />}
              </div>

              {/* 评估得分 */}
              <div className="rounded-2xl border border-black/5 bg-white p-5">
                <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink-primary"><Target className="h-4 w-4 text-brand-700" /> 评估得分分析</h3>
                {evalData?.summary ? (<>
                  <div className="mb-4 grid grid-cols-3 gap-3">
                    <MiniCard icon={TrendingUp} label="平均分" value={evalData.summary.average_score?.toFixed(1) || "—"} color="text-brand-700" />
                    <MiniCard icon={Target} label="最新评语" value={evalData.summary.latest_verdict || "—"} color="text-amber-600" />
                    <MiniCard icon={Hash} label="评估轮次" value={evalData.summary.turns_evaluated || 0} color="text-blue-600" />
                  </div>
                  {scoreLineData.length > 0 && (<div className="mb-4"><p className="mb-2 text-xs text-ink-tertiary">逐轮得分趋势</p><ResponsiveContainer width="100%" height={180}><LineChart data={scoreLineData}><CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" /><XAxis dataKey="turn" fontSize={10} /><YAxis domain={[0, 100]} fontSize={10} /><Tooltip /><Line type="monotone" dataKey="score" stroke="#005A4E" strokeWidth={2} dot={{ r: 4, fill: "#005A4E" }} name="得分" /></LineChart></ResponsiveContainer></div>)}
                  {radarData.length > 0 && (<div><p className="mb-2 text-xs text-ink-tertiary">维度雷达图</p><ResponsiveContainer width="100%" height={200}><RadarChart data={radarData}><PolarGrid stroke="#e5e7eb" /><PolarAngleAxis dataKey="dimension" fontSize={10} /><PolarRadiusAxis angle={90} domain={[0, 100]} fontSize={9} tick={false} /><Radar dataKey="score" stroke="#005A4E" fill="#005A4E" fillOpacity={0.2} name="得分" /><Tooltip /></RadarChart></ResponsiveContainer></div>)}
                </>) : <EmptyPanel />}
              </div>

              {/* 优缺点 */}
              <div className="rounded-2xl border border-black/5 bg-white p-5">
                <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink-primary"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> 优势与不足</h3>
                {evalData?.summary ? (<div className="grid grid-cols-2 gap-4"><div><p className="mb-2 text-xs font-medium text-emerald-600">优势</p><div className="flex flex-col gap-1.5">{(evalData.summary.all_strengths || []).length > 0 ? evalData.summary.all_strengths.map((s: string, i: number) => (<div key={i} className="flex items-start gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-700"><CheckCircle2 className="mt-0.5 h-3 w-3 flex-shrink-0" /><span>{s}</span></div>)) : <p className="text-xs text-ink-tertiary">暂无数据</p>}</div></div><div><p className="mb-2 text-xs font-medium text-amber-600">不足</p><div className="flex flex-col gap-1.5">{(evalData.summary.all_weaknesses || []).length > 0 ? evalData.summary.all_weaknesses.map((w: string, i: number) => (<div key={i} className="flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700"><AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" /><span>{w}</span></div>)) : <p className="text-xs text-ink-tertiary">暂无数据</p>}</div></div></div>) : <EmptyPanel />}
              </div>

              {/* 候选人洞察 */}
              <div className="rounded-2xl border border-black/5 bg-white p-5">
                <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink-primary"><Brain className="h-4 w-4 text-purple-500" /> 候选人洞察</h3>
                {insightData?.insights ? (<div className="flex flex-col gap-4">
                  <TagGroup title="技术信号" items={insightData.insights.technical_signals} className="bg-blue-50 text-blue-700" />
                  <TagGroup title="知识盲区" items={insightData.insights.knowledge_gaps} className="bg-red-50 text-red-600" />
                  <TagGroup title="思维模式" items={insightData.insights.thinking_patterns} className="bg-purple-50 text-purple-700" />
                  <TagGroup title="沟通风格" items={insightData.insights.communication_style} className="bg-cyan-50 text-cyan-700" />
                  {insightData.insights.notable_quotes?.length > 0 && (<div><p className="mb-1.5 text-[10px] font-medium text-ink-tertiary flex items-center gap-1"><Quote className="h-3 w-3" /> 候选人原话</p>{insightData.insights.notable_quotes.slice(0, 3).map((q: string, i: number) => (<blockquote key={i} className="mb-1.5 border-l-2 border-brand-700/20 pl-2 text-xs italic text-ink-secondary">&ldquo;{q}&rdquo;</blockquote>))}</div>)}
                  {insightData.insights.strategy_suggestions?.length > 0 && (<div><p className="mb-1.5 text-[10px] font-medium text-ink-tertiary">策略建议</p><div className="flex flex-col gap-1">{insightData.insights.strategy_suggestions.map((s: string, i: number) => (<p key={i} className="text-xs text-ink-secondary">{i + 1}. {s}</p>))}</div></div>)}
                </div>) : <EmptyPanel />}
              </div>
            </div>
          )}

          {tokenData?.optimization_suggestions?.length > 0 && (<div className="mt-5 rounded-2xl border border-black/5 bg-white p-5"><h3 className="mb-3 text-sm font-semibold text-ink-primary">优化建议</h3><div className="flex flex-col gap-2">{tokenData.optimization_suggestions.map((s: string, i: number) => (<p key={i} className="text-xs text-ink-secondary">{i + 1}. {s}</p>))}</div></div>)}
        </div>
      </main>
    </div>
    </AdminGuard>
  );
}

export default function AdminDashboardPage() {
  return (
    <Suspense fallback={<LoadingSpinner fullPage text="加载仪表盘..." />}>
      <DashboardContent />
    </Suspense>
  );
}

function MiniCard({ icon: Icon, label, value, color }: { icon: typeof Hash; label: string; value: string | number; color: string }) {
  return (<div className="rounded-xl bg-surface-card p-3 text-center"><Icon className={`mx-auto mb-1 h-4 w-4 ${color}`} /><p className="text-base font-semibold text-ink-primary">{value}</p><p className="text-[10px] text-ink-tertiary">{label}</p></div>);
}

function TagGroup({ title, items, className }: { title: string; items: string[]; className: string }) {
  if (!items || items.length === 0) return null;
  return (<div><p className="mb-1.5 text-[10px] font-medium text-ink-tertiary">{title}</p><div className="flex flex-wrap gap-1">{items.map((item, i) => (<span key={i} className={`rounded-full px-2 py-0.5 text-[10px] ${className}`}>{item}</span>))}</div></div>);
}

function EmptyPanel() {
  return (<div className="flex items-center justify-center py-8"><p className="text-xs text-ink-tertiary">暂无数据（仅活跃会话可用）</p></div>);
}
