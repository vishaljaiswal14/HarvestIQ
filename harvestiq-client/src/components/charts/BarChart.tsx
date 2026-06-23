"use client";

type BarChartProps = {
  data: Array<{ label: string; value: number; color?: string }>;
  maxValue?: number;
  unit?: string;
  title?: string;
};

export function BarChart({ data, maxValue, unit = "", title }: BarChartProps) {
  const peak = maxValue ?? Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="space-y-2">
      {title && (
        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{title}</p>
      )}
      <div className="relative">
        <div className="pointer-events-none absolute inset-x-0 top-5 bottom-6 flex flex-col justify-between">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="border-t border-dashed border-slate-100" />
          ))}
        </div>
        <div className="relative flex h-24 items-end justify-between gap-1.5 border-b border-slate-200 pb-0.5">
          {data.map((item, index) => {
            const heightPct = Math.max(8, (item.value / peak) * 100);
            const color = item.color ?? "#0ea5e9";
            return (
              <div key={index} className="flex flex-1 flex-col items-center gap-0.5">
                <span className="text-[10px] font-bold tabular-nums text-slate-700">
                  {item.value.toFixed(item.value < 10 ? 1 : 0)}
                  <span className="text-[9px] font-medium text-slate-400">{unit}</span>
                </span>
                <div className="flex w-full flex-1 items-end px-0.5">
                  <div
                    className="w-full rounded-t-md shadow-sm transition-all duration-500"
                    style={{
                      height: `${heightPct}%`,
                      minHeight: 6,
                      background: `linear-gradient(180deg, ${color} 0%, ${color}99 100%)`,
                    }}
                  />
                </div>
                <span className="max-w-full truncate text-[9px] font-semibold text-slate-500">
                  {item.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
