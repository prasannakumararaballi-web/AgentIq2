"use client";

import React, { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { QualityGauge } from "@/components/ui/quality-gauge";
import { StatCard } from "@/components/ui/stat-card";
import {
  ShieldAlert,
  CheckCircle2,
  FileSearch,
  Database,
  ArrowRight,
  TrendingDown,
  Layers,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  Search,
  Fingerprint,
  Type,
  Maximize2,
  Shuffle,
  Binary,
  CheckSquare,
  FileCode,
  AlertOctagon,
} from "lucide-react";

interface OverviewPageProps {
  params: Promise<{ runId: string }>;
}

export default function RunOverviewPage({ params }: OverviewPageProps) {
  const { runId } = use(params);

  const { data: summary, isLoading, isError, error } = useQuery({
    queryKey: ["run-summary", runId],
    queryFn: () => apiClient.runs.getSummary(runId),
  });

  if (isLoading) {
    return (
      <div className="flex h-72 items-center justify-center rounded-xl bg-white border border-slate-200">
        <div className="flex flex-col items-center gap-3 text-sm text-slate-500">
          <RefreshCw className="h-6 w-6 animate-spin text-[#635BFF]" />
          <span className="font-medium">Aggregating dataset quality metrics...</span>
        </div>
      </div>
    );
  }

  if (isError || !summary) {
    return (
      <Card className="p-8 text-center text-xs text-rose-700 bg-rose-50 border-rose-200">
        Summary metrics currently unavailable: {(error as Error)?.message || "No data"}
      </Card>
    );
  }

  const qualityScore = summary.estimated_quality_score;
  const cleanPct = summary.total_rows > 0 ? (summary.clean_rows / summary.total_rows) * 100 : 0;
  const dirtyPct = summary.total_rows > 0 ? (summary.dirty_rows / summary.total_rows) * 100 : 0;

  // Detector category metadata with icons
  const categoryMeta: Record<string, { label: string; icon: React.ElementType; description: string }> = {
    missing_value: {
      label: "Missing Values",
      icon: Search,
      description: "Nulls, empty strings, and missing data points",
    },
    duplicate: {
      label: "Duplicate Records",
      icon: Fingerprint,
      description: "Exact duplicate rows & key collisions",
    },
    format_inconsistency: {
      label: "Format & Encoding",
      icon: FileCode,
      description: "Mojibake, UTF-8 anomalies, unescaped whitespace",
    },
    type_mismatch: {
      label: "Type Mismatches",
      icon: Type,
      description: "Integer parsed as text, invalid dates",
    },
    outlier: {
      label: "Statistical Outliers",
      icon: Maximize2,
      description: "Values exceeding 3 IQR deviation thresholds",
    },
    inconsistency: {
      label: "Cross-Field Inconsistencies",
      icon: Shuffle,
      description: "State vs zip code mismatches, conflicting dates",
    },
    business_rule_violation: {
      label: "Validation Rules",
      icon: CheckSquare,
      description: "Negative financial totals, invalid status codes",
    },
    standardization: {
      label: "Standardization",
      icon: Binary,
      description: "Country code casing and phone number formatting",
    },
  };

  return (
    <div className="space-y-6">
      {/* SECTION 1: TOP KPI CARDS WITH RADIAL GAUGE */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Quality Score Hero Card */}
        <div className="col-span-1 md:col-span-2 rounded-xl border border-slate-200/80 bg-white p-5 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-6 hover:shadow-md transition-all">
          <div className="space-y-2 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Data Quality Score
              </span>
              <Badge variant="primary" className="text-[10px] font-semibold">
                AI Evaluated
              </Badge>
            </div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900">
              {qualityScore >= 80 ? "High Quality Dataset" : qualityScore >= 60 ? "Requires Review & Remediation" : "Critical Defect Level"}
            </h2>
            <p className="text-xs text-slate-500 leading-relaxed max-w-sm">
              Computed from clean-row ratio weighted against 8 detector categories, severity impact, and anomaly density.
            </p>
            <div className="pt-1 flex items-center gap-2">
              <Link href={`/runs/${runId}/findings`}>
                <Button variant="subtle" size="xs" className="gap-1 font-semibold">
                  <span>Inspect {summary.total_findings} findings</span>
                  <ArrowRight className="h-3 w-3" />
                </Button>
              </Link>
            </div>
          </div>

          <div className="shrink-0 flex items-center justify-center p-2">
            <QualityGauge score={qualityScore} size={130} strokeWidth={11} />
          </div>
        </div>

        {/* Total Rows StatCard */}
        <StatCard
          label="Total Rows"
          value={summary.total_rows}
          subtext={`${summary.total_columns} profiled columns across dataset`}
          icon={Database}
          accentColor="indigo"
          badge={<Badge variant="outline" className="font-mono text-[10px]">100%</Badge>}
        />

        {/* Clean Rows StatCard */}
        <StatCard
          label="Clean Rows"
          value={summary.clean_rows}
          subtext={`${cleanPct.toFixed(1)}% of rows free from anomalies`}
          icon={CheckCircle2}
          accentColor="emerald"
          badge={<Badge variant="success" className="font-mono text-[10px]">Pristine</Badge>}
        />
      </div>

      {/* SECTION 2: ROW RATIO SEGMENTED VISUALIZATION */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Dataset Row Composition</h3>
            <p className="text-xs text-slate-500">Distribution of pristine rows versus rows requiring remediation</p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
              <span className="font-medium text-slate-700">Clean: {cleanPct.toFixed(1)}%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
              <span className="font-medium text-slate-700">Affected: {dirtyPct.toFixed(1)}%</span>
            </div>
          </div>
        </div>

        {/* Segmented Bar */}
        <div className="h-3.5 w-full bg-slate-100 rounded-full overflow-hidden flex shadow-inner">
          <div
            className="h-full bg-emerald-500 transition-all duration-700"
            style={{ width: `${cleanPct}%` }}
            title={`Clean Rows: ${summary.clean_rows}`}
          />
          <div
            className="h-full bg-rose-500 transition-all duration-700"
            style={{ width: `${dirtyPct}%` }}
            title={`Dirty Rows: ${summary.dirty_rows}`}
          />
        </div>
      </div>

      {/* SECTION 3: SEVERITY & CATEGORY INTELLIGENCE */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Severity Distribution Card (1 col) */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-sm flex items-center justify-between">
              <span>Severity Distribution</span>
              <ShieldAlert className="h-4 w-4 text-slate-400" />
            </CardTitle>
            <CardDescription>
              Finding severity impact classified by business and data risk.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-1">
            {Object.entries(summary.findings_by_severity || {}).map(([sev, count]) => {
              const total = summary.total_findings || 1;
              const pct = ((count / total) * 100).toFixed(0);
              const colors: Record<string, { bar: string; text: string; bg: string }> = {
                critical: { bar: "bg-rose-600", text: "text-rose-700", bg: "bg-rose-50 border-rose-200" },
                high: { bar: "bg-orange-500", text: "text-orange-700", bg: "bg-orange-50 border-orange-200" },
                medium: { bar: "bg-amber-500", text: "text-amber-700", bg: "bg-amber-50 border-amber-200" },
                low: { bar: "bg-blue-500", text: "text-blue-700", bg: "bg-blue-50 border-blue-200" },
              };
              const c = colors[sev] || { bar: "bg-slate-500", text: "text-slate-700", bg: "bg-slate-50 border-slate-200" };

              return (
                <div key={sev} className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-semibold text-slate-700 capitalize flex items-center gap-1.5">
                      <span className={`h-2 w-2 rounded-full ${c.bar}`} />
                      {sev}
                    </span>
                    <span className="font-mono font-bold text-slate-900">
                      {count} <span className="text-slate-400 font-normal">({pct}%)</span>
                    </span>
                  </div>
                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${c.bar} transition-all duration-500 rounded-full`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* 8 Detector Categories Grid (2 cols) */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm flex items-center justify-between">
              <span>Detection Engine Findings by Category</span>
              <Layers className="h-4 w-4 text-[#635BFF]" />
            </CardTitle>
            <CardDescription>
              Real findings identified across the 8 data-quality detector categories.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-1">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {Object.entries(summary.findings_by_category || {}).map(([cat, count]) => {
                const meta = categoryMeta[cat] || {
                  label: cat.replace(/_/g, " "),
                  icon: AlertTriangle,
                  description: "Quality anomaly detected in column",
                };
                const Icon = meta.icon;

                return (
                  <Link
                    key={cat}
                    href={`/runs/${runId}/findings?category=${cat}`}
                    className="flex items-start justify-between p-3 rounded-lg border border-slate-200/80 bg-white hover:bg-slate-50/80 hover:border-[#635BFF]/40 transition-all group shadow-2xs"
                  >
                    <div className="flex items-start gap-2.5">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#EEF0FF] text-[#635BFF] group-hover:bg-[#635BFF] group-hover:text-white transition-colors">
                        <Icon className="h-4 w-4" />
                      </div>
                      <div>
                        <span className="text-xs font-semibold text-slate-800 capitalize group-hover:text-[#635BFF] transition-colors block">
                          {meta.label}
                        </span>
                        <span className="text-[11px] text-slate-400 line-clamp-1">
                          {meta.description}
                        </span>
                      </div>
                    </div>

                    <Badge variant="primary" className="ml-2 font-mono font-bold shrink-0">
                      {count}
                    </Badge>
                  </Link>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* SECTION 4: CALL TO ACTION BANNER */}
      <div className="rounded-xl bg-gradient-to-r from-[#111827] via-[#1E293B] to-[#111827] text-white p-6 shadow-md border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="space-y-1 text-center md:text-left">
          <div className="flex items-center justify-center md:justify-start gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Analyst Remediation Workspace
            </span>
          </div>
          <h3 className="text-base font-bold text-white">
            Review and remediate {summary.total_findings} data quality issues
          </h3>
          <p className="text-xs text-slate-300 max-w-xl">
            Inspect individual cards, verify suggested remediation transformations, and commit reversible decisions with full audit tracking.
          </p>
        </div>

        <Link href={`/runs/${runId}/findings`}>
          <Button variant="primary" size="lg" className="gap-2 shrink-0 shadow-lg shadow-[#635BFF]/30">
            <FileSearch className="h-4 w-4" />
            <span>Open Findings Cards</span>
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </div>
    </div>
  );
}
