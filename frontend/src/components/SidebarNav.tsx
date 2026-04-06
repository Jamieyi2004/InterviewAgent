"use client";

import { Home, BarChart3, History, Settings, FileText, ChevronRight } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";

interface NavLinkProps {
  href: string;
  icon: LucideIcon;
  label: string;
  active?: boolean;
}

export function SidebarHeader() {
  return (
    <div className="flex items-center gap-2.5 px-5 py-5">
      <Image src="/logo.png" alt="logo" width={36} height={36} className="rounded-xl" />
      <div className="min-w-0">
        <h1 className="text-sm font-semibold text-ink-primary leading-tight">AI 面试官</h1>
        <p className="text-[11px] text-ink-tertiary">华中师范大学</p>
      </div>
    </div>
  );
}

export function SidebarNavLink({ href, icon: Icon, label, active }: NavLinkProps) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm transition-all hover:bg-surface-hover active:scale-[0.98] ${
        active
          ? "bg-brand-700/8 text-brand-700 font-medium"
          : "text-ink-secondary"
      }`}
    >
      <Icon className="h-4 w-4 flex-shrink-0" />
      <span className="truncate">{label}</span>
    </Link>
  );
}

export function SidebarDivider() {
  return <div className="mx-4 my-2 border-t border-black/5" />;
}

export function SidebarFooter() {
  return (
    <div className="border-t border-black/5 p-3">
      <div className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs text-ink-tertiary">
        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-700/10">
          <span className="text-[10px] font-medium text-brand-700">AI</span>
        </div>
        <span>智能面试系统 v0.2</span>
      </div>
    </div>
  );
}

export function SidebarNavGroup({ currentPath }: { currentPath: string }) {
  const links = [
    { href: "/", icon: Home, label: "首页" },
    { href: "/sessions", icon: History, label: "会话管理" },
    { href: "/dashboard", icon: BarChart3, label: "数据仪表盘" },
    { href: "/admin", icon: Settings, label: "后台管理" },
  ];

  return (
    <nav className="flex flex-col gap-0.5 px-3 py-2">
      {links.map((link) => (
        <SidebarNavLink
          key={link.href}
          href={link.href}
          icon={link.icon}
          label={link.label}
          active={currentPath === link.href}
        />
      ))}
    </nav>
  );
}
