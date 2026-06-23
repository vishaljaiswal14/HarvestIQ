from datetime import date, datetime, timezone
from typing import List, Optional, Dict, Tuple, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.farm_db_service import FarmDbService
from app.models.profitability_schemas import (
    ProfitabilityMetrics,
    CropCycleProfitability,
    FarmProfitabilitySummary,
    SeasonProfitability,
)


class ProfitabilityService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.farm_service = FarmDbService(db)

    def _extract_year(self, sowing_date: Any) -> int:
        if isinstance(sowing_date, (datetime, date)):
            return sowing_date.year
        try:
            return datetime.fromisoformat(str(sowing_date)).year
        except Exception:
            return datetime.now(timezone.utc).year

    async def _get_cycle_expenses_and_harvests(self, cycle_id: str) -> Tuple[list, list]:
        expenses = await self.db.expenses.find({"crop_cycle_id": ObjectId(cycle_id)}).to_list(length=None)
        harvests = await self.db.harvests.find({"crop_cycle_id": ObjectId(cycle_id)}).to_list(length=None)
        return expenses, harvests

    def _calculate_metrics(self, expenses: list, harvests: list) -> ProfitabilityMetrics:
        total_cost = sum(e["amount"] for e in expenses)
        total_revenue = sum(h["revenue"] for h in harvests)
        net_profit = total_revenue - total_cost

        roi_percent = 0.0
        if total_cost > 0.0:
            roi_percent = (net_profit / total_cost) * 100.0

        total_yield = sum(h["yield_quantity"] for h in harvests)
        
        cost_per_unit = 0.0
        revenue_per_unit = 0.0
        if total_yield > 0.0:
            cost_per_unit = total_cost / total_yield
            revenue_per_unit = total_revenue / total_yield

        break_even_yield = 0.0
        if revenue_per_unit > 0.0:
            break_even_yield = total_cost / revenue_per_unit

        break_even_price = 0.0
        if total_yield > 0.0:
            break_even_price = total_cost / total_yield

        return ProfitabilityMetrics(
            total_cost=total_cost,
            total_revenue=total_revenue,
            net_profit=net_profit,
            roi_percent=roi_percent,
            cost_per_unit=cost_per_unit,
            revenue_per_unit=revenue_per_unit,
            break_even_yield=break_even_yield,
            break_even_price=break_even_price,
        )

    async def calculate_crop_cycle_metrics(self, user_id: str, cycle_id: str) -> CropCycleProfitability:
        cycle = await self.farm_service._verify_crop_cycle_owner(cycle_id, user_id)
        expenses, harvests = await self._get_cycle_expenses_and_harvests(cycle_id)
        metrics = self._calculate_metrics(expenses, harvests)

        return CropCycleProfitability(
            crop_cycle_id=cycle_id,
            crop_type=cycle["crop_type"],
            season=cycle.get("season", "WHOLE_YEAR"),
            metrics=metrics,
        )

    async def calculate_plot_metrics(self, user_id: str, plot_id: str) -> ProfitabilityMetrics:
        await self.farm_service._verify_plot_owner(plot_id, user_id)
        cycles = await self.db.crop_cycles.find({"plot_id": ObjectId(plot_id)}).to_list(length=None)

        all_expenses = []
        all_harvests = []
        for cycle in cycles:
            cycle_id = str(cycle["_id"])
            expenses, harvests = await self._get_cycle_expenses_and_harvests(cycle_id)
            all_expenses.extend(expenses)
            all_harvests.extend(harvests)

        return self._calculate_metrics(all_expenses, all_harvests)

    async def calculate_farm_summary(self, user_id: str, farm_id: str) -> FarmProfitabilitySummary:
        await self.farm_service._verify_farm_owner(farm_id, user_id)
        plots = await self.db.plots.find({"farm_id": ObjectId(farm_id)}).to_list(length=None)
        plot_ids = [p["_id"] for p in plots]
        
        cycles = await self.db.crop_cycles.find({
            "$or": [
                {"plot_id": {"$in": plot_ids}},
                {"farm_id": ObjectId(farm_id)}
            ]
        }).to_list(length=None)

        all_expenses = []
        all_harvests = []
        crop_profits: Dict[str, float] = {}

        for cycle in cycles:
            cycle_id = str(cycle["_id"])
            crop_type = cycle["crop_type"].upper()
            
            expenses, harvests = await self._get_cycle_expenses_and_harvests(cycle_id)
            all_expenses.extend(expenses)
            all_harvests.extend(harvests)

            c_cost = sum(e["amount"] for e in expenses)
            c_revenue = sum(h["revenue"] for h in harvests)
            c_profit = c_revenue - c_cost

            crop_profits[crop_type] = crop_profits.get(crop_type, 0.0) + c_profit

        total_cost = sum(e["amount"] for e in all_expenses)
        total_revenue = sum(h["revenue"] for h in all_harvests)
        total_profit = total_revenue - total_cost

        roi_percent = 0.0
        if total_cost > 0.0:
            roi_percent = (total_profit / total_cost) * 100.0

        best_crop = ""
        worst_crop = ""
        if crop_profits:
            best_crop = max(crop_profits, key=crop_profits.get)
            worst_crop = min(crop_profits, key=crop_profits.get)

        return FarmProfitabilitySummary(
            total_cost=total_cost,
            total_revenue=total_revenue,
            total_profit=total_profit,
            best_performing_crop=best_crop,
            worst_performing_crop=worst_crop,
            roi_percent=roi_percent,
        )

    async def calculate_season_comparison(self, user_id: str, farm_id: str) -> List[SeasonProfitability]:
        await self.farm_service._verify_farm_owner(farm_id, user_id)
        plots = await self.db.plots.find({"farm_id": ObjectId(farm_id)}).to_list(length=None)
        plot_ids = [p["_id"] for p in plots]
        
        cycles = await self.db.crop_cycles.find({
            "$or": [
                {"plot_id": {"$in": plot_ids}},
                {"farm_id": ObjectId(farm_id)}
            ]
        }).to_list(length=None)

        season_data: Dict[str, Tuple[float, float]] = {}  # key -> (cost, revenue)

        for cycle in cycles:
            cycle_id = str(cycle["_id"])
            year = self._extract_year(cycle.get("sowing_date"))
            season_key = f"{cycle.get('season', 'WHOLE_YEAR').upper()}_{year}"

            expenses, harvests = await self._get_cycle_expenses_and_harvests(cycle_id)
            c_cost = sum(e["amount"] for e in expenses)
            c_revenue = sum(h["revenue"] for h in harvests)

            prev_cost, prev_rev = season_data.get(season_key, (0.0, 0.0))
            season_data[season_key] = (prev_cost + c_cost, prev_rev + c_revenue)

        comparisons = []
        for season, (cost, revenue) in season_data.items():
            profit = revenue - cost
            roi = 0.0
            if cost > 0.0:
                roi = (profit / cost) * 100.0
            
            comparisons.append(
                SeasonProfitability(
                    season=season,
                    profit=profit,
                    roi=roi,
                )
            )

        # Sort comparisons by season key for chronological clarity
        comparisons.sort(key=lambda x: x.season)
        return comparisons
