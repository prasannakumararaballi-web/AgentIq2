import React from "react";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: LucideIcon;
  badge?: React.ReactNode;
  accentColor?: "indigo" | "emerald" | "rose" | "amber" | "slate";
  className?: string;
}

export function StatCard({
  label,
  value,
  subtext,
  icon: Icon,
  badge,
  accentColor = "slate",
  className,
}: StatCardProps) {
  const accentClasses = {
    indigo: "border-l-4 border-l-[#635BFF]",
    emerald: "border-l-4 border-l-emerald-500",
    rose: "border-l-4 border-l-rose-500",
    amber: "border-l-4 border-l-amber-500",
    slate: "border-l-4 border-l-slate-400",
  };

  const iconBgClasses = {
    indigo: "bg-[#EEF0FF] text-[#635BFF]",
    emerald: "bg-emerald-50 text-emerald-600",
    rose: "bg-rose-50 text-rose-600",
    amber: "bg-amber-50 text-amber-600",
    slate: "bg-slate-100 text-slate-600",
  };

  return (
    <div
      className={cn(
        "rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_1px_3px_0_rgba(0,0,0,0.03)] transition-all hover:shadow-md hover:border-slate-300",
        accentClasses[accentColor],
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">{label}</span>
        {Icon && (
          <div className={cn("flex h-7 w-7 items-center justify-center rounded-lg", iconBgClasses[accentColor])}>
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>

      <div className="mt-2 flex items-baseline justify-between">
        <span className="text-2xl font-bold tracking-tight text-slate-900 tabular-nums">
          {typeof value === "number" ? value.toLocaleString() : value}
        </span>
        {badge}
      </div>

      {subtext && <p className="mt-1 text-xs text-slate-500 truncate">{subtext}</p>}
    </div>
  );
}
