"use client";

import {
  Home,
  BarChart3,
  History,
  Settings,
  FileSearch,
  GraduationCap,
  BookOpen,
  Users,
  LogOut,
  User,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import { useAuthStore } from "@/store/useAuthStore";

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

/** 用户侧边栏底部：显示真实用户信息 + 退出登录 */
export function SidebarFooter() {
  const { user, logout } = useAuthStore();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <div className="border-t border-black/5 p-3">
      <div className="flex items-center gap-2.5 rounded-xl px-2.5 py-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-700/10">
          <User className="h-4 w-4 text-brand-700" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-ink-primary truncate">
            {user?.username || "未登录"}
          </p>
          <p className="text-[11px] text-ink-tertiary">
            {user?.role === "admin" ? "管理员" : "普通用户"}
          </p>
        </div>
        <button
          onClick={handleLogout}
          title="退出登录"
          className="rounded-lg p-1.5 text-ink-tertiary transition-colors hover:bg-red-50 hover:text-red-500"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

/** 用户导航组 */
export function SidebarNavGroup({ currentPath }: { currentPath: string }) {
  const { user } = useAuthStore();

  const links = [
    { href: "/", icon: Home, label: "首页" },
    { href: "/sessions", icon: History, label: "我的会话" },
    { href: "/resume-analysis?setup=1", icon: FileSearch, label: "简历分析" },
    { href: "/coaching", icon: GraduationCap, label: "面试辅导" },
    { href: "/knowledge", icon: BookOpen, label: "面试题库" },
  ];

  return (
    <nav className="flex flex-col gap-0.5 px-3 py-2">
      {links.map((link) => (
        <SidebarNavLink
          key={link.href}
          href={link.href}
          icon={link.icon}
          label={link.label}
          active={currentPath === link.href.split("?")[0]}
        />
      ))}
      {/* 管理员快捷入口 */}
      {user?.role === "admin" && (
        <>
          <SidebarDivider />
          <SidebarNavLink
            href="/admin"
            icon={Settings}
            label="管理后台"
            active={currentPath.startsWith("/admin")}
          />
        </>
      )}
    </nav>
  );
}

/** 管理员导航组 */
export function AdminSidebarNavGroup({ currentPath }: { currentPath: string }) {
  const links = [
    { href: "/admin", icon: Settings, label: "系统概览" },
    { href: "/admin/sessions", icon: History, label: "所有会话" },
    { href: "/admin/users", icon: Users, label: "用户管理" },
    { href: "/admin/dashboard", icon: BarChart3, label: "数据仪表盘" },
  ];

  return (
    <nav className="flex flex-col gap-0.5 px-3 py-2">
      {links.map((link) => (
        <SidebarNavLink
          key={link.href}
          href={link.href}
          icon={link.icon}
          label={link.label}
          active={currentPath === link.href.split("?")[0]}
        />
      ))}
      <SidebarDivider />
      <SidebarNavLink
        href="/"
        icon={Home}
        label="返回首页"
        active={false}
      />
    </nav>
  );
}
