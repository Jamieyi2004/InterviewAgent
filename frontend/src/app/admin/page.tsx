/**
 * 后台管理 —— 系统概览 / 人设管理 / 技能概览 / 近期活动 / 岗位分布
 *
 * 布局：左侧栏 (260px) + 右侧内容区
 */

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  MessageSquare,
  FileText,
  Activity,
  Star,
  Users,
  Zap,
  Shield,
  Gauge,
  Clock,
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

import { fetchAdminStats, fetchPersonas, fetchSkills, type AdminStats } from "@/lib/api";
import { SidebarHeader, SidebarNavGroup, SidebarDivider, SidebarFooter } from "@/components/SidebarNav";
import StatCard from "@/components/StatCard";
import StatusBadge from "@/components/StatusBadge";
import LoadingSpinner from "@/components/LoadingSpinner";
import { STAGE_LABELS } from "@/lib/constants";

const STRICTNESS_LABELS: Record<string, { label: string; color: string }> = {
  lenient: { label: "宽松", color: "bg-green-50 text-green-700" },
  balanced: { label: "均衡", color: "bg-blue-50 text-blue-700" },
  strict: { label: "严格", color: "bg-red-50 text-red-700" },
};

const AGGRESSIVENESS_LABELS: Record<string, { label: string; color: string }> = {
  low: { label: "温和", color: "bg-green-50 text-green-700" },
  medium: { label: "适中", color: "bg-blue-50 text-blue-700" },
  high: { label: "积极", color: "bg-amber-50 text-amber-700" },
  very_high: { label: "强势", color: "bg-red-50 text-red-700" },
};

