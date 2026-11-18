"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { isSupabaseConfigured } from "@/lib/supabase";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Database,
  ShieldCheck,
  Key,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Sparkles,
  Lock,
  Layers,
  UserCheck,
  Eye,
  RefreshCw,
  Server,
} from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { user, loginWithToken, loginWithSupabase, signUpWithSupabase } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [customToken, setCustomToken] = useState("");
  const [activeTab, setActiveTab] = useState<"demo" | "supabase" | "manual">("demo");
  const [error, setError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    if (user) {
      router.replace("/projects");
    }
  }, [user, router]);

  // Check live backend connectivity on mount
  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
    const healthUrl = apiUrl.replace(/\/api\/v1\/?$/, "") + "/health";
    fetch(healthUrl)
      .then((r) => (r.ok ? setBackendStatus("online") : setBackendStatus("offline")))
      .catch(() => setBackendStatus("offline"));
  }, []);

  const handleDemoLogin = async (role: "admin" | "reviewer" | "viewer") => {
    setError(null);
    setIsLoading(true);
    setSelectedRole(role);
    try {
      const res = await fetch("/api/demo-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      if (!res.ok) throw new Error("Could not acquire demo token from server");
      const data = await res.json();
      await loginWithToken(data.token, data.workspace_id);
      router.push("/projects");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Demo login failed";
      setError(msg);
    } finally {
      setIsLoading(false);
      setSelectedRole(null);
    }
  };

  const handleSupabaseAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessNotice(null);
    setIsLoading(true);
    try {
      if (isSignUp) {
        await signUpWithSupabase(email, password, fullName);
      } else {
        await loginWithSupabase(email, password);
      }
      router.push("/projects");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      if (msg.includes("Verification email sent")) {
        setSuccessNotice(msg);
      } else {
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleManualTokenLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customToken.trim()) {
      setError("Please paste a valid JWT Bearer token");
      return;
    }
    setError(null);
    setIsLoading(true);
    try {
      await loginWithToken(customToken.trim());
      router.push("/projects");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Invalid or expired token";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-[80vh] items-center justify-center py-12 px-4">
      <div className="w-full max-w-md space-y-4">
        {/* BACKEND STATUS TELEMETRY CHIP */}
        <div className="flex items-center justify-between text-xs px-2 text-slate-500">
          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                backendStatus === "online"
                  ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"
                  : backendStatus === "offline"
                  ? "bg-rose-500"
                  : "bg-amber-500 animate-pulse"
              }`}
            />
            <span className="font-medium text-slate-600">
              {backendStatus === "online" ? (
                <span>API Gateway: <strong className="text-slate-800">Online</strong></span>
              ) : backendStatus === "offline" ? (
                <span>API Gateway: <strong className="text-rose-600">Offline</strong></span>
              ) : (
                <span>Connecting to Engine...</span>
              )}
            </span>
          </div>
          <span className="font-mono text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
            FastAPI + DuckDB
          </span>
        </div>

        {/* MAIN AUTH CARD */}
        <Card className="border-slate-200/80 shadow-md bg-white rounded-2xl overflow-hidden">
          <CardHeader className="text-center pb-5 pt-7">
            <div className="mx-auto flex h-13 w-13 items-center justify-center rounded-2xl bg-gradient-to-br from-[#635BFF] to-indigo-700 text-white shadow-md shadow-indigo-500/20 mb-3.5">
              <Database className="h-6 w-6" />
            </div>
            <CardTitle className="text-xl font-bold tracking-tight text-slate-900">
              AgentIQ v2
            </CardTitle>
            <CardDescription className="text-xs text-slate-500 mt-1">
              AI-Powered Data Quality &amp; Automated Remediation Platform
            </CardDescription>
          </CardHeader>

          {/* SEGMENTED TAB SELECTOR */}
          <div className="px-6 pb-2">
            <div className="grid grid-cols-3 p-1 bg-slate-100 rounded-lg text-xs font-medium text-slate-600 border border-slate-200/60">
              <button
                type="button"
                onClick={() => setActiveTab("demo")}
                className={`py-1.5 rounded-md text-center transition-all ${
                  activeTab === "demo"
                    ? "bg-white text-slate-900 font-semibold shadow-xs"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Stage Demo
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("supabase")}
                className={`py-1.5 rounded-md text-center transition-all ${
                  activeTab === "supabase"
                    ? "bg-white text-slate-900 font-semibold shadow-xs"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Supabase
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("manual")}
                className={`py-1.5 rounded-md text-center transition-all ${
                  activeTab === "manual"
                    ? "bg-white text-slate-900 font-semibold shadow-xs"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Custom JWT
              </button>
            </div>
          </div>

          <CardContent className="pt-4 px-6 space-y-4">
            {error && (
              <div className="flex items-start gap-2.5 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
                <AlertCircle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* TAB 1: ONE-CLICK DEMO AUTH */}
            {activeTab === "demo" && (
              <div className="space-y-3">
                <div className="p-3 bg-indigo-50/60 border border-indigo-200/70 rounded-xl text-xs text-indigo-900 space-y-1">
                  <div className="font-semibold flex items-center gap-1.5 text-indigo-950">
                    <Sparkles className="h-3.5 w-3.5 text-[#635BFF]" />
                    <span>Instant Stage Demo Access</span>
                  </div>
                  <p className="text-[11px] text-indigo-800 leading-relaxed">
                    Instantly mints an authenticated Supabase JWT signed with the backend secret for the pre-seeded tenant workspace.
                  </p>
                </div>

                <div className="space-y-2 pt-1">
                  {/* ADMIN ROLE */}
                  <button
                    type="button"
                    disabled={isLoading}
                    onClick={() => handleDemoLogin("admin")}
                    className="w-full text-left p-3 rounded-xl border border-slate-200/90 hover:border-[#635BFF] bg-white hover:bg-slate-50/60 transition-all flex items-center justify-between group shadow-xs disabled:opacity-60"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-900 group-hover:text-[#635BFF] transition-colors">
                          Tenant Administrator
                        </span>
                        <span className="inline-flex px-1.5 py-0.2 rounded text-[10px] font-mono font-semibold bg-indigo-100 text-[#635BFF]">
                          FULL ACCESS
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500">
                        Scan datasets, approve &amp; undo findings, and export cleaned files.
                      </p>
                    </div>
                    {isLoading && selectedRole === "admin" ? (
                      <RefreshCw className="h-4 w-4 animate-spin text-[#635BFF] shrink-0" />
                    ) : (
                      <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-[#635BFF] group-hover:translate-x-0.5 transition-all shrink-0" />
                    )}
                  </button>

                  {/* REVIEWER ROLE */}
                  <button
                    type="button"
                    disabled={isLoading}
                    onClick={() => handleDemoLogin("reviewer")}
                    className="w-full text-left p-3 rounded-xl border border-slate-200/90 hover:border-[#635BFF] bg-white hover:bg-slate-50/60 transition-all flex items-center justify-between group shadow-xs disabled:opacity-60"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-900 group-hover:text-[#635BFF] transition-colors">
                          Data Reviewer
                        </span>
                        <span className="inline-flex px-1.5 py-0.2 rounded text-[10px] font-mono font-semibold bg-slate-100 text-slate-700">
                          REVIEW &amp; UNDO
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500">
                        Human-in-the-loop decision making and audit inspection.
                      </p>
                    </div>
                    {isLoading && selectedRole === "reviewer" ? (
                      <RefreshCw className="h-4 w-4 animate-spin text-[#635BFF] shrink-0" />
                    ) : (
                      <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-[#635BFF] group-hover:translate-x-0.5 transition-all shrink-0" />
                    )}
                  </button>

                  {/* VIEWER ROLE */}
                  <button
                    type="button"
                    disabled={isLoading}
                    onClick={() => handleDemoLogin("viewer")}
                    className="w-full text-left p-3 rounded-xl border border-slate-200/80 hover:border-slate-300 bg-white hover:bg-slate-50/40 transition-all flex items-center justify-between group shadow-xs disabled:opacity-60"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-700 group-hover:text-slate-900 transition-colors">
                          Read-Only Auditor
                        </span>
                        <span className="inline-flex px-1.5 py-0.2 rounded text-[10px] font-mono font-semibold bg-slate-100 text-slate-500">
                          RBAC RESTRICTED
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400">
                        View finding telemetry and cryptographic ledger in read-only mode.
                      </p>
                    </div>
                    {isLoading && selectedRole === "viewer" ? (
                      <RefreshCw className="h-4 w-4 animate-spin text-slate-400 shrink-0" />
                    ) : (
                      <ArrowRight className="h-4 w-4 text-slate-300 group-hover:text-slate-600 group-hover:translate-x-0.5 transition-all shrink-0" />
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* TAB 2: SUPABASE AUTH */}
            {activeTab === "supabase" && (
              <form onSubmit={handleSupabaseAuth} className="space-y-3.5">
                {!isSupabaseConfigured && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-[11px] text-amber-800 leading-relaxed">
                    Live Supabase credentials not configured in environment. Set <code>NEXT_PUBLIC_SUPABASE_URL</code> and <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> or use the <strong>Stage Demo</strong> tab.
                  </div>
                )}
                {successNotice && (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                    <span>{successNotice}</span>
                  </div>
                )}
                {isSignUp && (
                  <div>
                    <label className="text-xs font-medium text-slate-700 block mb-1">Full Name</label>
                    <Input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Jane Doe"
                      className="text-xs h-9 bg-white"
                      required
                    />
                  </div>
                )}
                <div>
                  <label className="text-xs font-medium text-slate-700 block mb-1">Email Address</label>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="analyst@enterprise.com"
                    className="text-xs h-9 bg-white"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-700 block mb-1">Password</label>
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="text-xs h-9 bg-white"
                    required
                  />
                </div>
                <Button
                  type="submit"
                  variant="primary"
                  className="w-full text-xs font-semibold h-9 shadow-xs"
                  disabled={isLoading || !isSupabaseConfigured}
                >
                  {isLoading
                    ? isSignUp
                      ? "Creating Account..."
                      : "Authenticating..."
                    : isSignUp
                    ? "Create Enterprise Account"
                    : "Sign In with Supabase"}
                </Button>

                <div className="text-center pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      setIsSignUp(!isSignUp);
                      setError(null);
                      setSuccessNotice(null);
                    }}
                    className="text-[11px] text-[#635BFF] hover:underline font-medium"
                  >
                    {isSignUp
                      ? "Already have an account? Sign In"
                      : "Don't have an account? Create one"}
                  </button>
                </div>
              </form>
            )}

            {/* TAB 3: CUSTOM JWT */}
            {activeTab === "manual" && (
              <form onSubmit={handleManualTokenLogin} className="space-y-3.5">
                <div>
                  <label className="text-xs font-medium text-slate-700 block mb-1">JWT Bearer Token</label>
                  <textarea
                    rows={4}
                    value={customToken}
                    onChange={(e) => setCustomToken(e.target.value)}
                    placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                    className="w-full rounded-xl border border-slate-300 p-2.5 font-mono text-[11px] focus:border-[#635BFF] focus:outline-none focus:ring-1 focus:ring-[#635BFF] bg-white text-slate-800"
                    required
                  />
                </div>
                <Button
                  type="submit"
                  variant="primary"
                  className="w-full text-xs font-semibold h-9 shadow-xs"
                  disabled={isLoading}
                >
                  {isLoading ? "Verifying Token..." : "Authenticate Session"}
                </Button>
              </form>
            )}
          </CardContent>

          <CardFooter className="border-t border-slate-100 px-6 py-3.5 text-[11px] text-slate-500 flex items-center justify-between bg-slate-50/50">
            <span className="flex items-center gap-1">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
              <span>Multi-Tenant RBAC</span>
            </span>
            <span className="font-mono text-slate-400">AgentIQ v2.0 Enterprise</span>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
