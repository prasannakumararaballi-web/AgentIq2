"use client";

import React, { useState, useRef, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { UploadResponse } from "@/types/api";
import { formatBytes } from "@/lib/utils";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  Play,
  ArrowLeft,
  Sparkles,
  ShieldCheck,
  RefreshCw,
  Copy,
  Check,
  FileCheck,
  FileCode,
  Layers,
} from "lucide-react";

interface UploadPageProps {
  params: Promise<{ projectId: string }>;
}

export default function UploadPage({ params }: UploadPageProps) {
  const { projectId } = use(params);
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [loadingDemo, setLoadingDemo] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);

  // Upload Mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => apiClient.uploads.uploadFile(file, projectId),
    onSuccess: (data) => {
      setUploadResult(data);
      setError(null);
    },
    onError: (err: Error) => {
      setError(err.message || "Failed to upload dataset file");
    },
  });

  // Run Creation Mutation
  const runMutation = useMutation({
    mutationFn: (uploadId: string) =>
      apiClient.runs.create({ project_id: projectId, upload_id: uploadId }, true),
    onSuccess: (runData) => {
      router.push(`/runs/${runData.id}`);
    },
    onError: (err: Error) => {
      setError(err.message || "Failed to initiate data profiling run");
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setUploadResult(null);
      setError(null);
      uploadMutation.mutate(file);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setUploadResult(null);
      setError(null);
      uploadMutation.mutate(file);
    }
  };

  // Load Real Stage Demo Dataset via Next.js API route
  const handleLoadDemoDataset = async () => {
    setLoadingDemo(true);
    setError(null);
    try {
      const res = await fetch("/api/demo-dataset");
      if (!res.ok) {
        throw new Error("Could not load stage demo file from local storage");
      }
      const blob = await res.blob();
      const demoFile = new File([blob], "demo_customers_1000.csv", {
        type: "text/csv",
      });
      setSelectedFile(demoFile);
      setUploadResult(null);
      uploadMutation.mutate(demoFile);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load demo dataset";
      setError(msg);
    } finally {
      setLoadingDemo(false);
    }
  };

  const copyHash = () => {
    if (uploadResult?.file_hash) {
      navigator.clipboard.writeText(uploadResult.file_hash);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* NAVIGATION BREADCRUMB */}
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <Link
          href="/projects"
          className="hover:text-[#635BFF] flex items-center gap-1 font-medium transition-colors"
        >
          <ArrowLeft className="h-3 w-3" />
          <span>Projects</span>
        </Link>
        <span className="text-slate-300">/</span>
        <span className="font-mono text-slate-500">{projectId.slice(0, 8)}</span>
        <span className="text-slate-300">/</span>
        <span className="font-semibold text-slate-900">Upload Dataset</span>
      </div>

      <div className="border-b border-slate-200/80 pb-4">
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Upload Dataset File</h1>
        <p className="text-xs text-slate-500 mt-1">
          Stream tabular datasets for automated quality inspection. Raw files are stored immutably and verified via SHA-256.
        </p>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* STAGE DEMO PRE-LOAD ACCELERATOR BANNER */}
      <div className="p-5 rounded-xl bg-gradient-to-r from-indigo-50/80 via-white to-purple-50/50 border border-indigo-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#635BFF] text-white">
              <Sparkles className="h-3 w-3" />
              Demo Dataset
            </span>
            <span className="text-xs font-semibold text-slate-900">1,000-Row Customer Benchmark</span>
          </div>
          <p className="text-xs text-slate-600 max-w-lg leading-relaxed">
            Planted with real-world anomalies across all 8 detectors: phone format inconsistencies, salary outliers, cross-column logic violations, and duplicate emails.
          </p>
        </div>
        <Button
          type="button"
          variant="primary"
          size="sm"
          disabled={loadingDemo || uploadMutation.isPending}
          onClick={handleLoadDemoDataset}
          className="shrink-0 gap-1.5 text-xs h-9 shadow-xs"
        >
          {loadingDemo ? (
            <>
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              <span>Fetching Seed File...</span>
            </>
          ) : (
            <>
              <Sparkles className="h-3.5 w-3.5" />
              <span>Load 1,000-Row Demo CSV</span>
            </>
          )}
        </Button>
      </div>

      {/* DROPZONE CARD */}
      <Card className="border-slate-200/80 shadow-xs bg-white rounded-xl">
        <CardContent className="p-6">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.tsv,.parquet,.xlsx,.xlsm"
            className="hidden"
            onChange={handleFileChange}
          />

          {!uploadResult ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-200 ${
                isDragOver
                  ? "border-[#635BFF] bg-indigo-50/40 scale-[0.99]"
                  : "border-slate-300/80 hover:border-[#635BFF]/50 bg-slate-50/50 hover:bg-white"
              }`}
            >
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white shadow-xs border border-slate-200/80 mb-3.5 text-[#635BFF]">
                {uploadMutation.isPending ? (
                  <RefreshCw className="h-6 w-6 animate-spin text-[#635BFF]" />
                ) : (
                  <UploadCloud className="h-7 w-7" />
                )}
              </div>
              <div className="space-y-1.5">
                <p className="text-sm font-semibold text-slate-800">
                  {uploadMutation.isPending
                    ? `Streaming & hashing ${selectedFile?.name || "file"}...`
                    : "Click to upload or drag and drop tabular file"}
                </p>
                <p className="text-xs text-slate-500">
                  Supports CSV, TSV, Parquet, or Excel (.xlsx) up to 100MB
                </p>
                <div className="flex items-center justify-center gap-2 pt-2">
                  <span className="font-mono text-[10px] text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
                    .CSV
                  </span>
                  <span className="font-mono text-[10px] text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
                    .XLSX
                  </span>
                  <span className="font-mono text-[10px] text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
                    .PARQUET
                  </span>
                </div>
              </div>
            </div>
          ) : (
            /* UPLOAD SUCCESS CARD WITH IMMUTABLE HASH */
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-emerald-50/60 border border-emerald-200/80 flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0 border border-emerald-200">
                    <FileSpreadsheet className="h-5 w-5" />
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-bold text-slate-900">{uploadResult.filename}</span>
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                        <CheckCircle2 className="h-3 w-3" />
                        Verified File
                      </span>
                    </div>
                    <div className="text-xs text-slate-500 font-medium">
                      Size: {formatBytes(uploadResult.file_size_bytes)} &bull; MIME: {uploadResult.mime_type}
                    </div>
                  </div>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setUploadResult(null);
                    setSelectedFile(null);
                  }}
                  className="text-xs text-slate-600 h-8"
                >
                  Change File
                </Button>
              </div>

              {/* SHA-256 IMMUTABILITY DIGEST */}
              <div className="p-3.5 bg-slate-900 text-slate-200 rounded-xl text-xs space-y-1.5 font-mono border border-slate-800 shadow-inner">
                <div className="flex items-center justify-between text-slate-400 text-[11px] font-sans">
                  <div className="flex items-center gap-1.5">
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Cryptographic SHA-256 Digest (PostgreSQL Storage):</span>
                  </div>
                  <button
                    type="button"
                    onClick={copyHash}
                    className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors"
                  >
                    {copiedHash ? (
                      <>
                        <Check className="h-3 w-3 text-emerald-400" />
                        <span className="text-emerald-400 text-[10px]">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3 w-3" />
                        <span className="text-[10px]">Copy</span>
                      </>
                    )}
                  </button>
                </div>
                <div className="break-all text-[11px] text-emerald-400 font-semibold tracking-wider bg-slate-950 p-2 rounded border border-slate-800/80">
                  {uploadResult.file_hash}
                </div>
              </div>

              {/* START ANALYSIS ACTION BUTTON */}
              <div className="pt-2 flex items-center justify-end">
                <Button
                  variant="primary"
                  size="lg"
                  disabled={runMutation.isPending}
                  onClick={() => runMutation.mutate(uploadResult.id)}
                  className="gap-2 w-full sm:w-auto shadow-md text-xs font-semibold h-10 px-5"
                >
                  {runMutation.isPending ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      <span>Running 8 Detector Classes in TabularEngine...</span>
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 fill-white" />
                      <span>Start Real Data Quality Analysis</span>
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
