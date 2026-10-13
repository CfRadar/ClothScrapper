import React, { forwardRef } from "react";
import { cn } from "../lib/cn";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  hasError?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, hasError, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          "w-full p-3 rounded-input text-sm bg-surface border transition-colors duration-150 text-text placeholder:text-text-muted/60 resize-y",
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

Textarea.displayName = "Textarea";
