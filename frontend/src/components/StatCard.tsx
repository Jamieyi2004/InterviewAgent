"use client";

import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  subtext?: string;
  colorClass?: string;
}

export default function StatCard({
  icon: Icon,
  label,
  value,
  subtext,
  colorClass = "text-brand-700",
}: StatCardProps) {
  return (
    <div className="rounded-2xl border border-black/5 bg-white p-5 transition-shadow hover:shadow-card-hover">
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-xl bg-current/8 ${colorClass}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="text-2xl font-semibold text-ink-primary">{value}</p>
          <p className="text-xs text-ink-tertiary">{label}</p>
        </div>
      </div>
      {subtext && (
        <p className="mt-2 text-xs text-ink-secondary">{subtext}</p>
      )}
    </div>
  );
}
