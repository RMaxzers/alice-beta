// Shared API types for the Alice web UI. Mirrors the backend contract exactly;
// do not rename fields without updating the backend docs.

export type Privacy = "PUBLIC" | "INTERNAL" | "PRIVATE";

export type Route =
  | "LOCAL_SIMPLE"
  | "LOCAL_CODE"
  | "LOCAL_RAG"
  | "CLOUD_CHEAP"
  | "CLOUD_POWERFUL"
  | "WEB_RESEARCH"
  | "FINANCIAL_RESEARCH"
  | "OBSERVABILITY"
  | "AUTOMATION"
  | "STRUCTURED_QUERY"
  | "LOG_ANALYSIS";

export type LogoState =
  | "idle"
  | "routing"
  | "local"
  | "knowledge"
  | "cloud"
  | "observability"
  | "error";

export interface SessionUser {
  user: unknown;
  csrf: string;
}

export interface ChatHistoryTurn {
  role: "user" | "assistant";
  content: string;
  privacy: Privacy;
}

export interface ChatRequest {
  message: string;
  privacy: Privacy;
  history: ChatHistoryTurn[];
  document_ids: string[];
  force_route?: Route;
  authorization_ticket?: string;
}

export interface RouteDecision {
  category: string;
  complexity: string;
  privacy: Privacy;
  requires_web: boolean;
  requires_rag: boolean;
  requires_sql: boolean;
  requires_tools: boolean;
  route: Route;
  model_alias: string;
  confidence: number | null;
  decided_by: "rules" | "semantic" | "classifier" | "policy";
  reason: string;
}

export interface SourceItem {
  kind: "document" | "table" | "web" | "metric" | "log" | "fact" | "container";
  title: string;
  location: string | null;
  url: string | null;
  privacy: Privacy;
  verification: string;
  retrieved_at: string | null;
}

export interface ToolEvent {
  type: "tool";
  name: string;
  summary: string;
  sql?: string;
  params?: unknown;
  data?: unknown;
}

export interface AuthorizationPreview {
  provider: string;
  recipients: string[];
  model: string;
  reason: string;
  privacy: Privacy;
  fields: string[];
  payload_preview: string;
  payload_hash: string;
  estimated_cost_usd: number | null;
  ticket_request_id: string;
}

export type AuthorizationOption = "AUTHORIZE_ONCE" | "CONTINUE_LOCAL" | "CANCEL";

export type ChatStreamEvent =
  | { type: "route"; decision: RouteDecision; raised_by: string[] }
  | ToolEvent
  | { type: "sources"; sources: SourceItem[] }
  | { type: "token"; text: string }
  | { type: "authorization_required"; preview: AuthorizationPreview; options: AuthorizationOption[] }
  | { type: "error"; code: string; message: string }
  | {
      type: "done";
      request_id: string;
      provider: string;
      model: string;
      latency_s: number;
      queue_s: number;
      retrieval_s: number;
      tokens_out: number;
      cost_usd: number | null;
      cost_state: "local" | "reported" | "unknown";
      privacy: Privacy;
    };

export interface DocumentItem {
  document_id: string;
  original_name: string;
  checksum: string;
  size_bytes: number;
  kind: string;
  source: string;
  version: number;
  supersedes: string | null;
  ingested_at: string;
  privacy: Privacy;
  verification: string;
  status: "pending" | "processing" | "ready" | "failed";
  status_detail: string | null;
  chunks: number | null;
  embedding_model: string | null;
}

export interface DatasetItem {
  table_name: string;
  document_id: string;
  owner: string;
  privacy: Privacy;
  columns_json: string;
  row_count: number;
}

export interface FactItem {
  fact_id: string;
  subject_key: string;
  statement: string;
  privacy: Privacy;
  verification: "UNVERIFIED" | "EMPIRICAL" | "VERIFIED";
  source_id: string;
  source_location: string | null;
  verified_by: string | null;
  verified_at: string | null;
  notes: string | null;
}

export interface FactsResponse {
  facts: FactItem[];
  conflict: FactItem[];
}

export interface HealthEntry {
  state: "healthy" | "degraded" | "unavailable" | "error" | "disabled" | "not_configured" | "configured_not_tested";
  detail: string | null;
  checked_at: string | null;
}

export interface GpuTemp {
  value: number | null;
  unit: string;
  age_s?: number;
  error?: string;
}

export interface ObservabilityMetrics {
  host_cpu_percent: number | null;
  host_mem_used_bytes: number | null;
  host_mem_total_bytes: number | null;
  gpu_util_percent: number | null;
  gpu_mem_used_bytes: number | null;
  gpu_mem_total_bytes: number | null;
  gpu_temp_c: GpuTemp;
}

export interface RecentRequest {
  request_id: string;
  started_at: string;
  route: string;
  provider: string;
  model: string;
  status: string;
  duration_s: number;
}

export interface ObservabilityOverview {
  health: Record<string, HealthEntry>;
  metrics: ObservabilityMetrics;
  usage_today: {
    by_provider: Record<string, number>;
    spent: {
      reserved_open: number;
      accounted: number;
      unknown_cost_calls: number;
      calls: number;
    };
  };
  recent_requests: RecentRequest[];
  grafana_url: string | null;
}

export interface RangeGap {
  from: number;
  to: number;
}

export interface RangeSeries {
  labels: Record<string, string>;
  points: [number, number][];
}

export interface RangeResponse {
  metric: string;
  unit: string;
  description: string;
  coverage: { fraction: number; first: number | null; last: number | null; gaps: RangeGap[] };
  series: RangeSeries[];
  summary: unknown;
}

export interface ModelAlias {
  alias: string;
  provider: string;
  model: string;
  available: boolean;
  loaded?: boolean;
  vram_bytes?: number;
  size_bytes?: number;
  location: string;
  state?: string;
  detail?: string;
  pricing?: { usd_per_mtok_in: number; usd_per_mtok_out: number } | null;
}

export interface ModelsResponse {
  ollama_reachable: boolean;
  aliases: ModelAlias[];
  routes: Record<string, string>;
  future_providers: Record<string, "DISABLED" | "READY_FOR_CONFIGURATION">;
}

export interface SystemResponse {
  health: Record<string, HealthEntry>;
  local_only: boolean;
  budget: {
    per_request_usd: number;
    daily_usd: number;
    today: { reserved_open: number; accounted: number; unknown_cost_calls: number; calls: number };
  };
  remote: { public_origin: string | null; via_proxy: boolean };
  grafana_local: string | null;
  version: string;
}

export interface SettingsResponse {
  local_only: boolean;
  cloud_enabled: boolean;
  budget_per_request_usd: number;
  budget_daily_usd: number;
  timezone: string;
  max_upload_mb: number;
  credentials: Record<string, "configurada" | "no configurada">;
  features: Record<string, boolean>;
}
