"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Database, ShieldCheck, LogOut, Layers, ChevronDown } from "lucide-react";

export function Navbar() {
  const { user, activeWorkspace, setActiveWorkspaceId, logout } = useAuth();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-900 text-white shadow-sm">
      <div className="flex h-14 items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Link href="/projects" className="flex items-center gap-2 font-bold text-base tracking-tight hover:opacity-95">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-600 text-white">
              <Database className="h-4 w-4" />
            </div>
            <div className="flex items-center gap-1.5">
              <span>AgentIQ</span>
              <span className="text-xs font-semibold px-1.5 py-0.2 rounded bg-blue-500/20 text-blue-300 border border-blue-400/30">
                v2
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-4 text-xs font-medium">
            <Link
              href="/projects"
              className="flex items-center gap-1.5 text-slate-300 hover:text-white transition-colors"
            >
              <Layers className="h-3.5 w-3.5" />
              <span>Projects</span>
            </Link>
          </nav>
        </div>

        {user && (
          <div className="flex items-center gap-4">
            {/* Workspace Selector */}
            {user.workspaces && user.workspaces.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 hidden sm:inline">Workspace:</span>
                <select
                  value={activeWorkspace?.workspace_id || ""}
                  onChange={(e) => setActiveWorkspaceId(e.target.value)}
                  className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
                >
                  {user.workspaces.map((ws) => (
                    <option key={ws.workspace_id} value={ws.workspace_id}>
                      {ws.workspace_name} ({ws.role})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* User Pill */}
            <div className="flex items-center gap-2 border-l border-slate-800 pl-3">
              <div className="flex flex-col text-right hidden sm:block">
                <span className="text-xs font-medium text-slate-200">{user.email}</span>
                {activeWorkspace && (
                  <span className="text-[10px] text-slate-400 capitalize">{activeWorkspace.role}</span>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={logout}
                className="text-slate-400 hover:text-white hover:bg-slate-800 h-8 w-8 p-0"
                title="Sign out"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
