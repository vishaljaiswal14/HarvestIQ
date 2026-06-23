import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.constants.crop_stages import CropCycleStatus
from app.core.constants.disease import ALLOWED_IMAGE_TYPES, MAX_IMAGE_BYTES
from app.core.constants.crop_types import normalize_crop_type
from app.core.exceptions import bad_gateway, unprocessable_entity
from app.integrations.gemini_client import OpenRouterClient
from app.models.day4_schemas import DiseaseDetectResponse
from app.services.deterministic_engine import confirm_disease_detection, normalize_disease_tag
from app.services.explainability_service import build_disease_explanation
from app.services.farm_access_service import get_owned_farm
from app.services.image_quality import analyze_image_quality


class DiseaseDetectionService:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        gemini_client: Optional[OpenRouterClient] = None,
    ) -> None:
        self.db = db
        self.gemini_client = gemini_client or OpenRouterClient()
        self.settings = get_settings()
        self.allowed_regions = self._load_allowed_regions()

    async def detect(
        self,
        user_id: str,
        farm_id: str,
        image_bytes: bytes,
        content_type: str,
        lang: str = "en",
    ) -> DiseaseDetectResponse:
        if not image_bytes:
            raise unprocessable_entity("Image file is required")
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise unprocessable_entity("Image file exceeds maximum allowed size")
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise unprocessable_entity("Unsupported image type")

        farm = await get_owned_farm(self.db, farm_id, user_id)
        crop_type, cycle_status = await self._resolve_crop_type(farm_id)
        state = str(farm.get("state", "ALL"))

        # Stage 2: Objective Image Quality Check
        quality_res = analyze_image_quality(image_bytes)
        if not quality_res["valid"]:
            print("="*60, flush=True)
            print("CROP DOCTOR PIPELINE TRACE LOG:", flush=True)
            print(f"Farm State: {state}", flush=True)
            print(f"DOWNGRADE TRACE: Downgraded to INVALID_IMAGE because Image Quality analysis failed: {quality_res['message']}", flush=True)
            print("="*60, flush=True)
            from app.models.engine_schemas import ExplanationPayload
            return DiseaseDetectResponse(
                valid=False,
                reason=quality_res["reason"],
                message=quality_res["message"],
                farm_id=farm_id,
                crop_type=crop_type,
                disease="UNKNOWN",
                confidence=0.0,
                deterministic_status="INVALID_IMAGE",
                explanation=ExplanationPayload(
                    summary=quality_res["message"],
                    inputs={},
                    primary_factor="NONE",
                ),
                cycle_status=cycle_status,
            )

        # Stage 1: Content validation check (via LLM/Vision)
        try:
            val_res = await self.gemini_client.validate_image(
                image_bytes=image_bytes,
                mime_type=content_type
            )
        except Exception as exc:
            print("VALIDATION_EXCEPTION =", repr(exc))
            raise bad_gateway(f"Image validation failed: {exc}") from exc

        if not val_res["valid"]:
            print("="*60, flush=True)
            print("CROP DOCTOR PIPELINE TRACE LOG:", flush=True)
            print(f"Farm State: {state}", flush=True)
            print(f"DOWNGRADE TRACE: Downgraded to INVALID_IMAGE because Content Validation failed (Image Type: {val_res['image_type']}, Message: {val_res['message']})", flush=True)
            print("="*60, flush=True)
            from app.models.engine_schemas import ExplanationPayload
            return DiseaseDetectResponse(
                valid=False,
                image_type=val_res["image_type"],
                validation_confidence=val_res["validation_confidence"],
                reason=val_res["reason"],
                message=val_res["message"],
                farm_id=farm_id,
                crop_type=crop_type,
                disease="UNKNOWN",
                confidence=0.0,
                deterministic_status="INVALID_IMAGE",
                explanation=ExplanationPayload(
                    summary=val_res["message"],
                    inputs={},
                    primary_factor="NONE",
                ),
                cycle_status=cycle_status,
            )

        # Stage 1b: Crop Identification Stage
        try:
            crop_id_res = await self.gemini_client.identify_crop(
                image_bytes=image_bytes,
                mime_type=content_type,
                registered_crop=crop_type
            )
        except Exception as exc:
            print("CROP_ID_EXCEPTION =", repr(exc))
            raise bad_gateway(f"Crop identification failed: {exc}") from exc

        # Crop Consistency Check & Gating
        identified_crop = crop_id_res.get("crop_type", "UNKNOWN").strip().upper()
        crop_conf = float(crop_id_res.get("crop_confidence", 0.0))

        crop_mismatch_triggered = False
        mismatch_reason = "No mismatch"
        low_confidence_warning = False

        if crop_conf < 0.70 or identified_crop == "UNKNOWN":
            crop_mismatch_triggered = False
            mismatch_reason = f"Crop confidence {crop_conf:.2f} is below 0.70 threshold or identified crop is UNKNOWN"
            
            print("="*60, flush=True)
            print("CROP DOCTOR PIPELINE TRACE LOG:", flush=True)
            print(f"crop_identified: {identified_crop}", flush=True)
            print(f"crop_confidence: {crop_conf:.2f}", flush=True)
            print(f"crop_mismatch_triggered: {crop_mismatch_triggered}", flush=True)
            print(f"mismatch_reason: {mismatch_reason}", flush=True)
            print(f"Farm State: {state}", flush=True)
            print("DOWNGRADE TRACE: Downgraded to UNKNOWN because Crop Identification confidence is less than 70% or crop type is UNKNOWN.", flush=True)
            print("="*60, flush=True)
            
            from app.models.engine_schemas import ExplanationPayload
            return DiseaseDetectResponse(
                valid=True,
                image_type=identified_crop,
                validation_confidence=crop_conf,
                farm_id=farm_id,
                crop_type=crop_type,
                disease="UNKNOWN",
                confidence=None,
                deterministic_status="UNKNOWN",
                explanation=ExplanationPayload(
                    summary="Unable to confidently identify a disease. Please upload a clearer close-up image of the affected leaf.",
                    inputs={"crop_id_confidence": crop_conf},
                    primary_factor="NONE",
                ),
                cycle_status=cycle_status,
                disease_name="Unknown Anomaly",
                severity="None",
                what_it_means="Unable to confidently identify a crop or disease.",
                immediate_actions=["Please upload a clearer close-up image of the affected leaf."],
                recommended_treatment=None,
                prevention_advice=[],
                risk_level="Low",
                message="Unable to confidently identify a disease. Please upload a clearer close-up image of the affected leaf."
            )

        elif crop_conf >= 0.90:
            if identified_crop != crop_type:
                crop_mismatch_triggered = True
                mismatch_reason = f"CROP_MISMATCH: identified_crop={identified_crop} registered_crop={crop_type}"
                
                print("="*60, flush=True)
                print("CROP DOCTOR PIPELINE TRACE LOG:", flush=True)
                print(f"crop_identified: {identified_crop}", flush=True)
                print(f"crop_confidence: {crop_conf:.2f}", flush=True)
                print(f"crop_mismatch_triggered: {crop_mismatch_triggered}", flush=True)
                print(f"mismatch_reason: {mismatch_reason}", flush=True)
                print("DOWNGRADE TRACE: Downgraded to UNKNOWN because of CROP_MISMATCH.", flush=True)
                print("="*60, flush=True)
                
                from app.models.engine_schemas import ExplanationPayload
                return DiseaseDetectResponse(
                    valid=True,
                    image_type=identified_crop,
                    validation_confidence=crop_conf,
                    farm_id=farm_id,
                    crop_type=crop_type,
                    disease="UNKNOWN",
                    confidence=None,
                    deterministic_status="UNKNOWN",
                    explanation=ExplanationPayload(
                        summary="Crop mismatch detected. Unable to confidently identify a disease. Please upload a clearer close-up image of the affected leaf.",
                        inputs={"crop_id_confidence": crop_conf},
                        primary_factor="NONE",
                    ),
                    cycle_status=cycle_status,
                    disease_name="Unknown Anomaly",
                    severity="None",
                    what_it_means="Crop mismatch detected between visual scan and registered farm crop.",
                    immediate_actions=["Please upload a clearer close-up image of the affected leaf."],
                    recommended_treatment=None,
                    prevention_advice=[],
                    risk_level="Low",
                    message="Unable to confidently identify a disease. Please upload a clearer close-up image of the affected leaf."
                )
            else:
                mismatch_reason = f"Identified crop matches registered crop {crop_type}"
        else:
            # 0.70 <= crop_conf < 0.90
            low_confidence_warning = True
            if identified_crop != crop_type:
                mismatch_reason = f"Crop mismatch detected (identified={identified_crop}, registered={crop_type}), but ignored because crop confidence {crop_conf:.2f} is below 0.90"
            else:
                mismatch_reason = f"Identified crop matches registered crop {crop_type} with crop confidence {crop_conf:.2f}"

        # If we continue, print the pre-detection trace logs too
        print("="*60, flush=True)
        print("CROP DOCTOR PIPELINE TRACE LOG:", flush=True)
        print(f"crop_identified: {identified_crop}", flush=True)
        print(f"crop_confidence: {crop_conf:.2f}", flush=True)
        print(f"crop_mismatch_triggered: {crop_mismatch_triggered}", flush=True)
        print(f"mismatch_reason: {mismatch_reason}", flush=True)
        print("="*60, flush=True)

        # Resolve allowed regional rules early for prompt dynamic enum constraint
        crop_key = crop_type.strip().upper()
        state_key = state.strip().upper().replace(" ", "_")
        crop_rules = self.allowed_regions.get(crop_key, {})
        allowed = set(crop_rules.get(state_key, [])) | set(crop_rules.get("ALL", []))
        allowed_list = list(allowed)

        # Stage 3: Disease Detection (Only execute when valid is true)
        try:
            vision_result = await self.gemini_client.detect_disease(
                image_bytes=image_bytes,
                mime_type=content_type,
                crop_type=crop_type,
                state=state,
                allowed_diseases=allowed_list,
            )
        except Exception as exc:
            print("DETECT_DISEASE_EXCEPTION =", repr(exc))
            raise bad_gateway(f"Disease detection failed: {exc}") from exc

        detected_disease = str(vision_result["disease"]).strip().upper()
        confidence = vision_result.get("confidence")
        raw_response = vision_result.get("raw_response", "MOCKED_OR_UNAVAILABLE")

        # Post-validation checks
        valid_tags = allowed_list + ["HEALTHY", "UNKNOWN"]
        norm_detected = normalize_disease_tag(detected_disease)
        if norm_detected not in valid_tags and detected_disease not in valid_tags:
            print(f"POST_VALIDATION_FAILURE: disease_tag='{detected_disease}' (normalized='{norm_detected}') not in {valid_tags}. Overwriting to UNKNOWN and setting confidence to None.", flush=True)
            detected_disease = "UNKNOWN"
            confidence = None

        disease_tag, deterministic_status = confirm_disease_detection(
            crop_type=crop_type,
            state=state,
            detected_disease=detected_disease,
            confidence=confidence,
            confidence_threshold=self.settings.disease_confidence_threshold,
            allowed_by_crop=self.allowed_regions,
        )

        if deterministic_status in {"HEALTHY", "UNKNOWN", "INVALID_IMAGE"}:
            confidence = None

        # Tracing Downgrades
        is_allowed = False
        norm_detected = normalize_disease_tag(detected_disease)
        if norm_detected in allowed:
            is_allowed = True
        else:
            for candidate in allowed:
                if candidate in norm_detected or norm_detected in candidate:
                    is_allowed = True
                    break

        print("="*60, flush=True)
        print("CROP DOCTOR PIPELINE TRACE LOG:", flush=True)
        print(f"Raw Vision Model Response: {raw_response}", flush=True)
        print(f"Disease Tag returned by Model: {detected_disease} (Normalized: {norm_detected})", flush=True)
        print(f"Disease Confidence: {confidence}", flush=True)
        print(f"Crop Identified (Model): {crop_id_res['crop_type']}", flush=True)
        print(f"Crop Confidence: {crop_id_res['crop_confidence']}", flush=True)
        print(f"Farm State: {state}", flush=True)
        print(f"Allowed Diseases for {crop_type} in {state}: {list(allowed)}", flush=True)
        print(f"Deterministic Validation Result (is_allowed): {is_allowed}", flush=True)
        print(f"Final Status: {deterministic_status}", flush=True)

        if not is_allowed:
            print(f"DOWNGRADE TRACE: Downgraded to UNKNOWN because the normalized disease '{norm_detected}' is not allowed for crop '{crop_type}' in state '{state}' (regional allowlist mismatch).", flush=True)
        elif confidence is None:
            print(f"DOWNGRADE TRACE: Downgraded to UNKNOWN because disease confidence is None (invalid/unrecognized disease tag).", flush=True)
        elif confidence < 0.50:
            print(f"DOWNGRADE TRACE: Downgraded to UNKNOWN because disease confidence {confidence} is less than 50%.", flush=True)
        elif norm_detected == "UNKNOWN":
            print(f"DOWNGRADE TRACE: Downgraded to UNKNOWN because the model returned 'UNKNOWN' tag.", flush=True)
        elif deterministic_status == "LOW_CONFIDENCE":
            print(f"DOWNGRADE TRACE: Downgraded to LOW_CONFIDENCE because disease confidence {confidence} is in 50-69% range.", flush=True)
        print("="*60, flush=True)

        from app.core.constants.disease_guidance import get_disease_guidance
        guidance = get_disease_guidance(disease_tag, lang)

        # Enforce treatment suppression (Requirement 7 & 8)
        if deterministic_status not in {"CONFIRMED_DISEASE", "POSSIBLE_DISEASE"}:
            guidance["recommended_treatment"] = None

        now = datetime.now(timezone.utc)
        location = farm["location"]
        inputs = {
            "crop_type": crop_type,
            "state": state,
            "district": farm.get("district"),
            "detected_disease": normalize_disease_tag(detected_disease),
            "confidence": confidence,
            "deterministic_status": deterministic_status,
            "confidence_threshold": self.settings.disease_confidence_threshold,
        }
        explanation = build_disease_explanation(
            disease=disease_tag,
            confidence=confidence,
            deterministic_status=deterministic_status,
            primary_factor="DISEASE",
            inputs=inputs,
        )

        if deterministic_status == "UNKNOWN":
            explanation["summary"] = "Unable to confidently identify a disease. Please upload a clearer close-up image of the affected leaf."

        warning_msg = None
        if low_confidence_warning:
            warning_msg = "Crop identification confidence is low."
            explanation["summary"] = "Crop identification confidence is low. " + explanation["summary"]

        doc = {
            "user_id": ObjectId(user_id),
            "farm_id": ObjectId(farm_id),
            "crop_type": crop_type,
            "detected_disease": disease_tag,
            "confidence": confidence,
            "deterministic_status": deterministic_status,
            "location": location,
            "explanation": explanation,
            "created_at": now,
            # Actionable guidance
            "disease_name": guidance["disease_name"],
            "severity": guidance["severity"],
            "what_it_means": guidance["what_it_means"],
            "immediate_actions": guidance["immediate_actions"],
            "recommended_treatment": guidance["recommended_treatment"],
            "prevention_advice": guidance["prevention_advice"],
            "risk_level": guidance["risk_level"],
            # Explainability
            "crop_confidence": crop_conf,
            "validation_result": val_res.get("valid", True),
            "region_validation_result": is_allowed,
        }
        result = await self.db.disease_reports.insert_one(doc)
        report_id = str(result.inserted_id)

        upload_dir = Path(self.settings.disease_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        extension = "jpg" if "jpeg" in content_type or content_type == "image/jpg" else content_type.split("/")[-1]
        image_path = upload_dir / f"{report_id}.{extension}"
        image_path.write_bytes(image_bytes)
        await self.db.disease_reports.update_one(
            {"_id": result.inserted_id},
            {"$set": {
                "image_storage_key": str(image_path),
                "image_url": f"/api/v1/disease/history/{report_id}/image",
                "image_path": str(image_path),
            }},
        )

        return DiseaseDetectResponse(
            valid=True,
            image_type=val_res["image_type"],
            validation_confidence=val_res["validation_confidence"],
            report_id=report_id,
            farm_id=farm_id,
            crop_type=crop_type,
            disease=disease_tag,
            confidence=confidence,
            deterministic_status=deterministic_status,
            explanation=explanation,
            cycle_status=cycle_status,
            disease_name=guidance["disease_name"],
            severity=guidance["severity"],
            what_it_means=guidance["what_it_means"],
            immediate_actions=guidance["immediate_actions"],
            recommended_treatment=guidance["recommended_treatment"],
            prevention_advice=guidance["prevention_advice"],
            risk_level=guidance["risk_level"],
            message=warning_msg if deterministic_status != "UNKNOWN" else "Unable to confidently identify a disease. Please upload a clearer close-up image of the affected leaf.",
            crop_confidence=crop_conf,
            validation_result=val_res.get("valid", True),
            region_validation_result=is_allowed,
            created_at=now,
            image_url=f"/api/v1/disease/history/{report_id}/image",
            image_path=str(image_path),
        )

    async def _resolve_crop_type(self, farm_id: str) -> tuple[str, str]:
        from app.services.farm_access_service import get_latest_relevant_crop_cycle
        cycle, cycle_status = await get_latest_relevant_crop_cycle(self.db, farm_id)
        return normalize_crop_type(cycle["crop_type"]), cycle_status

    @staticmethod
    def _load_allowed_regions() -> dict:
        path = Path(__file__).resolve().parents[2] / "data" / "disease_allowed_regions.json"
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
