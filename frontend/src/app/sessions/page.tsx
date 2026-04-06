/**
 * 会话管理 —— 面试历史记录列表
 *
 * 布局：左侧栏 (260px) + 右侧表格区域
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  Eye,
  BarChart3,
  FileText,
  Calendar,
  Filter,
  Users,
} from "lucide-react";

import { fetchSessions, type SessionListItem, type SessionListParams } from "@/lib/api";
import { SidebarHeader, SidebarNavGroup, SidebarDivider, SidebarFooter } from "@/components/SidebarNav";
import StatusBadge from "@/components/StatusBadge";
import Pagination from "@/components/Pagination";
import LoadingSpinner from "@/components/LoadingSpinner";
import { STAGE_LABELS } from "@/lib/constants";

export default function SessionsPage() {
  const router = useRouter();
  const [items, setItems] = useState<SessionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 筛选条件
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [position, setPosition] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);

  const loadSessions = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params: SessionListParams = { page, page_size: 15 };
      if (search) params.search = search;
      if (status) params.status = status;
      if (position) params.position = position;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const res = await fetchSessions(params);
      setItems(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [page, search, status, position, dateFrom, dateTo]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleSearch = () => {
    setPage(1);
    loadSessions();
  };

  const scoreColor = (score: number | null) => {
    if (score === null) return "text-ink-tertiary";
    if (score >= 80) return "text-emerald-600";
    if (score >= 60) return "text-amber-600";
    return "text-red-500";
  };

  return (
    <div className="flex h-screen">
      {/* 侧边栏 */}
      <aside className="flex w-[260px] flex-shrink-0 flex-col border-r border-black/5 bg-surface-sidebar">
        <SidebarHeader />
        <SidebarDivider />
        <SidebarNavGroup currentPath="/sessions" />
        <SidebarDivider />

        {/* 筛选面板 */}
        <div className="flex-1 overflow-y-auto px-3 py-3">
          <p className="mb-3 flex items-center gap-1.5 px-1 text-xs font-medium text-ink-tertiary">
            <Filter className="h-3.5 w-3.5" /> 筛选条件
          </p>

          <div className="flex flex-col gap-2.5">
            <select
              value={status}
              onChange={(e) => { setStatus(e.target.value); setPage(1); }}
              className="rounded-lg border border-black/10 bg-white px-3 py-2 text-xs text-ink-primary outline-none focus:border-brand-700"
            >
              <option value="">全部状态</option>
              <option value="in_progress">进行中</option>
              <option value="completed">已完成</option>
            </select>

            <input
              type="text"
              placeholder="筛选岗位..."
              value={position}
              onChange={(e) => { setPosition(e.target.value); setPage(1); }}
              className="rounded-lg border border-black/10 bg-white px-3 py-2 text-xs text-ink-primary outline-none focus:border-brand-700"
            />

            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-ink-tertiary">起始日期</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
                className="rounded-lg border border-black/10 bg-white px-3 py-2 text-xs text-ink-primary outline-none focus:border-brand-700"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-ink-tertiary">截止日期</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
                className="rounded-lg border border-black/10 bg-white px-3 py-2 text-xs text-ink-primary outline-none focus:border-brand-700"
              />
            </div>
          </div>
        </div>

        <SidebarFooter />
      </aside>

      {/* 主区域 */}
      <main className="flex flex-1 flex-col bg-surface-main">
        {/* 顶部搜索栏 */}
        <div className="border-b border-black/5 px-8 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-ink-primary">会话管理</h2>
              <p className="mt-0.5 text-xs text-ink-tertiary">
                共 {total} 条面试记录
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-tertiary" />
                <input
                  type="text"
                  placeholder="搜索候选人姓名..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  className="w-56 rounded-xl border border-black/10 bg-white py-2 pl-9 pr-3 text-sm text-ink-primary outline-none focus:border-brand-700"
                />
              </div>
              <button
                onClick={handleSearch}
                className="rounded-xl bg-brand-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-800 active:scale-[0.98]"
              >
                搜索
              </button>
            </div>
          </div>
        </div>

        {/* 表格区域 */}
        <div className="flex-1 overflow-auto px-8 py-5">
          {loading ? (
            <LoadingSpinner text="加载会话列表..." />
          ) : error ? (
            <div className="py-12 text-center text-sm text-red-500">{error}</div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20">
              <Users className="mb-3 h-12 w-12 text-ink-disabled" />
              <p className="text-sm text-ink-tertiary">暂无面试记录</p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-2xl border border-black/5 bg-white">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-black/5 bg-surface-card">
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">候选人</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">目标岗位</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">状态</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">阶段</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">评分</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">消息数</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">创建时间</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.id}
                      className="border-b border-black/5 transition-colors hover:bg-surface-hover cursor-pointer"
                      onClick={() => router.push(`/sessions/${item.id}`)}
                    >
                      <td className="px-4 py-3 text-sm text-ink-secondary">#{item.id}</td>
                      <td className="px-4 py-3 text-sm font-medium text-ink-primary">
                        {item.candidate_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-ink-secondary">{item.position}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={item.status} />
                      </td>
                      <td className="px-4 py-3 text-sm text-ink-secondary">
                        {STAGE_LABELS[item.current_stage] || item.current_stage}
                      </td>
                      <td className={`px-4 py-3 text-sm font-semibold ${scoreColor(item.overall_score)}`}>
                        {item.overall_score !== null ? item.overall_score : "—"}
                      </td>
                      <td className="px-4 py-3 text-sm text-ink-secondary">{item.message_count}</td>
                      <td className="px-4 py-3 text-xs text-ink-tertiary">
                        {item.created_at
                          ? new Date(item.created_at).toLocaleDateString("zh-CN")
                          : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              router.push(`/sessions/${item.id}`);
                            }}
                            className="rounded-lg p-1.5 text-ink-secondary transition-colors hover:bg-surface-hover hover:text-brand-700"
                            title="查看详情"
                          >
                            <Eye className="h-4 w-4" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              router.push(`/dashboard?session_id=${item.id}`);
                            }}
                            className="rounded-lg p-1.5 text-ink-secondary transition-colors hover:bg-surface-hover hover:text-brand-700"
                            title="数据分析"
                          >
                            <BarChart3 className="h-4 w-4" />
                          </button>
                          {item.overall_score !== null && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                router.push(`/report?session_id=${item.id}`);
                              }}
                              className="rounded-lg p-1.5 text-ink-secondary transition-colors hover:bg-surface-hover hover:text-brand-700"
                              title="查看报告"
                            >
                              <FileText className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* 分页 */}
        {!loading && totalPages > 1 && (
          <div className="border-t border-black/5 px-8 py-4">
            <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </div>
        )}
      </main>
    </div>
  );
}
