import React from "react";
import { cn } from "../lib/cn";

export interface ChipProps extends React.HTMLAttributes<HTMLDivElement> {
  active?: boolean;
  clickable?: boolean;
}

export function Chip({
  className,
  active = false,
  clickable = false,
  children,
  ...props
}: ChipProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center px-2.5 py-1 rounded-chip text-xs transition-colors duration-150 border select-none",
        active
          ? "bg-accent-soft text-accent border-accent/40 font-medium"
          : "bg-surface-2 text-text border-border",
        clickable && "cursor-pointer hover:border-border-strong hover:bg-surface",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
