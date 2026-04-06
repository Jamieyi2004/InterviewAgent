"use client";

const STATUS_MAP: Record<string, { label: string; className: string }> = {
  in_progress: {
    label: "进行中",
    className: "bg-amber-50 text-amber-700 border-amber-200",
  },
  completed: {
    label: "已完成",
    className: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  cancelled: {
    label: "已取消",
    className: "bg-gray-50 text-gray-500 border-gray-200",
  },
};

export default function StatusBadge({ status }: { status: string }) {
  const config = STATUS_MAP[status] || STATUS_MAP.cancelled;
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}
