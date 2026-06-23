"use client";

import { healthScoreColor } from "@/lib/dashboard-theme";

type HealthScoreRingProps = {
  score: number;
  band: string;
  size?: number;
  strokeWidth?: number;
  compact?: boolean;
};

export function HealthScoreRing({
  score,
  band,
  size = 160,
  strokeWidth = 12,
  compact = false,
}: HealthScoreRingProps) {
  const isCompact = compact || size < 80;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.min(100, Math.max(0, score));
  const offset = circumference - (clamped / 100) * circumference;
  const color = healthScoreColor(clamped);

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className={isCompact ? "text-lg font-bold text-slate-800" : "text-4xl font-bold tracking-tight text-slate-900"}>
          {Math.round(score)}
        </span>
        {!isCompact && (
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{band}</span>
        )}
      </div>
    </div>
  );
}
