import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "华中师大 AI 面试官",
  description: "华中师范大学智能模拟面试系统",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-surface-main">
        {children}
      </body>
    </html>
  );
}
