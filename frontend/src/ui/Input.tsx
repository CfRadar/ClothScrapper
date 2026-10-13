import React, { forwardRef } from "react";
import { cn } from "../lib/cn";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  hasError?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, hasError, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          "w-full h-10 px-3.5 rounded-input text-sm bg-surface border transition-colors duration-150 text-text placeholder:text-text-muted/60",
          hasError
            ? "border-danger focus-visible:outline-danger"
            : "border-border hover:border-border-strong focus-visible:outline-accent",
          className
        )}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";
