import {
  Carrot,
  Candy,
  Leaf,
  Sprout,
  Wheat,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { t } from "@/stores/localizationStore";

const CROP_ICONS: Record<string, LucideIcon> = {
  WHEAT: Wheat,
  SUGARCANE: Candy,
  SOYBEAN: Leaf,
  MUSTARD: Sprout,
  POTATO: Carrot,
};

const CROP_COLORS: Record<string, string> = {
  WHEAT: "#d97706",
  SUGARCANE: "#84cc16",
  SOYBEAN: "#65a30d",
  MUSTARD: "#eab308",
  POTATO: "#a16207",
};

export function getCropColor(cropType?: string | null): string {
  if (!cropType) return "#10b981";
  return CROP_COLORS[cropType.toUpperCase()] ?? "#10b981";
}

type CropIconProps = {
  cropType?: string | null;
  className?: string;
  size?: "sm" | "md" | "lg";
};

const SIZE_MAP = { sm: "h-4 w-4", md: "h-5 w-5", lg: "h-7 w-7" };
const BOX_MAP = { sm: "h-8 w-8", md: "h-10 w-10", lg: "h-14 w-14" };

export function CropIcon({ cropType, className, size = "md" }: CropIconProps) {
  const key = cropType?.toUpperCase() ?? "";
  const Icon = CROP_ICONS[key] ?? Sprout;
  const color = getCropColor(cropType);

  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-xl",
        BOX_MAP[size],
        className,
      )}
      style={{ backgroundColor: `${color}18`, color }}
    >
      <Icon className={SIZE_MAP[size]} />
    </div>
  );
}

export function CropBadge({ cropType }: { cropType?: string | null }) {
  if (!cropType) return null;
  const color = getCropColor(cropType);
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
      style={{ backgroundColor: `${color}18`, color }}
    >
      {t("crop." + cropType.toLowerCase(), cropType)}
    </span>
  );
}

export function FieldStatusChip({
  label,
  value,
  severity = "neutral",
}: {
  label: string;
  value: string;
  severity?: "healthy" | "moderate" | "critical" | "neutral";
}) {
  const colors = {
    healthy: "border-emerald-200 bg-emerald-50 text-emerald-800",
    moderate: "border-amber-200 bg-amber-50 text-amber-800",
    critical: "border-red-200 bg-red-50 text-red-800",
    neutral: "border-slate-200 bg-slate-50 text-slate-700",
  };

  return (
    <div className={cn("rounded-lg border px-2.5 py-1.5", colors[severity])}>
      <p className="text-[9px] font-semibold uppercase tracking-wider opacity-70">{label}</p>
      <p className="text-sm font-bold leading-tight">{value}</p>
    </div>
  );
}
