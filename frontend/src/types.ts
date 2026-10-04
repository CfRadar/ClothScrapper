export type PlatformName = 'amazon' | 'myntra' | 'flipkart';

export interface ProductBrief {
  platforms: PlatformName[];
  tshirt_type: string;
  color: string;
  gender: 'men' | 'women' | 'unisex' | 'kids';
  fit?: string | null;
  fabric?: string | null;
  neck?: string | null;
  sleeve?: string | null;
  print_or_design?: string | null;
  occasion?: string | null;
  price_min?: number | null;
  price_max?: number | null;
  sizes?: string | null;
  brand_name?: string | null;
  extra_details?: string | null;
}

export interface TargetMarket {
  age_range: string;
  personas: string[];
  interests: string[];
  regions: string[];
  language_notes: string;
}

export interface PlatformKeywords {
  platform: PlatformName;
  keywords: string[];
}

export interface PlatformFactors {
  title_formula: string;
  recommended_title_example: string;
  attributes_to_fill: string[];
  price_band: string;
  negative_keywords: string[];
  hashtags_or_tags: string[];
  competition_note: string;
  seasonality_note: string;
}

export interface OtherFactors {
  target_market_summary: string;
  per_platform: Record<PlatformName, PlatformFactors>;
  general: string[];
}

export interface RunResult {
  run_id: string;
  keywords: PlatformKeywords[];
  other_factors: OtherFactors;
  platform_statuses: Record<string, string>;
  llm_calls_used: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  reply: string;
  keywords_patch?: PlatformKeywords[] | null;
  factors_patch?: Record<string, unknown> | null;
}

export interface SSEEvent {
  type: 'stage' | 'progress' | 'warning' | 'result' | 'error' | 'done';
  stage: 'planner' | 'marketplace' | 'social' | 'analyst' | 'system';
  message: string;
  data?: Record<string, unknown> | null;
  ts: number;
}

export interface QuotaInfo {
  remaining_today: number;
  daily_limit: number;
  rpm_limit: number;
  active_model: string;
}
