import React from "react";
import { cn } from "../lib/cn";

export interface FieldProps {
  label: string;
  required?: boolean;
  hint?: string;
  error?: string;
  counter?: { current: number; max: number };
  className?: string;
  children: React.ReactNode;
}

export function Field({
  label,
  required,
  hint,
  error,
  counter,
  className,
  children,
}: FieldProps) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-center justify-between text-sm">
        <label className="font-semibold text-text">
          {label}
          {required && <span className="text-danger ml-0.5">*</span>}
        </label>
        {counter && (
          <span
            className={cn(
              "font-mono text-xs",
              counter.current > counter.max
                ? "text-danger font-medium"
                : "text-text-muted"
            )}
          >
            {counter.current} / {counter.max}
          </span>
        )}
      </div>

      {children}

      {error ? (
        <p className="text-xs text-danger font-medium">{error}</p>
      ) : hint ? (
        <p className="text-xs text-text-muted">{hint}</p>
      ) : null}
    </div>
  );
}
