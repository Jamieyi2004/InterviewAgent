"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";
import type { LucideIcon } from "lucide-react";

interface CollapsibleSectionProps {
  title: string;
  icon?: LucideIcon;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

export default function CollapsibleSection({
  title,
  icon: Icon,
  defaultOpen = true,
  children,
}: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-2xl border border-black/5 bg-white overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-5 py-4 text-left transition-colors hover:bg-surface-hover"
      >
        {Icon && <Icon className="h-4 w-4 text-ink-secondary" />}
        <span className="flex-1 text-sm font-medium text-ink-primary">{title}</span>
        <ChevronDown
          className={`h-4 w-4 text-ink-tertiary transition-transform duration-200 ${
            open ? "rotate-0" : "-rotate-90"
          }`}
        />
      </button>
      {open && (
        <div className="border-t border-black/5 px-5 py-4">{children}</div>
      )}
    </div>
  );
}
