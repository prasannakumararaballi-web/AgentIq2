"use client";

import React, { use, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/ui/stat-card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  GitCompare,
  FileDown,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Database,
  SlidersHorizontal,
  TableProperties,
  Sparkles,
  Download,
  FileSpreadsheet,
  Check,
  Columns,
  Layers,
  ArrowRightLeft,
} from "lucide-react";

interface ComparePageProps {
  params: Promise<{ runId: string }>;
}

export default function RunComparePage({ params }: ComparePageProps) {
  const { runId } = use(params);
  const [activeTab, setActiveTab] = useState<"matrix" | "sideBySide" | "original" | "cleaned">("matrix");
  const [exportFormat, setExportFormat] = useState<"csv" | "parquet" | "excel">("csv");
  const [isExporting, setIsExporting] = useState(false);
  const [exportResult, setExportResult] = useState<{ download_url: string; format: string; size: number } | null>(null);

  const {
    data: compareData,
    isLoading,
    isError,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: ["run-compare", runId],
    queryFn: () => apiClient.runs.getComparison(runId),
  });

  const handleExport = async (fmt: "csv" | "parquet" | "excel") => {
    try {
      setIsExporting(true);
      setExportFormat(fmt);
      const res = await apiClient.runs.createExport(runId, fmt);
      setExportResult({ download_url: res.download_url, format: res.format, size: res.file_size_bytes });
    } catch (err: unknown) {
      console.error("Export error:", err);
      alert("Export failed: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setIsExporting(false);
    }
  };

  const handleDownload = async () => {
    if (!exportResult) return;
    try {
      const token = apiClient.getToken();
      const workspaceId = apiClient.getWorkspaceId();
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const downloadPath = exportResult.download_url.startsWith("/api/v1")
        ? exportResult.download_url.replace(/^\/api\/v1/, "")
        : exportResult.download_url;
      const fullUrl = `${baseUrl}${downloadPath}`;

      const res = await fetch(fullUrl, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(workspaceId ? { "X-Workspace-ID": workspaceId } : {}),
        },
      });

      if (!res.ok) {
        throw new Error(`Download failed with status ${res.status}`);
      }

      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      const ext = exportResult.format === "excel" ? "xlsx" : exportResult.format;
      a.download = `cleaned_dataset_${runId.slice(0, 8)}.${ext}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (err: unknown) {
      alert("Download failed: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-72 items-center justify-center rounded-xl bg-white border border-slate-200">
        <div className="flex flex-col items-center gap-3 text-sm text-slate-500">
          <RefreshCw className="h-6 w-6 animate-spin text-[#635BFF]" />
          <span>Computing dataset before/after comparison matrix...</span>
        </div>
      </div>
    );
  }

  if (isError || !compareData) {
    return (
      <Card className="p-8 text-center text-xs text-rose-700 bg-rose-50 border-rose-200">
        Comparison metrics currently unavailable.
      </Card>
    );
  }

  const columns = compareData.columns_diff || [];
  const totalChanges = columns.reduce((acc, col) => acc + (col.changes_count || 0), 0);
  const totalNullsReduced = columns.reduce(
    (acc, col) => acc + Math.max(0, (col.original_nulls || 0) - (col.cleaned_nulls || 0)),
    0
  );

  // Extract column keys from preview rows
  const previewKeys = compareData.preview_original?.[0]
    ? Object.keys(compareData.preview_original[0])
    : [];

  return (
    <div className="space-y-6">
      {/* SECTION 1: COMPARISON KPI STATS */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Original Golden Records"
          value={compareData.original_rows_count}
          subtext="Raw uploaded row baseline"
          icon={Database}
          accentColor="slate"
        />

        <StatCard
          label="Cleaned Dataset Rows"
          value={compareData.cleaned_rows_count}
          subtext={`${compareData.cleaned_rows_count === compareData.original_rows_count ? "100% row preservation" : "Rows deduplicated / dropped"}`}
          icon={CheckCircle2}
          accentColor="emerald"
        />

        <StatCard
          label="Mutated Data Cells"
          value={totalChanges}
          subtext="Cells transformed by applied fixes"
          icon={Sparkles}
          accentColor="indigo"
          badge={<Badge variant="primary" className="font-mono text-[10px]">{totalChanges > 0 ? "Active" : "None"}</Badge>}
        />

        <StatCard
          label="Null Values Imputed"
          value={totalNullsReduced}
          subtext="Missing values resolved"
          icon={SlidersHorizontal}
          accentColor="emerald"
        />
      </div>

      {/* SECTION 2: EXPORT WORKSTATION */}
      <div className="rounded-xl border border-slate-200/90 bg-white p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Export Station
            </span>
            <Badge variant="success" className="text-[10px] font-semibold">
              Ready for Download
            </Badge>
          </div>
          <h3 className="text-sm font-bold text-slate-900">
            Export Remediated Dataset to Production Formats
          </h3>
          <p className="text-xs text-slate-500">
            Generates real, downloadable files containing all approved transformations and deduplications.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1">
            <Button
              variant={exportFormat === "csv" ? "primary" : "ghost"}
              size="xs"
              onClick={() => handleExport("csv")}
              disabled={isExporting}
            >
              CSV
            </Button>
            <Button
              variant={exportFormat === "excel" ? "primary" : "ghost"}
              size="xs"
              onClick={() => handleExport("excel")}
              disabled={isExporting}
            >
              Excel (.xlsx)
            </Button>
            <Button
              variant={exportFormat === "parquet" ? "primary" : "ghost"}
              size="xs"
              onClick={() => handleExport("parquet")}
              disabled={isExporting}
            >
              Parquet
            </Button>
          </div>

          {exportResult && (
            <Button
              variant="success"
              size="sm"
              onClick={handleDownload}
              className="gap-2 shadow-sm font-semibold"
            >
              <Download className="h-4 w-4" />
              <span>
                Download {exportResult.format.toUpperCase()} ({(exportResult.size / 1024).toFixed(0)} KB)
              </span>
            </Button>
          )}
        </div>
      </div>

      {/* SECTION 3: NAVIGATION TABS FOR COMPARISON VIEWS */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <div className="flex items-center gap-2">
            <Button
              variant={activeTab === "matrix" ? "primary" : "outline"}
              size="sm"
              onClick={() => setActiveTab("matrix")}
              className="gap-1.5"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              <span>Column Mutation Matrix ({columns.length})</span>
            </Button>

            <Button
              variant={activeTab === "sideBySide" ? "primary" : "outline"}
              size="sm"
              onClick={() => setActiveTab("sideBySide")}
              className="gap-1.5"
            >
              <ArrowRightLeft className="h-3.5 w-3.5" />
              <span>Side-by-Side Data Diff</span>
            </Button>

            <Button
              variant={activeTab === "cleaned" ? "primary" : "outline"}
              size="sm"
              onClick={() => setActiveTab("cleaned")}
              className="gap-1.5"
            >
              <TableProperties className="h-3.5 w-3.5" />
              <span>Cleaned Preview (10 Rows)</span>
            </Button>
          </div>

          <Button
            variant="ghost"
            size="xs"
            onClick={() => refetch()}
            disabled={isRefetching}
            className="text-xs text-slate-500 gap-1"
          >
            <RefreshCw className={`h-3 w-3 ${isRefetching ? "animate-spin" : ""}`} />
            <span>Recalculate Diff</span>
          </Button>
        </div>

        {/* TAB 1: COLUMN MUTATION MATRIX */}
        {activeTab === "matrix" && (
          <div className="rounded-xl border border-slate-200/90 bg-white overflow-hidden shadow-xs">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-[11px]">
                <tr>
                  <th className="py-3 px-4">Column Name</th>
                  <th className="py-3 px-4 text-center">Original Nulls</th>
                  <th className="py-3 px-4 text-center">Cleaned Nulls</th>
                  <th className="py-3 px-4 text-center">Nulls Reduced</th>
                  <th className="py-3 px-4 text-center">Transformed Cells</th>
                  <th className="py-3 px-4 text-right">Remediation Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {columns.map((col) => {
                  const nullDiff = Math.max(0, (col.original_nulls || 0) - (col.cleaned_nulls || 0));
                  const isModified = col.changes_count > 0 || nullDiff > 0;

                  return (
                    <tr
                      key={col.column_name}
                      className={`hover:bg-slate-50/70 transition-colors ${
                        isModified ? "bg-[#EEF0FF]/20" : ""
                      }`}
                    >
                      <td className="py-2.5 px-4 font-mono font-bold text-slate-800 flex items-center gap-1.5">
                        <Columns className="h-3.5 w-3.5 text-slate-400" />
                        {col.column_name}
                      </td>

                      <td className="py-2.5 px-4 text-center font-mono tabular-nums text-slate-600">
                        {col.original_nulls}
                      </td>

                      <td className="py-2.5 px-4 text-center font-mono tabular-nums text-slate-600">
                        {col.cleaned_nulls}
                      </td>

                      <td className="py-2.5 px-4 text-center font-mono tabular-nums">
                        {nullDiff > 0 ? (
                          <span className="text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                            -{nullDiff}
                          </span>
                        ) : (
                          <span className="text-slate-400">0</span>
                        )}
                      </td>

                      <td className="py-2.5 px-4 text-center font-mono tabular-nums">
                        {col.changes_count > 0 ? (
                          <span className="text-[#635BFF] font-bold bg-[#EEF0FF] px-2 py-0.5 rounded-full border border-[#D8DCFF]">
                            {col.changes_count} cells
                          </span>
                        ) : (
                          <span className="text-slate-400">0</span>
                        )}
                      </td>

                      <td className="py-2.5 px-4 text-right">
                        {isModified ? (
                          <Badge variant="success" className="font-semibold text-[10px]">
                            Remediated
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-[10px] text-slate-400">
                            Unchanged
                          </Badge>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* TAB 2: SIDE-BY-SIDE DIFF */}
        {activeTab === "sideBySide" && (
          <div className="rounded-xl border border-slate-200/90 bg-white overflow-hidden shadow-xs">
            <div className="p-3 bg-slate-50 border-b border-slate-200 text-xs text-slate-600 flex items-center justify-between">
              <span className="font-semibold">Side-by-Side Cell Mutation Inspection (Top 10 Rows)</span>
              <span className="text-slate-400 text-[11px]">Changed cells highlighted in green</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-100/70 border-b border-slate-200 text-slate-600 text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3">Row</th>
                    {previewKeys.map((key) => (
                      <th key={key} className="py-2.5 px-3 whitespace-nowrap">
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-[11px]">
                  {(compareData.preview_original || []).map((origRow, rowIdx) => {
                    const cleanedRow = compareData.preview_cleaned?.[rowIdx] || {};

                    return (
                      <tr key={rowIdx} className="hover:bg-slate-50/70">
                        <td className="py-2 px-3 font-sans font-bold text-slate-400 bg-slate-50/50">
                          #{rowIdx + 1}
                        </td>
                        {previewKeys.map((key) => {
                          const origVal = origRow[key];
                          const cleanVal = cleanedRow[key];
                          const isChanged = String(origVal) !== String(cleanVal);

                          return (
                            <td
                              key={key}
                              className={`py-2 px-3 whitespace-nowrap ${
                                isChanged ? "bg-emerald-50 text-emerald-800 font-bold border-l border-r border-emerald-200" : "text-slate-700"
                              }`}
                              title={isChanged ? `Original: ${String(origVal)} -> Cleaned: ${String(cleanVal)}` : undefined}
                            >
                              {String(cleanVal ?? "<NULL>")}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: CLEANED PREVIEW */}
        {activeTab === "cleaned" && (
          <div className="rounded-xl border border-slate-200/90 bg-white overflow-hidden shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3">#</th>
                    {previewKeys.map((key) => (
                      <th key={key} className="py-2.5 px-3 whitespace-nowrap">
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-[11px]">
                  {(compareData.preview_cleaned || []).map((row, i) => (
                    <tr key={i} className="hover:bg-slate-50">
                      <td className="py-2 px-3 font-sans text-slate-400">#{i + 1}</td>
                      {previewKeys.map((key) => (
                        <td key={key} className="py-2 px-3 whitespace-nowrap text-slate-800">
                          {String(row[key] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
