"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface QualityGaugeProps {
  score: number;
  size?: number;
  strokeWidth?: number;
  showGrade?: boolean;
  className?: string;
}

export function QualityGauge({
  score,
  size = 140,
  strokeWidth = 10,
  showGrade = true,
  className,
}: QualityGaugeProps) {
  const normalizedScore = Math.min(100, Math.max(0, score));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (normalizedScore / 100) * circumference;

  const getColor = (s: number) => {
    if (s >= 85) return { stroke: "#10B981", bg: "rgba(16, 185, 129, 0.1)", text: "text-emerald-600", grade: "A", label: "Pristine" };
    if (s >= 70) return { stroke: "#635BFF", bg: "rgba(99, 91, 255, 0.1)", text: "text-[#635BFF]", grade: "B+", label: "Good Quality" };
    if (s >= 50) return { stroke: "#F59E0B", bg: "rgba(245, 158, 11, 0.1)", text: "text-amber-600", grade: "C", label: "Requires Review" };
    return { stroke: "#F43F5E", bg: "rgba(244, 63, 94, 0.1)", text: "text-rose-600", grade: "D", label: "Critical Quality" };
  };

  const color = getColor(normalizedScore);

  return (
    <div className={cn("relative flex items-center justify-center", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#E2E8F0"
          strokeWidth={strokeWidth}
          fill="transparent"
          strokeLinecap="round"
        />
        {/* Animated metric progress arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color.stroke}
          strokeWidth={strokeWidth}
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
      </svg>

      {/* Center Label */}
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <div className="flex items-baseline">
          <span className="text-2xl font-extrabold tracking-tight text-slate-900 tabular-nums">
            {normalizedScore.toFixed(1)}
          </span>
          <span className="text-xs font-semibold text-slate-400 ml-0.5">%</span>
        </div>
        {showGrade && (
          <div className="flex items-center gap-1 mt-0.5">
            <span className={cn("text-[11px] font-bold px-1.5 py-0.2 rounded font-mono", color.text)} style={{ background: color.bg }}>
              Grade {color.grade}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
