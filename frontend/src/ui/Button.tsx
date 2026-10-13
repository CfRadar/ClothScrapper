import React, { forwardRef } from "react";
import { cn } from "../lib/cn";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "icon";
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "secondary",
      size = "md",
      loading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium rounded-input transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed select-none focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2";

    const variants = {
      primary: "bg-accent text-white hover:brightness-105 active:brightness-95",
      secondary:
        "bg-surface text-text border border-border hover:bg-surface-2 hover:border-border-strong",
      ghost:
        "bg-transparent text-text hover:bg-surface-2 active:bg-surface-2/80",
      danger:
        "bg-danger text-white hover:brightness-105 active:brightness-95",
    };

    const sizes = {
      sm: "h-7 px-2.5 text-xs gap-1.5",
      md: "h-8 px-3 text-xs gap-2",
      icon: "h-8 w-8 p-0 text-text-muted hover:text-text",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
