"use client";

import type { ReactNode } from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import {
  apiFetch,
  getToken,
  setMustChangePassword,
  setToken,
} from "../../lib/api";

export type Me = {
  id: number;
  email: string;
  display_name: string;
  is_admin: boolean;
  is_blocked: boolean;
  must_change_password: boolean;
};

type AuthContextValue = {
  me: Me | null;
  token: string | null;
  ready: boolean;
  refreshMe: () => Promise<void>;
  updateToken: (token: string | null) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [tokenState, setTokenState] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    setTokenState(getToken());
    setReady(true);
  }, []);

  const refreshMe = useCallback(async () => {
    if (!tokenState) {
      setMe(null);
      return;
    }
    try {
      const response = await apiFetch("/auth/me");
      if (!response.ok) {
        setMe(null);
        return;
      }
      const data = (await response.json()) as Me;
      setMe(data);
      setMustChangePassword(Boolean(data.must_change_password));
    } catch {
      setMe(null);
    }
  }, [tokenState]);

  useEffect(() => {
    if (!ready || !tokenState) {
      return;
    }
    refreshMe();
  }, [ready, tokenState, refreshMe]);

  const updateToken = useCallback((token: string | null) => {
    setToken(token);
    setTokenState(token);
    if (!token) {
      setMe(null);
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setMustChangePassword(false);
    setTokenState(null);
    setMe(null);
    router.push("/login");
  }, [router]);

  const value = useMemo(
    () => ({
      me,
      token: tokenState,
      ready,
      refreshMe,
      updateToken,
      logout,
    }),
    [me, tokenState, ready, refreshMe, updateToken, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
