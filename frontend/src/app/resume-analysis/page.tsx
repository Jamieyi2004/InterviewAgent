/**
 * 简历分析页面 —— 上传简历获取 AI 优化建议
 */

"use client";

import ResumeUploader from "@/components/ResumeUploader";
import { LoadingSpinner } from "@/components";
import {
  SidebarHeader,
  SidebarNavGroup,
  SidebarDivider,
  SidebarFooter,
} from "@/components/SidebarNav";
import {
  analyzeResume,
  fetchResumeAnalysis,
  type ResumeAnalysisResponse,
} from "@/lib/api";
import {
  Briefcase,
  CheckCircle2,
  ChevronDown,
  FileSearch,
  Lightbulb,
  Tag,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

const POSITION_OPTIONS = [
  "通用岗位",
  "Java后端开发工程师",
  "前端开发工程师",
  "Python开发工程师",
  "全栈开发工程师",
  "数据分析师",
  "算法工程师",
];

const SECTION_LABELS: Record<string, string> = {
  basic_info: "基本信息",
  education: "教育背景",
  skills: "技能清单",
  projects: "项目经历",
  work_experience: "工作/实习经历",
};

function ScoreRing({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 40;
  const offset = circumference - (score / 100) * circumference;
  const color =
    score >= 80 ? "#059669" : score >= 60 ? "#D97706" : "#DC2626";

  return (
    <div className="relative flex h-28 w-28 items-center justify-center">
      <svg className="absolute h-full w-full -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="40" stroke="#F0F1F3" strokeWidth="6" fill="none" />
        <circle
          cx="50" cy="50" r="40" stroke={color} strokeWidth="6" fill="none"
          strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset}
          className="transition-all duration-1000"
        />
      </svg>
      <div className="text-center">
        <span className="text-2xl font-bold" style={{ color }}>{score}</span>
        <p className="text-[10px] text-ink-tertiary">综合评分</p>
      </div>
    </div>
  );
}

function ScoreBar({ score, label }: { score: number; label: string }) {
  const color = score >= 80 ? "bg-emerald-500" : score >= 60 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-3">
      <span className="w-20 text-xs text-ink-secondary shrink-0">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-black/5">
        <div className={`h-full rounded-full ${color} transition-all duration-700`} style={{ width: `${score}%` }} />
      </div>
      <span className="w-8 text-xs font-medium text-ink-primary text-right">{score}</span>
    </div>
  );
}

function ResumeAnalysisContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setupFlag = searchParams.get("setup");
  const resumeIdParam = searchParams.get("resume_id");
  const urlResumeId =
    resumeIdParam && !Number.isNaN(Number(resumeIdParam))
      ? Number(resumeIdParam)
      : null;

  /** 本页上传完成后的简历 ID（不再用全局 store 自动进入分析，避免侧栏每次应显示上传表单） */
  const [pageResumeId, setPageResumeId] = useState<number | null>(null);
  /** 每次「新分析」时递增，强制重置 ResumeUploader 内部状态 */
  const [uploaderKey, setUploaderKey] = useState(0);

  const [analysis, setAnalysis] = useState<ResumeAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [position, setPosition] = useState(POSITION_OPTIONS[0]);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  const resumeId = urlResumeId ?? pageResumeId;

  /** 侧栏「简历分析」等带 ?setup=1：清空本页状态并回到上传+岗位步骤 */
  useEffect(() => {
    if (setupFlag !== "1") return;
    setPageResumeId(null);
    setAnalysis(null);
    setError("");
    setExpandedSections(new Set());
    setUploaderKey((k) => k + 1);
    router.replace("/resume-analysis", { scroll: false });
  }, [setupFlag, router]);

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const loadAnalysis = useCallback(async (rid: number) => {
    setIsLoading(true);
    setError("");
    try {
      let data = await fetchResumeAnalysis(rid);
      if (!data) {
        data = await analyzeResume(rid, position);
      }
      setAnalysis(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "分析失败");
    } finally {
      setIsLoading(false);
    }
  }, [position]);

  useEffect(() => {
    if (resumeId) {
      loadAnalysis(resumeId);
    }
  }, [resumeId, loadAnalysis]);

  const handleReAnalyze = async () => {
    if (!resumeId) return;
    setIsLoading(true);
    setError("");
    try {
      const data = await analyzeResume(resumeId, position);
      setAnalysis(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "分析失败");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen">
      {/* ========== 侧边栏 ========== */}
      <aside className="flex w-[260px] flex-shrink-0 flex-col border-r border-black/5 bg-surface-sidebar">
        <SidebarHeader />
        <SidebarDivider />
        <SidebarNavGroup currentPath="/resume-analysis" />
        <div className="flex-1" />
        <SidebarFooter />
      </aside>

      {/* ========== 主区域 ========== */}
      <main className="flex-1 overflow-y-auto bg-surface-main">
        {!resumeId ? (
          /* 上传入口 */
          <div className="flex h-full flex-col items-center justify-center px-8">
            <div className="w-full max-w-lg animate-fade-in">
              <div className="mb-6 flex flex-col items-center">
                <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-700/8">
                  <FileSearch className="h-7 w-7 text-brand-700" />
                </div>
                <h2 className="text-lg font-semibold text-ink-primary">简历分析</h2>
                <p className="mt-1 text-sm text-ink-secondary">上传简历，获取 AI 优化建议</p>
              </div>

              <div className="mb-4 rounded-2xl border border-black/5 bg-surface-card p-5">
                <h3 className="mb-3 text-sm font-semibold text-ink-primary">上传你的简历</h3>
                <ResumeUploader
                  key={uploaderKey}
                  ignoreStoredResume
                  onUploaded={(rid) => {
                    setPageResumeId(rid);
                  }}
                />
              </div>

              <div className="mb-4 rounded-2xl border border-black/5 bg-surface-card p-5">
                <h3 className="mb-3 text-sm font-semibold text-ink-primary">面试岗位（可选）</h3>
                <div className="flex items-center gap-2.5">
                  <Briefcase className="h-4 w-4 text-ink-tertiary" />
                  <select
                    value={position}
                    onChange={(e) => setPosition(e.target.value)}
                    className="flex-1 rounded-xl border border-black/8 bg-white px-3.5 py-2.5 text-sm text-ink-primary outline-none transition-colors focus:border-brand-700/40 focus:ring-2 focus:ring-brand-700/8"
                  >
                    {POSITION_OPTIONS.map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </div>
        ) : isLoading ? (
          <LoadingSpinner fullPage text="AI 正在分析你的简历..." />
        ) : error ? (
          <div className="flex h-full flex-col items-center justify-center">
            <p className="text-sm text-red-500">{error}</p>
            <button onClick={() => loadAnalysis(resumeId)} className="mt-4 rounded-xl bg-brand-700 px-4 py-2 text-sm text-white hover:bg-brand-800">
              重试
            </button>
          </div>
        ) : analysis ? (
          <div className="mx-auto max-w-3xl px-8 py-8">
            {/* 页头 */}
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h1 className="text-lg font-semibold text-ink-primary">简历分析报告</h1>
                <p className="mt-0.5 text-xs text-ink-tertiary">
                  面试岗位：{analysis.target_position || "通用"} · AI 自动生成
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={position}
                  onChange={(e) => setPosition(e.target.value)}
                  className="rounded-xl border border-black/8 bg-white px-3 py-2 text-xs text-ink-primary outline-none"
                >
                  {POSITION_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
                <button
                  onClick={handleReAnalyze}
                  className="rounded-xl bg-brand-700 px-4 py-2 text-xs font-medium text-white hover:bg-brand-800 active:scale-[0.98]"
                >
                  重新分析
                </button>
                <button
                  type="button"
                  onClick={() => router.push("/resume-analysis?setup=1")}
                  className="rounded-xl border border-black/10 bg-white px-4 py-2 text-xs font-medium text-ink-secondary hover:bg-surface-hover active:scale-[0.98]"
                >
                  新简历分析
                </button>
              </div>
            </div>

            {/* 总分 + 综合评价 */}
            <div className="mb-6 rounded-2xl border border-black/5 bg-surface-card p-6">
              <div className="flex items-start gap-6">
                <ScoreRing score={analysis.overall_score} />
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-ink-primary mb-2">综合评价</h3>
                  <p className="text-sm text-ink-secondary leading-relaxed">
                    {analysis.overall_feedback}
                  </p>
                </div>
              </div>
            </div>

            {/* 分项评分 */}
            <div className="mb-6 rounded-2xl border border-black/5 bg-surface-card p-6">
              <h3 className="text-sm font-semibold text-ink-primary mb-4">分项评分</h3>
              <div className="space-y-3 mb-5">
                {Object.entries(analysis.sections || {}).map(([key, sec]) => (
                  <ScoreBar key={key} score={sec.score} label={SECTION_LABELS[key] || key} />
                ))}
              </div>

              {/* 分项详情 */}
              <div className="space-y-2">
                {Object.entries(analysis.sections || {}).map(([key, sec]) => (
                  <div key={key} className="rounded-xl border border-black/5 overflow-hidden">
                    <button
                      onClick={() => toggleSection(key)}
                      className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-surface-hover transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-ink-primary">
                          {SECTION_LABELS[key] || key}
                        </span>
                        <span className={`text-xs font-medium ${sec.score >= 80 ? "text-emerald-600" : sec.score >= 60 ? "text-amber-600" : "text-red-500"}`}>
                          {sec.score}分
                        </span>
                      </div>
                      <ChevronDown className={`h-4 w-4 text-ink-tertiary transition-transform ${expandedSections.has(key) ? "rotate-180" : ""}`} />
                    </button>
                    {expandedSections.has(key) && (
                      <div className="border-t border-black/5 px-4 py-3 space-y-2">
                        <p className="text-sm text-ink-secondary">{sec.feedback}</p>
                        {sec.suggestions?.length > 0 && (
                          <div>
                            <p className="text-xs font-medium text-ink-tertiary mb-1">改进建议</p>
                            <ul className="space-y-1">
                              {sec.suggestions.map((s, i) => (
                                <li key={i} className="flex items-start gap-2 text-xs text-ink-secondary">
                                  <Lightbulb className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
                                  {s}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* 关键词推荐 */}
            {analysis.keyword_recommendations?.length > 0 && (
              <div className="mb-6 rounded-2xl border border-black/5 bg-surface-card p-6">
                <div className="flex items-center gap-2 mb-3">
                  <Tag className="h-4 w-4 text-brand-700" />
                  <h3 className="text-sm font-semibold text-ink-primary">推荐补充关键词</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {analysis.keyword_recommendations.map((kw, i) => (
                    <span
                      key={i}
                      className="rounded-full bg-brand-700/8 px-3 py-1 text-xs font-medium text-brand-700"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 格式优化建议 */}
            {analysis.format_suggestions?.length > 0 && (
              <div className="rounded-2xl border border-black/5 bg-surface-card p-6">
                <div className="flex items-center gap-2 mb-3">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  <h3 className="text-sm font-semibold text-ink-primary">格式优化建议</h3>
                </div>
                <ul className="space-y-2">
                  {analysis.format_suggestions.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-ink-secondary">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-[10px] font-bold text-emerald-600">
                        {i + 1}
                      </span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : null}
      </main>
    </div>
  );
}

export default function ResumeAnalysisPage() {
  return (
    <Suspense fallback={<LoadingSpinner fullPage />}>
      <ResumeAnalysisContent />
    </Suspense>
  );
}
