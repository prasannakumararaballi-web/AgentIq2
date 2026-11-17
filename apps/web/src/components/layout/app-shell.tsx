"use client";

import React, { useState, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { RefreshCw, Database } from "lucide-react";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading } = useAuth();

  const isLoginPage = pathname === "/login";

  useEffect(() => {
    if (!isLoading) {
      if (!user && !isLoginPage) {
        router.replace("/login");
      } else if (user && isLoginPage) {
        router.replace("/projects");
      }
    }
  }, [user, isLoading, isLoginPage, router]);

  // Auth pages (login / signup) - render clean full-screen layout
  if (isLoginPage) {
    return (
      <div className="min-h-screen bg-[#F6F7FB] flex flex-col justify-center">
        {children}
      </div>
    );
  }

  // Session verification state
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F6F7FB]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-[#635BFF] to-indigo-700 text-white flex items-center justify-center shadow-md shadow-indigo-500/20">
            <Database className="h-5 w-5" />
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <RefreshCw className="h-3.5 w-3.5 animate-spin text-[#635BFF]" />
            <span className="font-medium text-slate-700">Verifying session...</span>
          </div>
        </div>
      </div>
    );
  }

  // Guard: if unauthenticated, do not render protected children while redirecting
  if (!user) {
    return null;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#F6F7FB]">
      {/* Mobile Backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-xs lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Primary Sidebar (#111827) */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Canvas Area */}
      <div className="flex flex-1 flex-col overflow-y-auto">
        <Header onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
        <main className="flex-1 px-4 sm:px-8 py-6 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
