from datetime import date, datetime, timezone
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import forbidden, not_found, unprocessable_entity
from app.models.farm_models import (
    FarmerProfileSchema,
    FarmerProfileUpdate,
    FarmSchema,
    FarmCreateSchema,
    PlotSchema,
    PlotCreateSchema,
    CropCycleSchema,
    CropCycleCreateSchemaNew,
    ExpenseSchema,
    ExpenseCreateSchema,
    HarvestSchema,
    HarvestCreateSchema,
)

# Helper function to convert date objects to datetimes for MongoDB storage
def _date_to_datetime(d: date) -> datetime:
    return datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)

# Helper function to convert datetime objects from MongoDB back to dates
def _datetime_to_date(dt: Optional[datetime]) -> Optional[date]:
    if dt is None:
        return None
    return dt.date()


class FarmDbService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    # Helper function to verify farm ownership
    async def _verify_farm_owner(self, farm_id: str, user_id: str) -> dict:
        try:
            f_oid = ObjectId(farm_id)
        except Exception:
            raise unprocessable_entity("Invalid farm ID format")
        
        farm = await self.db.farms.find_one({"_id": f_oid})
        if farm is None:
            raise not_found("Farm not found")
        if str(farm["user_id"]) != user_id:
            raise forbidden("Not authorized to access this farm")
        return farm

    # Helper function to verify plot ownership
    async def _verify_plot_owner(self, plot_id: str, user_id: str) -> dict:
        try:
            p_oid = ObjectId(plot_id)
        except Exception:
            raise unprocessable_entity("Invalid plot ID format")
            
        plot = await self.db.plots.find_one({"_id": p_oid})
        if plot is None:
            raise not_found("Plot not found")
        
        await self._verify_farm_owner(str(plot["farm_id"]), user_id)
        return plot

    # Helper function to verify crop cycle ownership
    async def _verify_crop_cycle_owner(self, cycle_id: str, user_id: str) -> dict:
        try:
            c_oid = ObjectId(cycle_id)
        except Exception:
            raise unprocessable_entity("Invalid crop cycle ID format")
            
        cycle = await self.db.crop_cycles.find_one({"_id": c_oid})
        if cycle is None:
            raise not_found("Crop cycle not found")
            
        plot_id = cycle.get("plot_id")
        if plot_id:
            await self._verify_plot_owner(str(plot_id), user_id)
        elif "farm_id" in cycle:
            await self._verify_farm_owner(str(cycle["farm_id"]), user_id)
        else:
            raise unprocessable_entity("Crop cycle has no associated plot or farm")
            
        return cycle

    # --- Farmer profile operations ---
    async def get_farmer(self, user_id: str) -> FarmerProfileSchema:
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise not_found("Farmer not found")
            
        return FarmerProfileSchema(
            id=str(user["_id"]),
            name=user["name"],
            preferred_language=user.get("preferred_lang", "hi"),
            state=user.get("state", ""),
            district=user.get("district", ""),
            created_at=user.get("created_at", datetime.now(timezone.utc)),
        )

    async def update_farmer(self, user_id: str, payload: FarmerProfileUpdate) -> FarmerProfileSchema:
        updates: dict = {}
        if payload.name is not None:
            updates["name"] = payload.name
        if payload.preferred_language is not None:
            updates["preferred_lang"] = payload.preferred_language
        if payload.state is not None:
            updates["state"] = payload.state
        if payload.district is not None:
            updates["district"] = payload.district

        if updates:
            updates["updated_at"] = datetime.now(timezone.utc)
            await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": updates},
            )
            
        return await self.get_farmer(user_id)

    # --- Farm operations ---
    async def create_farm(self, user_id: str, payload: FarmCreateSchema) -> FarmSchema:
        now = datetime.now(timezone.utc)
        farm_doc = {
            "user_id": ObjectId(user_id),
            "name": payload.name,
            "area": payload.area,
            "area_unit": payload.area_unit,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "created_at": now,
        }
        res = await self.db.farms.insert_one(farm_doc)
        
        return FarmSchema(
            id=str(res.inserted_id),
            farmer_id=user_id,
            name=payload.name,
            area=payload.area,
            area_unit=payload.area_unit,
            latitude=payload.latitude,
            longitude=payload.longitude,
            created_at=now,
        )

    async def get_farms(self, user_id: str) -> List[FarmSchema]:
        cursor = self.db.farms.find({"user_id": ObjectId(user_id)})
        farms = []
        async for doc in cursor:
            farms.append(
                FarmSchema(
                    id=str(doc["_id"]),
                    farmer_id=user_id,
                    name=doc["name"],
                    area=doc.get("area", 0.0),
                    area_unit=doc.get("area_unit", "ACRE"),
                    latitude=doc.get("latitude", 0.0),
                    longitude=doc.get("longitude", 0.0),
                    created_at=doc.get("created_at", datetime.now(timezone.utc)),
                )
            )
        return farms

    async def get_farm(self, user_id: str, farm_id: str) -> FarmSchema:
        doc = await self._verify_farm_owner(farm_id, user_id)
        return FarmSchema(
            id=str(doc["_id"]),
            farmer_id=user_id,
            name=doc["name"],
            area=doc.get("area", 0.0),
            area_unit=doc.get("area_unit", "ACRE"),
            latitude=doc.get("latitude", 0.0),
            longitude=doc.get("longitude", 0.0),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
        )

    async def update_farm(self, user_id: str, farm_id: str, payload: FarmCreateSchema) -> FarmSchema:
        await self._verify_farm_owner(farm_id, user_id)
        
        updates = {
            "name": payload.name,
            "area": payload.area,
            "area_unit": payload.area_unit,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "updated_at": datetime.now(timezone.utc)
        }
        await self.db.farms.update_one({"_id": ObjectId(farm_id)}, {"$set": updates})
        return await self.get_farm(user_id, farm_id)

    async def delete_farm(self, user_id: str, farm_id: str) -> None:
        await self._verify_farm_owner(farm_id, user_id)
        
        # Cascade delete plots, crop cycles, etc.
        plots_cursor = self.db.plots.find({"farm_id": ObjectId(farm_id)})
        async for plot in plots_cursor:
            plot_id = str(plot["_id"])
            cycles_cursor = self.db.crop_cycles.find({"plot_id": ObjectId(plot_id)})
            async for cycle in cycles_cursor:
                cycle_id = str(cycle["_id"])
                await self.db.expenses.delete_many({"crop_cycle_id": ObjectId(cycle_id)})
                await self.db.harvests.delete_many({"crop_cycle_id": ObjectId(cycle_id)})
            await self.db.crop_cycles.delete_many({"plot_id": ObjectId(plot_id)})
        await self.db.plots.delete_many({"farm_id": ObjectId(farm_id)})
        await self.db.farms.delete_one({"_id": ObjectId(farm_id)})

    # --- Plot operations ---
    async def create_plot(self, user_id: str, payload: PlotCreateSchema) -> PlotSchema:
        await self._verify_farm_owner(payload.farm_id, user_id)
        
        plot_doc = {
            "farm_id": ObjectId(payload.farm_id),
            "name": payload.name,
            "area": payload.area,
            "area_unit": payload.area_unit,
            "created_at": datetime.now(timezone.utc),
        }
        res = await self.db.plots.insert_one(plot_doc)
        
        return PlotSchema(
            id=str(res.inserted_id),
            farm_id=payload.farm_id,
            name=payload.name,
            area=payload.area,
            area_unit=payload.area_unit,
        )

    async def get_plots(self, user_id: str, farm_id: str) -> List[PlotSchema]:
        await self._verify_farm_owner(farm_id, user_id)
        
        cursor = self.db.plots.find({"farm_id": ObjectId(farm_id)})
        plots = []
        async for doc in cursor:
            plots.append(
                PlotSchema(
                    id=str(doc["_id"]),
                    farm_id=farm_id,
                    name=doc["name"],
                    area=doc.get("area", 0.0),
                    area_unit=doc.get("area_unit", "ACRE"),
                )
            )
        return plots

    async def get_plot(self, user_id: str, plot_id: str) -> PlotSchema:
        doc = await self._verify_plot_owner(plot_id, user_id)
        return PlotSchema(
            id=str(doc["_id"]),
            farm_id=str(doc["farm_id"]),
            name=doc["name"],
            area=doc.get("area", 0.0),
            area_unit=doc.get("area_unit", "ACRE"),
        )

    async def update_plot(self, user_id: str, plot_id: str, payload: PlotCreateSchema) -> PlotSchema:
        await self._verify_plot_owner(plot_id, user_id)
        await self._verify_farm_owner(payload.farm_id, user_id)
        
        updates = {
            "farm_id": ObjectId(payload.farm_id),
            "name": payload.name,
            "area": payload.area,
            "area_unit": payload.area_unit,
            "updated_at": datetime.now(timezone.utc),
        }
        await self.db.plots.update_one({"_id": ObjectId(plot_id)}, {"$set": updates})
        return await self.get_plot(user_id, plot_id)

    async def delete_plot(self, user_id: str, plot_id: str) -> None:
        await self._verify_plot_owner(plot_id, user_id)
        
        # Cascade delete crop cycles, expenses, harvests
        cycles_cursor = self.db.crop_cycles.find({"plot_id": ObjectId(plot_id)})
        async for cycle in cycles_cursor:
            cycle_id = str(cycle["_id"])
            await self.db.expenses.delete_many({"crop_cycle_id": ObjectId(cycle_id)})
            await self.db.harvests.delete_many({"crop_cycle_id": ObjectId(cycle_id)})
        await self.db.crop_cycles.delete_many({"plot_id": ObjectId(plot_id)})
        await self.db.plots.delete_one({"_id": ObjectId(plot_id)})

    # --- Crop Cycle operations ---
    async def create_crop_cycle(self, user_id: str, payload: CropCycleCreateSchemaNew) -> CropCycleSchema:
        plot = await self._verify_plot_owner(payload.plot_id, user_id)
        
        now = datetime.now(timezone.utc)
        cycle_doc = {
            "plot_id": ObjectId(payload.plot_id),
            "farm_id": plot["farm_id"],
            "crop_type": payload.crop_type.upper(),
            "season": payload.season.upper(),
            "sowing_date": _date_to_datetime(payload.sowing_date),
            "expected_harvest_date": _date_to_datetime(payload.expected_harvest_date),
            "status": "ACTIVE",
            "current_gdd": 0.0,
            "created_at": now,
            "updated_at": now,
        }
        res = await self.db.crop_cycles.insert_one(cycle_doc)
        
        return CropCycleSchema(
            id=str(res.inserted_id),
            plot_id=payload.plot_id,
            crop_type=payload.crop_type,
            season=payload.season,
            sowing_date=payload.sowing_date,
            expected_harvest_date=payload.expected_harvest_date,
            status="ACTIVE",
        )

    async def get_crop_cycles(self, user_id: str, plot_id: str) -> List[CropCycleSchema]:
        await self._verify_plot_owner(plot_id, user_id)
        
        cursor = self.db.crop_cycles.find({"plot_id": ObjectId(plot_id)})
        cycles = []
        async for doc in cursor:
            cycles.append(
                CropCycleSchema(
                    id=str(doc["_id"]),
                    plot_id=plot_id,
                    crop_type=doc["crop_type"],
                    season=doc["season"],
                    sowing_date=_datetime_to_date(doc["sowing_date"]),
                    expected_harvest_date=_datetime_to_date(doc["expected_harvest_date"]),
                    status=doc.get("status", "ACTIVE"),
                )
            )
        return cycles

    async def get_active_crop_cycles(self, user_id: str) -> List[CropCycleSchema]:
        # Retrieve all active crop cycles across all user farms and plots
        farms = await self.get_farms(user_id)
        active_cycles = []
        for farm in farms:
            plots = await self.get_plots(user_id, farm.id)
            for plot in plots:
                cursor = self.db.crop_cycles.find({"plot_id": ObjectId(plot.id), "status": "ACTIVE"})
                async for doc in cursor:
                    active_cycles.append(
                        CropCycleSchema(
                            id=str(doc["_id"]),
                            plot_id=plot.id,
                            crop_type=doc["crop_type"],
                            season=doc["season"],
                            sowing_date=_datetime_to_date(doc["sowing_date"]),
                            expected_harvest_date=_datetime_to_date(doc["expected_harvest_date"]),
                            status="ACTIVE",
                        )
                    )
        return active_cycles

    async def get_crop_cycle(self, user_id: str, cycle_id: str) -> CropCycleSchema:
        doc = await self._verify_crop_cycle_owner(cycle_id, user_id)
        
        expected_date = doc.get("expected_harvest_date")
        if expected_date is None:
            sowing = doc["sowing_date"]
            if isinstance(sowing, str):
                sowing = datetime.fromisoformat(sowing)
            from datetime import timedelta
            expected_date = sowing + timedelta(days=120)

        return CropCycleSchema(
            id=str(doc["_id"]),
            plot_id=str(doc.get("plot_id", "")),
            crop_type=doc["crop_type"],
            season=doc.get("season", "WHOLE_YEAR"),
            sowing_date=_datetime_to_date(doc["sowing_date"]),
            expected_harvest_date=_datetime_to_date(expected_date),
            status=doc.get("status", "ACTIVE"),
        )

    async def update_crop_cycle(self, user_id: str, cycle_id: str, payload: CropCycleCreateSchemaNew) -> CropCycleSchema:
        await self._verify_crop_cycle_owner(cycle_id, user_id)
        await self._verify_plot_owner(payload.plot_id, user_id)
        
        updates = {
            "plot_id": ObjectId(payload.plot_id),
            "crop_type": payload.crop_type.upper(),
            "season": payload.season.upper(),
            "sowing_date": _date_to_datetime(payload.sowing_date),
            "expected_harvest_date": _date_to_datetime(payload.expected_harvest_date),
            "updated_at": datetime.now(timezone.utc),
        }
        await self.db.crop_cycles.update_one({"_id": ObjectId(cycle_id)}, {"$set": updates})
        return await self.get_crop_cycle(user_id, cycle_id)

    async def delete_crop_cycle(self, user_id: str, cycle_id: str) -> None:
        await self._verify_crop_cycle_owner(cycle_id, user_id)
        
        await self.db.expenses.delete_many({"crop_cycle_id": ObjectId(cycle_id)})
        await self.db.harvests.delete_many({"crop_cycle_id": ObjectId(cycle_id)})
        await self.db.crop_cycles.delete_one({"_id": ObjectId(cycle_id)})

    # --- Expense operations ---
    async def create_expense(self, user_id: str, payload: ExpenseCreateSchema) -> ExpenseSchema:
        await self._verify_crop_cycle_owner(payload.crop_cycle_id, user_id)
        
        expense_doc = {
            "crop_cycle_id": ObjectId(payload.crop_cycle_id),
            "category": payload.category,
            "amount": payload.amount,
            "notes": payload.notes,
            "expense_date": _date_to_datetime(payload.expense_date),
            "created_at": datetime.now(timezone.utc),
        }
        res = await self.db.expenses.insert_one(expense_doc)
        
        return ExpenseSchema(
            id=str(res.inserted_id),
            crop_cycle_id=payload.crop_cycle_id,
            category=payload.category,
            amount=payload.amount,
            notes=payload.notes,
            expense_date=payload.expense_date,
        )

    async def get_expenses(self, user_id: str, crop_cycle_id: str) -> List[ExpenseSchema]:
        await self._verify_crop_cycle_owner(crop_cycle_id, user_id)
        
        cursor = self.db.expenses.find({"crop_cycle_id": ObjectId(crop_cycle_id)})
        expenses = []
        async for doc in cursor:
            expenses.append(
                ExpenseSchema(
                    id=str(doc["_id"]),
                    crop_cycle_id=crop_cycle_id,
                    category=doc["category"],
                    amount=doc["amount"],
                    notes=doc.get("notes"),
                    expense_date=_datetime_to_date(doc["expense_date"]),
                )
            )
        return expenses

    async def get_expense(self, user_id: str, expense_id: str) -> ExpenseSchema:
        try:
            e_oid = ObjectId(expense_id)
        except Exception:
            raise unprocessable_entity("Invalid expense ID format")
            
        doc = await self.db.expenses.find_one({"_id": e_oid})
        if doc is None:
            raise not_found("Expense not found")
            
        await self._verify_crop_cycle_owner(str(doc["crop_cycle_id"]), user_id)
        
        return ExpenseSchema(
            id=str(doc["_id"]),
            crop_cycle_id=str(doc["crop_cycle_id"]),
            category=doc["category"],
            amount=doc["amount"],
            notes=doc.get("notes"),
            expense_date=_datetime_to_date(doc["expense_date"]),
        )

    async def update_expense(self, user_id: str, expense_id: str, payload: ExpenseCreateSchema) -> ExpenseSchema:
        # Check permissions
        try:
            e_oid = ObjectId(expense_id)
        except Exception:
            raise unprocessable_entity("Invalid expense ID format")
            
        doc = await self.db.expenses.find_one({"_id": e_oid})
        if doc is None:
            raise not_found("Expense not found")
            
        await self._verify_crop_cycle_owner(str(doc["crop_cycle_id"]), user_id)
        await self._verify_crop_cycle_owner(payload.crop_cycle_id, user_id)
        
        updates = {
            "crop_cycle_id": ObjectId(payload.crop_cycle_id),
            "category": payload.category,
            "amount": payload.amount,
            "notes": payload.notes,
            "expense_date": _date_to_datetime(payload.expense_date),
            "updated_at": datetime.now(timezone.utc),
        }
        await self.db.expenses.update_one({"_id": e_oid}, {"$set": updates})
        return await self.get_expense(user_id, expense_id)

    async def delete_expense(self, user_id: str, expense_id: str) -> None:
        try:
            e_oid = ObjectId(expense_id)
        except Exception:
            raise unprocessable_entity("Invalid expense ID format")
            
        doc = await self.db.expenses.find_one({"_id": e_oid})
        if doc is None:
            raise not_found("Expense not found")
            
        await self._verify_crop_cycle_owner(str(doc["crop_cycle_id"]), user_id)
        await self.db.expenses.delete_one({"_id": e_oid})

    # --- Harvest operations ---
    async def create_harvest(self, user_id: str, payload: HarvestCreateSchema) -> HarvestSchema:
        await self._verify_crop_cycle_owner(payload.crop_cycle_id, user_id)
        
        harvest_doc = {
            "crop_cycle_id": ObjectId(payload.crop_cycle_id),
            "yield_quantity": payload.yield_quantity,
            "yield_unit": payload.yield_unit,
            "revenue": payload.revenue,
            "harvest_date": _date_to_datetime(payload.harvest_date),
            "created_at": datetime.now(timezone.utc),
        }
        res = await self.db.harvests.insert_one(harvest_doc)
        
        # Mark CropCycle status as HARVESTED
        await self.db.crop_cycles.update_one(
            {"_id": ObjectId(payload.crop_cycle_id)},
            {"$set": {"status": "HARVESTED", "updated_at": datetime.now(timezone.utc)}}
        )
        
        return HarvestSchema(
            id=str(res.inserted_id),
            crop_cycle_id=payload.crop_cycle_id,
            yield_quantity=payload.yield_quantity,
            yield_unit=payload.yield_unit,
            revenue=payload.revenue,
            harvest_date=payload.harvest_date,
        )

    async def get_harvests(self, user_id: str, crop_cycle_id: str) -> List[HarvestSchema]:
        await self._verify_crop_cycle_owner(crop_cycle_id, user_id)
        
        cursor = self.db.harvests.find({"crop_cycle_id": ObjectId(crop_cycle_id)})
        harvests = []
        async for doc in cursor:
            harvests.append(
                HarvestSchema(
                    id=str(doc["_id"]),
                    crop_cycle_id=crop_cycle_id,
                    yield_quantity=doc["yield_quantity"],
                    yield_unit=doc["yield_unit"],
                    revenue=doc["revenue"],
                    harvest_date=_datetime_to_date(doc["harvest_date"]),
                )
            )
        return harvests

    async def get_harvest(self, user_id: str, harvest_id: str) -> HarvestSchema:
        try:
            h_oid = ObjectId(harvest_id)
        except Exception:
            raise unprocessable_entity("Invalid harvest ID format")
            
        doc = await self.db.harvests.find_one({"_id": h_oid})
        if doc is None:
            raise not_found("Harvest not found")
            
        await self._verify_crop_cycle_owner(str(doc["crop_cycle_id"]), user_id)
        
        return HarvestSchema(
            id=str(doc["_id"]),
            crop_cycle_id=str(doc["crop_cycle_id"]),
            yield_quantity=doc["yield_quantity"],
            yield_unit=doc["yield_unit"],
            revenue=doc["revenue"],
            harvest_date=_datetime_to_date(doc["harvest_date"]),
        )

    async def update_harvest(self, user_id: str, harvest_id: str, payload: HarvestCreateSchema) -> HarvestSchema:
        try:
            h_oid = ObjectId(harvest_id)
        except Exception:
            raise unprocessable_entity("Invalid harvest ID format")
            
        doc = await self.db.harvests.find_one({"_id": h_oid})
        if doc is None:
            raise not_found("Harvest not found")
            
        await self._verify_crop_cycle_owner(str(doc["crop_cycle_id"]), user_id)
        await self._verify_crop_cycle_owner(payload.crop_cycle_id, user_id)
        
        updates = {
            "crop_cycle_id": ObjectId(payload.crop_cycle_id),
            "yield_quantity": payload.yield_quantity,
            "yield_unit": payload.yield_unit,
            "revenue": payload.revenue,
            "harvest_date": _date_to_datetime(payload.harvest_date),
            "updated_at": datetime.now(timezone.utc),
        }
        await self.db.harvests.update_one({"_id": h_oid}, {"$set": updates})
        return await self.get_harvest(user_id, harvest_id)

    async def delete_harvest(self, user_id: str, harvest_id: str) -> None:
        try:
            h_oid = ObjectId(harvest_id)
        except Exception:
            raise unprocessable_entity("Invalid harvest ID format")
            
        doc = await self.db.harvests.find_one({"_id": h_oid})
        if doc is None:
            raise not_found("Harvest not found")
            
        await self._verify_crop_cycle_owner(str(doc["crop_cycle_id"]), user_id)
        await self.db.harvests.delete_one({"_id": h_oid})
        
        # Optionally reset crop cycle status to ACTIVE if all harvests are deleted
        harvests_count = await self.db.harvests.count_documents({"crop_cycle_id": doc["crop_cycle_id"]})
        if harvests_count == 0:
            await self.db.crop_cycles.update_one(
                {"_id": doc["crop_cycle_id"]},
                {"$set": {"status": "ACTIVE", "updated_at": datetime.now(timezone.utc)}}
            )
