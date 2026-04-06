/**
 * 管理后台 — 所有会话列表
 */

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, BarChart3 } from "lucide-react";

import { fetchAdminSessions, type SessionListItem, type SessionListParams } from "@/lib/api";
import { SidebarHeader, AdminSidebarNavGroup, SidebarDivider, SidebarFooter } from "@/components/SidebarNav";
import AdminGuard from "@/components/AdminGuard";
import StatusBadge from "@/components/StatusBadge";
import Pagination from "@/components/Pagination";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function AdminSessionsPage() {
  const router = useRouter();
  const [items, setItems] = useState<SessionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [params, setParams] = useState<SessionListParams>({ page: 1, page_size: 15 });
  const [searchInput, setSearchInput] = useState("");

  useEffect(() => {
    setLoading(true);
    fetchAdminSessions(params)
      .then((data) => { setItems(data.items); setTotal(data.total); setTotalPages(data.total_pages); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [params]);

  const handleSearch = () => setParams((p) => ({ ...p, search: searchInput || undefined, page: 1 }));

  return (
    <AdminGuard>
    <div className="flex h-screen">
      <aside className="flex w-[260px] flex-shrink-0 flex-col border-r border-black/5 bg-surface-sidebar">
        <SidebarHeader />
        <SidebarDivider />
        <AdminSidebarNavGroup currentPath="/admin/sessions" />
        <div className="flex-1" />
        <SidebarFooter />
      </aside>

      <main className="flex flex-1 flex-col overflow-auto bg-surface-main">
        <div className="border-b border-black/5 px-8 py-5">
          <h2 className="text-lg font-semibold text-ink-primary">所有会话</h2>
          <p className="mt-0.5 text-xs text-ink-tertiary">管理所有用户的面试会话 · 共 {total} 条</p>
        </div>

        <div className="flex-1 px-8 py-6">
          {/* 搜索 + 筛选 */}
          <div className="mb-4 flex items-center gap-3">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-tertiary" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="搜索候选人..."
                className="w-full rounded-xl border border-black/8 bg-white pl-9 pr-4 py-2 text-sm outline-none placeholder:text-ink-disabled focus:border-brand-700/40 focus:ring-2 focus:ring-brand-700/8"
              />
            </div>
            <select
              value={params.status || ""}
              onChange={(e) => setParams((p) => ({ ...p, status: e.target.value || undefined, page: 1 }))}
              className="rounded-xl border border-black/8 bg-white px-3 py-2 text-sm outline-none"
            >
              <option value="">全部状态</option>
              <option value="in_progress">进行中</option>
              <option value="completed">已完成</option>
            </select>
          </div>

          {loading ? (
            <LoadingSpinner text="加载会话..." />
          ) : items.length === 0 ? (
            <div className="py-12 text-center text-sm text-ink-tertiary">暂无会话</div>
          ) : (
            <>
              <div className="overflow-hidden rounded-2xl border border-black/5 bg-white">
                <table className="w-full">
                  <thead>
                    <tr className="bg-surface-card">
                      <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">ID</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">候选人</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">岗位</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">状态</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">评分</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">消息数</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">创建时间</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((s) => (
                      <tr key={s.id} className="border-t border-black/5 hover:bg-surface-hover transition-colors">
                        <td className="px-4 py-3 text-sm text-ink-primary">#{s.id}</td>
                        <td className="px-4 py-3 text-sm text-ink-primary">{s.candidate_name || "—"}</td>
                        <td className="px-4 py-3 text-sm text-ink-secondary">{s.position}</td>
                        <td className="px-4 py-3"><StatusBadge status={s.status} /></td>
                        <td className="px-4 py-3 text-sm font-medium">{s.overall_score ?? "—"}</td>
                        <td className="px-4 py-3 text-sm text-ink-tertiary">{s.message_count}</td>
                        <td className="px-4 py-3 text-xs text-ink-tertiary">{s.created_at ? new Date(s.created_at).toLocaleString("zh-CN") : "—"}</td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            <button onClick={() => router.push(`/admin/sessions/${s.id}`)} className="text-xs text-brand-700 hover:underline">详情</button>
                            <button onClick={() => router.push(`/admin/dashboard?session_id=${s.id}`)} className="text-xs text-ink-tertiary hover:text-brand-700"><BarChart3 className="h-3.5 w-3.5" /></button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {totalPages > 1 && (
                <div className="mt-4">
                  <Pagination page={params.page || 1} totalPages={totalPages} onPageChange={(p) => setParams((prev) => ({ ...prev, page: p }))} />
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
    </AdminGuard>
  );
}
