/**
 * 管理后台 — 用户管理
 */

"use client";

import { useState, useEffect } from "react";
import { Users, Mail, Shield, Calendar } from "lucide-react";

import { fetchAdminUsers } from "@/lib/api";
import { SidebarHeader, AdminSidebarNavGroup, SidebarDivider, SidebarFooter } from "@/components/SidebarNav";
import AdminGuard from "@/components/AdminGuard";
import LoadingSpinner from "@/components/LoadingSpinner";

interface AdminUser {
  id: number;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  session_count: number;
  created_at: string | null;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchAdminUsers()
      .then((data) => { setUsers(data.users); setTotal(data.total); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <AdminGuard>
    <div className="flex h-screen">
      <aside className="flex w-[260px] flex-shrink-0 flex-col border-r border-black/5 bg-surface-sidebar">
        <SidebarHeader />
        <SidebarDivider />
        <AdminSidebarNavGroup currentPath="/admin/users" />
        <div className="flex-1" />
        <SidebarFooter />
      </aside>

      <main className="flex flex-1 flex-col overflow-auto bg-surface-main">
        <div className="border-b border-black/5 px-8 py-5">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-brand-700" />
            <h2 className="text-lg font-semibold text-ink-primary">用户管理</h2>
          </div>
          <p className="mt-0.5 text-xs text-ink-tertiary">共 {total} 位注册用户</p>
        </div>

        <div className="flex-1 px-8 py-6">
          {loading ? (
            <LoadingSpinner text="加载用户列表..." />
          ) : users.length === 0 ? (
            <div className="py-12 text-center text-sm text-ink-tertiary">暂无用户</div>
          ) : (
            <div className="overflow-hidden rounded-2xl border border-black/5 bg-white">
              <table className="w-full">
                <thead>
                  <tr className="bg-surface-card">
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">用户名</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">邮箱</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">角色</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">状态</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">面试次数</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-ink-tertiary">注册时间</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-t border-black/5 hover:bg-surface-hover transition-colors">
                      <td className="px-4 py-3 text-sm text-ink-primary">#{u.id}</td>
                      <td className="px-4 py-3 text-sm font-medium text-ink-primary">{u.username}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5 text-sm text-ink-secondary">
                          <Mail className="h-3.5 w-3.5" />
                          {u.email}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                          u.role === "admin"
                            ? "bg-purple-50 text-purple-700"
                            : "bg-blue-50 text-blue-700"
                        }`}>
                          <Shield className="h-3 w-3" />
                          {u.role === "admin" ? "管理员" : "普通用户"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                          u.is_active ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"
                        }`}>
                          {u.is_active ? "正常" : "禁用"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-ink-secondary">{u.session_count}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5 text-xs text-ink-tertiary">
                          <Calendar className="h-3.5 w-3.5" />
                          {u.created_at ? new Date(u.created_at).toLocaleString("zh-CN") : "—"}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
    </AdminGuard>
  );
}
