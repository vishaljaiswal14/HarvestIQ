import type { SimulatorSnapshotData } from "@/lib/api";

/** UI-only composite score derived from existing snapshot fields. */
export function estimateHealthScore(snapshot: SimulatorSnapshotData): number {
  const fsiPenalty = snapshot.fsi * 40;
  const riskPenalty = snapshot.yield_risk.estimated_risk_percent * 0.35;
  return Math.round(Math.max(0, Math.min(100, 100 - fsiPenalty - riskPenalty)));
}

export function computeDelta(current: number, projected: number): number {
  return projected - current;
}

export function formatDelta(value: number, unit = "", decimals = 1): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}${unit}`;
}

export function deltaSeverity(
  value: number,
  invert = false,
): "healthy" | "moderate" | "critical" | "neutral" {
  const v = invert ? -value : value;
  if (v <= -2) return "healthy";
  if (v >= 5) return "critical";
  if (Math.abs(v) < 0.5) return "neutral";
  return v > 0 ? "moderate" : "healthy";
}
