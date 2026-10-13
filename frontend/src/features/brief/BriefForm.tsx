import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp, Sparkles, StopCircle } from "lucide-react";
import { loadBriefFromStorage, saveBriefToStorage } from "../../lib/storage";
import type { ProductBrief } from "../../types";
import { Button } from "../../ui/Button";
import { Field } from "../../ui/Field";
import { Input } from "../../ui/Input";
import { SegmentedControl } from "../../ui/SegmentedControl";
import { Textarea } from "../../ui/Textarea";
import { PlatformPicker } from "./PlatformPicker";

export interface BriefFormProps {
  onGenerate: (brief: ProductBrief) => void;
  onStop: () => void;
  isRunning: boolean;
}

const DEFAULT_BRIEF: ProductBrief = {
  platforms: ["amazon", "myntra", "flipkart", "meesho"],
  tshirt_type: "oversized graphic tee",
  color: "black",
  gender: "unisex",
  fit: "oversized",
  fabric: "100% cotton 240 GSM",
  neck: "round neck",
  sleeve: "half sleeve",
  pattern: "graphic print",
  occasion: "casual streetwear",
  pack: "single",
  size_range: "S to XXL",
  price_range: "₹499 - ₹899",
  brand_name: "",
  extra_details: "",
};

export function BriefForm({ onGenerate, onStop, isRunning }: BriefFormProps) {
  const [brief, setBrief] = useState<ProductBrief>(() => {
    return loadBriefFromStorage() || DEFAULT_BRIEF;
  });

  const [showMore, setShowMore] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    saveBriefToStorage(brief);
  }, [brief]);

  const updateField = <K extends keyof ProductBrief>(key: K, value: ProductBrief[K]) => {
    setBrief((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) {
      setErrors((prev) => {
        const copy = { ...prev };
        delete copy[key];
        return copy;
      });
    }
  };

  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (!brief.platforms || brief.platforms.length === 0) {
      errs.platforms = "Select at least 1 marketplace.";
    }
    if (!brief.tshirt_type || !brief.tshirt_type.trim()) {
      errs.tshirt_type = "T-shirt type is required.";
    }
    if (!brief.color || !brief.color.trim()) {
      errs.color = "Color is required.";
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isRunning) {
      onStop();
      return;
    }
    if (validate()) {
      onGenerate(brief);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-surface border border-border rounded-modal p-5 sm:p-6 shadow-sm space-y-4 sm:space-y-5"
    >
      <div className="border-b border-border pb-3.5">
        <h2 className="text-base font-bold text-text">Product Brief</h2>
        <p className="text-xs sm:text-sm text-text-muted mt-1">
          Describe your T-shirt to generate search-optimized titles and rankable keywords.
        </p>
      </div>

      {/* 1. Marketplaces */}
      <PlatformPicker
        selected={brief.platforms}
        onChange={(platforms) => updateField("platforms", platforms)}
        disabled={isRunning}
      />
      {errors.platforms && (
        <p className="text-xs text-danger font-medium">{errors.platforms}</p>
      )}

      {/* 2. T-shirt Type (Required) */}
      <Field
        label="T-shirt Type"
        required
        error={errors.tshirt_type}
        hint="e.g. oversized graphic tee, polo collar tee, drop shoulder"
      >
        <Input
          value={brief.tshirt_type}
          onChange={(e) => updateField("tshirt_type", e.target.value)}
          placeholder="e.g. Oversized graphic tee"
          disabled={isRunning}
        />
        {/* Quick picks */}
        <div className="flex flex-wrap gap-1.5 mt-2">
          {["Oversized graphic tee", "Drop shoulder tee", "Plain crew neck", "Polo collar tee", "Acid wash tee"].map(
            (item) => (
              <button
                key={item}
                type="button"
                disabled={isRunning}
                onClick={() => updateField("tshirt_type", item.toLowerCase())}
                className="text-xs bg-surface-2 hover:bg-surface border border-border px-2.5 py-1 rounded text-text-muted hover:text-text font-medium transition-colors cursor-pointer"
              >
                + {item}
              </button>
            )
          )}
        </div>
      </Field>

      {/* 3. Color (Required) */}
      <Field
        label="Color"
        required
        error={errors.color}
        hint="Primary product color"
      >
        <Input
          value={brief.color}
          onChange={(e) => updateField("color", e.target.value)}
          placeholder="e.g. Black, Navy Blue, Sage Green"
          disabled={isRunning}
        />
        {/* Quick color picks */}
        <div className="flex flex-wrap gap-1.5 mt-2">
          {["Black", "White", "Navy Blue", "Sage Green", "Charcoal", "Beige"].map(
            (color) => (
              <button
                key={color}
                type="button"
                disabled={isRunning}
                onClick={() => updateField("color", color.toLowerCase())}
                className="text-xs bg-surface-2 hover:bg-surface border border-border px-2.5 py-1 rounded text-text-muted hover:text-text font-medium transition-colors cursor-pointer"
              >
                {color}
              </button>
            )
          )}
        </div>
      </Field>

      {/* 4. Gender */}
      <div className="space-y-1.5">
        <label className="text-sm font-semibold text-text">Gender Target</label>
        <div>
          <SegmentedControl
            options={[
              { value: "unisex", label: "Unisex" },
              { value: "men", label: "Men" },
              { value: "women", label: "Women" },
              { value: "kids", label: "Kids" },
            ]}
            value={brief.gender}
            onChange={(val) => updateField("gender", val)}
            className="w-full justify-between"
          />
        </div>
      </div>

      {/* 5. Collapsible More Details */}
      <div className="border border-border/80 rounded-input bg-surface-2/30 overflow-hidden">
        <button
          type="button"
          onClick={() => setShowMore(!showMore)}
          className="w-full flex items-center justify-between p-3 text-sm font-semibold text-text-muted hover:text-text transition-colors cursor-pointer"
        >
          <span>More details (optional)</span>
          {showMore ? (
            <ChevronUp className="w-4 h-4 text-text-muted" />
          ) : (
            <ChevronDown className="w-4 h-4 text-text-muted" />
          )}
        </button>

        {showMore && (
          <div className="p-4 pt-1 space-y-3.5 border-t border-border/50 text-sm">
            {/* Fit & Fabric */}
            <div className="grid grid-cols-2 gap-3">
              <Field label="Fit">
                <Input
                  value={brief.fit || ""}
                  onChange={(e) => updateField("fit", e.target.value)}
                  placeholder="e.g. Oversized, Slim, Boxy"
                  disabled={isRunning}
                />
              </Field>
              <Field label="Fabric">
                <Input
                  value={brief.fabric || ""}
                  onChange={(e) => updateField("fabric", e.target.value)}
                  placeholder="e.g. 100% Cotton, 240 GSM"
                  disabled={isRunning}
                />
              </Field>
            </div>

            {/* Neck & Sleeve */}
            <div className="grid grid-cols-2 gap-3">
              <Field label="Neck">
                <Input
                  value={brief.neck || ""}
                  onChange={(e) => updateField("neck", e.target.value)}
                  placeholder="e.g. Round neck, Polo collar"
                  disabled={isRunning}
                />
              </Field>
              <Field label="Sleeve">
                <Input
                  value={brief.sleeve || ""}
                  onChange={(e) => updateField("sleeve", e.target.value)}
                  placeholder="e.g. Half sleeve, Full sleeve"
                  disabled={isRunning}
                />
              </Field>
            </div>

            {/* Pattern & Occasion */}
            <div className="grid grid-cols-2 gap-3">
              <Field label="Pattern">
                <Input
                  value={brief.pattern || ""}
                  onChange={(e) => updateField("pattern", e.target.value)}
                  placeholder="e.g. Graphic print, Solid"
                  disabled={isRunning}
                />
              </Field>
              <Field label="Occasion">
                <Input
                  value={brief.occasion || ""}
                  onChange={(e) => updateField("occasion", e.target.value)}
                  placeholder="e.g. Casual, Streetwear, Gym"
                  disabled={isRunning}
                />
              </Field>
            </div>

            {/* Brand & Pack */}
            <div className="grid grid-cols-2 gap-3">
              <Field label="Brand Name (Optional)" hint="Leave empty if unbranded">
                <Input
                  value={brief.brand_name || ""}
                  onChange={(e) => updateField("brand_name", e.target.value)}
                  placeholder="e.g. UrbanAura"
                  disabled={isRunning}
                />
              </Field>
              <Field label="Pack / Multipack">
                <Input
                  value={brief.pack || ""}
                  onChange={(e) => updateField("pack", e.target.value)}
                  placeholder="e.g. Single, Pack of 2"
                  disabled={isRunning}
                />
              </Field>
            </div>

            {/* Size & Price Range */}
            <div className="grid grid-cols-2 gap-3">
              <Field label="Size Range">
                <Input
                  value={brief.size_range || ""}
                  onChange={(e) => updateField("size_range", e.target.value)}
                  placeholder="e.g. S to XXL"
                  disabled={isRunning}
                />
              </Field>
              <Field label="Target Price Range">
                <Input
                  value={brief.price_range || ""}
                  onChange={(e) => updateField("price_range", e.target.value)}
                  placeholder="e.g. ₹499 - ₹899"
                  disabled={isRunning}
                />
              </Field>
            </div>

            {/* Anything else */}
            <Field label="Anything else">
              <Textarea
                rows={3}
                value={brief.extra_details || ""}
                onChange={(e) => updateField("extra_details", e.target.value)}
                placeholder="Target demographic, aesthetic vibe, special details..."
                disabled={isRunning}
              />
            </Field>
          </div>
        )}
      </div>

      {/* Submit / Cancel Action Button */}
      {isRunning ? (
        <Button
          type="button"
          variant="secondary"
          className="w-full gap-2 text-danger hover:bg-danger/10 border-danger/40 py-3 font-semibold text-sm"
          onClick={onStop}
        >
          <StopCircle className="w-4 h-4" />
          <span>Stop Generation</span>
        </Button>
      ) : (
        <Button
          type="submit"
          variant="primary"
          className="w-full gap-2 py-3 font-semibold text-sm shadow-sm"
        >
          <Sparkles className="w-4 h-4" />
          <span>Generate Keywords & Titles</span>
        </Button>
      )}
    </form>
  );
}
