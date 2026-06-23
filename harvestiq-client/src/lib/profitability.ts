import {
  getFarmById,
  getPlotsByFarm,
  getPlotById,
  getCropCycleById,
  getCropCyclesByPlot,
  getExpensesByCropCycle,
  getHarvestsByCropCycle,
  LocalCropCycle,
  LocalExpense,
  LocalHarvest,
} from "./farmDb";

export interface ProfitabilityMetrics {
  total_cost: number;
  total_revenue: number;
  net_profit: number;
  roi_percent: number;
  cost_per_unit: number;
  revenue_per_unit: number;
  break_even_yield: number;
  break_even_price: number;
}

export interface CropCycleProfitability {
  crop_cycle_id: string;
  crop_type: string;
  season: string;
  metrics: ProfitabilityMetrics;
}

export interface FarmProfitabilitySummary {
  total_cost: number;
  total_revenue: number;
  total_profit: number;
  best_performing_crop: string;
  worst_performing_crop: string;
  roi_percent: number;
}

export interface SeasonProfitability {
  season: string;
  profit: number;
  roi: number;
}

function extractYear(sowingDate: string | Date | undefined | null): number {
  if (!sowingDate) return new Date().getFullYear();
  try {
    const d = new Date(sowingDate);
    if (isNaN(d.getTime())) {
      return new Date().getFullYear();
    }
    return d.getFullYear();
  } catch {
    return new Date().getFullYear();
  }
}

function calculateMetrics(expenses: LocalExpense[], harvests: LocalHarvest[]): ProfitabilityMetrics {
  const total_cost = expenses.reduce((sum, e) => sum + (e.amount || 0), 0);
  const total_revenue = harvests.reduce((sum, h) => sum + (h.revenue || 0), 0);
  const net_profit = total_revenue - total_cost;

  let roi_percent = 0.0;
  if (total_cost > 0.0) {
    roi_percent = (net_profit / total_cost) * 100.0;
  }

  const total_yield = harvests.reduce((sum, h) => sum + (h.yield_quantity || 0), 0);

  let cost_per_unit = 0.0;
  let revenue_per_unit = 0.0;
  if (total_yield > 0.0) {
    cost_per_unit = total_cost / total_yield;
    revenue_per_unit = total_revenue / total_yield;
  }

  let break_even_yield = 0.0;
  if (revenue_per_unit > 0.0) {
    break_even_yield = total_cost / revenue_per_unit;
  }

  let break_even_price = 0.0;
  if (total_yield > 0.0) {
    break_even_price = total_cost / total_yield;
  }

  return {
    total_cost,
    total_revenue,
    net_profit,
    roi_percent,
    cost_per_unit,
    revenue_per_unit,
    break_even_yield,
    break_even_price,
  };
}

export async function calculateLocalCropCycleProfitability(cycleId: string): Promise<CropCycleProfitability | null> {
  const cycle = await getCropCycleById(cycleId);
  if (!cycle) return null;

  const expenses = await getExpensesByCropCycle(cycleId);
  const harvests = await getHarvestsByCropCycle(cycleId);
  const metrics = calculateMetrics(expenses, harvests);

  return {
    crop_cycle_id: cycleId,
    crop_type: cycle.crop_type,
    season: cycle.season,
    metrics,
  };
}

export async function calculateLocalPlotProfitability(plotId: string): Promise<ProfitabilityMetrics | null> {
  const plot = await getPlotById(plotId);
  if (!plot) return null;

  const cycles = await getCropCyclesByPlot(plotId);
  const allExpenses: LocalExpense[] = [];
  const allHarvests: LocalHarvest[] = [];

  for (const cycle of cycles) {
    const expenses = await getExpensesByCropCycle(cycle.id);
    const harvests = await getHarvestsByCropCycle(cycle.id);
    allExpenses.push(...expenses);
    allHarvests.push(...harvests);
  }

  return calculateMetrics(allExpenses, allHarvests);
}

export async function calculateLocalFarmProfitability(farmId: string): Promise<FarmProfitabilitySummary | null> {
  const farm = await getFarmById(farmId);
  if (!farm) return null;

  const plots = await getPlotsByFarm(farmId);
  const allExpenses: LocalExpense[] = [];
  const allHarvests: LocalHarvest[] = [];
  const cropProfits: Record<string, number> = {};

  for (const plot of plots) {
    const cycles = await getCropCyclesByPlot(plot.id);
    for (const cycle of cycles) {
      const expenses = await getExpensesByCropCycle(cycle.id);
      const harvests = await getHarvestsByCropCycle(cycle.id);
      allExpenses.push(...expenses);
      allHarvests.push(...harvests);

      const c_cost = expenses.reduce((sum, e) => sum + (e.amount || 0), 0);
      const c_revenue = harvests.reduce((sum, h) => sum + (h.revenue || 0), 0);
      const c_profit = c_revenue - c_cost;

      const crop_type = (cycle.crop_type || "").toUpperCase();
      cropProfits[crop_type] = (cropProfits[crop_type] || 0) + c_profit;
    }
  }

  const total_cost = allExpenses.reduce((sum, e) => sum + (e.amount || 0), 0);
  const total_revenue = allHarvests.reduce((sum, h) => sum + (h.revenue || 0), 0);
  const total_profit = total_revenue - total_cost;

  let roi_percent = 0.0;
  if (total_cost > 0.0) {
    roi_percent = (total_profit / total_cost) * 100.0;
  }

  let best_performing_crop = "";
  let worst_performing_crop = "";
  const cropKeys = Object.keys(cropProfits);
  if (cropKeys.length > 0) {
    best_performing_crop = cropKeys.reduce((a, b) => (cropProfits[a] > cropProfits[b] ? a : b));
    worst_performing_crop = cropKeys.reduce((a, b) => (cropProfits[a] < cropProfits[b] ? a : b));
  }

  return {
    total_cost,
    total_revenue,
    total_profit,
    best_performing_crop,
    worst_performing_crop,
    roi_percent,
  };
}

export async function calculateLocalSeasonComparison(farmId: string): Promise<SeasonProfitability[]> {
  const farm = await getFarmById(farmId);
  if (!farm) return [];

  const plots = await getPlotsByFarm(farmId);
  const seasonData: Record<string, { cost: number; revenue: number }> = {};

  for (const plot of plots) {
    const cycles = await getCropCyclesByPlot(plot.id);
    for (const cycle of cycles) {
      const expenses = await getExpensesByCropCycle(cycle.id);
      const harvests = await getHarvestsByCropCycle(cycle.id);

      const c_cost = expenses.reduce((sum, e) => sum + (e.amount || 0), 0);
      const c_revenue = harvests.reduce((sum, h) => sum + (h.revenue || 0), 0);

      const year = extractYear(cycle.sowing_date);
      const season_key = `${(cycle.season || "").toUpperCase()}_${year}`;

      if (!seasonData[season_key]) {
        seasonData[season_key] = { cost: 0, revenue: 0 };
      }
      seasonData[season_key].cost += c_cost;
      seasonData[season_key].revenue += c_revenue;
    }
  }

  const comparisons: SeasonProfitability[] = [];
  for (const [season, data] of Object.entries(seasonData)) {
    const profit = data.revenue - data.cost;
    let roi = 0.0;
    if (data.cost > 0.0) {
      roi = (profit / data.cost) * 100.0;
    }

    comparisons.push({
      season,
      profit,
      roi,
    });
  }

  // Sort chronologically/alphabetically by season key
  comparisons.sort((a, b) => a.season.localeCompare(b.season));
  return comparisons;
}
