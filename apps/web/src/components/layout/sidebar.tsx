"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  FolderKanban,
  FileSpreadsheet,
  Cpu,
  Layers,
  Sparkles,
  LogOut,
  ChevronDown,
  Building2,
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
  History,
  Activity,
  Menu,
  X,
  FileCheck,
  Terminal,
} from "lucide-react";

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, activeWorkspace, setActiveWorkspaceId, logout } = useAuth();
  const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false);

  // Determine current active run ID if on a run page
  const runIdMatch = pathname.match(/\/runs\/([a-zA-Z0-9-]+)/);
  const currentRunId = runIdMatch ? runIdMatch[1] : null;

  const isProjectsActive = pathname === "/projects" || pathname.startsWith("/projects/");
  const isRunActive = Boolean(currentRunId);

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-[#111827] text-slate-200 border-r border-[#1F2937] transition-transform duration-200 lg:static lg:translate-x-0 ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      {/* BRAND HEADER */}
      <div className="flex h-16 items-center justify-between px-5 border-b border-[#1F2937]">
        <Link href="/projects" className="flex items-center gap-2.5 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-[#635BFF] to-[#8C85FF] text-white shadow-md shadow-[#635BFF]/30">
            <Sparkles className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-base tracking-tight text-white group-hover:text-slate-100">
                AgentIQ
              </span>
              <span className="rounded bg-[#635BFF]/20 px-1.5 py-0.5 text-[10px] font-bold text-[#A5A0FF] border border-[#635BFF]/30">
                v2
              </span>
            </div>
            <span className="text-[10px] text-slate-400 font-medium tracking-wide">
              Data Intelligence
            </span>
          </div>
        </Link>

        {/* Mobile close button */}
        {onClose && (
          <button
            onClick={onClose}
            className="lg:hidden p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* WORKSPACE SELECTOR */}
      {user && (
        <div className="px-3 py-3 border-b border-[#1F2937]">
          <div className="relative">
            <button
              onClick={() => setShowWorkspaceMenu(!showWorkspaceMenu)}
              className="w-full flex items-center justify-between rounded-lg bg-[#1F2937]/70 hover:bg-[#1F2937] px-3 py-2 text-left transition-colors border border-slate-700/60"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-[#635BFF]/30 text-[#A5A0FF] font-bold text-xs">
                  {activeWorkspace?.workspace_name?.[0] || "W"}
                </div>
                <div className="truncate">
                  <div className="text-xs font-semibold text-white truncate">
                    {activeWorkspace?.workspace_name || "Personal Workspace"}
                  </div>
                  <div className="text-[10px] text-slate-400 capitalize">
                    {activeWorkspace?.role || "Admin"} &bull; Tenant Isolation
                  </div>
                </div>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-slate-400 shrink-0 ml-1" />
            </button>

            {showWorkspaceMenu && user.workspaces && user.workspaces.length > 0 && (
              <div className="absolute left-0 right-0 top-full mt-1.5 z-50 rounded-lg bg-[#1F2937] border border-slate-700 shadow-xl py-1">
                <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Switch Workspace
                </div>
                {user.workspaces.map((ws) => (
                  <button
                    key={ws.workspace_id}
                    onClick={() => {
                      setActiveWorkspaceId(ws.workspace_id);
                      setShowWorkspaceMenu(false);
                      router.push("/projects");
                    }}
                    className={`w-full flex items-center justify-between px-3 py-1.5 text-xs text-left hover:bg-slate-800 transition-colors ${
                      ws.workspace_id === activeWorkspace?.workspace_id
                        ? "text-[#A5A0FF] font-semibold bg-[#635BFF]/10"
                        : "text-slate-300"
                    }`}
                  >
                    <span className="truncate">{ws.workspace_name}</span>
                    <span className="text-[10px] uppercase font-mono px-1 rounded bg-slate-800 text-slate-400">
                      {ws.role}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* NAVIGATION SECTIONS */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {/* Core Navigation */}
        <div className="space-y-1">
          <div className="px-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
            Platform
          </div>
          <Link
            href="/projects"
            className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
              isProjectsActive && !currentRunId
                ? "bg-[#635BFF] text-white font-semibold shadow-sm"
                : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
            }`}
          >
            <FolderKanban className="h-4 w-4 shrink-0" />
            <span>Projects & Datasets</span>
          </Link>
        </div>

        {/* Current / Active Analysis Section */}
        {currentRunId && (
          <div className="space-y-1">
            <div className="px-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
              Active Run Telemetry
            </div>
            <Link
              href={`/runs/${currentRunId}`}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                pathname === `/runs/${currentRunId}`
                  ? "bg-[#635BFF] text-white font-semibold"
                  : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
              }`}
            >
              <Activity className="h-4 w-4 shrink-0" />
              <span>Overview & KPIs</span>
            </Link>
            <Link
              href={`/runs/${currentRunId}/findings`}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                pathname.startsWith(`/runs/${currentRunId}/findings`)
                  ? "bg-[#635BFF] text-white font-semibold"
                  : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
              }`}
            >
              <FileCheck className="h-4 w-4 shrink-0" />
              <span>Findings & Remediation</span>
            </Link>
            <Link
              href={`/runs/${currentRunId}/compare`}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                pathname === `/runs/${currentRunId}/compare`
                  ? "bg-[#635BFF] text-white font-semibold"
                  : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
              }`}
            >
              <Layers className="h-4 w-4 shrink-0" />
              <span>Dataset Comparison</span>
            </Link>
            <Link
              href={`/runs/${currentRunId}/audit`}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                pathname === `/runs/${currentRunId}/audit`
                  ? "bg-[#635BFF] text-white font-semibold"
                  : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
              }`}
            >
              <History className="h-4 w-4 shrink-0" />
              <span>Audit Trail</span>
            </Link>
          </div>
        )}

        {/* Engine Status & System Info */}
        <div className="space-y-2 pt-2 border-t border-[#1F2937]">
          <div className="px-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Data Quality Engine
          </div>
          <div className="rounded-lg bg-slate-900/80 border border-slate-800 p-3 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Cpu className="h-3.5 w-3.5 text-[#635BFF]" />
                Detectors
              </span>
              <span className="font-mono font-bold text-emerald-400 text-[11px] flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                8 Active
              </span>
            </div>
            <div className="text-[10px] text-slate-400">
              DuckDB + Vectorized Pandas Core
            </div>
          </div>
        </div>
      </div>

      {/* USER ACCOUNT FOOTER */}
      {user ? (
        <div className="p-3 border-t border-[#1F2937] bg-[#0D131F]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-tr from-slate-700 to-slate-600 text-white font-bold text-xs shadow-inner">
                {user.email?.slice(0, 2).toUpperCase() || "US"}
              </div>
              <div className="truncate">
                <div className="text-xs font-semibold text-white truncate">
                  {user.email}
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-emerald-400 font-mono font-medium">
                    Verified User
                  </span>
                  <span className="text-[10px] text-slate-400">&bull;</span>
                  <span className="text-[10px] text-slate-400 uppercase font-mono">
                    {activeWorkspace?.role || "Admin"}
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={logout}
              title="Sign Out"
              className="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      ) : (
        <div className="p-3 border-t border-[#1F2937]">
          <Link href="/login">
            <Button variant="primary" size="sm" className="w-full">
              Sign In
            </Button>
          </Link>
        </div>
      )}
    </aside>
  );
}
