"use client";

import React, { use, useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";
import {
  History,
  ShieldCheck,
  User,
  Clock,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Filter,
  CheckCircle2,
  RotateCcw,
  AlertCircle,
  FileDown,
  Copy,
  Check,
  Zap,
  ArrowRight,
  Database,
  FileCheck,
} from "lucide-react";

interface AuditPageProps {
  params: Promise<{ runId: string }>;
}

export default function RunAuditPage({ params }: AuditPageProps) {
  const { runId } = use(params);
  const [filterAction, setFilterAction] = useState<string>("all");
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const {
    data: auditData,
    isLoading,
    isError,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: ["run-audit", runId],
    queryFn: () => apiClient.runs.getAudit(runId),
  });

  const events = useMemo(() => auditData?.events || [], [auditData?.events]);

  const counts = useMemo(() => {
    return {
      all: events.length,
      run: events.filter((e) => e.action.toLowerCase().includes("run") || e.action.toLowerCase().includes("created")).length,
      decision: events.filter((e) => e.action.toLowerCase().includes("decid") || e.action.toLowerCase().includes("approved")).length,
      undone: events.filter((e) => e.action.toLowerCase().includes("undone") || e.action.toLowerCase().includes("reject")).length,
      export: events.filter((e) => e.action.toLowerCase().includes("export")).length,
    };
  }, [events]);

  const filteredEvents = useMemo(() => {
    if (filterAction === "all") return events;
    if (filterAction === "run") return events.filter((e) => e.action.toLowerCase().includes("run") || e.action.toLowerCase().includes("created"));
    if (filterAction === "decision") return events.filter((e) => e.action.toLowerCase().includes("decid") || e.action.toLowerCase().includes("approved"));
    if (filterAction === "undone") return events.filter((e) => e.action.toLowerCase().includes("undone") || e.action.toLowerCase().includes("reject"));
    if (filterAction === "export") return events.filter((e) => e.action.toLowerCase().includes("export"));
    return events.filter((ev) => ev.action.toLowerCase().includes(filterAction.toLowerCase()));
  }, [events, filterAction]);

  const toggleExpand = (id: string) => {
    setExpandedEvents((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const expandAll = () => {
    const all = events.reduce((acc, ev) => {
      acc[ev.id] = true;
      return acc;
    }, {} as Record<string, boolean>);
    setExpandedEvents(all);
  };

  const collapseAll = () => {
    setExpandedEvents({});
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getEventMeta = (action: string) => {
    const a = action.toLowerCase();
    if (a.includes("created") || a.includes("run")) {
      return {
        badge: (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
            <Zap className="h-3 w-3 text-indigo-500" />
            {action}
          </span>
        ),
        dotColor: "bg-indigo-500 ring-indigo-100",
        icon: <Zap className="h-3.5 w-3.5 text-indigo-600" />,
      };
    }
    if (a.includes("decid") || a.includes("approved")) {
      return {
        badge: (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="h-3 w-3 text-emerald-500" />
            {action}
          </span>
        ),
        dotColor: "bg-emerald-500 ring-emerald-100",
        icon: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />,
      };
    }
    if (a.includes("undone") || a.includes("reject")) {
      return {
        badge: (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <RotateCcw className="h-3 w-3 text-amber-500" />
            {action}
          </span>
        ),
        dotColor: "bg-amber-500 ring-amber-100",
        icon: <RotateCcw className="h-3.5 w-3.5 text-amber-600" />,
      };
    }
    if (a.includes("export")) {
      return {
        badge: (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-sky-50 text-sky-700 border border-sky-200">
            <FileDown className="h-3 w-3 text-sky-500" />
            {action}
          </span>
        ),
        dotColor: "bg-sky-500 ring-sky-100",
        icon: <FileDown className="h-3.5 w-3.5 text-sky-600" />,
      };
    }
    return {
      badge: (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
          <Clock className="h-3 w-3 text-slate-500" />
          {action}
        </span>
      ),
      dotColor: "bg-slate-400 ring-slate-100",
      icon: <Clock className="h-3.5 w-3.5 text-slate-500" />,
    };
  };

  return (
    <div className="space-y-6">
      {/* HEADER HERO CARD */}
      <Card className="border-slate-200/80 shadow-xs bg-white">
        <CardContent className="p-5 sm:p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <div className="h-7 w-7 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600 border border-emerald-100">
                  <ShieldCheck className="h-4 w-4" />
                </div>
                <h2 className="text-base font-semibold text-slate-900 tracking-tight">
                  Cryptographic Audit Trail
                </h2>
                <Badge variant="outline" className="text-[10px] font-mono border-emerald-200 text-emerald-700 bg-emerald-50/50">
                  SHA-256 Ledger
                </Badge>
              </div>
              <p className="text-xs text-slate-500 max-w-2xl">
                Immutable chronological log of engine execution, analyst decisions, and exported dataset mutations for run{" "}
                <span className="font-mono text-slate-700 font-medium">{runId.slice(0, 8)}</span>.
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
                disabled={isLoading || isRefetching}
                className="text-xs h-8 gap-1.5 border-slate-200 hover:bg-slate-50 text-slate-700"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isRefetching ? "animate-spin text-[#635BFF]" : ""}`} />
                <span>Refresh Log</span>
              </Button>
            </div>
          </div>

          {/* FILTER BAR / SEGMENTED TABS */}
          <div className="mt-5 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="inline-flex p-1 bg-slate-100/80 rounded-lg gap-1 border border-slate-200/60">
              <button
                type="button"
                onClick={() => setFilterAction("all")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  filterAction === "all"
                    ? "bg-white text-slate-900 shadow-xs font-semibold"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                All Events ({counts.all})
              </button>
              <button
                type="button"
                onClick={() => setFilterAction("run")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  filterAction === "run"
                    ? "bg-white text-slate-900 shadow-xs font-semibold"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Runs ({counts.run})
              </button>
              <button
                type="button"
                onClick={() => setFilterAction("decision")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  filterAction === "decision"
                    ? "bg-white text-slate-900 shadow-xs font-semibold"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Decisions ({counts.decision})
              </button>
              <button
                type="button"
                onClick={() => setFilterAction("undone")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  filterAction === "undone"
                    ? "bg-white text-slate-900 shadow-xs font-semibold"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Reversals ({counts.undone})
              </button>
              <button
                type="button"
                onClick={() => setFilterAction("export")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  filterAction === "export"
                    ? "bg-white text-slate-900 shadow-xs font-semibold"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Exports ({counts.export})
              </button>
            </div>

            <div className="flex items-center gap-3 text-slate-500 text-[11px]">
              <span>
                Showing <strong className="text-slate-800">{filteredEvents.length}</strong> of {events.length} records
              </span>
              <span className="text-slate-300">|</span>
              <button
                type="button"
                onClick={expandAll}
                className="text-[#635BFF] hover:text-[#5248e5] font-semibold hover:underline"
              >
                Expand all
              </button>
              <span className="text-slate-300">&bull;</span>
              <button
                type="button"
                onClick={collapseAll}
                className="text-slate-500 hover:text-slate-800 font-medium hover:underline"
              >
                Collapse all
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* TIMELINE CONTAINER */}
      <div className="relative pl-7 space-y-4 before:absolute before:left-3 before:top-4 before:bottom-4 before:w-0.5 before:bg-slate-200">
        {isLoading && (
          <div className="py-16 text-center text-slate-400 text-xs">
            <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-[#635BFF]" />
            <p className="font-medium text-slate-600">Retrieving audit ledger...</p>
            <p className="text-slate-400 text-[11px] mt-0.5">Verifying event signatures with PostgreSQL</p>
          </div>
        )}

        {isError && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
            <div>
              <div className="font-semibold text-rose-900">Failed to load audit trail</div>
              <p className="mt-0.5 text-rose-700">
                Could not retrieve records for run {runId}. Verify tenant permissions or server status.
              </p>
            </div>
          </div>
        )}

        {!isLoading && filteredEvents.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-200 bg-white p-10 text-center text-slate-500 text-xs">
            <History className="h-8 w-8 mx-auto mb-2 text-slate-300" />
            <p className="font-semibold text-slate-700">No audit events found</p>
            <p className="text-slate-400 mt-1 max-w-sm mx-auto">
              {filterAction === "all"
                ? "Actions performed by the detection engine or human reviewers will appear here automatically."
                : `No events match the "${filterAction}" filter.`}
            </p>
          </div>
        )}

        {filteredEvents.map((event, idx) => {
          const isExpanded = !!expandedEvents[event.id];
          const meta = getEventMeta(event.action);
          const hasDetails = event.details && Object.keys(event.details).length > 0;

          return (
            <div key={event.id} className="relative group">
              {/* TIMELINE NODE PIN */}
              <div
                className={`absolute -left-[1.88rem] top-4 h-4 w-4 rounded-full border-2 border-white ${meta.dotColor} ring-4 transition-all shadow-xs`}
              />

              {/* EVENT CARD */}
              <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs hover:border-slate-300 transition-all space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    {meta.badge}
                    <div className="flex items-center gap-1 font-mono text-[11px] text-slate-400 bg-slate-50 px-2 py-0.5 rounded border border-slate-200/60">
                      <span>id:</span>
                      <span className="text-slate-700 font-medium">{event.id.slice(0, 8)}</span>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(event.id, event.id)}
                        className="text-slate-400 hover:text-slate-700 ml-1"
                        title="Copy Event ID"
                      >
                        {copiedId === event.id ? (
                          <Check className="h-3 w-3 text-emerald-600" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 text-[11px] text-slate-500">
                    <span className="flex items-center gap-1 font-medium">
                      <Clock className="h-3.5 w-3.5 text-slate-400" />
                      {formatDate(event.timestamp)}
                    </span>
                    {event.user_id && (
                      <span className="flex items-center gap-1 font-mono text-slate-600 bg-slate-100/80 px-2 py-0.5 rounded text-[10px] border border-slate-200/60">
                        <User className="h-3 w-3 text-slate-400" />
                        {event.user_id.slice(0, 8)}
                      </span>
                    )}
                  </div>
                </div>

                {/* SUMMARY DETAILS CHIPS */}
                {event.details && (
                  <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px]">
                    {event.details.finding_id != null && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-50 text-slate-600 rounded border border-slate-200 font-mono text-[10px]">
                        finding: <strong className="text-slate-800">{String(event.details.finding_id).slice(0, 8)}</strong>
                      </span>
                    )}
                    {event.details.decision_type != null && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded border border-emerald-200 font-medium">
                        action: {String(event.details.decision_type)}
                      </span>
                    )}
                    {event.details.status != null && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded border border-indigo-200 font-mono text-[10px]">
                        status: {String(event.details.status)}
                      </span>
                    )}
                    {event.details.format != null && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-sky-50 text-sky-700 rounded border border-sky-200 font-mono text-[10px]">
                        format: {String(event.details.format).toUpperCase()}
                      </span>
                    )}
                    {event.details.column != null && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-100 text-slate-700 rounded font-mono text-[10px]">
                        column: {String(event.details.column)}
                      </span>
                    )}
                  </div>
                )}

                {/* DETAILS ACCORDION */}
                {hasDetails && (
                  <div className="pt-1.5 border-t border-slate-100">
                    <div className="flex items-center justify-between">
                      <button
                        type="button"
                        onClick={() => toggleExpand(event.id)}
                        className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5 text-slate-500" />
                        )}
                        <span>Payload Parameters</span>
                        <span className="text-[10px] text-slate-400 font-mono font-normal">
                          ({event.details ? Object.keys(event.details).length : 0} fields)
                        </span>
                      </button>

                      {isExpanded && (
                        <button
                          type="button"
                          onClick={() => copyToClipboard(JSON.stringify(event.details, null, 2), `json-${event.id}`)}
                          className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-800 transition-colors"
                        >
                          {copiedId === `json-${event.id}` ? (
                            <>
                              <Check className="h-3 w-3 text-emerald-600" />
                              <span className="text-emerald-600 font-medium">Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="h-3 w-3" />
                              <span>Copy JSON</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>

                    {isExpanded && (
                      <div className="mt-2.5 p-3.5 bg-slate-900 text-slate-100 rounded-lg font-mono text-[11px] overflow-x-auto border border-slate-800 shadow-inner">
                        <pre className="whitespace-pre-wrap">{JSON.stringify(event.details, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
