from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import forbidden, not_found, unprocessable_entity


async def get_owned_farm(db: AsyncIOMotorDatabase, farm_id: str, user_id: str) -> dict:
    if not ObjectId.is_valid(farm_id):
        raise not_found("Farm not found")

    farm = await db.farms.find_one({"_id": ObjectId(farm_id)})
    if farm is None:
        raise not_found("Farm not found")

    if str(farm["user_id"]) != user_id:
        raise forbidden("You do not have access to this farm")

    if not farm.get("location") or not farm["location"].get("coordinates"):
        raise unprocessable_entity("Farm location missing")

    return farm


async def get_owned_crop_cycle(
    db: AsyncIOMotorDatabase,
    cycle_id: str,
    user_id: str,
) -> tuple[dict, dict]:
    if not ObjectId.is_valid(cycle_id):
        raise not_found("Crop cycle not found")

    cycle = await db.crop_cycles.find_one({"_id": ObjectId(cycle_id)})
    if cycle is None:
        raise not_found("Crop cycle not found")

    plot_id = cycle.get("plot_id")
    if plot_id:
        plot = await db.plots.find_one({"_id": ObjectId(plot_id)})
        if plot is None:
            raise not_found("Plot not found")
        farm_id = plot["farm_id"]
    else:
        farm_id = cycle.get("farm_id")
        if not farm_id:
            raise unprocessable_entity("Crop cycle has no associated plot or farm")

    farm = await get_owned_farm(db, str(farm_id), user_id)
    return cycle, farm


async def get_latest_relevant_crop_cycle(
    db: AsyncIOMotorDatabase,
    farm_id: str,
) -> tuple[dict, str]:
    """
    Returns the most relevant crop cycle for a farm.
    Prefers ACTIVE; falls back to most recently updated cycle of any status.
    Raises 422 only if NO cycle exists at all.
    """
    if not ObjectId.is_valid(farm_id):
        raise not_found("Farm not found")

    # Try ACTIVE first
    cycle = await db.crop_cycles.find_one(
        {"farm_id": ObjectId(farm_id), "status": "ACTIVE"},
        sort=[("updated_at", -1)],
    )
    if cycle is not None:
        return cycle, "ACTIVE"

    # Fallback: most recently updated cycle regardless of status
    cycle = await db.crop_cycles.find_one(
        {"farm_id": ObjectId(farm_id)},
        sort=[("updated_at", -1)],
    )
    if cycle is None:
        raise unprocessable_entity("No crop cycle found for this farm")

    return cycle, cycle.get("status", "UNKNOWN")

