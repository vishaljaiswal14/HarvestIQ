"use client";

type SparklineProps = {
  values: number[];
  color?: string;
  height?: number;
  fill?: boolean;
  labels?: string[];
  smooth?: boolean;
};

function smoothPath(points: Array<{ x: number; y: number }>): string {
  if (points.length < 2) return "";
  if (points.length === 2) {
    return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`;
  }

  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(i - 1, 0)];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[Math.min(i + 2, points.length - 1)];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
  }
  return d;
}

export function Sparkline({
  values,
  color = "#10b981",
  height = 80,
  fill = true,
  labels,
  smooth = true,
}: SparklineProps) {
  if (values.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50/80 text-xs font-medium text-slate-400"
        style={{ height }}
      >
        No trend data
      </div>
    );
  }

  const width = 320;
  const padding = { top: 12, right: 8, bottom: 4, left: 8 };
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const chartH = height - padding.top - padding.bottom;

  const points = values.map((v, i) => ({
    x: padding.left + (i / Math.max(values.length - 1, 1)) * (width - padding.left - padding.right),
    y: padding.top + (1 - (v - min) / range) * chartH,
  }));

  const hasMultiplePoints = values.length > 1;
  const linePath = hasMultiplePoints
    ? (smooth ? smoothPath(points) : points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" "))
    : "";
  const areaPath = hasMultiplePoints && linePath.startsWith("M")
    ? `${linePath} L ${points[points.length - 1].x} ${height - padding.bottom} L ${points[0].x} ${height - padding.bottom} Z`
    : "";

  return (
    <div className="w-full">
      <div className="mb-1 flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-slate-400">
        <span>{min.toFixed(2)}</span>
        <span>{max.toFixed(2)}</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" preserveAspectRatio="none" role="img">
        {[0.25, 0.5, 0.75].map((pct) => (
          <line
            key={pct}
            x1={padding.left}
            x2={width - padding.right}
            y1={padding.top + chartH * pct}
            y2={padding.top + chartH * pct}
            stroke="#e2e8f0"
            strokeWidth={1}
            strokeDasharray="4 4"
          />
        ))}
        {fill && areaPath && (
          <>
            <defs>
              <linearGradient id={`spark-fill-${color.replace("#", "")}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.25} />
                <stop offset="100%" stopColor={color} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <path d={areaPath} fill={`url(#spark-fill-${color.replace("#", "")})`} />
          </>
        )}
        {linePath && (
          <path
            d={linePath}
            fill="none"
            stroke={color}
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}
        {points.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={3.5} fill="white" stroke={color} strokeWidth={2} />
        ))}
      </svg>
      {labels && labels.length > 0 && (
        <div className="mt-1.5 flex justify-between text-[10px] font-semibold text-slate-500">
          {labels.map((label, index) => (
            <span key={index}>{label}</span>
          ))}
        </div>
      )}
    </div>
  );
}
