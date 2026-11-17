import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "danger" | "success" | "ghost" | "subtle";
  size?: "xs" | "sm" | "md" | "lg";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", disabled, ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:pointer-events-none rounded-lg cursor-pointer active:scale-[0.99]";

    const variantStyles = {
      primary: "bg-[#635BFF] text-white hover:bg-[#5248E5] focus:ring-[#635BFF]/40 shadow-sm shadow-[#635BFF]/20 border border-[#5248E5]",
      secondary: "bg-[#111827] text-white hover:bg-[#1F2937] focus:ring-slate-400 shadow-sm",
      outline: "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 hover:text-slate-900 hover:border-slate-300 focus:ring-slate-300 shadow-xs",
      danger: "bg-rose-600 text-white hover:bg-rose-700 focus:ring-rose-500/40 shadow-sm shadow-rose-600/20 border border-rose-700",
      success: "bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-emerald-500/40 shadow-sm shadow-emerald-600/20",
      ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus:ring-slate-200",
      subtle: "bg-[#EEF0FF] text-[#635BFF] hover:bg-[#E0E4FF] focus:ring-[#635BFF]/30 font-semibold",
    };

    const sizeStyles = {
      xs: "h-7 px-2.5 text-xs gap-1 rounded-md",
      sm: "h-8 px-3 text-xs gap-1.5",
      md: "h-9 px-4 text-sm gap-2",
      lg: "h-11 px-5 text-sm gap-2.5 font-semibold",
    };

    return (
      <button
        ref={ref}
        disabled={disabled}
        className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
