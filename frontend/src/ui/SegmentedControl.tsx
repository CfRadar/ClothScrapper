import { cn } from "../lib/cn";

export interface SegmentedControlOption<T extends string> {
  value: T;
  label: string;
}

export interface SegmentedControlProps<T extends string> {
  options: SegmentedControlOption<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  className,
}: SegmentedControlProps<T>) {
  return (
    <div
      className={cn(
        "inline-flex p-0.5 bg-surface-2 border border-border rounded-input select-none",
        className
      )}
      role="radiogroup"
    >
      {options.map((opt) => {
        const isSelected = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={isSelected}
            onClick={() => onChange(opt.value)}
            className={cn(
              "px-3 py-1 text-xs font-medium rounded-input transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-accent",
              isSelected
                ? "bg-surface text-text shadow-sm"
                : "text-text-muted hover:text-text"
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
