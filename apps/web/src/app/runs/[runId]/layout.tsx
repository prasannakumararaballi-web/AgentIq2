"use client";

import React, { use, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";
import {
  BarChart3,
  FileSearch,
  GitCompare,
  History,
  CheckCircle2,
  Clock,
  AlertCircle,
  RefreshCw,
  Copy,
  Check,
  Cpu,
  Layers,
  ArrowRight,
} from "lucide-react";

interface RunLayoutProps {
  children: React.ReactNode;
  params: Promise<{ runId: string }>;
}

export default function RunLayout({ children, params }: RunLayoutProps) {
  const { runId } = use(params);
  const pathname = usePathname();
  const [copied, setCopied] = useState(false);

  const { data: run } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => apiClient.runs.get(runId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && (data.status === "completed" || data.status === "failed")) {
        return false;
      }
      return 2000;
    },
  });

  const { data: summary } = useQuery({
    queryKey: ["run-summary", runId],
    queryFn: () => apiClient.runs.getSummary(runId),
    enabled: run?.status === "completed",
  });

  const handleCopyId = () => {
    navigator.clipboard.writeText(runId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const tabs = [
    {
      name: "Overview & Intelligence",
      href: `/runs/${runId}`,
      icon: BarChart3,
      exact: true,
    },
    {
      name: "Finding Cards",
      href: `/runs/${runId}/findings`,
      icon: FileSearch,
      count: summary?.total_findings,
    },
    {
      name: "Dataset Comparison",
      href: `/runs/${runId}/compare`,
      icon: GitCompare,
    },
    {
      name: "Audit Trail",
      href: `/runs/${runId}/audit`,
      icon: History,
    },
  ];

  const getStatusBadge = () => {
    if (!run) return null;
    switch (run.status) {
      case "completed":
        return (
          <Badge variant="success" dot className="font-semibold text-xs px-2.5 py-0.5">
            Analysis Completed
          </Badge>
        );
      case "processing":
        return (
          <Badge variant="primary" dot className="font-semibold text-xs px-2.5 py-0.5 animate-pulse">
            Profiling Dataset...
          </Badge>
        );
      case "failed":
        return (
          <Badge variant="danger" dot className="font-semibold text-xs px-2.5 py-0.5">
            Execution Failed
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" dot className="font-semibold text-xs px-2.5 py-0.5">
            Queued
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* RUN TELEMETRY BANNER */}
      <div className="rounded-xl border border-slate-200/80 bg-white shadow-xs p-5 transition-all">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          {/* Left: Project title & identifiers */}
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Run Execution
              </span>
              <div className="flex items-center gap-1.5 rounded-md bg-slate-100 px-2 py-0.5 border border-slate-200">
                <span className="font-mono text-xs font-bold text-slate-800">
                  {runId.slice(0, 13)}...
                </span>
                <button
                  onClick={handleCopyId}
                  className="text-slate-400 hover:text-slate-700 transition-colors p-0.5"
                  title="Copy full Run UUID"
                >
                  {copied ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                </button>
              </div>
              {getStatusBadge()}
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5 text-slate-400" />
                Started: {formatDate(run?.started_at || run?.created_at)}
              </span>
              {run?.completed_at && (
                <span>&bull; Completed: {formatDate(run.completed_at)}</span>
              )}
            </div>
          </div>

          {/* Right: Engine Pipeline Telemetry */}
          {run && (
            <div className="flex items-center gap-4 lg:border-l lg:border-slate-100 lg:pl-6">
              <div className="text-left lg:text-right">
                <div className="text-xs font-semibold text-slate-700 flex items-center lg:justify-end gap-1.5">
                  <Cpu className="h-3.5 w-3.5 text-[#635BFF]" />
                  Stage: <span className="capitalize font-bold text-[#635BFF]">{run.stage || "Completed"}</span>
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5 font-mono">
                  {run.progress?.message || "All detectors executed & summary generated"}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* PROCESSING PROGRESS BAR */}
        {run && run.status === "processing" && (
          <div className="mt-4 pt-3 border-t border-slate-100 space-y-1.5">
            <div className="flex justify-between text-xs font-medium text-slate-600">
              <span>Profiling tabular dataset & executing 8 detectors</span>
              <span className="font-mono font-bold text-[#635BFF]">{run.progress?.total_percent || 0}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full bg-[#635BFF] transition-all duration-300 rounded-full shadow-xs"
                style={{ width: `${run.progress?.total_percent || 0}%` }}
              />
            </div>
          </div>
        )}

        {/* ERROR NOTICE IF FAILED */}
        {run?.status === "failed" && run.error_message && (
          <div className="mt-4 p-3.5 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-start gap-2.5">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
            <div>
              <span className="font-bold">Execution Error: </span>
              <span>{run.error_message}</span>
            </div>
          </div>
        )}

        {/* REFINED NAVIGATION TABS */}
        <div className="mt-5 -mb-5 flex border-b border-slate-200 gap-1 overflow-x-auto text-xs font-medium scrollbar-none">
          {tabs.map((tab) => {
            const isActive = tab.exact ? pathname === tab.href : pathname.startsWith(tab.href);
            const Icon = tab.icon;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={`flex items-center gap-2 pb-3.5 px-4 border-b-2 transition-all whitespace-nowrap ${
                  isActive
                    ? "border-[#635BFF] text-[#635BFF] font-semibold"
                    : "border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-[#635BFF]" : "text-slate-400"}`} />
                <span>{tab.name}</span>
                {tab.count !== undefined && (
                  <span
                    className={`ml-1 text-[11px] px-2 py-0.5 rounded-full font-bold tabular-nums ${
                      isActive ? "bg-[#EEF0FF] text-[#635BFF]" : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </div>

      {/* SUB-SCREEN CONTENT */}
      <div>{children}</div>
    </div>
  );
}
