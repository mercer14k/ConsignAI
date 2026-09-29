export type View =
  | "Overview"
  | "Exceptions"
  | "Inventory"
  | "Redistribution"
  | "Data & imports"
  | "Architecture";
export interface Alert {
  id: string;
  kind: string;
  severity: string;
  title: string;
  detail: string;
  location_id: string;
  location_name: string;
  market: string;
  sku: string;
  material_name: string;
  category: string;
  unit: string;
  variance: number;
  value_cents: number;
  days_of_supply: number | null;
  evidence_ids: string[];
}
export interface Position {
  location_id: string;
  location_name: string;
  sku: string;
  material_name: string;
  market: string;
  location_kind: string;
  category: string;
  on_hand: number;
  expected: number;
  reserved: number;
  available: number;
  variance: number;
  unit: string;
  unit_cost_cents: number;
  days_of_supply: number | null;
  daily_demand: number | null;
  risk_score: number;
  risk_kinds: string[];
  opening: number;
  net_movement: number;
  opening_day: string;
  snapshot_day: string;
  method: string;
  forecast_quality: string;
  history: number[];
  movement_count: number;
  snapshot_age_days: number;
}
export interface Transfer {
  id: string;
  from_name: string;
  to_name: string;
  from_location: string;
  to_location: string;
  sku: string;
  material_name: string;
  market: string;
  quantity: number;
  unit: string;
  value_cents: number;
  coverage_before: number;
  coverage_after: number;
  constraints: string[];
  expedite_required: boolean;
}
export interface Overview {
  id: string;
  as_of: string;
  created_at: string;
  dataset_version: string;
  algorithm_version: string;
  stale_analysis: boolean;
  summary: {
    inventory_value_cents: number;
    variance_value_cents: number;
    exception_count: number;
    shortage_count: number;
    contractors: number;
    skus: number;
    positions: number;
    record_count: number;
    movement_count: number;
    snapshot_count: number;
    redistribution_value_cents: number;
    anomaly_counts: Record<string, number>;
    elapsed_seconds: number;
    sources: string[];
  };
  contractors: {
    location_id: string;
    location_name: string;
    market: string;
    risk_score: number;
    days_of_supply: number | null;
    materials: { sku: string; name: string; risk_score: number }[];
  }[];
  markets: {
    market: string;
    value_cents: number;
    exceptions: number;
    shortages: number;
    days_of_supply: number | null;
    categories: Record<string, number>;
  }[];
  trend: { day: string; value_cents: number; units: number }[];
}
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
export interface Evidence {
  run_id: string;
  position: Position;
  snapshots: Record<string, any>[];
  movements: Record<string, any>[];
  alerts: Alert[];
  total: number;
  offset: number;
  limit: number;
}
export interface Batch {
  id: string;
  created_at: string;
  filename: string;
  status: string;
  rows: number;
  accepted: number;
  duplicates: number;
  errors: { row: number; message: string; record_id?: string }[];
}
