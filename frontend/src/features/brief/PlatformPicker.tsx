import { Check } from "lucide-react";
import type { PlatformName } from "../../types";

export interface PlatformPickerProps {
  selected: PlatformName[];
  onChange: (platforms: PlatformName[]) => void;
  disabled?: boolean;
}

const PLATFORMS: { id: PlatformName; label: string; badge: string }[] = [
  { id: "amazon", label: "Amazon", badge: "200c max" },
  { id: "myntra", label: "Myntra", badge: "60c max" },
  { id: "flipkart", label: "Flipkart", badge: "120c max" },
  { id: "meesho", label: "Meesho", badge: "100c max" },
];

export function PlatformPicker({ selected, onChange, disabled = false }: PlatformPickerProps) {
  const togglePlatform = (id: PlatformName) => {
    if (disabled) return;
    if (selected.includes(id)) {
      if (selected.length > 1) {
        onChange(selected.filter((p) => p !== id));
      }
    } else {
      onChange([...selected, id]);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-semibold text-text">
          Target Marketplaces <span className="text-danger">*</span>
        </label>
        <span className="text-xs text-text-muted">Select 1 to 4</span>
      </div>
      <div className="grid grid-cols-2 gap-2.5">
        {PLATFORMS.map((plat) => {
          const isSelected = selected.includes(plat.id);
          return (
            <button
              key={plat.id}
              type="button"
              disabled={disabled}
              onClick={() => togglePlatform(plat.id)}
              className={`flex items-center justify-between px-3.5 py-2.5 rounded-input border text-sm transition-all text-left ${
                isSelected
                  ? "bg-accent/10 border-accent text-text font-semibold ring-1 ring-accent"
                  : "bg-surface-2 border-border text-text-muted hover:border-border-strong hover:text-text font-medium"
              } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
            >
              <div className="flex items-center gap-2">
                <div
                  className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
                    isSelected
                      ? "bg-accent border-accent text-white"
                      : "border-border bg-surface"
                  }`}
                >
                  {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                </div>
                <span>{plat.label}</span>
              </div>
              <span className="text-xs text-text-muted font-mono">{plat.badge}</span>
            </button>
          );
        })}
      </div>
      {selected.length === 0 && (
        <p className="text-xs text-danger font-medium">Please select at least one marketplace.</p>
      )}
    </div>
  );
}
