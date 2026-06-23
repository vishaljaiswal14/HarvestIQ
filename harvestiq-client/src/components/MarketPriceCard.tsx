"use client";

import { ArrowDownRight, ArrowUpRight, Minus, Store } from "lucide-react";

import { Sparkline } from "@/components/charts/Sparkline";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useMarketPrices } from "@/hooks/useMarketPrices";
import { useTranslation } from "@/stores/localizationStore";
type MarketPriceCardProps = {
  farmId?: string | null;
};

function trendSeverity(trend: string) {
  const upper = trend.toUpperCase();
  if (upper.includes("UP") || upper.includes("RISING")) return "healthy" as const;
  if (upper.includes("DOWN") || upper.includes("FALL")) return "critical" as const;
  return "moderate" as const;
}

function TrendIcon({ trend }: { trend: string }) {
  const upper = trend.toUpperCase();
  if (upper.includes("UP") || upper.includes("RISING")) return <ArrowUpRight className="h-4 w-4" />;
  if (upper.includes("DOWN") || upper.includes("FALL")) return <ArrowDownRight className="h-4 w-4" />;
  return <Minus className="h-4 w-4" />;
}

export function MarketPriceCard({ farmId }: MarketPriceCardProps) {
  const { t } = useTranslation();
  const { data, isLoading, error } = useMarketPrices(farmId);

  if (!farmId) return null;

  if (isLoading) {
    return (
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle>{t("market_intel", "Market Intelligence")}</CardTitle>
          <CardDescription>{t("market.loading", "Loading mandi prices…")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-32 animate-pulse rounded-xl bg-slate-100" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle>{t("market_intel", "Market Intelligence")}</CardTitle>
          <CardDescription className="text-amber-700">
            {t("market.unavailable", "Market prices unavailable — last known prices shown when cached.")}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const latest = data.prices[0];
  const priceHistory = [...data.prices].reverse().map((p) => p.modal_price);
  const historyLabels = [...data.prices].reverse().map((p) =>
    new Date(p.price_date).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
  );

  return (
    <Card className="dashboard-card">
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <p className="dashboard-section-title mb-1">{t("market.mandiPrices", "Mandi Prices")}</p>
          <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-800">
            <Store className="h-5 w-5 text-amber-600" />
            {t("market_intel", "Market Intelligence")}
          </CardTitle>
          <CardDescription>{t("crop." + data.crop_type.toLowerCase(), data.crop_type)}</CardDescription>
        </div>
        <Badge severity={trendSeverity(data.modal_trend)} variant="outline">
          <TrendIcon trend={data.modal_trend} />
          {t(data.modal_trend, data.modal_trend)}
        </Badge>
      </CardHeader>

      <CardContent className="space-y-4">
        {latest ? (
          <>
            <div className="flex items-end justify-between">
              <div>
                <p className="text-3xl font-bold tracking-tight text-slate-900">₹{latest.modal_price}</p>
                <p className="text-sm text-slate-600">
                  {latest.mandi} · {t("market.range", "range")} ₹{latest.min_price}–₹{latest.max_price}
                </p>
              </div>
              <p className="text-xs text-slate-400">
                {t("market.asOf", "As of")}: {new Date(data.as_of).toLocaleDateString()}
              </p>
            </div>

            {priceHistory.length > 1 && (
              <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{t("market.priceTrend", "Price trend")}</p>
                <Sparkline values={priceHistory} color="#d97706" height={64} labels={[historyLabels[0], historyLabels[historyLabels.length - 1]]} />
              </div>
            )}

            <div className="overflow-hidden rounded-xl border border-slate-100">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/80 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2">{t("market.mandi", "Mandi")}</th>
                    <th className="px-3 py-2 text-right">{t("market.modal", "Modal")}</th>
                    <th className="hidden px-3 py-2 text-right sm:table-cell">{t("market.rangeHeader", "Range")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.prices.slice(0, 5).map((row) => (
                    <tr key={`${row.mandi}-${row.price_date}`} className="border-b border-slate-50 last:border-0">
                      <td className="px-3 py-2 font-medium text-slate-800">{row.mandi}</td>
                      <td className="px-3 py-2 text-right font-semibold text-slate-900">₹{row.modal_price}</td>
                      <td className="hidden px-3 py-2 text-right text-slate-500 sm:table-cell">
                        ₹{row.min_price}–₹{row.max_price}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="text-sm text-slate-600">{t("market.noRecords", "No market records for this crop and state.")}</p>
        )}
      </CardContent>
    </Card>
  );
}
