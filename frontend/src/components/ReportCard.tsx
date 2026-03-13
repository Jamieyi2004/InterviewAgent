/**
 * 评估报告卡片 —— Soft Minimalism 风格
 */

interface DimensionScore {
  score: number;
  comment: string;
}

interface QuestionReview {
  question: string;
  answer_quality: string;
  comment: string;
  reference_answer: string;
}

interface Props {
  report: {
    overall_score: number;
    dimensions: Record<string, DimensionScore>;
    strengths: string[];
    weaknesses: string[];
    suggestions: string[];
    question_reviews: QuestionReview[];
    hiring_recommendation?: string;
    summary?: string;
  };
}

const DIMENSION_LABELS: Record<string, string> = {
  technical_depth: "技术深度",
  communication: "沟通表达",
  logic_thinking: "逻辑思维",
  project_experience: "项目经验",
  coding_ability: "编程能力",
};

function ScoreRing({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 40;
  const offset = circumference - (score / 100) * circumference;
  const color =
    score >= 80 ? "#059669" : score >= 60 ? "#D97706" : "#DC2626";

  return (
    <div className="relative flex h-28 w-28 items-center justify-center">
      <svg className="absolute h-full w-full -rotate-90" viewBox="0 0 100 100">
        <circle
          cx="50" cy="50" r="40"
          stroke="#F0F1F3"
          strokeWidth="6"
          fill="none"
        />
        <circle
          cx="50" cy="50" r="40"
          stroke={color}
          strokeWidth="6"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-1000"
        />
      </svg>
      <div className="text-center">
        <span className="text-2xl font-bold text-ink-primary">{score}</span>
        <p className="text-[10px] text-ink-tertiary">综合评分</p>
      </div>
    </div>
  );
}

function ScoreBar({ score, label }: { score: number; label: string }) {
  const color =
    score >= 80 ? "bg-emerald-500" : score >= 60 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-ink-secondary">{label}</span>
        <span className="font-semibold text-ink-primary">{score}</span>
      </div>
      <div className="h-1.5 rounded-full bg-black/5">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

function QualityBadge({ quality }: { quality: string }) {
  const styles: Record<string, string> = {
    好: "bg-emerald-50 text-emerald-700 border-emerald-200",
    一般: "bg-amber-50 text-amber-700 border-amber-200",
    差: "bg-red-50 text-red-700 border-red-200",
  };

  return (
    <span
      className={`inline-block rounded-lg border px-2 py-0.5 text-[11px] font-medium ${
        styles[quality] || "bg-surface-card text-ink-secondary border-black/5"
      }`}
    >
      {quality}
    </span>
  );
}

export default function ReportCard({ report }: Props) {
  return (
    <div className="space-y-4">
      {/* 综合评分 + 维度分数 */}
      <div className="rounded-2xl border border-black/5 bg-white p-6">
        <div className="flex items-start gap-6">
          <ScoreRing score={report.overall_score} />
          <div className="flex-1 space-y-3 pt-1">
            {Object.entries(report.dimensions || {}).map(([key, dim]) => (
              <ScoreBar
                key={key}
                score={dim.score}
                label={DIMENSION_LABELS[key] || key}
              />
            ))}
          </div>
        </div>

        {/* 总结 & 录用建议 */}
        {(report.summary || report.hiring_recommendation) && (
          <div className="mt-5 rounded-xl bg-surface-card p-4">
            {report.hiring_recommendation && (
              <div className="mb-2">
                <span className={`inline-block rounded-lg px-2.5 py-1 text-xs font-semibold ${
                  report.hiring_recommendation.includes("录用")
                    ? "bg-emerald-100 text-emerald-700"
                    : report.hiring_recommendation.includes("复试")
                    ? "bg-amber-100 text-amber-700"
                    : "bg-red-100 text-red-700"
                }`}>
                  {report.hiring_recommendation}
                </span>
              </div>
            )}
            {report.summary && (
              <p className="text-sm text-ink-secondary leading-relaxed">
                {report.summary}
              </p>
            )}
          </div>
        )}
      </div>

      {/* 优缺点 */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-black/5 bg-white p-5">
          <h3 className="mb-3 text-sm font-semibold text-emerald-700">优势亮点</h3>
          <ul className="space-y-2">
            {(report.strengths || []).map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-ink-secondary">
                <span className="mt-1 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-md bg-emerald-100 text-[10px] text-emerald-600">
                  ✓
                </span>
                {s}
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-black/5 bg-white p-5">
          <h3 className="mb-3 text-sm font-semibold text-amber-700">待提升项</h3>
          <ul className="space-y-2">
            {(report.weaknesses || []).map((w, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-ink-secondary">
                <span className="mt-1 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-md bg-amber-100 text-[10px] text-amber-600">
                  !
                </span>
                {w}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* 改进建议 */}
      <div className="rounded-2xl border border-black/5 bg-white p-5">
        <h3 className="mb-3 text-sm font-semibold text-brand-700">改进建议</h3>
        <ul className="space-y-2">
          {(report.suggestions || []).map((s, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-ink-secondary">
              <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-lg bg-brand-700/8 text-[10px] font-bold text-brand-700">
                {i + 1}
              </span>
              {s}
            </li>
          ))}
        </ul>
      </div>

      {/* 逐题点评 */}
      <div className="rounded-2xl border border-black/5 bg-white p-5">
        <h3 className="mb-4 text-sm font-semibold text-ink-primary">逐题点评</h3>
        <div className="space-y-3">
          {(report.question_reviews || []).map((qr, i) => (
            <div key={i} className="rounded-xl border border-black/5 bg-surface-card p-4">
              <div className="mb-2 flex items-start justify-between gap-3">
                <p className="text-sm font-medium text-ink-primary">
                  <span className="mr-1.5 text-ink-tertiary">Q{i + 1}.</span>
                  {qr.question}
                </p>
                <QualityBadge quality={qr.answer_quality} />
              </div>
              <p className="text-sm text-ink-secondary leading-relaxed">{qr.comment}</p>
              <details className="group mt-2">
                <summary className="cursor-pointer text-xs font-medium text-brand-700 hover:text-brand-800">
                  查看参考答案
                </summary>
                <p className="mt-2 rounded-lg bg-brand-700/4 p-3 text-xs text-ink-secondary leading-relaxed">
                  {qr.reference_answer}
                </p>
              </details>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
