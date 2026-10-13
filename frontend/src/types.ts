export type PlatformName = "amazon" | "myntra" | "flipkart" | "meesho";

export type NodeStatus =
  | "idle"
  | "queued"
  | "running"
  | "success"
  | "warning"
  | "error"
  | "skipped"
  | "cached";

export interface NodeEvent {
  type: "node";
  seq: number;
  node_id: string;
  status: NodeStatus;
  detail?: string | null;
  metrics?: Record<string, any> | null;
  ts: number;
}

export type TitleStyle = "search" | "balanced" | "short";

export type PartLabel =
  | "brand"
  | "gender"
  | "fit"
  | "fabric"
  | "color"
  | "tshirt_type"
  | "neck"
  | "sleeve"
  | "pattern"
  | "occasion"
  | "pack"
  | "key_feature";

export interface TitlePart {
  label: PartLabel;
  text: string;
}

export interface TitleSuggestion {
  style: TitleStyle;
  title: string;
  length: number;
  parts: TitlePart[];
  warnings?: string[];
}

export interface PlatformDetails {
  attributes_to_fill: string[];
  price_band: string;
  negative_keywords: string[];
  hashtags_or_tags: string[];
  competition_note: string;
  seasonality_note: string;
  notes?: string;
}

export interface CompetitorTitle {
  rank: number;
  title: string;
  brand?: string | null;
  price?: number | string | null;
  rating?: number | null;
  rating_count?: number | null;
  reviews_count?: number | null;
  length: number;
}

export interface PlatformResult {
  platform: PlatformName;
  keywords: string[];
  titles: TitleSuggestion[];
  top_scraped_titles?: CompetitorTitle[];
  details: PlatformDetails;
}

export interface ProductBrief {
  platforms: PlatformName[];
  tshirt_type: string;
  color: string;
  gender: "men" | "women" | "unisex" | "kids";
  fit?: string | null;
  fabric?: string | null;
  neck?: string | null;
  sleeve?: string | null;
  pattern?: string | null;
  occasion?: string | null;
  pack?: string | null;
  size_range?: string | null;
  price_range?: string | null;
  brand_name?: string | null;
  extra_details?: string | null;
  research_sources?: string[];
}

export interface RunResult {
  run_id: string;
  target_market_summary: string;
  platforms: PlatformResult[];
  llm_calls_used: number;
  nodes_snapshot?: Record<string, any>;
}

export interface ChatResponse {
  reply: string;
  patch?: PlatformResult[] | null;
}

export interface PreflightCheck {
  id: string;
  label: string;
  status: "pass" | "warn" | "fail";
  detail: string;
}

export interface PreflightResponse {
  checks: PreflightCheck[];
  generated_at: number;
}

export interface SSEEvent {
  seq: number;
  type: "stage" | "progress" | "warning" | "result" | "error" | "done" | "node";
  stage?: "planner" | "marketplace" | "social" | "analyst" | "system" | null;
  message?: string | null;
  data?: any;
  node_id?: string | null;
  status?: string | null;
  detail?: string | null;
  metrics?: Record<string, any> | null;
  ts: number;
}
