"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { clearSession, getStoredRole, getToken, storeSession } from "@/lib/api";
import type { AuthResponse } from "@/lib/types";

interface AuthContextValue {
  ready: boolean;
  authenticated: boolean;
  role: string | null;
  signIn: (auth: AuthResponse) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const PUBLIC_ROUTES = new Set(["/login", "/register"]);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [role, setRole] = useState<string | null>(null);
  const pathname = usePathname();
  const router = useRouter();

  const loadSession = useCallback(() => {
    const token = getToken();
    const storedRole = getStoredRole();
    setRole(token ? storedRole : null);
    setReady(true);
    if (!token && !PUBLIC_ROUTES.has(pathname)) router.replace("/login");
    if (token && PUBLIC_ROUTES.has(pathname)) router.replace("/dashboard");
  }, [pathname, router]);

  useEffect(() => {
    const timer = window.setTimeout(loadSession, 0);
    window.addEventListener("eap:unauthorized", loadSession);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("eap:unauthorized", loadSession);
    };
  }, [loadSession]);

  const signIn = useCallback((auth: AuthResponse) => {
    storeSession(auth);
    setRole(auth.role);
    router.replace("/dashboard");
  }, [router]);

  const signOut = useCallback(() => {
    clearSession();
    setRole(null);
    router.replace("/login");
  }, [router]);

  const value = useMemo(() => ({
    ready,
    authenticated: Boolean(role),
    role,
    signIn,
    signOut,
  }), [ready, role, signIn, signOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