export default function AdminPage() {
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [personas, setPersonas] = useState<any[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [skills, setSkills] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchAdminStats(),
      fetchPersonas(),
      fetchSkills(),
    ])
      .then(([s, p, sk]) => {
        setStats(s);
        setPersonas(p.personas || []);
        setSkills(sk.skills || []);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, []);

  const positionData = stats
    ? Object.entries(stats.position_distribution).map(([pos, count]) => ({
        name: pos.length > 8 ? pos.slice(0, 8) + "..." : pos,
        fullName: pos,
        count,
      }))
    : [];

  return (
    <div className="flex h-screen">
      {/* 侧边栏 */}
      <aside className="flex w-[260px] flex-shrink-0 flex-col border-r border-black/5 bg-surface-sidebar">
        <SidebarHeader />
        <SidebarDivider />
        <SidebarNavGroup currentPath="/admin" />
        <SidebarDivider />

        <div className="flex-1 overflow-y-auto px-4 py-3">
          <p className="mb-3 text-xs font-medium text-ink-tertiary">系统信息</p>
          <div className="flex flex-col gap-2 text-xs text-ink-secondary">
            <div className="flex justify-between">
              <span>版本</span>
              <span className="text-ink-primary">v0.2.0-enhanced</span>
            </div>
            <div className="flex justify-between">
              <span>人设数</span>
              <span className="text-ink-primary">{personas.length}</span>
            </div>
            <div className="flex justify-between">
              <span>技能数</span>
              <span className="text-ink-primary">{skills.length}</span>
            </div>
          </div>
        </div>

        <SidebarFooter />
      </aside>

      {/* 主区域 */}
      <main className="flex flex-1 flex-col overflow-auto bg-surface-main">
        <div className="border-b border-black/5 px-8 py-5">
          <h2 className="text-lg font-semibold text-ink-primary">后台管理</h2>
          <p className="mt-0.5 text-xs text-ink-tertiary">系统概览、面试官人设与技能管理</p>
        </div>

        <div className="flex-1 px-8 py-6">
          {loading ? (
            <LoadingSpinner text="加载管理数据..." />
          ) : error ? (
            <div className="py-12 text-center text-sm text-red-500">{error}</div>
          ) : stats ? (
            <div className="flex flex-col gap-6">
              {/* 概览卡片 */}
              <div className="grid grid-cols-4 gap-4">
                <StatCard
                  icon={MessageSquare}
                  label="总面试次数"
                  value={stats.total_sessions}
                  subtext={`${stats.active_sessions} 进行中 / ${stats.completed_sessions} 已完成`}
                />
                <StatCard
                  icon={FileText}
                  label="总简历数"
                  value={stats.total_resumes}
                  colorClass="text-blue-600"
                />
                <StatCard
                  icon={Activity}
                  label="总消息数"
                  value={stats.total_messages}
                  colorClass="text-purple-600"
                />
                <StatCard
                  icon={Star}
                  label="平均评分"
                  value={stats.avg_score !== null ? stats.avg_score : "—"}
                  subtext={stats.total_reports > 0 ? `${stats.total_reports} 份报告` : "暂无报告"}
                  colorClass="text-amber-500"
                />
              </div>

              {/* 人设 + 技能 */}
              <div className="grid grid-cols-2 gap-5">
                {/* 人设管理 */}
                <div className="rounded-2xl border border-black/5 bg-white p-5">
                  <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink-primary">
                    <Users className="h-4 w-4 text-brand-700" />
                    面试官人设
                    <span className="ml-auto text-xs font-normal text-ink-tertiary">
                      {personas.length} 个
                    </span>
                  </h3>
                  {personas.length === 0 ? (
                    <p className="py-4 text-center text-xs text-ink-tertiary">暂无人设配置</p>
                  ) : (
                    <div className="flex flex-col gap-3">
                      {personas.map((p, i) => (
                        <div
                          key={i}
                          className="rounded-xl border border-black/5 bg-surface-card p-4 transition-shadow hover:shadow-card-hover"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="text-sm font-medium text-ink-primary">{p.name}</h4>
                            <div className="flex gap-1.5">
                              {p.evaluation_strictness && (
                                <span
                                  className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                                    STRICTNESS_LABELS[p.evaluation_strictness]?.color || "bg-gray-50 text-gray-600"
                                  }`}
                                >
                                  {STRICTNESS_LABELS[p.evaluation_strictness]?.label || p.evaluation_strictness}
                                </span>
                              )}
                              {p.follow_up_aggressiveness && (
                                <span
                                  className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                                    AGGRESSIVENESS_LABELS[p.follow_up_aggressiveness]?.color || "bg-gray-50 text-gray-600"
                                  }`}
                                >
                                  追问: {AGGRESSIVENESS_LABELS[p.follow_up_aggressiveness]?.label || p.follow_up_aggressiveness}
                                </span>
                              )}
                            </div>
                          </div>
                          <p className="text-xs text-ink-secondary">{p.style}</p>
                          {p.description && (
                            <p className="mt-1 text-xs text-ink-tertiary">{p.description}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 技能概览 */}
                <div className="rounded-2xl border border-black/5 bg-white p-5">
                  <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink-primary">
                    <Zap className="h-4 w-4 text-amber-500" />
                    面试技能
                    <span className="ml-auto text-xs font-normal text-ink-tertiary">
                      {skills.length} 个
                    </span>
                  </h3>
                  {skills.length === 0 ? (
                    <p className="py-4 text-center text-xs text-ink-tertiary">暂无技能配置</p>
                  ) : (
                    <div className="flex flex-col gap-3">
                      {skills.map((sk, i) => (
                        <div
                          key={i}
                          className="rounded-xl border border-black/5 bg-surface-card p-4 transition-shadow hover:shadow-card-hover"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="text-sm font-medium text-ink-primary">{sk.name}</h4>
                            <div className="flex gap-1">
                              {sk.is_concurrent_safe && (
                                <span className="rounded-full bg-green-50 px-2 py-0.5 text-[10px] text-green-700">
                                  并发安全
                                </span>
                              )}
                            </div>
                          </div>
                          <p className="text-xs text-ink-secondary">{sk.description}</p>
                          {sk.available_stages && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {sk.available_stages.map((stage: string) => (
                                <span
                                  key={stage}
                                  className="rounded-md bg-brand-700/8 px-1.5 py-0.5 text-[10px] text-brand-700"
                                >
                                  {STAGE_LABELS[stage] || stage}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* 近期活动 + 岗位分布 */}
              <div className="grid grid-cols-2 gap-5">
                {/* 近期活动 */}
                <div className="rounded-2xl border border-black/5 bg-white p-5">
                  <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink-primary">
                    <Clock className="h-4 w-4 text-ink-secondary" />
                    近期面试活动
                  </h3>
                  {stats.recent_sessions.length === 0 ? (
                    <p className="py-4 text-center text-xs text-ink-tertiary">暂无活动</p>
                  ) : (
                    <div className="overflow-hidden rounded-xl border border-black/5">
                      <table className="w-full">
                        <thead>
                          <tr className="bg-surface-card">
                            <th className="px-3 py-2 text-left text-[10px] font-medium text-ink-tertiary">候选人</th>
                            <th className="px-3 py-2 text-left text-[10px] font-medium text-ink-tertiary">岗位</th>
                            <th className="px-3 py-2 text-left text-[10px] font-medium text-ink-tertiary">状态</th>
                            <th className="px-3 py-2 text-left text-[10px] font-medium text-ink-tertiary">时间</th>
                          </tr>
                        </thead>
                        <tbody>
                          {stats.recent_sessions.map((s) => (
                            <tr
                              key={s.id}
                              className="border-t border-black/5 cursor-pointer hover:bg-surface-hover transition-colors"
                              onClick={() => router.push(`/sessions/${s.id}`)}
                            >
                              <td className="px-3 py-2 text-xs text-ink-primary">{s.candidate_name}</td>
                              <td className="px-3 py-2 text-xs text-ink-secondary">
                                {s.position.length > 10 ? s.position.slice(0, 10) + "..." : s.position}
                              </td>
                              <td className="px-3 py-2">
                                <StatusBadge status={s.status} />
                              </td>
                              <td className="px-3 py-2 text-[10px] text-ink-tertiary">
                                {s.created_at ? new Date(s.created_at).toLocaleDateString("zh-CN") : "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* 岗位分布 */}
                <div className="rounded-2xl border border-black/5 bg-white p-5">
                  <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink-primary">
                    <Gauge className="h-4 w-4 text-purple-500" />
                    岗位分布
                  </h3>
                  {positionData.length === 0 ? (
                    <p className="py-4 text-center text-xs text-ink-tertiary">暂无数据</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={Math.max(200, positionData.length * 40)}>
                      <BarChart data={positionData} layout="vertical" margin={{ left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis type="number" fontSize={10} allowDecimals={false} />
                        <YAxis type="category" dataKey="name" fontSize={10} width={80} />
                        <Tooltip
                          // eslint-disable-next-line @typescript-eslint/no-explicit-any
                          formatter={(v: any) => [`${v} 次`, "面试次数"]}
                          labelFormatter={(label) => {
                            const item = positionData.find((d) => d.name === label);
                            return item?.fullName || label;
                          }}
                        />
                        <Bar dataKey="count" fill="#005A4E" radius={[0, 4, 4, 0]} name="面试次数" />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </main>
    </div>
  );
}
