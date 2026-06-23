"use client";

import { riskBandSeverity, SEVERITY_STYLES } from "@/lib/dashboard-theme";
import { t } from "@/stores/localizationStore";

type RiskGaugeProps = {
  percent: number;
  band: string;
};

export function RiskGauge({ percent, band }: RiskGaugeProps) {
  const clamped = Math.min(100, Math.max(0, percent));
  const severity = riskBandSeverity(band);
  const accent = SEVERITY_STYLES[severity].accent;

  return (
    <div className="space-y-2">
      <div className="flex items-end justify-between">
        <span className="text-2xl font-bold text-slate-900">{clamped}%</span>
        <span
          className="rounded-full px-2 py-0.5 text-xs font-semibold uppercase"
          style={{ backgroundColor: `${accent}20`, color: accent }}
        >
          {band}
        </span>
      </div>
      <div className="relative h-3 overflow-hidden rounded-full bg-slate-100">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all duration-700"
          style={{ width: `${clamped}%`, backgroundColor: accent }}
        />
        <div className="absolute inset-0 flex">
          {[25, 50, 75].map((tick) => (
            <div
              key={tick}
              className="absolute top-0 bottom-0 w-px bg-white/60"
              style={{ left: `${tick}%` }}
            />
          ))}
        </div>
      </div>
      <div className="flex justify-between text-[10px] font-medium uppercase tracking-wide text-slate-400">
        <span>{t("common.low", "Low")}</span>
        <span>{t("common.moderate", "Moderate")}</span>
        <span>{t("common.high", "High")}</span>
      </div>
    </div>
  );
}
