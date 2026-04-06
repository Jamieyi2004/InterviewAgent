/**
 * 面试题库与技巧页面 —— 分类浏览 + 搜索 + 展开答案
 */

"use client";

import { LoadingSpinner } from "@/components";
import {
  SidebarHeader,
  SidebarNavGroup,
  SidebarDivider,
  SidebarFooter,
} from "@/components/SidebarNav";
import {
  fetchKnowledgeCategories,
  fetchKnowledgeQuestions,
  fetchKnowledgeTips,
  searchKnowledge,
  type KnowledgeCategory,
  type KnowledgeQuestion,
  type KnowledgeTip,
} from "@/lib/api";
import {
  BookOpen,
  ChevronDown,
  Lightbulb,
  Search,
  Sparkles,
  Tag,
} from "lucide-react";
import { useEffect, useState } from "react";

const DIFFICULTY_STYLE: Record<string, string> = {
  "简单": "bg-emerald-50 text-emerald-700",
  "中等": "bg-amber-50 text-amber-700",
  "困难": "bg-red-50 text-red-600",
};

export default function KnowledgePage() {
  const [categories, setCategories] = useState<KnowledgeCategory[]>([]);
  const [activeCategory, setActiveCategory] = useState("java");
  const [questions, setQuestions] = useState<KnowledgeQuestion[]>([]);
  const [tips, setTips] = useState<KnowledgeTip[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"questions" | "tips">("questions");
  const [semanticResults, setSemanticResults] = useState<KnowledgeQuestion[] | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const handleSemanticSearch = async () => {
    if (!searchQuery.trim()) {
      setSemanticResults(null);
      return;
    }
    setIsSearching(true);
    try {
      const data = await searchKnowledge(searchQuery, 8);
      setSemanticResults(data.results);
      setActiveTab("questions");
    } catch {
      setSemanticResults(null);
    } finally {
      setIsSearching(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery("");
    setSemanticResults(null);
  };

  // 加载分类和技巧
  useEffect(() => {
    const load = async () => {
      const [catData, tipData] = await Promise.all([
        fetchKnowledgeCategories(),
        fetchKnowledgeTips(),
      ]);
      setCategories(catData.categories);
      setTips(tipData.tips);
      setIsLoading(false);
    };
    load();
  }, []);

  // 切换分类时加载题目
  useEffect(() => {
    if (activeTab !== "questions") return;
    setIsLoading(true);
    fetchKnowledgeQuestions(activeCategory).then((data) => {
      setQuestions(data.questions);
      setExpandedIds(new Set());
      setIsLoading(false);
    });
  }, [activeCategory, activeTab]);

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  // 搜索过滤
  const filteredQuestions = searchQuery
    ? questions.filter(
        (q) =>
          q.title.includes(searchQuery) ||
          q.tags.some((t) => t.includes(searchQuery)) ||
          q.answer.includes(searchQuery)
      )
    : questions;

  // 显示的题目列表：语义搜索结果优先，否则按分类
  const displayQuestions = semanticResults || filteredQuestions;

  const filteredTips = searchQuery
    ? tips.filter(
        (t) => t.title.includes(searchQuery) || t.content.includes(searchQuery)
      )
    : tips;

  return (
    <div className="flex h-screen">
      {/* ========== 侧边栏 ========== */}
      <aside className="flex w-[260px] flex-shrink-0 flex-col border-r border-black/5 bg-surface-sidebar">
        <SidebarHeader />
        <SidebarDivider />
        <SidebarNavGroup currentPath="/knowledge" />
        <SidebarDivider />

        {/* 分类筛选 */}
        <div className="flex-1 overflow-y-auto px-3 py-2">
          <p className="px-2 pb-2 text-[11px] font-medium uppercase tracking-wider text-ink-tertiary">
            题目分类
          </p>
          <nav className="flex flex-col gap-0.5">
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => {
                  setActiveCategory(cat.id);
                  setActiveTab("questions");
                }}
                className={`flex items-center justify-between rounded-xl px-3 py-2.5 text-sm transition-all hover:bg-surface-hover ${
                  activeCategory === cat.id && activeTab === "questions"
                    ? "bg-brand-700/8 text-brand-700 font-medium"
                    : "text-ink-secondary"
                }`}
              >
                <span>{cat.name}</span>
                <span className="text-xs text-ink-tertiary">{cat.count}</span>
              </button>
            ))}
            <SidebarDivider />
            <button
              onClick={() => setActiveTab("tips")}
              className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm transition-all hover:bg-surface-hover ${
                activeTab === "tips"
                  ? "bg-brand-700/8 text-brand-700 font-medium"
                  : "text-ink-secondary"
              }`}
            >
              <Lightbulb className="h-4 w-4" />
              面试技巧
            </button>
          </nav>
        </div>

        <SidebarFooter />
      </aside>

      {/* ========== 主区域 ========== */}
      <main className="flex-1 overflow-y-auto bg-surface-main">
        <div className="mx-auto max-w-3xl px-8 py-8">
          {/* 页头 */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-1">
              <BookOpen className="h-5 w-5 text-brand-700" />
              <h1 className="text-lg font-semibold text-ink-primary">
                {activeTab === "questions" ? "面试题库" : "面试技巧"}
              </h1>
            </div>
            <p className="text-xs text-ink-tertiary">
              {activeTab === "questions"
                ? `${categories.find((c) => c.id === activeCategory)?.name || ""} · 高频面试题目与参考答案`
                : "面试全流程实用技巧"}
            </p>
          </div>

          {/* 搜索栏 */}
          <div className="mb-5 flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-tertiary" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  if (!e.target.value.trim()) setSemanticResults(null);
                }}
                onKeyDown={(e) => e.key === "Enter" && handleSemanticSearch()}
                placeholder="语义搜索面试题（如：Redis 缓存策略）..."
                className="w-full rounded-xl border border-black/8 bg-white pl-10 pr-4 py-2.5 text-sm text-ink-primary outline-none placeholder:text-ink-disabled transition-colors focus:border-brand-700/40 focus:ring-2 focus:ring-brand-700/8"
              />
            </div>
            <button
              onClick={handleSemanticSearch}
              disabled={!searchQuery.trim() || isSearching}
              className="flex items-center gap-1.5 rounded-xl bg-brand-700 px-4 py-2.5 text-sm font-medium text-white transition-all hover:bg-brand-800 active:scale-[0.98] disabled:bg-ink-disabled"
            >
              <Sparkles className="h-3.5 w-3.5" />
              {isSearching ? "搜索中..." : "AI 搜索"}
            </button>
          </div>

          {/* 语义搜索结果提示 */}
          {semanticResults && (
            <div className="mb-4 flex items-center justify-between rounded-xl bg-brand-700/5 px-4 py-2.5">
              <p className="text-xs text-brand-700">
                <Sparkles className="mr-1 inline h-3.5 w-3.5" />
                语义搜索 &ldquo;{searchQuery}&rdquo; 找到 {semanticResults.length} 道相关题目
              </p>
              <button onClick={clearSearch} className="text-xs text-ink-tertiary hover:text-ink-primary">
                清除搜索
              </button>
            </div>
          )}

          {isLoading ? (
            <LoadingSpinner />
          ) : activeTab === "questions" ? (
            /* ===== 题目列表 ===== */
            <div className="space-y-3">
              {displayQuestions.length === 0 ? (
                <div className="py-12 text-center text-sm text-ink-tertiary">
                  {searchQuery ? "未找到匹配的题目" : "暂无题目"}
                </div>
              ) : (
                displayQuestions.map((q) => (
                  <div
                    key={q.id}
                    className="rounded-2xl border border-black/5 bg-surface-card overflow-hidden transition-shadow hover:shadow-card"
                  >
                    {/* 题目标题 */}
                    <button
                      onClick={() => toggleExpand(q.id)}
                      className="flex w-full items-center justify-between px-5 py-4 text-left"
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-ink-primary truncate">
                          {q.title}
                        </h3>
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold shrink-0 ${
                            DIFFICULTY_STYLE[q.difficulty] || "bg-gray-50 text-gray-600"
                          }`}
                        >
                          {q.difficulty}
                        </span>
                      </div>
                      <ChevronDown
                        className={`h-4 w-4 text-ink-tertiary shrink-0 ml-2 transition-transform ${
                          expandedIds.has(q.id) ? "rotate-180" : ""
                        }`}
                      />
                    </button>

                    {/* 展开内容 */}
                    {expandedIds.has(q.id) && (
                      <div className="border-t border-black/5 px-5 py-4 space-y-3">
                        {/* 标签 */}
                        <div className="flex items-center gap-1.5">
                          <Tag className="h-3.5 w-3.5 text-ink-tertiary" />
                          {q.tags.map((tag) => (
                            <span
                              key={tag}
                              className="rounded-full bg-brand-700/6 px-2 py-0.5 text-[10px] text-brand-700"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>

                        {/* 参考答案 */}
                        <div>
                          <p className="text-xs font-medium text-ink-tertiary mb-1.5">
                            参考答案
                          </p>
                          <p className="text-sm text-ink-secondary leading-relaxed whitespace-pre-wrap">
                            {q.answer}
                          </p>
                        </div>

                        {/* 考察要点 */}
                        {q.key_points?.length > 0 && (
                          <div>
                            <p className="text-xs font-medium text-ink-tertiary mb-1.5">
                              考察要点
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {q.key_points.map((kp) => (
                                <span
                                  key={kp}
                                  className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-[10px] font-medium text-emerald-700"
                                >
                                  {kp}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          ) : (
            /* ===== 面试技巧 ===== */
            <div className="space-y-4">
              {filteredTips.length === 0 ? (
                <div className="py-12 text-center text-sm text-ink-tertiary">
                  {searchQuery ? "未找到匹配的技巧" : "暂无技巧"}
                </div>
              ) : (
                filteredTips.map((tip) => (
                  <div
                    key={tip.id}
                    className="rounded-2xl border border-black/5 bg-surface-card p-5"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Lightbulb className="h-4 w-4 text-amber-500" />
                      <h3 className="text-sm font-semibold text-ink-primary">
                        {tip.title}
                      </h3>
                      <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                        {tip.category}
                      </span>
                    </div>
                    <p className="text-sm text-ink-secondary leading-relaxed whitespace-pre-wrap">
                      {tip.content}
                    </p>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
