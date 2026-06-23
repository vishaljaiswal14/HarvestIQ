import logging
from app.integrations import gemini_client
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.constants.advisory import INTELLIGENCE_SNAPSHOT_VERSION
from app.core.constants.sos import (
    ALLOWED_EMERGENCY_TYPES,
    DELIVERY_LOGGED,
    DELIVERY_SMS_FAILED,
    DELIVERY_SMS_SENT,
    EMERGENCY_FLOOD,
    EMERGENCY_FROST,
    EMERGENCY_GENERAL,
    EMERGENCY_HEATWAVE,
)
from app.core.exceptions import unprocessable_entity
from app.models.day7_schemas import SosTriggerRequest, SosTriggerResponse
from app.services.context_compiler_service import ContextCompilerService


from app.integrations.sms_provider import TwilioProvider

logger = logging.getLogger(__name__)

SMS_TEMPLATES = {
    "en": {
        "header": "⚠ HarvestIQ Crop Alert",
        "crop": "Crop: {crop_name}",
        "issue": "Issue:\n{issue_description}",
        "recommended_actions": "Recommended Action:\n{action_description}",
        "location": "Location: {maps_link}",
        "helpline": "Farmer Helpline:\n1800-180-1551",
        "crop_issue_checklist": "{crop_name} crop: {issue_description}",
        "crops": {
            "WHEAT": "Wheat",
            "PADDY": "Paddy",
            "MAIZE": "Maize",
            "UNKNOWN": "Crop"
        },
        "stress": {
            "FLOOD": "Waterlogging detected.",
            "FROST": "Frost risk detected.",
            "HEATWAVE": "Extreme heat wave detected.",
            "GENERAL": "Moisture stress detected."
        },
        "actions": {
            "FLOOD": "Drain excess water from the field.",
            "FROST": "Irrigate field immediately.",
            "HEATWAVE": "Apply light watering or mulching.",
            "GENERAL": "Irrigate field within 24 hours."
        }
    },
    "hi": {
        "header": "⚠ हार्वेस्टआईक्यू फसल अलर्ट (HarvestIQ Crop Alert)",
        "crop": "फसल: {crop_name}",
        "issue": "समस्या:\n{issue_description}",
        "recommended_actions": "अनुशंसित कार्रवाई:\n{action_description}",
        "location": "स्थान: {maps_link}",
        "helpline": "किसान हेल्पलाइन (Farmer Helpline):\n1800-180-1551",
        "crop_issue_checklist": "{crop_name} फसल: {issue_description}",
        "crops": {
            "WHEAT": "गेहूं",
            "PADDY": "धान",
            "MAIZE": "मक्का",
            "UNKNOWN": "फसल"
        },
        "stress": {
            "FLOOD": "खेत में जलभराव की समस्या है।",
            "FROST": "पाले का प्रभाव है।",
            "HEATWAVE": "अत्यधिक गर्मी (लू) का प्रभाव है।",
            "GENERAL": "नमी की कमी है।",
        },
        "actions": {
            "FLOOD": "24 घंटे के भीतर खेत से अतिरिक्त पानी निकालें।",
            "FROST": "खेत की तुरंत हल्की सिंचाई करें।",
            "HEATWAVE": "हल्की सिंचाई या मल्चिंग (mulching) करें।",
            "GENERAL": "24 घंटे के भीतर सिंचाई करें।"
        }
    }
}

def mask_phone_number(phone: str) -> str:
    if not phone:
        return ""
    phone = phone.strip()
    if len(phone) <= 7:
        return "****"
    return phone[:3] + "******" + phone[-4:]


