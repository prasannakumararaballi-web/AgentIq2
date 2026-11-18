"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { UserResponse, WorkspaceMembership } from "@/types/api";
import { apiClient } from "@/lib/api-client";
import { supabase, isSupabaseConfigured } from "@/lib/supabase";

interface AuthContextType {
  token: string | null;
  user: UserResponse | null;
  activeWorkspace: WorkspaceMembership | null;
  isLoading: boolean;
  loginWithToken: (token: string, workspaceId?: string) => Promise<void>;
  loginWithSupabase: (email: string, pass: string) => Promise<void>;
  signUpWithSupabase: (email: string, pass: string, fullName?: string) => Promise<void>;
  setActiveWorkspaceId: (workspaceId: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserResponse | null>(null);
  const [activeWorkspaceId, setActiveWorkspaceIdState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize from localStorage & sync with Supabase Auth
  useEffect(() => {
    const savedToken = typeof window !== "undefined" ? localStorage.getItem("agentiq_jwt_token") : null;
    const savedWsId = typeof window !== "undefined" ? localStorage.getItem("agentiq_active_workspace_id") : null;

    if (savedToken) {
      setToken(savedToken);
      apiClient.setSession(savedToken, savedWsId);
      apiClient.auth
        .getMe()
        .then((userData) => {
          setUser(userData);
          // Auto-select first workspace if none or invalid
          const targetWs = userData.workspaces.find((w) => w.workspace_id === savedWsId) || userData.workspaces[0];
          if (targetWs) {
            setActiveWorkspaceIdState(targetWs.workspace_id);
            apiClient.setSession(savedToken, targetWs.workspace_id);
          }
        })
        .catch(() => {
          logout();
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      setIsLoading(false);
    }

    // Subscribe to real-time Supabase Auth events
    let authListener: { unsubscribe: () => void } | null = null;
    if (isSupabaseConfigured && supabase) {
      const { data } = supabase.auth.onAuthStateChange(async (event, session) => {
        if (event === "SIGNED_IN" || event === "TOKEN_REFRESHED") {
          if (session?.access_token) {
            setToken(session.access_token);
            apiClient.setSession(session.access_token, savedWsId);
          }
        } else if (event === "SIGNED_OUT") {
          logout();
        }
      });
      authListener = data.subscription;
    }

    return () => {
      authListener?.unsubscribe();
    };
  }, []);

  const loginWithToken = async (newToken: string, workspaceId?: string) => {
    setIsLoading(true);
    try {
      apiClient.setSession(newToken, workspaceId || null);
      const userData = await apiClient.auth.getMe();
      setUser(userData);
      setToken(newToken);

      const targetWs = userData.workspaces.find((w) => w.workspace_id === workspaceId) || userData.workspaces[0];
      if (targetWs) {
        setActiveWorkspaceIdState(targetWs.workspace_id);
        apiClient.setSession(newToken, targetWs.workspace_id);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithSupabase = async (email: string, pass: string) => {
    if (!isSupabaseConfigured || !supabase) {
      throw new Error("Supabase is not configured. Check NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.");
    }

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password: pass,
    });

    if (error || !data.session) {
      throw new Error(error?.message || "Authentication failed");
    }

    await loginWithToken(data.session.access_token);
  };

  const signUpWithSupabase = async (email: string, pass: string, fullName?: string) => {
    if (!isSupabaseConfigured || !supabase) {
      throw new Error("Supabase is not configured. Check NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.");
    }

    const { data, error } = await supabase.auth.signUp({
      email,
      password: pass,
      options: {
        data: {
          full_name: fullName || email.split("@")[0],
        },
      },
    });

    if (error) {
      throw new Error(error.message);
    }

    if (data.session) {
      await loginWithToken(data.session.access_token);
    } else {
      // Email confirmation may be required depending on Supabase Auth settings
      throw new Error("Verification email sent! Please confirm your email before signing in.");
    }
  };

  const setActiveWorkspaceId = (wsId: string) => {
    setActiveWorkspaceIdState(wsId);
    apiClient.setSession(token, wsId);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setActiveWorkspaceIdState(null);
    apiClient.setSession(null, null);
    if (isSupabaseConfigured && supabase) {
      supabase.auth.signOut().catch(() => {});
    }
  };

  const activeWorkspace = user?.workspaces.find((w) => w.workspace_id === activeWorkspaceId) || null;

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        activeWorkspace,
        isLoading,
        loginWithToken,
        loginWithSupabase,
        signUpWithSupabase,
        setActiveWorkspaceId,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
