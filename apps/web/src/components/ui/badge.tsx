import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?:
    | "default"
    | "primary"
    | "secondary"
    | "success"
    | "warning"
    | "danger"
    | "outline"
    | "tier0"
    | "tier1"
    | "tier2"
    | "tier3";
  dot?: boolean;
}

export function Badge({ className, variant = "default", dot = false, children, ...props }: BadgeProps) {
  const variantStyles = {
    default: "bg-slate-100 text-slate-700 border-slate-200/80",
    primary: "bg-[#EEF0FF] text-[#635BFF] border-[#D8DCFF] font-semibold",
    secondary: "bg-slate-100 text-slate-800 border-slate-200",
    success: "bg-emerald-50 text-emerald-700 border-emerald-200",
    warning: "bg-amber-50 text-amber-700 border-amber-200",
    danger: "bg-rose-50 text-rose-700 border-rose-200",
    outline: "border-slate-200 text-slate-600 bg-white shadow-2xs",
    // Conservative Risk Tiers
    tier0: "bg-emerald-50 text-emerald-700 border-emerald-200 font-medium",
    tier1: "bg-sky-50 text-sky-700 border-sky-200 font-medium",
    tier2: "bg-amber-50 text-amber-800 border-amber-200 font-medium",
    tier3: "bg-rose-50 text-rose-800 border-rose-300 font-semibold",
  };

  const dotColors: Record<string, string> = {
    default: "bg-slate-400",
    primary: "bg-[#635BFF]",
    secondary: "bg-slate-500",
    success: "bg-emerald-500",
    warning: "bg-amber-500",
    danger: "bg-rose-500",
    outline: "bg-slate-400",
    tier0: "bg-emerald-500",
    tier1: "bg-sky-500",
    tier2: "bg-amber-500",
    tier3: "bg-rose-500 animate-pulse",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors select-none",
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {dot && <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", dotColors[variant] || "bg-slate-400")} />}
      {children}
    </div>
  );
}
