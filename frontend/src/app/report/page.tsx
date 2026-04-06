/**
 * 评估报告页面
 */

"use client";

import ReportCard from "@/components/ReportCard";
import {
  SidebarHeader,
  SidebarNavGroup,
  SidebarDivider,
  SidebarFooter,
} from "@/components/SidebarNav";
import { fetchReport, generateReport } from "@/lib/api";
import { useInterviewStore } from "@/store/useInterviewStore";
import { GraduationCap, Loader2, Plus, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

function ReportContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { reset } = useInterviewStore();

  const sessionId = Number(searchParams.get("session_id"));

  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sessionId) {
      setError("缺少面试会话ID");
      setIsLoading(false);
      return;
    }

    const loadReport = async () => {
      try {
        let data = await fetchReport(sessionId).catch(() => null);
        if (!data) {
          data = await generateReport(sessionId);
        }
        setReport(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载报告失败");
      } finally {
        setIsLoading(false);
      }
    };

    loadReport();
  }, [sessionId]);

  const handleNewInterview = () => {
    reset();
    router.push("/");
  };

  return (
    <div className="flex h-screen">
      {/* 侧边栏 */}
      <aside className="flex w-[260px] flex-shrink-0 flex-col border-r border-black/5 bg-surface-sidebar">
        <SidebarHeader />
        <SidebarDivider />
        <SidebarNavGroup currentPath="/report" />
        <SidebarDivider />

        {/* 操作 */}
        <div className="px-3 space-y-1">
          <button
            onClick={handleNewInterview}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-ink-primary transition-all hover:bg-surface-hover active:scale-[0.98]"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-700 text-white">
              <Plus className="h-3.5 w-3.5" />
            </div>
            新建面试
          </button>
          <Link
            href={`/coaching?session_id=${sessionId}`}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-ink-secondary transition-all hover:bg-surface-hover"
          >
            <GraduationCap className="h-4 w-4" />
            面试辅导
          </Link>
        </div>

        <div className="flex-1" />
        <SidebarFooter />
      </aside>

      {/* 主区域 */}
      <main className="flex-1 overflow-y-auto bg-surface-main">
        {isLoading ? (
          <div className="flex h-full flex-col items-center justify-center">
            <Loader2 className="mb-3 h-6 w-6 animate-spin text-brand-700" />
            <p className="text-sm font-medium text-ink-primary">正在生成评估报告</p>
            <p className="mt-1 text-xs text-ink-tertiary">AI 正在分析你的面试表现，请稍候</p>
          </div>
        ) : error ? (
          <div className="flex h-full flex-col items-center justify-center">
            <p className="text-sm text-red-500">{error}</p>
            <button
              onClick={handleNewInterview}
              className="mt-4 rounded-xl bg-brand-700 px-4 py-2 text-sm text-white hover:bg-brand-800"
            >
              返回首页
            </button>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl px-8 py-8">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h1 className="text-lg font-semibold text-ink-primary">面试评估报告</h1>
                <p className="mt-0.5 text-xs text-ink-tertiary">
                  会话 #{sessionId} · 由 AI 自动生成
                </p>
              </div>
              <button
                onClick={handleNewInterview}
                className="flex items-center gap-1.5 rounded-xl bg-brand-700 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-brand-800 active:scale-[0.98]"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                再来一次
              </button>
            </div>

            {report && <ReportCard report={report as any} />}
          </div>
        )}
      </main>
    </div>
  );
}

export default function ReportPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-brand-700" />
        </div>
      }
    >
      <ReportContent />
    </Suspense>
  );
}
