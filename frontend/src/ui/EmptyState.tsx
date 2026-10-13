import React from "react";
import { cn } from "../lib/cn";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center space-y-3",
        className
      )}
    >
      {icon && (
        <div className="p-2.5 rounded-card bg-surface-2 text-text-muted border border-border">
          {icon}
        </div>
      )}
      <div className="space-y-1">
        <h4 className="text-xs font-semibold text-text">{title}</h4>
        {description && (
          <p className="text-[12px] text-text-muted max-w-xs">{description}</p>
        )}
      </div>
      {action && <div className="pt-1">{action}</div>}
    </div>
  );
}
