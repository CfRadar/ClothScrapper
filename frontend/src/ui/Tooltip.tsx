import React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "../lib/cn";

export function TooltipProvider({
  children,
  delayDuration = 200,
}: {
  children: React.ReactNode;
  delayDuration?: number;
}) {
  return (
    <TooltipPrimitive.Provider delayDuration={delayDuration}>
      {children}
    </TooltipPrimitive.Provider>
  );
}

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  side?: "top" | "right" | "bottom" | "left";
  className?: string;
}

export function Tooltip({
  content,
  children,
  side = "top",
  className,
}: TooltipProps) {
  if (!content) return <>{children}</>;

  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={4}
          className={cn(
            "z-50 px-2 py-1 text-[11px] font-medium text-text bg-surface-2 border border-border rounded-input shadow-sm select-none",
            className
          )}
        >
          {content}
          <TooltipPrimitive.Arrow className="fill-border" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
