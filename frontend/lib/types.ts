export type AppType = "web_api" | "web_app" | "static_site" | "background_worker";
export type DatabaseEngine = "postgresql" | "mysql" | "none";
export type AvailabilityTier = "standard" | "high" | "critical";
export type OptimizeFor = "cost" | "performance" | "availability" | "simplicity" | "balanced";

export type Requirements = {
  app_type: AppType;
  monthly_active_users: number;
  requests_per_minute: number;
  database: DatabaseEngine;
  storage_gb: number;
  availability: AvailabilityTier;
  monthly_budget_usd: number;
  region: string;
  optimize_for: OptimizeFor;
};

export type Component = {
  id: string;
  service_id: string;
  category: string;
  display_name: string;
  count: number;
  config: Record<string, unknown>;
  estimated_monthly_cost_usd: number;
};

export type Connection = {
  source: string;
  target: string;
  label?: string | null;
};

export type Decision = {
  component_id: string;
  reasoning: string;
  factors: Record<string, string>;
};

export type ScoreCard = {
  cost_usd_month: number;
  complexity: "low" | "medium" | "high";
  scalability: "low" | "medium" | "high";
  availability_pct: number;
  operational_overhead: "low" | "medium" | "high";
};

export type ArchSpec = {
  id: string;
  provider: "aws";
  requirements: Requirements;
  components: Component[];
  connections: Connection[];
  decisions: Decision[];
  score: ScoreCard | null;
  total_monthly_cost_usd: number;
  created_at: string;
};
