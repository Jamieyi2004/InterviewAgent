"use client";

import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  text?: string;
  fullPage?: boolean;
}

export default function LoadingSpinner({
  text = "加载中...",
  fullPage = false,
}: LoadingSpinnerProps) {
  const content = (
    <div className="flex flex-col items-center justify-center gap-3">
      <Loader2 className="h-8 w-8 animate-spin text-brand-700" />
      <p className="text-sm text-ink-tertiary">{text}</p>
    </div>
  );

  if (fullPage) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-surface-main">
        {content}
      </div>
    );
  }

  return <div className="flex items-center justify-center py-12">{content}</div>;
}
