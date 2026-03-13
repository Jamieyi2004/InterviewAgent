/**
 * 面试进度指示器 —— 竖向步骤条（侧栏布局适配）
 */

import { STAGE_LABELS } from "@/store/useInterviewStore";
import { Check } from "lucide-react";

interface Props {
  currentStage: string;
}

const STAGES = ["opening", "coding", "basic_qa", "project_deep", "summary"];

export default function InterviewProgress({ currentStage }: Props) {
  const currentIdx = STAGES.indexOf(currentStage);

  return (
    <div className="space-y-1">
      {STAGES.map((stage, idx) => {
        const isActive = idx === currentIdx;
        const isDone = idx < currentIdx;

        return (
          <div
            key={stage}
            className={`flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition-all ${
              isActive
                ? "bg-brand-700/8 text-brand-700 font-medium"
                : isDone
                ? "text-ink-secondary"
                : "text-ink-disabled"
            }`}
          >
            {/* 步骤图标 */}
            <div
              className={`flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-md text-[10px] font-bold ${
                isActive
                  ? "bg-brand-700 text-white"
                  : isDone
                  ? "bg-brand-700/15 text-brand-700"
                  : "bg-black/5 text-ink-disabled"
              }`}
            >
              {isDone ? <Check className="h-3 w-3" /> : idx + 1}
            </div>

            {/* 阶段名称 */}
            <span>{STAGE_LABELS[stage] || stage}</span>
          </div>
        );
      })}
    </div>
  );
}
