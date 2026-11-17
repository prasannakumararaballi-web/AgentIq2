"use client";

import React, { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import {
  FolderPlus,
  UploadCloud,
  Layers,
  AlertCircle,
  ArrowRight,
  Clock,
  Plus,
  RefreshCw,
  Search,
  Database,
  Building2,
  Sparkles,
  FileSpreadsheet,
  CheckCircle2,
} from "lucide-react";

export default function ProjectsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, activeWorkspace, isLoading: authLoading } = useAuth();

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);

  const {
    data: projectsData,
    isLoading: projectsLoading,
    isError,
    error,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: ["projects", activeWorkspace?.workspace_id],
    queryFn: () => apiClient.projects.list({ limit: 50 }),
    enabled: Boolean(activeWorkspace?.workspace_id),
  });

  const createMutation = useMutation({
    mutationFn: (payload: { name: string; description?: string }) =>
      apiClient.projects.create(payload),
    onSuccess: (newProject) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowCreateDialog(false);
      setName("");
      setDescription("");
      router.push(`/projects/${newProject.id}/upload`);
    },
    onError: (err: Error) => {
      setCreateError(err.message || "Failed to create project");
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreateError(null);
    createMutation.mutate({ name: name.trim(), description: description.trim() || undefined });
  };

  const filteredProjects = useMemo(() => {
    const items = projectsData?.items || [];
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase();
    return items.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.description && p.description.toLowerCase().includes(q))
    );
  }, [projectsData?.items, searchQuery]);

  if (authLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="flex flex-col items-center gap-2 text-xs text-slate-500">
          <RefreshCw className="h-5 w-5 animate-spin text-[#635BFF]" />
          <span className="font-medium text-slate-700">Verifying tenant workspace session...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* HEADER & TENANT TELEMETRY */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Projects</h1>
            {activeWorkspace && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                <Building2 className="h-3 w-3 text-slate-500" />
                {activeWorkspace.workspace_name}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Data quality workspaces, uploaded datasets, and automated inspection histories.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={projectsLoading || isRefetching}
            className="gap-1.5 text-xs h-9 border-slate-200 text-slate-700 hover:bg-slate-50"
            title="Refresh projects list"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefetching ? "animate-spin text-[#635BFF]" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowCreateDialog(true)}
            className="gap-1.5 text-xs h-9 shadow-xs"
          >
            <Plus className="h-4 w-4" />
            <span>New Project</span>
          </Button>
        </div>
      </div>

      {/* SEARCH AND FILTER BAR */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search projects by name or description..."
            className="pl-9 text-xs h-9 bg-white border-slate-200"
          />
        </div>

        <div className="text-xs text-slate-500">
          Total: <strong className="text-slate-800">{projectsData?.total ?? 0}</strong> projects
        </div>
      </div>

      {/* CREATE PROJECT MODAL / EXPANDED FORM */}
      {showCreateDialog && (
        <Card className="border-[#635BFF]/30 bg-gradient-to-br from-indigo-50/40 via-white to-purple-50/20 shadow-sm rounded-xl">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-900">
                <div className="h-6 w-6 rounded-md bg-[#635BFF]/10 text-[#635BFF] flex items-center justify-center">
                  <FolderPlus className="h-3.5 w-3.5" />
                </div>
                <span>Create New Project</span>
              </CardTitle>
              <button
                type="button"
                onClick={() => setShowCreateDialog(false)}
                className="text-slate-400 hover:text-slate-600 text-xs font-medium"
              >
                Close
              </button>
            </div>
            <CardDescription className="text-xs text-slate-500">
              Projects provide strict tenant isolation for uploaded files, detector configurations, and audit trails.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              {createError && (
                <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
                  <span>{createError}</span>
                </div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label className="text-xs font-medium text-slate-700 block mb-1">Project Name *</label>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Q4 Customer Intelligence Scan"
                    className="text-xs h-9 bg-white"
                    required
                    autoFocus
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-700 block mb-1">Description (optional)</label>
                  <Input
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="e.g. Profiling customer contacts and purchase ledgers"
                    className="text-xs h-9 bg-white"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowCreateDialog(false)}
                  className="text-xs h-8"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={createMutation.isPending || !name.trim()}
                  className="text-xs h-8 gap-1.5 shadow-xs"
                >
                  {createMutation.isPending ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      <span>Creating...</span>
                    </>
                  ) : (
                    <>
                      <span>Create &amp; Upload Dataset</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* ERROR STATE */}
      {isError && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-3">
          <AlertCircle className="h-5 w-5 shrink-0 text-rose-600 mt-0.5" />
          <div>
            <div className="font-semibold text-rose-900">Failed to load projects</div>
            <p className="mt-0.5 text-rose-700">{(error as Error)?.message || "Internal server error"}</p>
          </div>
        </div>
      )}

      {/* LOADING STATE */}
      {projectsLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 rounded-xl border border-slate-200/80 bg-white p-5 animate-pulse space-y-3">
              <div className="h-4 bg-slate-100 rounded w-2/3" />
              <div className="h-3 bg-slate-100 rounded w-5/6" />
              <div className="h-3 bg-slate-100 rounded w-1/2 pt-4" />
            </div>
          ))}
        </div>
      )}

      {/* EMPTY STATE */}
      {!projectsLoading && filteredProjects.length === 0 && (
        <Card className="text-center py-14 border-dashed border-slate-300/80 bg-white rounded-xl">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-400 mb-3 border border-slate-200/60">
            <Layers className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-semibold text-slate-900">
            {searchQuery ? "No matching projects" : "No projects in this workspace"}
          </h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-5">
            {searchQuery
              ? `No project names match "${searchQuery}". Clear your search query to see all projects.`
              : "Create your first project to upload tabular datasets and run automated data quality detection."}
          </p>
          {searchQuery ? (
            <Button variant="outline" size="sm" onClick={() => setSearchQuery("")} className="text-xs">
              Clear Search
            </Button>
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowCreateDialog(true)}
              className="gap-1.5 text-xs shadow-xs"
            >
              <Plus className="h-4 w-4" />
              <span>Create Project</span>
            </Button>
          )}
        </Card>
      )}

      {/* PROJECTS GRID */}
      {!projectsLoading && filteredProjects.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((project) => (
            <Card
              key={project.id}
              className="group hover:border-[#635BFF]/40 hover:shadow-sm transition-all duration-200 flex flex-col justify-between bg-white rounded-xl border-slate-200/80"
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-lg bg-indigo-50 text-[#635BFF] flex items-center justify-center border border-indigo-100 shrink-0 group-hover:bg-[#635BFF] group-hover:text-white transition-colors">
                      <FileSpreadsheet className="h-4 w-4" />
                    </div>
                    <div>
                      <CardTitle className="text-sm font-semibold text-slate-900 line-clamp-1 group-hover:text-[#635BFF] transition-colors">
                        {project.name}
                      </CardTitle>
                      <span className="font-mono text-[10px] text-slate-400">
                        {project.id.slice(0, 8)}
                      </span>
                    </div>
                  </div>
                </div>
                <CardDescription className="text-xs text-slate-500 line-clamp-2 mt-2 leading-relaxed min-h-[2rem]">
                  {project.description || "No description provided for this project."}
                </CardDescription>
              </CardHeader>

              <CardContent className="pt-0 text-[11px] text-slate-400 flex items-center justify-between border-t border-slate-100 pt-3">
                <div className="flex items-center gap-1.5 text-slate-500">
                  <Clock className="h-3 w-3 text-slate-400" />
                  <span>{formatDate(project.created_at)}</span>
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => router.push(`/projects/${project.id}/upload`)}
                  className="gap-1.5 h-7 text-xs font-semibold shadow-xs"
                >
                  <UploadCloud className="h-3.5 w-3.5" />
                  <span>Upload &amp; Scan</span>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
