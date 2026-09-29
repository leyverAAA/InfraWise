import type { Requirements } from "@/lib/types";

export const DEFAULT_REQUIREMENTS: Requirements = {
  app_type: "web_api",
  monthly_active_users: 5000,
  requests_per_minute: 300,
  database: "postgresql",
  storage_gb: 50,
  availability: "high",
  monthly_budget_usd: 150,
  region: "us-east-1",
  optimize_for: "balanced",
};

export function validateRequirements(requirements: Requirements): string | null {
  if (requirements.monthly_active_users <= 0) {
    return "Los usuarios activos deben ser mayores que 0.";
  }
  if (requirements.requests_per_minute <= 0) {
    return "Las solicitudes por minuto deben ser mayores que 0.";
  }
  if (requirements.storage_gb < 0) {
    return "El almacenamiento no puede ser negativo.";
  }
  if (requirements.monthly_budget_usd <= 0) {
    return "El presupuesto mensual debe ser mayor que 0.";
  }
  if (!requirements.region.trim()) {
    return "La región es obligatoria.";
  }
  return null;
}
