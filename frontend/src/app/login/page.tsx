"use client";

import { loginUser } from "@/lib/api";
import { useAuthStore } from "@/store/useAuthStore";
import { Loader2 } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await loginUser(email, password);
      setAuth(data.access_token, data.user);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-main px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center">
          <Image
            src="/logo.png"
            alt="AI 面试官"
            width={56}
            height={56}
            className="mb-3 rounded-2xl"
          />
          <h1 className="text-xl font-semibold text-ink-primary">AI 面试官</h1>
          <p className="mt-1 text-sm text-ink-tertiary">华中师范大学智能模拟面试系统</p>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="rounded-2xl border border-black/5 bg-surface-card p-6 space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-primary">邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              className="w-full rounded-xl border border-black/8 bg-white px-4 py-2.5 text-sm text-ink-primary outline-none placeholder:text-ink-disabled transition-colors focus:border-brand-700/40 focus:ring-2 focus:ring-brand-700/8"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-primary">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="输入密码"
              required
              className="w-full rounded-xl border border-black/8 bg-white px-4 py-2.5 text-sm text-ink-primary outline-none placeholder:text-ink-disabled transition-colors focus:border-brand-700/40 focus:ring-2 focus:ring-brand-700/8"
            />
          </div>

          {error && (
            <p className="text-sm text-red-500">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-700 py-2.5 text-sm font-medium text-white transition-all hover:bg-brand-800 active:scale-[0.98] disabled:opacity-60"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? "登录中..." : "登录"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-ink-tertiary">
          还没有账号？{" "}
          <Link href="/register" className="font-medium text-brand-700 hover:underline">
            注册
          </Link>
        </p>
      </div>
    </div>
  );
}
