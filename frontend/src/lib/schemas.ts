import { z } from "zod";

export const PlatformEnum = z.enum(["amazon", "myntra", "flipkart", "meesho"]);

export const ProductBriefSchema = z.object({
  platforms: z.array(PlatformEnum).min(1, "Select at least one platform").max(4, "Maximum 4 platforms"),
  tshirt_type: z.string().min(1, "T-shirt type is required").max(60, "Max 60 characters"),
  color: z.string().min(1, "Color is required").max(60, "Max 60 characters"),
  gender: z.enum(["men", "women", "unisex", "kids"]).default("unisex"),
  fit: z.string().max(100).nullable().optional(),
  fabric: z.string().max(100).nullable().optional(),
  neck: z.string().max(100).nullable().optional(),
  sleeve: z.string().max(100).nullable().optional(),
  pattern: z.string().max(100).nullable().optional(),
  occasion: z.string().max(100).nullable().optional(),
  pack: z.string().max(50).nullable().optional(),
  size_range: z.string().max(100).nullable().optional(),
  price_range: z.string().max(100).nullable().optional(),
  brand_name: z.string().max(100).nullable().optional(),
  extra_details: z.string().max(1000).nullable().optional(),
  research_sources: z.array(z.string()).optional(),
});

export const TitlePartSchema = z.object({
  label: z.string(),
  text: z.string(),
});

export const TitleSuggestionSchema = z.object({
  style: z.enum(["search", "balanced", "short"]),
  title: z.string(),
  length: z.number(),
  parts: z.array(TitlePartSchema).default([]),
  warnings: z.array(z.string()).optional(),
});

export const PlatformDetailsSchema = z.object({
  attributes_to_fill: z.array(z.string()).default([]),
  price_band: z.string().default(""),
  negative_keywords: z.array(z.string()).default([]),
  hashtags_or_tags: z.array(z.string()).default([]),
  competition_note: z.string().default(""),
  seasonality_note: z.string().default(""),
  notes: z.string().optional(),
});

export const CompetitorTitleSchema = z.object({
  rank: z.number(),
  title: z.string(),
  brand: z.string().nullable().optional(),
  price: z.number().nullable().optional(),
  rating: z.number().nullable().optional(),
  length: z.number().default(0),
});

export const PlatformResultSchema = z.object({
  platform: PlatformEnum,
  keywords: z.array(z.string()).default([]),
  titles: z.array(TitleSuggestionSchema).default([]),
  top_scraped_titles: z.array(CompetitorTitleSchema).default([]),
  details: PlatformDetailsSchema.default({
    attributes_to_fill: [],
    price_band: "",
    negative_keywords: [],
    hashtags_or_tags: [],
    competition_note: "",
    seasonality_note: "",
  }),
});

export const RunResultSchema = z.object({
  run_id: z.string(),
  target_market_summary: z.string().default(""),
  platforms: z.array(PlatformResultSchema),
  llm_calls_used: z.number().default(0),
  nodes_snapshot: z.record(z.string(), z.any()).optional(),
});

export const PreflightCheckSchema = z.object({
  id: z.string(),
  label: z.string(),
  status: z.enum(["pass", "warn", "fail"]),
  detail: z.string(),
});

export const PreflightResponseSchema = z.object({
  checks: z.array(PreflightCheckSchema),
  generated_at: z.number(),
});
