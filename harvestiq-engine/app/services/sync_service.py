from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import unprocessable_entity
from app.models.day7_schemas import SyncBatchRequest, SyncBatchResponse, SyncOperationResult
from app.models.day4_schemas import SoilRecordCreateSchema
from app.models.farm_models import (
    FarmCreateSchema,
    PlotCreateSchema,
    CropCycleCreateSchemaNew,
    ExpenseCreateSchema,
    HarvestCreateSchema,
)
from app.services.soil_health_service import SoilHealthService
from app.services.farm_db_service import FarmDbService

ALLOWED_SYNC_OPERATIONS = frozenset({
    "MARK_ALERT_READ",
    "DISPATCH_ALERT_ESCALATION",
    "SAVE_PUSH_SUBSCRIPTION",
    "CREATE_SOIL_RECORD",
    "CREATE_FARM", "UPDATE_FARM", "DELETE_FARM",
    "CREATE_PLOT", "UPDATE_PLOT", "DELETE_PLOT",
    "CREATE_CROP_CYCLE", "UPDATE_CROP_CYCLE", "DELETE_CROP_CYCLE",
    "CREATE_EXPENSE", "UPDATE_EXPENSE", "DELETE_EXPENSE",
    "CREATE_HARVEST", "UPDATE_HARVEST", "DELETE_HARVEST",
    "TRIGGER_SOS",
    "SAVE_EMERGENCY_CONTACTS"
})


