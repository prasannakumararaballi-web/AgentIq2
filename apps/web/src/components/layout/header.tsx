"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Menu,
  ChevronRight,
  Database,
  ExternalLink,
  ShieldCheck,
  Activity,
  Layers,
  Sparkles,
  HelpCircle,
} from "lucide-react";

interface HeaderProps {
  onToggleSidebar?: () => void;
}

export function Header({ onToggleSidebar }: HeaderProps) {
  const pathname = usePathname();
  const { user, activeWorkspace } = useAuth();
  const [backendHealth, setBackendHealth] = useState<"checking" | "healthy" | "offline">("checking");

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    const healthUrl = apiUrl.replace(/\/api\/v1\/?$/, "") + "/health";
    fetch(healthUrl)
      .then((r) => (r.ok ? setBackendHealth("healthy") : setBackendHealth("offline")))
      .catch(() => setBackendHealth("offline"));
  }, []);

  // Compute dynamic breadcrumbs from path
  const getBreadcrumbs = () => {
    const parts = pathname.split("/").filter(Boolean);
    const crumbs = [];

    if (parts.length === 0 || parts[0] === "projects") {
      crumbs.push({ label: "Projects", href: "/projects" });
      if (parts.length > 2 && parts[2] === "upload") {
        crumbs.push({ label: "Upload Dataset", href: pathname });
      }
    } else if (parts[0] === "runs" && parts[1]) {
      crumbs.push({ label: "Projects", href: "/projects" });
      crumbs.push({ label: `Run ${parts[1].slice(0, 8)}...`, href: `/runs/${parts[1]}` });
      if (parts[2]) {
        const sub = parts[2] === "findings" ? "Findings" : parts[2] === "compare" ? "Comparison" : "Audit Trail";
        crumbs.push({ label: sub, href: pathname });
      }
    } else if (parts[0] === "login") {
      crumbs.push({ label: "Authentication", href: "/login" });
    }

    return crumbs;
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-slate-200/80 bg-white/80 px-4 sm:px-6 backdrop-blur-md">
      {/* Left: Mobile hamburger & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="lg:hidden p-2 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          title="Toggle Navigation"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Dynamic Breadcrumbs */}
        <nav className="flex items-center gap-1.5 text-xs text-slate-500 font-medium overflow-x-auto py-1">
          <span className="hidden sm:inline font-semibold text-slate-800">
            {activeWorkspace?.workspace_name || "AgentIQ"}
          </span>
          {breadcrumbs.map((crumb, idx) => (
            <React.Fragment key={crumb.href + idx}>
              <ChevronRight className="h-3 w-3 text-slate-400 shrink-0" />
              <Link
                href={crumb.href}
                className={`transition-colors whitespace-nowrap ${
                  idx === breadcrumbs.length - 1
                    ? "font-semibold text-slate-900"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                {crumb.label}
              </Link>
            </React.Fragment>
          ))}
        </nav>
      </div>

      {/* Right: Engine status & Quick Links */}
      <div className="flex items-center gap-3">
        {/* Backend Engine Status Pill */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200 text-xs">
          <span
            className={`h-2 w-2 rounded-full shrink-0 ${
              backendHealth === "healthy"
                ? "bg-emerald-500 shadow-xs shadow-emerald-500"
                : backendHealth === "checking"
                ? "bg-amber-400 animate-pulse"
                : "bg-rose-500"
            }`}
          />
          <span className="text-[11px] font-medium text-slate-600">
            {backendHealth === "healthy"
              ? "Engine Active"
              : backendHealth === "checking"
              ? "Connecting..."
              : "Backend Offline"}
          </span>
        </div>

        {/* Interactive API Docs Link */}
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden md:flex items-center gap-1 text-xs text-slate-500 hover:text-slate-900 transition-colors px-2.5 py-1 rounded-lg hover:bg-slate-100"
        >
          <span>API Docs</span>
          <ExternalLink className="h-3 w-3" />
        </a>

        {/* Quick New Project CTA */}
        {pathname !== "/projects" && (
          <Link href="/projects">
            <Button variant="outline" size="xs" className="gap-1.5 text-xs">
              <Layers className="h-3.5 w-3.5 text-[#635BFF]" />
              <span>All Projects</span>
            </Button>
          </Link>
        )}
      </div>
    </header>
  );
}
