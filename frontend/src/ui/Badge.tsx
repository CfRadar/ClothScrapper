import React from "react";
import { cn } from "../lib/cn";
import type { NodeStatus } from "../types";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status?: NodeStatus | "default";
}

export function Badge({
  className,
  status = "default",
  children,
  ...props
}: BadgeProps) {
  const statusStyles: Record<string, string> = {
    default: "bg-surface-2 text-text-muted border-border",
    idle: "bg-surface-2 text-text-muted border-border",
    queued: "bg-surface-2 text-idle border-border",
    running: "bg-accent-soft text-accent border-accent/30",
    success: "bg-success/10 text-success border-success/30",
    warning: "bg-warning/10 text-warning border-warning/30",
    error: "bg-danger/10 text-danger border-danger/30",
    skipped: "bg-surface-2 text-idle border-border opacity-70",
    cached: "bg-success/10 text-success border-success/30",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-chip text-[11px] font-medium border select-none",
        statusStyles[status] || statusStyles.default,
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
