import { create } from "zustand";
import type { AuthUser } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isLoading: boolean;

  setAuth: (token: string, user: AuthUser) => void;
  logout: () => void;
  loadFromStorage: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isLoading: true,

  setAuth: (token, user) => {
    localStorage.setItem("token", token);
    set({ token, user, isLoading: false });
  },

  logout: () => {
    localStorage.removeItem("token");
    set({ token: null, user: null, isLoading: false });
  },

  loadFromStorage: async () => {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (!token) {
      set({ isLoading: false });
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const user = await res.json();
        set({ token, user, isLoading: false });
      } else {
        localStorage.removeItem("token");
        set({ token: null, user: null, isLoading: false });
      }
    } catch {
      set({ isLoading: false });
    }
  },
}));