class SyncService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.soil_service = SoilHealthService(db)
        self.farm_service = FarmDbService(db)

    def _replace_local_ids(self, data: Any, id_map: dict[str, str]) -> Any:
        if isinstance(data, str):
            return id_map.get(data, data)
        elif isinstance(data, dict):
            return {k: self._replace_local_ids(v, id_map) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_local_ids(x, id_map) for x in data]
        return data

    async def replay_batch(self, user_id: str, payload: SyncBatchRequest, status_callback: Optional[str] = None) -> SyncBatchResponse:
        results: list[SyncOperationResult] = []
        id_map: dict[str, str] = {}

        for operation in payload.operations:
            if operation.operation_type == "TRIGGER_SOS":
                print("[SOS] Replaying queued SOS request")
            # 1. Replace any client temporary ID in the payload with reconciled server ObjectId
            op_payload = self._replace_local_ids(operation.payload, id_map)

            # 2. Check for duplicate receipt to enforce idempotency
            existing = await self.db.sync_receipts.find_one({"client_id": operation.client_id})
            if existing is not None:
                server_id = existing.get("server_id")
                if server_id:
                    id_map[operation.client_id] = server_id
                results.append(
                    SyncOperationResult(
                        operation_type=operation.operation_type,
                        client_id=operation.client_id,
                        server_id=server_id,
                        status="DUPLICATE",
                        detail="Duplicate execution bypassed",
                    )
                )
                continue

            try:
                # 3. Execute replay handler (returns a tuple of detail string and created server_id)
                detail, server_id = await self._execute_operation(user_id, operation.operation_type, op_payload, status_callback=status_callback)

                # 4. If creation created a server_id, record mapping from client_id -> server_id
                if server_id:
                    id_map[operation.client_id] = server_id

                # 5. Insert receipt for idempotency validation
                await self.db.sync_receipts.insert_one(
                    {
                        "client_id": operation.client_id,
                        "user_id": ObjectId(user_id),
                        "operation_type": operation.operation_type,
                        "server_id": server_id,
                        "processed_at": datetime.now(timezone.utc),
                    }
                )

                results.append(
                    SyncOperationResult(
                        operation_type=operation.operation_type,
                        client_id=operation.client_id,
                        server_id=server_id,
                        status="SUCCESS",
                        detail=detail,
                    )
                )
                if operation.operation_type == "TRIGGER_SOS":
                    print("[SOS] Replay succeeded")
            except Exception as exc:
                results.append(
                    SyncOperationResult(
                        operation_type=operation.operation_type,
                        client_id=operation.client_id,
                        server_id=None,
                        status="FAILED",
                        error=str(exc),
                        detail=f"Replay failed: {str(exc)}",
                    )
                )
                if operation.operation_type == "TRIGGER_SOS":
                    print("[SOS] Replay failed, retaining queue item")

        return SyncBatchResponse(processed=len(results), results=results)

    async def _execute_operation(self, user_id: str, operation_type: str, payload: dict, status_callback: Optional[str] = None) -> tuple[str, Optional[str]]:
        if operation_type not in ALLOWED_SYNC_OPERATIONS:
            raise unprocessable_entity(f"Unsupported sync operation: {operation_type}")

        # --- Baseline Operations ---
        if operation_type == "MARK_ALERT_READ":
            alert_id = payload.get("alert_id")
            if not alert_id:
                raise unprocessable_entity("alert_id is required")
            from app.services.alert_escalation_service import AlertEscalationService

            escalation = AlertEscalationService(self.db)
            await escalation.acknowledge_alert(alert_id, user_id)
            return f"alert {alert_id} acknowledged", None

        if operation_type == "DISPATCH_ALERT_ESCALATION":
            from app.services.alert_escalation_service import AlertEscalationService

            escalation = AlertEscalationService(self.db)
            result = await escalation.process_tick()
            return f"escalation tick processed ({result.processed} records)", None

        if operation_type == "SAVE_PUSH_SUBSCRIPTION":
            from app.services.alert_escalation_service import AlertEscalationService

            endpoint = payload.get("endpoint")
            keys = payload.get("keys")
            if not endpoint or not keys:
                raise unprocessable_entity("endpoint and keys are required")
            escalation = AlertEscalationService(self.db)
            await escalation.save_push_subscription(user_id, payload)
            return "push subscription saved", None

        if operation_type == "CREATE_SOIL_RECORD":
            record = SoilRecordCreateSchema(**payload)
            created = await self.soil_service.create_record(user_id, record)
            return f"soil record {created.id} created", created.id

        # --- Farm Replays ---
        if operation_type == "CREATE_FARM":
            record = FarmCreateSchema(**payload)
            created = await self.farm_service.create_farm(user_id, record)
            return f"farm {created.id} created", created.id

        if operation_type == "UPDATE_FARM":
            farm_id = payload.get("farm_id")
            if not farm_id:
                raise unprocessable_entity("farm_id is required")
            clean_payload = {k: v for k, v in payload.items() if k != "farm_id"}
            record = FarmCreateSchema(**clean_payload)
            await self.farm_service.update_farm(user_id, farm_id, record)
            return f"farm {farm_id} updated", farm_id

        if operation_type == "DELETE_FARM":
            farm_id = payload.get("farm_id")
            if not farm_id:
                raise unprocessable_entity("farm_id is required")
            await self.farm_service.delete_farm(user_id, farm_id)
            return f"farm {farm_id} deleted", None

        # --- Plot Replays ---
        if operation_type == "CREATE_PLOT":
            record = PlotCreateSchema(**payload)
            created = await self.farm_service.create_plot(user_id, record)
            return f"plot {created.id} created", created.id

        if operation_type == "UPDATE_PLOT":
            plot_id = payload.get("plot_id")
            if not plot_id:
                raise unprocessable_entity("plot_id is required")
            clean_payload = {k: v for k, v in payload.items() if k != "plot_id"}
            record = PlotCreateSchema(**clean_payload)
            await self.farm_service.update_plot(user_id, plot_id, record)
            return f"plot {plot_id} updated", plot_id

        if operation_type == "DELETE_PLOT":
            plot_id = payload.get("plot_id")
            if not plot_id:
                raise unprocessable_entity("plot_id is required")
            await self.farm_service.delete_plot(user_id, plot_id)
            return f"plot {plot_id} deleted", None

        # --- Crop Cycle Replays ---
        if operation_type == "CREATE_CROP_CYCLE":
            record = CropCycleCreateSchemaNew(**payload)
            created = await self.farm_service.create_crop_cycle(user_id, record)
            return f"crop cycle {created.id} created", created.id

        if operation_type == "UPDATE_CROP_CYCLE":
            cycle_id = payload.get("crop_cycle_id")
            if not cycle_id:
                raise unprocessable_entity("crop_cycle_id is required")
            clean_payload = {k: v for k, v in payload.items() if k != "crop_cycle_id"}
            record = CropCycleCreateSchemaNew(**clean_payload)
            await self.farm_service.update_crop_cycle(user_id, cycle_id, record)
            return f"crop cycle {cycle_id} updated", cycle_id

        if operation_type == "DELETE_CROP_CYCLE":
            cycle_id = payload.get("crop_cycle_id")
            if not cycle_id:
                raise unprocessable_entity("crop_cycle_id is required")
            await self.farm_service.delete_crop_cycle(user_id, cycle_id)
            return f"crop cycle {cycle_id} deleted", None

        # --- Expense Replays ---
        if operation_type == "CREATE_EXPENSE":
            record = ExpenseCreateSchema(**payload)
            created = await self.farm_service.create_expense(user_id, record)
            return f"expense {created.id} created", created.id

        if operation_type == "UPDATE_EXPENSE":
            expense_id = payload.get("expense_id")
            if not expense_id:
                raise unprocessable_entity("expense_id is required")
            clean_payload = {k: v for k, v in payload.items() if k != "expense_id"}
            record = ExpenseCreateSchema(**clean_payload)
            await self.farm_service.update_expense(user_id, expense_id, record)
            return f"expense {expense_id} updated", expense_id

        if operation_type == "DELETE_EXPENSE":
            expense_id = payload.get("expense_id")
            if not expense_id:
                raise unprocessable_entity("expense_id is required")
            await self.farm_service.delete_expense(user_id, expense_id)
            return f"expense {expense_id} deleted", None

        # --- Harvest Replays ---
        if operation_type == "CREATE_HARVEST":
            record = HarvestCreateSchema(**payload)
            created = await self.farm_service.create_harvest(user_id, record)
            return f"harvest {created.id} created", created.id

        if operation_type == "UPDATE_HARVEST":
            harvest_id = payload.get("harvest_id")
            if not harvest_id:
                raise unprocessable_entity("harvest_id is required")
            clean_payload = {k: v for k, v in payload.items() if k != "harvest_id"}
            record = HarvestCreateSchema(**clean_payload)
            await self.farm_service.update_harvest(user_id, harvest_id, record)
            return f"harvest {harvest_id} updated", harvest_id

        if operation_type == "DELETE_HARVEST":
            harvest_id = payload.get("harvest_id")
            if not harvest_id:
                raise unprocessable_entity("harvest_id is required")
            await self.farm_service.delete_harvest(user_id, harvest_id)
            return f"harvest {harvest_id} deleted", None

        if operation_type == "TRIGGER_SOS":
            from app.services.sos_service import SosService
            from app.models.day7_schemas import SosTriggerRequest
            sos_payload = SosTriggerRequest(**payload)
            sos_service = SosService(self.db)
            result = await sos_service.trigger(user_id, sos_payload, status_callback=status_callback)
            return f"SOS action {result.action_id} triggered", result.action_id

        if operation_type == "SAVE_EMERGENCY_CONTACTS":
            from app.services.sos_service import SosService
            sos_service = SosService(self.db)
            await sos_service.save_contacts(user_id, payload)
            return "emergency contacts updated", None

        raise unprocessable_entity(f"Unhandled operation: {operation_type}")