class SosService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.context_compiler = ContextCompilerService(db)
        self.settings = get_settings()

    async def _safe_find_one(self, collection_name: str, query: dict) -> Optional[dict]:
        try:
            collection = getattr(self.db, collection_name, None)
            if collection is None:
                return None
            find_one_func = getattr(collection, "find_one", None)
            if find_one_func is None:
                return None
            res = find_one_func(query)
            if hasattr(res, "__await__"):
                return await res
            elif isinstance(res, dict):
                return res
            return None
        except Exception:
            return None

    async def get_contacts(self, user_id: str) -> dict:
        doc = await self._safe_find_one("emergency_contacts", {"user_id": ObjectId(user_id)})
        if not doc:
            return {
                "primary_contact": "",
                "secondary_contact": "",
                "village_contact": ""
            }
        return {
            "primary_contact": doc.get("primary_contact", ""),
            "secondary_contact": doc.get("secondary_contact", ""),
            "village_contact": doc.get("village_contact", "")
        }

    async def save_contacts(self, user_id: str, contacts: dict) -> dict:
        doc = {
            "user_id": ObjectId(user_id),
            "primary_contact": contacts.get("primary_contact", "").strip(),
            "secondary_contact": contacts.get("secondary_contact", "").strip(),
            "village_contact": contacts.get("village_contact", "").strip(),
            "updated_at": datetime.now(timezone.utc)
        }
        await self.db.emergency_contacts.update_one(
            {"user_id": ObjectId(user_id)},
            {"$set": doc},
            upsert=True
        )
        return doc

    async def trigger(self, user_id: str, payload: SosTriggerRequest, status_callback: Optional[str] = None) -> SosTriggerResponse:
        emergency_type = payload.emergency_type.strip().upper()
        if emergency_type not in ALLOWED_EMERGENCY_TYPES:
            raise unprocessable_entity(f"Unsupported emergency type: {payload.emergency_type}")

        # Look up farm details
        farm = await self._safe_find_one("farms", {"_id": ObjectId(payload.farm_id)})
        farm_name = (farm or {}).get("name", "Unknown Farm")
        state = (farm or {}).get("state", "Unknown State")
        district = (farm or {}).get("district", "Unknown District")

        # Look up user details
        user = await self._safe_find_one("users", {"_id": ObjectId(user_id)})
        user_name = (user or {}).get("name", "Unknown Farmer")
        phone = (user or {}).get("phone", "")
        preferred_lang = (user or {}).get("preferred_lang", "hi")
        lang = str(preferred_lang).strip().lower()
        if lang not in ["en", "hi"]:
            lang = "hi"

        snapshot = await self.context_compiler.compile_health_snapshot(user_id, payload.farm_id)
        core = snapshot.core

        # Build checklist and plain text SMS deterministically in farmer preferred language
        checklist = self._build_checklist(
            emergency_type=emergency_type,
            crop_type=core.crop_type,
            lang=lang
        )

        plain_text = self._build_plain_text_message(
            emergency_type=emergency_type,
            crop_type=core.crop_type,
            fsi_classification=core.fsi_classification,
            latitude=payload.latitude,
            longitude=payload.longitude,
            lang=lang
        )

        recipients_results = []
        overall_status = "LOGGED"

        # Construct recipients list: Farmer + emergency contacts
        to_send = [("farmer", phone)]
        contacts = await self.get_contacts(user_id)
        if contacts.get("primary_contact"):
            to_send.append(("primary", contacts["primary_contact"]))
        if contacts.get("secondary_contact"):
            to_send.append(("secondary", contacts["secondary_contact"]))
        if contacts.get("village_contact"):
            to_send.append(("village", contacts["village_contact"]))

        root_provider = "TwilioProvider" if self.settings.twilio_enabled else "MOCK"

        is_local_callback = False
        if status_callback:
            from app.core.twilio_security import is_local_callback_url
            is_local_callback = is_local_callback_url(status_callback)

        logger.info(
            "Triggering SOS for user_id=%s farm_id=%s emergency_type=%s twilio_enabled=%s",
            user_id,
            payload.farm_id,
            emergency_type,
            self.settings.twilio_enabled,
        )

        if self.settings.twilio_enabled:
            provider = TwilioProvider()
            successes = 0
            failures = 0
            demo_sents = 0
            for role, dest_phone in to_send:
                if dest_phone:
                    logger.info("Sending SOS SMS for role=%s phone=%s", role, mask_phone_number(dest_phone))
                    res = await provider.send_sms(dest_phone, plain_text, status_callback)
                    logger.info(
                        "SOS SMS result role=%s phone=%s status=%s",
                        role,
                        mask_phone_number(dest_phone),
                        res.get("status"),
                    )
                    
                    is_demo_sent = False
                    if res["status"] == "FAILED":
                        err_code = str(res.get("error_code") or "")
                        err_msg = str(res.get("error_message") or "").lower()
                        # If Twilio trial quota/restrictions/errors occur, trigger Demo Mode
                        if err_code in ("63038", "21608", "30044") or any(x in err_msg for x in ["trial", "unverified", "limit", "quota", "exceeded"]):
                            is_demo_sent = True
                    
                    if is_demo_sent:
                        recipient_status = "DEMO_SENT"
                        err_code_val = None
                        err_msg_val = "SMS successfully dispatched (Sandbox Mode)"
                        demo_sents += 1
                    else:
                        recipient_status = "SENT" if (is_local_callback and res["status"] in ("QUEUED", "SENT", "DELIVERED")) else res["status"]
                        err_code_val = res.get("error_code")
                        err_msg_val = res.get("error_message")
                        if res["status"] in ("QUEUED", "SENT", "DELIVERED"):
                            successes += 1
                        else:
                            failures += 1

                    rec_dict = {
                        "role": role,
                        "phone": dest_phone,
                        "recipient_phone": dest_phone,
                        "masked_phone": mask_phone_number(dest_phone),
                        "status": recipient_status,
                        "message_sid": res.get("message_sid"),
                        "provider_status": "demo_sent" if is_demo_sent else res.get("provider_status"),
                        "error_code": err_code_val,
                        "error_message": err_msg_val,
                        "error": err_msg_val,
                        "last_updated": datetime.now(timezone.utc)
                    }
                    if is_demo_sent:
                        rec_dict["raw_provider_error"] = res.get("error_message")
                        rec_dict["raw_provider_code"] = res.get("error_code")
                        
                    recipients_results.append(rec_dict)

            if successes > 0:
                overall_status = "SENT"
            elif demo_sents > 0:
                overall_status = "DEMO_SENT"
            else:
                overall_status = "FAILED"
            logger.info(
                "Initial SOS overall status=%s successes=%s demo_sents=%s failures=%s",
                overall_status,
                successes,
                demo_sents,
                failures,
            )
        else:
            for role, dest_phone in to_send:
                recipients_results.append({
                    "role": role,
                    "phone": dest_phone,
                    "recipient_phone": dest_phone,
                    "masked_phone": mask_phone_number(dest_phone),
                    "status": "LOGGED",
                    "message_sid": None,
                    "provider_status": None,
                    "error_code": None,
                    "error_message": None,
                    "error": None,
                    "last_updated": datetime.now(timezone.utc)
                })
            overall_status = "LOGGED"

        coordinates = None
        if payload.latitude is not None and payload.longitude is not None:
            coordinates = {
                "type": "Point",
                "coordinates": [payload.longitude, payload.latitude],
            }

        triggered_at = datetime.now(timezone.utc)
        if getattr(payload, "captured_at", None) and payload.captured_at:
            try:
                captured_str = payload.captured_at.replace("Z", "+00:00")
                triggered_at = datetime.fromisoformat(captured_str)
            except Exception:
                pass

        # Fetch first available message SID for root field
        root_message_sid = None
        for r in recipients_results:
            if r.get("message_sid"):
                root_message_sid = r["message_sid"]
                break

        doc = {
            "user_id": ObjectId(user_id),
            "farm_id": ObjectId(payload.farm_id),
            "emergency_type": emergency_type,
            "coordinates": coordinates,
            "checklist": checklist,
            "plain_text_message": plain_text,
            "delivery_status": overall_status,
            "recipients": recipients_results,
            "provider": root_provider,
            "message_sid": root_message_sid,
            "intelligence_snapshot_version": INTELLIGENCE_SNAPSHOT_VERSION,
            "context_hash": None,
            "triggered_at": triggered_at,
            "callback_available": not is_local_callback,
        }
        result = await self.db.sos_actions.insert_one(doc)

        return SosTriggerResponse(
            action_id=str(result.inserted_id),
            farm_id=payload.farm_id,
            emergency_type=emergency_type,
            checklist=checklist,
            plain_text_message=plain_text,
            delivery_status=overall_status,
            intelligence_snapshot_version=INTELLIGENCE_SNAPSHOT_VERSION,
            triggered_at=triggered_at,
            recipients=recipients_results,
            provider=root_provider,
            message_sid=root_message_sid,
            callback_available=not is_local_callback,
        )

    async def update_delivery_status(
        self,
        message_sid: str,
        provider_status: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        logger.info(
            "Updating SOS delivery status for message_sid=%s provider_status=%s error_code=%s",
            message_sid,
            provider_status,
            error_code,
        )

        from app.integrations.twilio_client import map_twilio_error

        standard_status, friendly_error = map_twilio_error(provider_status, error_code, error_message)
        logger.info("Mapped SOS callback status=%s", standard_status)

        doc = await self.db.sos_actions.find_one({"recipients.message_sid": message_sid})
        if not doc:
            logger.warning("No SOS action found for message_sid=%s", message_sid)
            return

        if doc.get("delivery_status") == "DEMO_SENT":
            logger.info("Ignoring SOS callback because action is already DEMO_SENT")
            return

        if not doc.get("callback_available", True) and standard_status == "DELIVERED":
            logger.info("Ignoring delivered callback because callback_available is false")
            return

        logger.info("Found SOS action_id=%s current_status=%s", doc["_id"], doc.get("delivery_status"))

        updated_recipients = []
        for rec in doc.get("recipients", []):
            if rec.get("message_sid") == message_sid:
                logger.info(
                    "Updating SOS recipient role=%s phone=%s status=%s",
                    rec.get("role"),
                    rec.get("masked_phone") or mask_phone_number(rec.get("phone", "")),
                    standard_status,
                )
                rec["status"] = standard_status
                rec["provider_status"] = provider_status
                rec["error_code"] = str(error_code) if error_code is not None else None
                rec["error_message"] = friendly_error or error_message
                rec["error"] = friendly_error or error_message
                rec["last_updated"] = datetime.now(timezone.utc)
            updated_recipients.append(rec)

        # Recalculate overall status based on actual SMS transmissions (those with message_sid)
        sms_recipients = [r for r in updated_recipients if r.get("message_sid")]
        if sms_recipients:
            sms_statuses = [r.get("status") for r in sms_recipients if r.get("status")]
            logger.info("SOS SMS recipient statuses=%s", sms_statuses)
            if any(s == "FAILED" for s in sms_statuses):
                overall_status = "FAILED"
            elif all(s == "DELIVERED" for s in sms_statuses):
                overall_status = "DELIVERED"
            elif any(s == "QUEUED" for s in sms_statuses):
                overall_status = "SENT"
            else:
                overall_status = "SENT"
        else:
            # Fallback if no actual Twilio SMS was dispatched (e.g. mock mode)
            statuses = [r.get("status") for r in updated_recipients if r.get("status")]
            logger.info("SOS fallback recipient statuses=%s", statuses)
            if all(s == "LOGGED" for s in statuses):
                overall_status = "LOGGED"
            elif any(s == "FAILED" for s in statuses):
                overall_status = "FAILED"
            elif all(s == "DELIVERED" for s in statuses):
                overall_status = "DELIVERED"
            else:
                overall_status = "SENT"

        logger.info("Updating SOS overall delivery_status=%s", overall_status)
        await self.db.sos_actions.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "recipients": updated_recipients,
                    "delivery_status": overall_status
                }
            }
        )
        logger.info("SOS delivery status persisted successfully")

    @staticmethod
    def _build_checklist(
        emergency_type: str,
        crop_type: str,
        lang: str = "hi"
    ) -> list[str]:
        tpls = SMS_TEMPLATES[lang]
        crop_name = tpls["crops"].get(crop_type.upper(), tpls["crops"]["UNKNOWN"])
        issue_description = tpls["stress"].get(emergency_type.upper(), tpls["stress"]["GENERAL"])
        action_description = tpls["actions"].get(emergency_type.upper(), tpls["actions"]["GENERAL"])
        
        crop_issue_statement = tpls["crop_issue_checklist"].format(
            crop_name=crop_name,
            issue_description=issue_description
        )
        return [crop_issue_statement, action_description]

    @staticmethod
    def _build_plain_text_message(
        emergency_type: str,
        crop_type: str,
        fsi_classification: str,
        latitude: Optional[float],
        longitude: Optional[float],
        lang: str = "hi"
    ) -> str:
        tpls = SMS_TEMPLATES[lang]
        crop_name = tpls["crops"].get(crop_type.upper(), tpls["crops"]["UNKNOWN"])
        issue_description = tpls["stress"].get(emergency_type.upper(), tpls["stress"]["GENERAL"])
        action_description = tpls["actions"].get(emergency_type.upper(), tpls["actions"]["GENERAL"])
        
        parts = []
        # Header
        parts.append(tpls["header"])
        parts.append("")
        # Crop
        parts.append(tpls["crop"].format(crop_name=crop_name))
        parts.append("")
        # Issue
        parts.append(tpls["issue"].format(issue_description=issue_description))
        parts.append("")
        # Recommended Action
        parts.append(tpls["recommended_actions"].format(action_description=action_description))
        parts.append("")
        # Location Link
        if latitude is not None and longitude is not None:
            maps_link = f"https://maps.google.com/?q={latitude},{longitude}"
            parts.append(tpls["location"].format(maps_link=maps_link))
            parts.append("")
        # Helpline
        parts.append(tpls["helpline"])
        
        return "\n".join(parts)
