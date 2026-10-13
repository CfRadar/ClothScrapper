/**
 * Static graph definition and node/edge registry for Marketplace Keyword Agent workflow canvas.
 */

export type NodeStatus = "idle" | "queued" | "running" | "success" | "warning" | "error" | "skipped";

export interface WorkflowNodeData {
  label: string;
  category: "input" | "agent" | "data" | "scraper" | "output";
  status: NodeStatus;
  detail?: string;
  metrics?: Record<string, string | number>;
  iconName?: string;
}

export interface CanvasNodeDefinition {
  id: string;
  position: { x: number; y: number };
  data: WorkflowNodeData;
}

export interface CanvasEdgeDefinition {
  id: string;
  source: string;
  target: string;
}

/**
 * Standard layout coordinates for the 14 pipeline nodes.
 * Designed with generous 40px spacing along an 8px grid.
 */
export const INITIAL_WORKFLOW_NODES: CanvasNodeDefinition[] = [
  // Input
  {
    id: "brief",
    position: { x: 50, y: 220 },
    data: { label: "Seller Brief", category: "input", status: "idle", detail: "T-shirt attributes & platforms", iconName: "FileText" },
  },

  // Agent 1: Planner
  {
    id: "planner",
    position: { x: 280, y: 220 },
    data: { label: "AI Planner", category: "agent", status: "idle", detail: "Infers audience & queries (1 LLM)", iconName: "Brain" },
  },

  // Inferred Context
  {
    id: "target_market",
    position: { x: 520, y: 140 },
    data: { label: "Target Market", category: "data", status: "idle", detail: "Demographics & personas", iconName: "Users" },
  },
  {
    id: "search_queries",
    position: { x: 520, y: 300 },
    data: { label: "Search Queries", category: "data", status: "idle", detail: "Platform & social queries", iconName: "Search" },
  },

  // Scraper Stage Gateways
  {
    id: "marketplace",
    position: { x: 760, y: 140 },
    data: { label: "Marketplace Scraper", category: "agent", status: "idle", detail: "Parallel retail search (0 LLM)", iconName: "Store" },
  },
  {
    id: "social",
    position: { x: 760, y: 340 },
    data: { label: "Social Scraper", category: "agent", status: "idle", detail: "Community listening (<=1 LLM)", iconName: "MessageCircle" },
  },

  // Retail Scrapers
  {
    id: "amazon",
    position: { x: 1000, y: 60 },
    data: { label: "Amazon.in", category: "scraper", status: "idle", detail: "Autosuggest & search cards", iconName: "ShoppingBag" },
  },
  {
    id: "myntra",
    position: { x: 1000, y: 140 },
    data: { label: "Myntra", category: "scraper", status: "idle", detail: "State JSON & brand catalog", iconName: "Tag" },
  },
  {
    id: "flipkart",
    position: { x: 1000, y: 220 },
    data: { label: "Flipkart", category: "scraper", status: "idle", detail: "DOM structure & price regex", iconName: "Box" },
  },

  // Social Channels
  {
    id: "reddit",
    position: { x: 1000, y: 320 },
    data: { label: "Reddit", category: "scraper", status: "idle", detail: "Fashion subreddits & wish phrases", iconName: "Hash" },
  },
  {
    id: "x",
    position: { x: 1000, y: 400 },
    data: { label: "X (Twitter)", category: "scraper", status: "idle", detail: "Best-effort public hashtags", iconName: "Globe" },
  },
  {
    id: "instagram",
    position: { x: 1000, y: 480 },
    data: { label: "Instagram", category: "scraper", status: "idle", detail: "Best-effort trend tags", iconName: "Camera" },
  },

  // Agent 4: Analyst
  {
    id: "analyst",
    position: { x: 1260, y: 240 },
    data: { label: "AI Analyst", category: "agent", status: "idle", detail: "Scoring & synthesis (1 LLM)", iconName: "Sparkles" },
  },

  // Final Output
  {
    id: "output",
    position: { x: 1500, y: 240 },
    data: { label: "Keyword Intelligence", category: "output", status: "idle", detail: "Platform chips & other factors", iconName: "CheckCircle" },
  },
];

export const INITIAL_WORKFLOW_EDGES: CanvasEdgeDefinition[] = [
  // Brief -> Planner
  { id: "e-brief-planner", source: "brief", target: "planner" },

  // Planner -> Intermediate Context
  { id: "e-planner-target", source: "planner", target: "target_market" },
  { id: "e-planner-queries", source: "planner", target: "search_queries" },

  // Queries -> Scraper Gateways
  { id: "e-queries-marketplace", source: "search_queries", target: "marketplace" },
  { id: "e-queries-social", source: "search_queries", target: "social" },

  // Marketplace -> Channels
  { id: "e-market-amazon", source: "marketplace", target: "amazon" },
  { id: "e-market-myntra", source: "marketplace", target: "myntra" },
  { id: "e-market-flipkart", source: "marketplace", target: "flipkart" },

  // Social -> Channels
  { id: "e-social-reddit", source: "social", target: "reddit" },
  { id: "e-social-x", source: "social", target: "x" },
  { id: "e-social-ig", source: "social", target: "instagram" },

  // Channels -> Analyst
  { id: "e-target-analyst", source: "target_market", target: "analyst" },
  { id: "e-amazon-analyst", source: "amazon", target: "analyst" },
  { id: "e-myntra-analyst", source: "myntra", target: "analyst" },
  { id: "e-flipkart-analyst", source: "flipkart", target: "analyst" },
  { id: "e-reddit-analyst", source: "reddit", target: "analyst" },
  { id: "e-x-analyst", source: "x", target: "analyst" },
  { id: "e-ig-analyst", source: "instagram", target: "analyst" },

  // Analyst -> Output
  { id: "e-analyst-output", source: "analyst", target: "output" },
];
