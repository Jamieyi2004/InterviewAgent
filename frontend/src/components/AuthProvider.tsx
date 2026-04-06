"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";
import { LoadingSpinner } from "@/components";

const PUBLIC_PATHS = ["/login", "/register"];

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const { user, isLoading, loadFromStorage } = useAuthStore();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  if (isLoading) {
    return <LoadingSpinner fullPage text="加载中..." />;
  }

  const isPublic = PUBLIC_PATHS.includes(pathname);

  if (!user && !isPublic) {
    router.replace("/login");
    return null;
  }

  if (user && isPublic) {
    router.replace("/");
    return null;
  }

  return <>{children}</>;
}
