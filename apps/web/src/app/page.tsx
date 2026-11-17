"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Database, RefreshCw } from "lucide-react";

export default function Home() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      if (user) {
        router.replace("/projects");
      } else {
        router.replace("/login");
      }
    }
  }, [user, isLoading, router]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-[#635BFF] to-indigo-700 text-white flex items-center justify-center shadow-md shadow-indigo-500/20">
          <Database className="h-5 w-5" />
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <RefreshCw className="h-3.5 w-3.5 animate-spin text-[#635BFF]" />
          <span className="font-medium text-slate-700">Initializing AgentIQ v2...</span>
        </div>
      </div>
    </div>
  );
}
