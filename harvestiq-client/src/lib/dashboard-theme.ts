export type SeverityLevel = "healthy" | "moderate" | "critical" | "neutral";

export function healthBandSeverity(band: string): SeverityLevel {
  if (band === "GOOD") return "healthy";
  if (band === "FAIR") return "moderate";
  if (band === "POOR") return "critical";
  return "neutral";
}

export function fsiSeverity(classification: string): SeverityLevel {
  if (classification === "LOW_STRESS") return "healthy";
  if (classification === "MEDIUM_STRESS") return "moderate";
  if (classification === "HIGH_STRESS") return "critical";
  return "neutral";
}

export function riskBandSeverity(band: string): SeverityLevel {
  if (band === "LOW") return "healthy";
  if (band === "MEDIUM") return "moderate";
  if (band === "HIGH") return "critical";
  return "neutral";
}

export function alertSeverity(severity: string): SeverityLevel {
  if (severity === "LOW") return "healthy";
  if (severity === "MEDIUM") return "moderate";
  if (severity === "HIGH") return "critical";
  return "neutral";
}

export const SEVERITY_STYLES: Record<
  SeverityLevel,
  { bg: string; text: string; border: string; ring: string; accent: string }
> = {
  healthy: {
    bg: "bg-emerald-50",
    text: "text-emerald-800",
    border: "border-emerald-200",
    ring: "stroke-emerald-500",
    accent: "#10b981",
  },
  moderate: {
    bg: "bg-amber-50",
    text: "text-amber-800",
    border: "border-amber-200",
    ring: "stroke-amber-500",
    accent: "#f59e0b",
  },
  critical: {
    bg: "bg-red-50",
    text: "text-red-800",
    border: "border-red-200",
    ring: "stroke-red-500",
    accent: "#ef4444",
  },
  neutral: {
    bg: "bg-slate-50",
    text: "text-slate-700",
    border: "border-slate-200",
    ring: "stroke-slate-400",
    accent: "#64748b",
  },
};

export function healthScoreColor(score: number): string {
  if (score >= 70) return "#10b981";
  if (score >= 45) return "#f59e0b";
  return "#ef4444";
}
