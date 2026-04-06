/**
 * 管理后台 — 会话详情
 */

"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, BarChart3 } from "lucide-react";

import { fetchAdminSessionDetail, type SessionDetail } from "@/lib/api";
import { SidebarHeader, AdminSidebarNavGroup, SidebarDivider, SidebarFooter } from "@/components/SidebarNav";
import AdminGuard from "@/components/AdminGuard";
import LoadingSpinner from "@/components/LoadingSpinner";
import StatusBadge from "@/components/StatusBadge";
import ConversationReplay from "@/components/ConversationReplay";

export default function AdminSessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = Number(params.id);

  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    fetchAdminSessionDetail(sessionId)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, [sessionId]);

  return (
    <AdminGuard>
    <div className="flex h-screen">
      <aside className="flex w-[260px] flex-shrink-0 flex-col border-r border-black/5 bg-surface-sidebar">
        <SidebarHeader />
        <SidebarDivider />
        <AdminSidebarNavGroup currentPath="/admin/sessions" />
        <SidebarDivider />

        {detail && (
          <div className="px-4 py-3">
            <p className="text-[11px] font-medium text-ink-tertiary uppercase tracking-wider mb-2">会话信息</p>
            <div className="space-y-1.5 text-xs text-ink-secondary">
              <div className="flex justify-between"><span>会话 ID</span><span className="text-ink-primary">#{sessionId}</span></div>
              <div className="flex justify-between"><span>候选人</span><span className="text-ink-primary">{detail.session.candidate_name}</span></div>
              <div className="flex justify-between"><span>岗位</span><span className="text-ink-primary">{detail.session.position}</span></div>
              <div className="flex justify-between"><span>状态</span><StatusBadge status={detail.session.status} /></div>
              {detail.report && (<div className="flex justify-between"><span>评分</span><span className="font-semibold text-brand-700">{detail.report.overall_score}</span></div>)}
            </div>
          </div>
        )}

        <div className="flex-1" />
        <SidebarFooter />
      </aside>

      <main className="flex-1 overflow-y-auto bg-surface-main">
        {loading ? (
          <LoadingSpinner fullPage text="加载会话详情..." />
        ) : error ? (
          <div className="flex h-full flex-col items-center justify-center">
            <p className="text-sm text-red-500">{error}</p>
            <button onClick={() => router.push("/admin/sessions")} className="mt-4 rounded-xl bg-brand-700 px-4 py-2 text-sm text-white hover:bg-brand-800">返回列表</button>
          </div>
        ) : detail ? (
          <div className="mx-auto max-w-3xl px-8 py-8">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h1 className="text-lg font-semibold text-ink-primary">会话详情 #{sessionId}</h1>
                <p className="mt-0.5 text-xs text-ink-tertiary">{detail.session.candidate_name} · {detail.session.position}</p>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => router.push("/admin/sessions")} className="flex items-center gap-1 rounded-xl border border-black/8 px-3 py-2 text-xs text-ink-secondary hover:bg-surface-hover">
                  <ArrowLeft className="h-3.5 w-3.5" /> 返回列表
                </button>
                <button onClick={() => router.push(`/admin/dashboard?session_id=${sessionId}`)} className="flex items-center gap-1 rounded-xl bg-brand-700 px-3 py-2 text-xs text-white hover:bg-brand-800">
                  <BarChart3 className="h-3.5 w-3.5" /> 数据分析
                </button>
              </div>
            </div>

            <ConversationReplay messages={detail.messages} />
          </div>
        ) : null}
      </main>
    </div>
    </AdminGuard>
  );
}
