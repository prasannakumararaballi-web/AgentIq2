"use client";

import React, { useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { FindingResponse, FindingActionType } from "@/types/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Columns,
  Sparkles,
  Info,
  Check,
  X,
  RotateCcw,
  RefreshCw,
  FileCode,
  ShieldCheck,
  AlertOctagon,
  CornerDownRight,
  Database,
  History,
} from "lucide-react";

interface FindingDetailPageProps {
  params: Promise<{ runId: string; findingId: string }>;
}

export default function FindingDetailPage({ params }: FindingDetailPageProps) {
  const { runId, findingId } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { activeWorkspace } = useAuth();

  const [notes, setNotes] = useState("");
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fetch finding by filtering the run's findings
  const { data: findingsData, isLoading } = useQuery({
    queryKey: ["findings", runId],
    queryFn: () => apiClient.runs.getFindings(runId, { limit: 100 }),
  });

  // Query audit trail to find matching decision ID if resolved
  const { data: auditData } = useQuery({
    queryKey: ["run-audit", runId],
    queryFn: () => apiClient.runs.getAudit(runId),
  });

  const finding = findingsData?.items.find((f) => f.id === findingId);

  // Find latest decision ID for this finding from audit events
  const latestDecisionId = React.useMemo(() => {
    if (!auditData?.events) return null;
    const decEvent = auditData.events.find(
      (ev) =>
        ev.action === "finding.decided" &&
        (ev.details?.finding_id === findingId || ev.details?.finding_id === finding?.id)
    );
    return (decEvent?.details?.decision_id as string) || null;
  }, [auditData, findingId, finding]);

  // Submit Decision Mutation
  const decisionMutation = useMutation({
    mutationFn: (payload: { action_type: FindingActionType; notes?: string }) =>
      apiClient.findings.submitDecision(findingId, {
        action_type: payload.action_type,
        notes: payload.notes,
        custom_parameters: finding?.suggested_action?.parameters,
      }),
    onSuccess: () => {
      setSuccessMsg("Decision committed to immutable audit trail.");
      setErrorMsg(null);
      queryClient.invalidateQueries({ queryKey: ["findings", runId] });
      queryClient.invalidateQueries({ queryKey: ["run-summary", runId] });
      queryClient.invalidateQueries({ queryKey: ["run-audit", runId] });
      queryClient.invalidateQueries({ queryKey: ["run-compare", runId] });
    },
    onError: (err: Error) => {
      setErrorMsg(err.message || "Failed to commit decision");
    },
  });

  // Undo Decision Mutation
  const undoMutation = useMutation({
    mutationFn: (decisionId: string) => apiClient.decisions.undo(decisionId),
    onSuccess: () => {
      setSuccessMsg("Decision successfully reverted. Finding restored to pending review.");
      setErrorMsg(null);
      queryClient.invalidateQueries({ queryKey: ["findings", runId] });
      queryClient.invalidateQueries({ queryKey: ["run-summary", runId] });
      queryClient.invalidateQueries({ queryKey: ["run-audit", runId] });
      queryClient.invalidateQueries({ queryKey: ["run-compare", runId] });
    },
    onError: (err: Error) => {
      setErrorMsg(err.message || "Failed to undo decision");
    },
  });

  const isViewer = activeWorkspace?.role === "viewer";

  if (isLoading) {
    return (
      <div className="flex h-72 items-center justify-center rounded-xl bg-white border border-slate-200">
        <div className="flex flex-col items-center gap-3 text-sm text-slate-500">
          <RefreshCw className="h-6 w-6 animate-spin text-[#635BFF]" />
          <span>Loading finding diagnostics...</span>
        </div>
      </div>
    );
  }

  if (!finding) {
    return (
      <div className="space-y-4">
        <Link
          href={`/runs/${runId}/findings`}
          className="text-xs text-[#635BFF] hover:underline flex items-center gap-1 font-medium"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to findings feed
        </Link>
        <Card className="p-8 text-center text-xs text-slate-500">
          Finding card &apos;{findingId}&apos; could not be located in active run.
        </Card>
      </div>
    );
  }

  const isTier3 = finding.risk_tier === 3;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* TOP NAVIGATION LINK */}
      <div className="flex items-center justify-between">
        <Link
          href={`/runs/${runId}/findings`}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5 text-slate-400" />
          <span>Back to Findings</span>
        </Link>

        <span className="text-xs font-mono text-slate-400">ID: {finding.id}</span>
      </div>

      {/* FEEDBACK NOTICES */}
      {successMsg && (
        <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            <span className="font-semibold">{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-700 hover:text-emerald-900 font-bold">
            &times;
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0" />
            <span className="font-semibold">{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-700 hover:text-rose-900 font-bold">
            &times;
          </button>
        </div>
      )}

      {/* FINDING HERO CARD */}
      <div className="rounded-xl border border-slate-200/90 bg-white p-6 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
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

              <Badge
                variant={
                  finding.severity === "critical"
                    ? "danger"
                    : finding.severity === "high"
                    ? "warning"
                    : "secondary"
                }
                dot
                className="uppercase font-bold text-[10px]"
              >
                {finding.severity}
              </Badge>

              <Badge
                variant={isTier3 ? "tier3" : finding.risk_tier === 2 ? "tier2" : "tier1"}
                className="text-[10px]"
              >
                Tier {finding.risk_tier} {isTier3 ? "&bull; Review Required" : ""}
              </Badge>
            </div>

            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              {finding.issue_title || finding.description}
            </h2>

            <p className="text-xs text-slate-600 leading-relaxed max-w-3xl">
              {finding.description}
            </p>
          </div>

          {/* Status Badge */}
          <div className="shrink-0">
            {finding.is_resolved ? (
              <Badge variant="success" className="gap-1.5 font-bold text-xs py-1 px-3">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Decision Applied</span>
              </Badge>
            ) : (
              <Badge variant="warning" className="gap-1.5 font-bold text-xs py-1 px-3">
                <AlertTriangle className="h-3.5 w-3.5" />
                <span>Pending Analyst Review</span>
              </Badge>
            )}
          </div>
        </div>

        {/* METRIC CHIPS */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-100 text-xs">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
            <span className="text-[11px] text-slate-400 block font-medium">Impacted Rows</span>
            <span className="text-lg font-bold text-slate-900 mt-0.5 block tabular-nums">
              {finding.affected_row_count.toLocaleString()}
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
            <span className="text-[11px] text-slate-400 block font-medium">Dataset Impact Ratio</span>
            <span className="text-lg font-bold text-slate-900 mt-0.5 block tabular-nums">
              {(finding.impact_estimate * 100).toFixed(1)}%
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
            <span className="text-[11px] text-slate-400 block font-medium">Detection Confidence</span>
            <span className="text-lg font-bold text-[#635BFF] mt-0.5 block tabular-nums">
              {(finding.confidence * 100).toFixed(0)}%
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
            <span className="text-[11px] text-slate-400 block font-medium">Detector Category</span>
            <span className="text-xs font-bold text-slate-800 mt-1 block capitalize truncate">
              {finding.category.replace(/_/g, " ")}
            </span>
          </div>
        </div>
      </div>

      {/* TWO-COLUMN ANALYST WORKSPACE */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEFT COLUMN: DIAGNOSTIC SAMPLES (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center justify-between">
                <span>Sample Affected Values & Proposed Output</span>
                <Database className="h-4 w-4 text-slate-400" />
              </CardTitle>
              <CardDescription>
                Direct data inspection showing sample offending raw values and expected cleaned state.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-1">
              <div className="border border-slate-200/90 rounded-lg overflow-hidden text-xs">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-[11px]">
                    <tr>
                      <th className="py-2.5 px-3 w-16">Row #</th>
                      <th className="py-2.5 px-3">Current Raw Value</th>
                      <th className="py-2.5 px-3">Proposed State</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                    {finding.sample_before && finding.sample_before.length > 0 ? (
                      finding.sample_before.map((b, i) => (
                        <tr key={i} className="hover:bg-slate-50/60">
                          <td className="py-2 px-3 text-slate-400 font-sans font-medium">
                            {b.row >= 0 ? `#${b.row}` : `Ex ${i + 1}`}
                          </td>
                          <td className="py-2 px-3 text-rose-700 bg-rose-50/40 font-bold">
                            {b.value || "<NULL>"}
                          </td>
                          <td className="py-2 px-3 text-emerald-700 bg-emerald-50/40 font-medium">
                            {finding.suggested_action?.action_type === "drop_row" ? (
                              <span className="text-rose-600 font-sans italic">&lt;Row Dropped&gt;</span>
                            ) : finding.suggested_action?.action_type === "impute" ? (
                              String(finding.suggested_action.parameters?.value || "Imputed Value")
                            ) : (
                              <span className="text-emerald-700 font-sans">Remediated via {finding.suggested_action?.action_type}</span>
                            )}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={3} className="py-4 text-center text-slate-400 italic font-sans">
                          No row-level samples attached to this finding.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* RIGHT COLUMN: ACTION & REMEDIATION CONTROL (1 col) */}
        <div className="space-y-4">
          <Card className="border-slate-300">
            <CardHeader className="bg-slate-50/70 border-b border-slate-100 rounded-t-xl">
              <CardTitle className="text-sm flex items-center justify-between">
                <span>Remediation Plan</span>
                <Sparkles className="h-4 w-4 text-[#635BFF]" />
              </CardTitle>
              <CardDescription>
                Proposed fix generated by TabularEngine
              </CardDescription>
            </CardHeader>
            <CardContent className="p-5 space-y-4">
              {finding.suggested_action ? (
                <div className="space-y-3">
                  <div>
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                      Recommended Action
                    </span>
                    <span className="font-mono text-sm font-bold text-[#635BFF] block mt-0.5 capitalize">
                      {finding.suggested_action.action_type.replace(/_/g, " ")}
                    </span>
                  </div>

                  {finding.suggested_action.rationale && (
                    <p className="text-xs text-slate-600 leading-relaxed bg-[#EEF0FF]/50 p-2.5 rounded-lg border border-[#D8DCFF]">
                      {finding.suggested_action.rationale}
                    </p>
                  )}

                  {finding.suggested_action.parameters && Object.keys(finding.suggested_action.parameters).length > 0 && (
                    <div>
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                        Execution Parameters
                      </span>
                      <pre className="text-[11px] font-mono bg-slate-900 text-slate-200 p-2.5 rounded-lg overflow-x-auto">
                        {JSON.stringify(finding.suggested_action.parameters, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic">No automated remediation suggested.</p>
              )}

              {/* TIER 3 WARNING NOTICE */}
              {isTier3 && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 space-y-1">
                  <div className="font-bold flex items-center gap-1.5">
                    <AlertOctagon className="h-4 w-4 text-rose-600 shrink-0" />
                    <span>Tier 3 Risk Warning</span>
                  </div>
                  <p className="text-[11px] text-rose-700 leading-relaxed">
                    This remediation impacts core data integrity. Human analyst approval is strictly mandatory before applying to exports.
                  </p>
                </div>
              )}

              {/* NOTES INPUT */}
              {!finding.is_resolved && (
                <div className="space-y-1.5 pt-2 border-t border-slate-100">
                  <label className="text-xs font-semibold text-slate-700 block">
                    Analyst Notes (Optional)
                  </label>
                  <textarea
                    rows={2}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Provide context for audit record..."
                    className="w-full text-xs rounded-lg border border-slate-200 p-2.5 focus:border-[#635BFF] focus:outline-none placeholder:text-slate-400"
                    disabled={isViewer || decisionMutation.isPending}
                  />
                </div>
              )}

              {/* ACTION BUTTONS */}
              <div className="space-y-2 pt-2">
                {!finding.is_resolved ? (
                  <>
                    <Button
                      variant={isTier3 ? "danger" : "primary"}
                      size="md"
                      className="w-full gap-2 font-semibold"
                      disabled={isViewer || decisionMutation.isPending}
                      onClick={() =>
                        decisionMutation.mutate({
                          action_type: finding.suggested_action?.action_type || "transform",
                          notes: notes.trim() || undefined,
                        })
                      }
                    >
                      <Check className="h-4 w-4" />
                      <span>
                        {decisionMutation.isPending
                          ? "Applying Decision..."
                          : isTier3
                          ? "Approve High-Risk Fix"
                          : "Approve & Apply Fix"}
                      </span>
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full gap-2 text-slate-600"
                      disabled={isViewer || decisionMutation.isPending}
                      onClick={() =>
                        decisionMutation.mutate({
                          action_type: "ignore",
                          notes: notes.trim() || "Dismissed by analyst as acceptable",
                        })
                      }
                    >
                      <X className="h-4 w-4" />
                      <span>Dismiss / Ignore</span>
                    </Button>
                  </>
                ) : (
                  /* UNDO CONTROLS IF RESOLVED */
                  <div className="space-y-2">
                    <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                      <span>Remediation committed and reflected in exports.</span>
                    </div>

                    {latestDecisionId && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full gap-2 text-amber-700 border-amber-300 hover:bg-amber-50"
                        disabled={isViewer || undoMutation.isPending}
                        onClick={() => undoMutation.mutate(latestDecisionId)}
                      >
                        <RotateCcw className={`h-4 w-4 ${undoMutation.isPending ? "animate-spin" : ""}`} />
                        <span>{undoMutation.isPending ? "Reverting Decision..." : "Undo Decision"}</span>
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
