from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.integrations.gemini_client import OpenRouterClient
from app.services.disease_detection_service import DiseaseDetectionService

FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())
CYCLE_ID = ObjectId()


@pytest.fixture(autouse=True)
def mock_validation_pipeline(monkeypatch):
    monkeypatch.setattr(
        "app.services.disease_detection_service.analyze_image_quality",
        lambda img_bytes: {
            "valid": True,
            "metrics": {
                "resolution": "300x300",
                "blur_score": 10.0,
                "brightness_score": 128.0,
                "contrast_score": 50.0,
            },
        },
    )
    monkeypatch.setattr(
        OpenRouterClient,
        "validate_image",
        AsyncMock(
            return_value={
                "valid": True,
                "image_type": "CROP_LEAF",
                "validation_confidence": 1.0,
            }
        ),
    )
    monkeypatch.setattr(
        OpenRouterClient,
        "identify_crop",
        AsyncMock(
            return_value={
                "crop_type": "WHEAT",
                "crop_confidence": 0.95,
            }
        ),
    )


@pytest.mark.asyncio
async def test_empty_image_returns_422() -> None:
    service = DiseaseDetectionService(MagicMock())
    with pytest.raises(HTTPException) as exc:
        await service.detect(USER_ID, FARM_ID, b"", "image/jpeg")
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_gemini_failure_returns_502(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "state": "Rajasthan",
            "district": "Bharatpur",
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.70, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(
        return_value={
            "valid": True,
            "image_type": "CROP_LEAF",
            "validation_confidence": 0.94,
        }
    )
    gemini.identify_crop = AsyncMock(
        return_value={
            "crop_type": "WHEAT",
            "crop_confidence": 0.95,
        }
    )
    gemini.detect_disease = AsyncMock(side_effect=RuntimeError("network down"))

    service = DiseaseDetectionService(db, gemini_client=gemini)
    with pytest.raises(HTTPException) as exc:
        await service.detect(USER_ID, FARM_ID, b"abc", "image/jpeg")
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_confirmed_detection_persists_report(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "state": "Rajasthan",
            "district": "Bharatpur",
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.70, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(
        return_value={
            "valid": True,
            "image_type": "CROP_LEAF",
            "validation_confidence": 0.94,
        }
    )
    gemini.identify_crop = AsyncMock(
        return_value={
            "crop_type": "WHEAT",
            "crop_confidence": 0.95,
        }
    )
    gemini.detect_disease = AsyncMock(return_value={"disease": "WHEAT_RUST", "confidence": 0.92})

    service = DiseaseDetectionService(db, gemini_client=gemini)
    result = await service.detect(USER_ID, FARM_ID, b"fake-image", "image/jpeg")

    assert result.deterministic_status == "CONFIRMED_DISEASE"
    assert result.disease == "WHEAT_RUST"
    assert result.explanation.primary_factor == "DISEASE"
    assert "Wheat Rust" in result.disease_name
    assert result.severity == "High"
    assert len(result.immediate_actions) > 0
    db.disease_reports.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_confirmed_detection_hindi_guidance(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "state": "Rajasthan",
            "district": "Bharatpur",
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.70, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(
        return_value={
            "valid": True,
            "image_type": "CROP_LEAF",
            "validation_confidence": 0.94,
        }
    )
    gemini.identify_crop = AsyncMock(
        return_value={
            "crop_type": "WHEAT",
            "crop_confidence": 0.95,
        }
    )
    gemini.detect_disease = AsyncMock(return_value={"disease": "WHEAT_RUST", "confidence": 0.92})

    service = DiseaseDetectionService(db, gemini_client=gemini)
    result = await service.detect(USER_ID, FARM_ID, b"fake-image", "image/jpeg", lang="hi")

    assert result.disease == "WHEAT_RUST"
    assert "पीला रतवा" in result.disease_name
    assert result.severity == "उच्च"
    assert len(result.immediate_actions) > 0


@pytest.mark.asyncio
async def test_invalid_disease_tag_lovse_or_random_text(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "state": "Rajasthan",
            "district": "Bharatpur",
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.70, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(
        return_value={
            "valid": True,
            "image_type": "CROP_LEAF",
            "validation_confidence": 0.94,
        }
    )
    gemini.identify_crop = AsyncMock(
        return_value={
            "crop_type": "WHEAT",
            "crop_confidence": 0.95,
        }
    )

    # First run: LOVSE
    gemini.detect_disease = AsyncMock(return_value={"disease": "LOVSE", "confidence": 0.92})
    service = DiseaseDetectionService(db, gemini_client=gemini)
    result = await service.detect(USER_ID, FARM_ID, b"fake-image", "image/jpeg")

    assert result.deterministic_status == "UNKNOWN"
    assert result.disease == "UNKNOWN"
    assert result.confidence is None

    # Second run: random text
    gemini.detect_disease = AsyncMock(return_value={"disease": "some_random_hallucination", "confidence": 0.88})
    result2 = await service.detect(USER_ID, FARM_ID, b"fake-image", "image/jpeg")

    assert result2.deterministic_status == "UNKNOWN"
    assert result2.disease == "UNKNOWN"
    assert result2.confidence is None


@pytest.mark.asyncio
async def test_crop_mismatch(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "state": "Rajasthan",
            "district": "Bharatpur",
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.70, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(
        return_value={
            "valid": True,
            "image_type": "CROP_LEAF",
            "validation_confidence": 0.94,
        }
    )
    
    # Model identifies SUGARCANE but registered is WHEAT
    gemini.identify_crop = AsyncMock(
        return_value={
            "crop_type": "SUGARCANE",
            "crop_confidence": 0.95,
        }
    )

    service = DiseaseDetectionService(db, gemini_client=gemini)
    result = await service.detect(USER_ID, FARM_ID, b"fake-image", "image/jpeg")

    assert result.deterministic_status == "UNKNOWN"
    assert result.disease == "UNKNOWN"
    assert result.confidence is None
    assert "Crop mismatch detected" in result.explanation.summary


@pytest.mark.asyncio
async def test_healthy_crop_image(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "state": "Rajasthan",
            "district": "Bharatpur",
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.70, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={"valid": True, "image_type": "CROP_LEAF", "validation_confidence": 0.95})
    gemini.identify_crop = AsyncMock(return_value={"crop_type": "WHEAT", "crop_confidence": 0.95})
    gemini.detect_disease = AsyncMock(return_value={"disease": "HEALTHY", "confidence": 0.95})

    service = DiseaseDetectionService(db, gemini_client=gemini)
    result = await service.detect(USER_ID, FARM_ID, b"fake-image", "image/jpeg")

    assert result.deterministic_status == "HEALTHY"
    assert result.disease == "HEALTHY"
    assert result.confidence is None # healthy/unknown has None confidence


@pytest.mark.asyncio
async def test_unknown_crop_image(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "state": "Rajasthan",
            "district": "Bharatpur",
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.70, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={"valid": True, "image_type": "CROP_LEAF", "validation_confidence": 0.95})
    gemini.identify_crop = AsyncMock(return_value={"crop_type": "WHEAT", "crop_confidence": 0.50})

    service = DiseaseDetectionService(db, gemini_client=gemini)
    result = await service.detect(USER_ID, FARM_ID, b"fake-image", "image/jpeg")

    assert result.deterministic_status == "UNKNOWN"
    assert result.disease == "UNKNOWN"
    assert result.confidence is None
    assert "Unable to confidently identify a disease. Please upload a clearer close-up image of the affected leaf." in result.explanation.summary


@pytest.mark.asyncio
async def test_low_confidence_crop_mismatch(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "state": "Rajasthan",
            "district": "Bharatpur",
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.70, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={"valid": True, "image_type": "CROP_LEAF", "validation_confidence": 0.95})
    # Low confidence mismatch: crop identified is SUGARCANE (0.80) while registered is WHEAT
    gemini.identify_crop = AsyncMock(return_value={"crop_type": "SUGARCANE", "crop_confidence": 0.80})
    gemini.detect_disease = AsyncMock(return_value={"disease": "WHEAT_RUST", "confidence": 0.92})

    service = DiseaseDetectionService(db, gemini_client=gemini)
    result = await service.detect(USER_ID, FARM_ID, b"fake-image", "image/jpeg")

    # Mismatch is ignored because confidence is < 0.90, so we check WHEAT_RUST
    assert result.deterministic_status == "CONFIRMED_DISEASE"
    assert result.disease == "WHEAT_RUST"
    assert result.message == "Crop identification confidence is low."
    assert result.explanation.summary.startswith("Crop identification confidence is low.")


@pytest.mark.asyncio
async def test_high_confidence_crop_mismatch(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "state": "Rajasthan",
            "district": "Bharatpur",
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.70, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={"valid": True, "image_type": "CROP_LEAF", "validation_confidence": 0.95})
    # High confidence mismatch: crop identified is SUGARCANE (0.95) while registered is WHEAT
    gemini.identify_crop = AsyncMock(return_value={"crop_type": "SUGARCANE", "crop_confidence": 0.95})

    service = DiseaseDetectionService(db, gemini_client=gemini)
    result = await service.detect(USER_ID, FARM_ID, b"fake-image", "image/jpeg")

    assert result.deterministic_status == "UNKNOWN"
    assert result.disease == "UNKNOWN"
    assert result.confidence is None
    assert "Crop mismatch detected" in result.explanation.summary
    assert "Unable to confidently identify a disease." in result.explanation.summary


@pytest.mark.asyncio
async def test_matching_crop(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "state": "Rajasthan",
            "district": "Bharatpur",
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.70, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={"valid": True, "image_type": "CROP_LEAF", "validation_confidence": 0.95})
    # Matching crop: WHEAT (0.95)
    gemini.identify_crop = AsyncMock(return_value={"crop_type": "WHEAT", "crop_confidence": 0.95})
    gemini.detect_disease = AsyncMock(return_value={"disease": "WHEAT_RUST", "confidence": 0.92})

    service = DiseaseDetectionService(db, gemini_client=gemini)
    result = await service.detect(USER_ID, FARM_ID, b"fake-image", "image/jpeg")

    assert result.deterministic_status == "CONFIRMED_DISEASE"
    assert result.disease == "WHEAT_RUST"
    assert result.message is None or "confidence is low" not in result.message

    gemini.identify_crop.assert_called_once()
    assert gemini.identify_crop.call_args.kwargs.get("registered_crop") == "WHEAT"


@pytest.mark.asyncio
async def test_disease_detection_without_crop_prediction(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "state": "Rajasthan",
            "district": "Bharatpur",
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.70, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={"valid": True, "image_type": "CROP_LEAF", "validation_confidence": 0.95})
    gemini.identify_crop = AsyncMock(return_value={"crop_type": "WHEAT", "crop_confidence": 0.95})
    gemini.detect_disease = AsyncMock(return_value={"disease": "WHEAT_RUST", "confidence": 0.92})

    service = DiseaseDetectionService(db, gemini_client=gemini)
    result = await service.detect(USER_ID, FARM_ID, b"fake-image", "image/jpeg")

    # Assert that detect_disease does not expect crop_type in return
    gemini.detect_disease.assert_called_once()
    args, kwargs = gemini.detect_disease.call_args
    # It still receives crop_type as input to guide detection, but does not predict it
    assert kwargs.get("crop_type") == "WHEAT"
    # Result has correct confidence and status
    assert result.disease == "WHEAT_RUST"
    assert result.confidence == 0.92


