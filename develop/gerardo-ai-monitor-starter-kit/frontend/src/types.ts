export type Cost = {
  estimated_api_equivalent: number | null;
  upper_usd: number | null;
  status: string;
  included_count: number;
  missing_count: number;
  price_as_of: string;
};
export type Provider = "claude" | "codex" | "antigravity";
export type Usage = {
  input_tokens: number | null;
  output_tokens: number | null;
  cache_read_tokens: number | null;
  cache_write_tokens: number | null;
  total_tokens: number | null;
  included_count: number;
  missing_count: number;
  estimated_count: number;
};
export type Source = {
  id: Provider;
  name: string;
  status: string;
  available: boolean;
  last_received_at?: string | null;
  last_success_at: string | null;
  last_attempt_at: string | null;
  error: string | null;
  files: number;
  total_files?: number;
  warnings: number;
  scan_limit: number;
  location: string;
  capabilities: string[];
};
export type Tool = {
  id: Provider;
  name: string;
  source: Source;
  usage: Usage;
  cost: Cost;
  sessions: number;
  latest: string | null;
  models: string[];
};
export type Task = {
  id: string;
  provider: Provider;
  project: string;
  project_id: string;
  title: string;
  summary: string;
  model: string | null;
  occurred_at: string;
  started_at: string;
  event_count: number;
  tool_count: number;
  usage: Usage;
  cost: Cost;
  status: string;
  synthetic: boolean;
};
export type Project = {
  id: string;
  name: string;
  usage: Usage;
  cost: Cost;
  sessions: number;
  providers: Provider[];
};
export type Point = {
  date: string;
  claude: number | null;
  codex: number | null;
  antigravity: number | null;
};
export type Event = {
  event_id: string;
  provider: Provider;
  model: string | null;
  event_type: string;
  title: string;
  occurred_at: string;
  source_ref: string;
  usage?: Usage;
  synthetic: boolean;
};
export type Overview = {
  usage: Usage;
  cost: Cost;
  sessions: number;
  confirmed: number;
  pending: number;
  providers: Tool[];
  tasks: Task[];
  projects: Project[];
  series: Point[];
  cost_series: ({ date: string } & Record<Provider, Cost>)[];
  pricing_sources: Record<string, string>;
  pricing_rates: Record<string, (number | null)[]>;
  coverage: {
    providers_with_usage: number;
    providers_total: number;
    missing_providers: string[];
  };
  briefing: string;
  timezone: string;
  recent_events: Event[];
};
export type Detail = {
  events: Event[];
  notes: { id: string; text: string; created_at: string }[];
  confirmed_at: string | null;
  evidence: { ref: string; type: string; time: string; available?: boolean }[];
};
export type AwsCosts = {
  status: string;
  message: string | null;
  currency: string;
  period: { start: string; end: string } | null;
  total: number | null;
  daily: { date: string; amount: number }[];
  services: { name: string; amount: number }[];
  updated_at: string | null;
};
