/**
 * 代码编辑器组件 —— 算法题环节（C++ 语法高亮）
 */

"use client";

import { CodingProblem } from "@/lib/api";
import { cpp } from "@codemirror/lang-cpp";
import { oneDark } from "@codemirror/theme-one-dark";
import CodeMirror from "@uiw/react-codemirror";
import { Play, RotateCcw, Send } from "lucide-react";
import { useEffect, useState } from "react";

interface CodeEditorProps {
  problem: CodingProblem | null;
  onSubmit: (code: string) => void;
  disabled?: boolean;
}

const DEFAULT_CPP_TEMPLATE = `#include <iostream>
#include <string>
using namespace std;

// 在此编写代码

int main() {
    // 测试代码

    return 0;
}
`;

export default function CodeEditor({ problem, onSubmit, disabled }: CodeEditorProps) {
  const [code, setCode] = useState(DEFAULT_CPP_TEMPLATE);
  const [runOutput, setRunOutput] = useState<string | null>(null);

  useEffect(() => {
    if (problem?.signature) {
      setCode(problem.signature);
    }
  }, [problem]);

  const handleRun = () => {
    setRunOutput("【运行功能开发中】\n代码已接收，但暂未实现真正的运行环境。\n请直接点击「提交代码」让面试官评价。");
  };

  const handleSubmit = () => {
    if (code.trim()) {
      onSubmit(code);
    }
  };

  const handleReset = () => {
    setCode(problem?.signature || DEFAULT_CPP_TEMPLATE);
    setRunOutput(null);
  };

  return (
    <div className="overflow-hidden border-b border-black/5 bg-white">
      {/* 题目信息 */}
      {problem && (
        <div className="border-b border-black/5 bg-surface-card px-5 py-4">
          <div className="mb-2 flex items-center gap-2">
            <h3 className="text-sm font-semibold text-ink-primary">{problem.title}</h3>
            <span className={`rounded-lg px-2 py-0.5 text-[11px] font-medium ${
              problem.difficulty === "简单"
                ? "bg-emerald-100 text-emerald-700"
                : problem.difficulty === "中等"
                ? "bg-amber-100 text-amber-700"
                : "bg-red-100 text-red-700"
            }`}>
              {problem.difficulty}
            </span>
          </div>
          <p className="text-sm text-ink-secondary leading-relaxed">{problem.description}</p>
          <div className="mt-3 rounded-xl bg-surface-sidebar p-3">
            <p className="mb-1 text-[11px] font-medium text-ink-tertiary">示例</p>
            <pre className="text-xs text-ink-secondary font-mono whitespace-pre-wrap">{problem.example}</pre>
          </div>
        </div>
      )}

      {/* 工具栏 */}
      <div className="flex items-center justify-between border-b border-black/5 bg-white px-5 py-2">
        <span className="text-xs font-medium text-ink-tertiary">C++</span>
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleReset}
            disabled={disabled}
            className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs text-ink-secondary transition-colors hover:bg-surface-hover disabled:opacity-40"
          >
            <RotateCcw className="h-3 w-3" />
            重置
          </button>
          <button
            onClick={handleRun}
            disabled={disabled}
            className="flex items-center gap-1 rounded-lg bg-ink-primary px-2.5 py-1.5 text-xs text-white transition-colors hover:bg-ink-primary/90 disabled:opacity-40"
          >
            <Play className="h-3 w-3" />
            运行
          </button>
          <button
            onClick={handleSubmit}
            disabled={disabled || !code.trim()}
            className="flex items-center gap-1 rounded-lg bg-brand-700 px-2.5 py-1.5 text-xs text-white transition-colors hover:bg-brand-800 disabled:opacity-40"
          >
            <Send className="h-3 w-3" />
            提交代码
          </button>
        </div>
      </div>

      {/* 编辑器 */}
      <CodeMirror
        value={code}
        height="200px"
        theme={oneDark}
        extensions={[cpp()]}
        onChange={(value) => setCode(value)}
        editable={!disabled}
        basicSetup={{
          lineNumbers: true,
          highlightActiveLineGutter: true,
          highlightActiveLine: true,
          foldGutter: true,
          autocompletion: true,
          bracketMatching: true,
          closeBrackets: true,
          indentOnInput: true,
        }}
      />

      {/* 运行输出 */}
      {runOutput && (
        <div className="border-t border-black/5 bg-[#1e1e2e] p-4">
          <p className="mb-1.5 text-[11px] font-medium text-white/40">输出</p>
          <pre className="font-mono text-xs text-white/70 whitespace-pre-wrap">
            {runOutput}
          </pre>
        </div>
      )}
    </div>
  );
}
