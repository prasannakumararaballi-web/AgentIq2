"use client";

import React, { useState, use, useMemo } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { FindingResponse, FindingCategory, FindingSeverity } from "@/types/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  FileSearch,
  Filter,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  Sparkles,
  RefreshCw,
  Columns,
  Search,
  X,
  SlidersHorizontal,
  Fingerprint,
  FileCode,
  Type,
  Maximize2,
  Shuffle,
  CheckSquare,
  Binary,
  Layers,
  ArrowUpDown,
  ShieldCheck,
} from "lucide-react";

interface FindingsPageProps {
  params: Promise<{ runId: string }>;
}

export default function FindingsDashboardPage({ params }: FindingsPageProps) {
  const { runId } = use(params);

  const [searchTerm, setSearchTerm] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [riskTierFilter, setRiskTierFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("severity");

  const {
    data: findingsData,
    isLoading,
    isError,
    error,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: ["findings", runId, categoryFilter, severityFilter, riskTierFilter],
    queryFn: () =>
      apiClient.runs.getFindings(runId, {
        category: categoryFilter || undefined,
        severity: severityFilter || undefined,
        risk_tier: riskTierFilter !== "" ? Number(riskTierFilter) : undefined,
        limit: 100,
      }),
  });

  const rawFindings = useMemo(() => findingsData?.items || [], [findingsData?.items]);

  // Client-side filtering & sorting
  const processedFindings = useMemo(() => {
    let result = [...rawFindings];

    // Search filter
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      result = result.filter(
        (f) =>
          f.issue_title?.toLowerCase().includes(q) ||
          f.description.toLowerCase().includes(q) ||
          f.column_name?.toLowerCase().includes(q) ||
          f.category.toLowerCase().includes(q)
      );
    }

    // Status filter
    if (statusFilter === "resolved") {
      result = result.filter((f) => f.is_resolved);
    } else if (statusFilter === "unresolved") {
      result = result.filter((f) => !f.is_resolved);
    }

    // Sorting
    const severityRank: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
    result.sort((a, b) => {
      if (sortBy === "severity") {
        return (severityRank[b.severity] || 0) - (severityRank[a.severity] || 0);
      }
      if (sortBy === "rows") {
        return (b.affected_row_count || 0) - (a.affected_row_count || 0);
      }
      if (sortBy === "tier") {
        return (b.risk_tier || 0) - (a.risk_tier || 0);
      }
      if (sortBy === "column") {
        return (a.column_name || "").localeCompare(b.column_name || "");
      }
      return 0;
    });

    return result;
  }, [rawFindings, searchTerm, statusFilter, sortBy]);

  const getSeverityBadge = (sev: FindingSeverity) => {
    switch (sev) {
      case "critical":
        return <Badge variant="danger" dot className="uppercase text-[10px] font-bold">Critical</Badge>;
      case "high":
        return <Badge variant="warning" dot className="uppercase text-[10px] font-bold">High</Badge>;
      case "medium":
        return <Badge variant="warning" dot className="uppercase text-[10px] font-medium">Medium</Badge>;
      case "low":
        return <Badge variant="secondary" dot className="uppercase text-[10px] font-medium">Low</Badge>;
    }
  };

  const getRiskBadge = (tier: number) => {
    switch (tier) {
      case 0:
        return <Badge variant="tier0" className="text-[10px]">Tier 0 &bull; Safe</Badge>;
      case 1:
        return <Badge variant="tier1" className="text-[10px]">Tier 1 &bull; Low</Badge>;
      case 2:
        return <Badge variant="tier2" className="text-[10px]">Tier 2 &bull; Moderate</Badge>;
      case 3:
        return <Badge variant="tier3" className="text-[10px]">Tier 3 &bull; Human Review</Badge>;
      default:
        return <Badge variant="outline" className="text-[10px]">Tier {tier}</Badge>;
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "missing_value":
        return Search;
      case "duplicate":
        return Fingerprint;
      case "format_inconsistency":
        return FileCode;
      case "type_mismatch":
        return Type;
      case "outlier":
        return Maximize2;
      case "business_rule_violation":
        return CheckSquare;
      default:
        return AlertTriangle;
    }
  };

  const clearAllFilters = () => {
    setSearchTerm("");
    setCategoryFilter("");
    setSeverityFilter("");
    setRiskTierFilter("");
    setStatusFilter("all");
    setSortBy("severity");
  };

  return (
    <div className="space-y-5">
      {/* FILTER & SEARCH CONTROL STATION */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-xs space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <Input
              type="text"
              placeholder="Search findings by column, issue title, category..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 h-9 text-xs"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm("")}
                className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Quick Refresh & Clear */}
          <div className="flex items-center gap-2">
            {(searchTerm || categoryFilter || severityFilter || riskTierFilter || statusFilter !== "all") && (
              <Button
                variant="ghost"
                size="xs"
                onClick={clearAllFilters}
                className="text-xs text-slate-500 hover:text-slate-900"
              >
                Clear Filters
              </Button>
            )}
            <Button
              variant="outline"
              size="xs"
              onClick={() => refetch()}
              disabled={isRefetching}
              className="gap-1.5 text-xs"
            >
              <RefreshCw className={`h-3 w-3 ${isRefetching ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </Button>
          </div>
        </div>

        {/* Dropdown Filters Row */}
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-100 text-xs">
          {/* Category Dropdown */}
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 focus:border-[#635BFF] focus:outline-none"
          >
            <option value="">All Categories (8)</option>
            <option value="missing_value">Missing Values</option>
            <option value="duplicate">Duplicates</option>
            <option value="format_inconsistency">Format & Encoding</option>
            <option value="type_mismatch">Type Mismatches</option>
            <option value="outlier">Outliers</option>
            <option value="business_rule_violation">Validation Rules</option>
          </select>

          {/* Severity Dropdown */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 focus:border-[#635BFF] focus:outline-none"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          {/* Risk Tier Dropdown */}
          <select
            value={riskTierFilter}
            onChange={(e) => setRiskTierFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 focus:border-[#635BFF] focus:outline-none"
          >
            <option value="">All Risk Tiers</option>
            <option value="0">Tier 0 (Safe Automation)</option>
            <option value="1">Tier 1 (Low Risk)</option>
            <option value="2">Tier 2 (Moderate Risk)</option>
            <option value="3">Tier 3 (Review Required)</option>
          </select>

          {/* Status Dropdown */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 focus:border-[#635BFF] focus:outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="unresolved">Pending Review</option>
            <option value="resolved">Resolved / Applied</option>
          </select>

          {/* Sort By Dropdown */}
          <div className="ml-auto flex items-center gap-1.5 text-slate-500">
            <ArrowUpDown className="h-3.5 w-3.5" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 focus:border-[#635BFF] focus:outline-none"
            >
              <option value="severity">Sort by Severity</option>
              <option value="rows">Sort by Impacted Rows</option>
              <option value="tier">Sort by Risk Tier</option>
              <option value="column">Sort by Column Name</option>
            </select>
          </div>
        </div>
      </div>

      {/* METRIC BANNER */}
      <div className="flex items-center justify-between text-xs text-slate-500 px-1">
        <span>
          Showing <span className="font-bold text-slate-900">{processedFindings.length}</span> of{" "}
          <span className="font-bold text-slate-900">{rawFindings.length}</span> finding cards
        </span>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            {rawFindings.filter((f) => f.is_resolved).length} Resolved
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            {rawFindings.filter((f) => !f.is_resolved).length} Pending Review
          </span>
        </div>
      </div>

      {/* FINDING CARDS FEED */}
      {isLoading ? (
        <div className="flex h-64 items-center justify-center rounded-xl bg-white border border-slate-200">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <RefreshCw className="h-4 w-4 animate-spin text-[#635BFF]" />
            <span>Loading finding cards...</span>
          </div>
        </div>
      ) : processedFindings.length === 0 ? (
        <div className="p-12 text-center rounded-xl border border-slate-200 bg-white shadow-xs space-y-3">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400">
            <ShieldCheck className="h-6 w-6 text-emerald-500" />
          </div>
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-slate-900">No findings match active filters</h4>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Try adjusting your search terms, severity, category, or risk tier filters above.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={clearAllFilters}>
            Reset Filters
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3.5">
          {processedFindings.map((finding) => {
            const Icon = getCategoryIcon(finding.category);

            return (
              <div
                key={finding.id}
                className={`rounded-xl border bg-white p-5 shadow-xs transition-all hover:shadow-md hover:border-slate-300 ${
                  finding.is_resolved
                    ? "border-emerald-200 bg-emerald-50/20"
                    : "border-slate-200/90"
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  {/* Left: Category Icon, Column, Title, Description */}
                  <div className="flex items-start gap-3.5 flex-1 min-w-0">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#EEF0FF] text-[#635BFF] border border-[#D8DCFF]">
                      <Icon className="h-5 w-5" />
                    </div>

                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        {/* Column Pill */}
                        {finding.column_name ? (
                          <span className="font-mono text-xs font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 flex items-center gap-1">
                            <Columns className="h-3 w-3 text-slate-500" />
                            {finding.column_name}
                          </span>
                        ) : (
                          <span className="font-mono text-xs font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                            Dataset Level
                          </span>
                        )}

                        {/* Severity & Risk Tier Badges */}
                        {getSeverityBadge(finding.severity)}
                        {getRiskBadge(finding.risk_tier)}

                        {/* Resolved Pill */}
                        {finding.is_resolved && (
                          <Badge variant="success" className="gap-1 font-semibold text-[10px]">
                            <CheckCircle2 className="h-3 w-3" /> Resolved
                          </Badge>
                        )}
                      </div>

                      <h4 className="text-sm font-bold text-slate-900 tracking-tight">
                        {finding.issue_title || finding.description}
                      </h4>

                      <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
                        {finding.description}
                      </p>
                    </div>
                  </div>

                  {/* Right: Metrics & Action CTA */}
                  <div className="flex flex-row md:flex-col items-center md:items-end justify-between md:justify-center gap-2 shrink-0 border-t md:border-t-0 md:border-l border-slate-100 pt-3 md:pt-0 md:pl-5">
                    <div className="text-left md:text-right">
                      <span className="font-mono text-xs font-bold text-slate-900 block tabular-nums">
                        {finding.affected_row_count} rows affected
                      </span>
                      {finding.suggested_action && (
                        <span className="text-[11px] text-slate-400 capitalize block">
                          Suggested: <span className="font-semibold text-slate-700">{finding.suggested_action.action_type.replace(/_/g, " ")}</span>
                        </span>
                      )}
                    </div>

                    <Link href={`/runs/${runId}/findings/${finding.id}`}>
                      <Button
                        variant={finding.is_resolved ? "outline" : "primary"}
                        size="sm"
                        className="gap-1.5"
                      >
                        <span>{finding.is_resolved ? "View Decision" : "Review & Fix"}</span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
