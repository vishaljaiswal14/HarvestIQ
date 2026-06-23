import io
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from PIL import Image, ImageDraw, ImageFilter
from bson import ObjectId

from app.integrations.gemini_client import OpenRouterClient
from app.services.disease_detection_service import DiseaseDetectionService
from app.services.image_quality import analyze_image_quality

FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())
CYCLE_ID = ObjectId()

# Helpers to generate actual Pillow image bytes
def make_solid_image(color="green", size=(300, 300)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def make_low_res_image() -> bytes:
    return make_solid_image(size=(100, 100))

def make_blurry_image() -> bytes:
    img = Image.new("RGB", (300, 300), "black")
    draw = ImageDraw.Draw(img)
    draw.rectangle([150, 0, 300, 300], fill="white")
    blurred_img = img.filter(ImageFilter.GaussianBlur(10))
    buf = io.BytesIO()
    blurred_img.save(buf, format="PNG")
    return buf.getvalue()

def make_detailed_image() -> bytes:
    # High contrast lines to give high edge scores (sharp image)
    img = Image.new("RGB", (300, 300), "green")
    draw = ImageDraw.Draw(img)
    for i in range(0, 300, 10):
        draw.line([(i, 0), (i, 300)], fill="yellow", width=2)
        draw.line([(0, i), (300, i)], fill="red", width=2)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

# Quality Checks (Stage 2)
def test_quality_low_resolution() -> None:
    img_bytes = make_low_res_image()
    res = analyze_image_quality(img_bytes)
    assert res["valid"] is False
    assert res["reason"] == "LOW_IMAGE_QUALITY"
    assert "resolution is too low" in res["message"]

def test_quality_blank_white() -> None:
    img_bytes = make_solid_image("white")
    res = analyze_image_quality(img_bytes)
    assert res["valid"] is False
    assert res["reason"] == "LOW_IMAGE_QUALITY"
    assert "white or overexposed" in res["message"]

def test_quality_blank_black() -> None:
    img_bytes = make_solid_image("black")
    res = analyze_image_quality(img_bytes)
    assert res["valid"] is False
    assert res["reason"] == "LOW_IMAGE_QUALITY"
    assert "dark or black" in res["message"]

def test_quality_low_contrast() -> None:
    img_bytes = make_solid_image("gray")
    res = analyze_image_quality(img_bytes)
    assert res["valid"] is False
    assert res["reason"] == "LOW_IMAGE_QUALITY"
    assert "contrast is too low" in res["message"]

def test_quality_blurry() -> None:
    img_bytes = make_blurry_image()
    res = analyze_image_quality(img_bytes)
    assert res["valid"] is False
    assert res["reason"] == "LOW_IMAGE_QUALITY"
    assert "blurry" in res["message"]

def test_quality_valid_sharp() -> None:
    img_bytes = make_detailed_image()
    res = analyze_image_quality(img_bytes)
    assert res["valid"] is True
    assert "metrics" in res

# Service Validation and Pipeline Checks (Stages 1, 2, and 3)
@pytest.mark.asyncio
async def test_selfie_rejection(monkeypatch) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    
    async def fake_owned(_db, _farm_id, _user_id):
        return {"_id": ObjectId(FARM_ID), "state": "Punjab", "location": {"type": "Point", "coordinates": [0,0]}}
    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={
        "valid": False,
        "image_type": "HUMAN",
        "validation_confidence": 0.99,
        "reason": "NOT_CROP_IMAGE",
        "message": "Please upload a crop leaf, crop canopy, or agricultural field image."
    })

    service = DiseaseDetectionService(db, gemini_client=gemini)
    img_bytes = make_detailed_image()
    res = await service.detect(USER_ID, FARM_ID, img_bytes, "image/jpeg")

    assert res.valid is False
    assert res.image_type == "HUMAN"
    assert res.reason == "NOT_CROP_IMAGE"
    assert "Please upload" in res.message
    gemini.detect_disease.assert_not_called()

@pytest.mark.asyncio
async def test_screenshot_rejection(monkeypatch) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    
    async def fake_owned(_db, _farm_id, _user_id):
        return {"_id": ObjectId(FARM_ID), "state": "Punjab", "location": {"type": "Point", "coordinates": [0,0]}}
    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={
        "valid": False,
        "image_type": "SCREENSHOT",
        "validation_confidence": 0.95,
        "reason": "NOT_CROP_IMAGE",
        "message": "Please upload a crop leaf, crop canopy, or agricultural field image."
    })

    service = DiseaseDetectionService(db, gemini_client=gemini)
    img_bytes = make_detailed_image()
    res = await service.detect(USER_ID, FARM_ID, img_bytes, "image/jpeg")

    assert res.valid is False
    assert res.image_type == "SCREENSHOT"
    gemini.detect_disease.assert_not_called()

@pytest.mark.asyncio
async def test_animal_rejection(monkeypatch) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    
    async def fake_owned(_db, _farm_id, _user_id):
        return {"_id": ObjectId(FARM_ID), "state": "Punjab", "location": {"type": "Point", "coordinates": [0,0]}}
    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={
        "valid": False,
        "image_type": "ANIMAL",
        "validation_confidence": 0.96,
        "reason": "NOT_CROP_IMAGE",
        "message": "Please upload a crop leaf, crop canopy, or agricultural field image."
    })

    service = DiseaseDetectionService(db, gemini_client=gemini)
    img_bytes = make_detailed_image()
    res = await service.detect(USER_ID, FARM_ID, img_bytes, "image/jpeg")

    assert res.valid is False
    assert res.image_type == "ANIMAL"
    gemini.detect_disease.assert_not_called()

@pytest.mark.asyncio
async def test_vehicle_rejection(monkeypatch) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    
    async def fake_owned(_db, _farm_id, _user_id):
        return {"_id": ObjectId(FARM_ID), "state": "Punjab", "location": {"type": "Point", "coordinates": [0,0]}}
    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={
        "valid": False,
        "image_type": "VEHICLE",
        "validation_confidence": 0.98,
        "reason": "NOT_CROP_IMAGE",
        "message": "Please upload a crop leaf, crop canopy, or agricultural field image."
    })

    service = DiseaseDetectionService(db, gemini_client=gemini)
    img_bytes = make_detailed_image()
    res = await service.detect(USER_ID, FARM_ID, img_bytes, "image/jpeg")

    assert res.valid is False
    assert res.image_type == "VEHICLE"
    gemini.detect_disease.assert_not_called()

@pytest.mark.asyncio
async def test_building_rejection(monkeypatch) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    
    async def fake_owned(_db, _farm_id, _user_id):
        return {"_id": ObjectId(FARM_ID), "state": "Punjab", "location": {"type": "Point", "coordinates": [0,0]}}
    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={
        "valid": False,
        "image_type": "BUILDING",
        "validation_confidence": 0.97,
        "reason": "NOT_CROP_IMAGE",
        "message": "Please upload a crop leaf, crop canopy, or agricultural field image."
    })

    service = DiseaseDetectionService(db, gemini_client=gemini)
    img_bytes = make_detailed_image()
    res = await service.detect(USER_ID, FARM_ID, img_bytes, "image/jpeg")

    assert res.valid is False
    assert res.image_type == "BUILDING"
    gemini.detect_disease.assert_not_called()

@pytest.mark.asyncio
async def test_valid_diseased_crop(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "state": "Punjab",
            "location": {"type": "Point", "coordinates": [0,0]},
        }
    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.50, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={
        "valid": True,
        "image_type": "CROP_LEAF",
        "validation_confidence": 0.94
    })
    gemini.identify_crop = AsyncMock(return_value={
        "crop_type": "WHEAT",
        "crop_confidence": 0.95
    })
    gemini.detect_disease = AsyncMock(return_value={
        "disease": "WHEAT_RUST",
        "confidence": 0.88
    })

    service = DiseaseDetectionService(db, gemini_client=gemini)
    img_bytes = make_detailed_image()
    res = await service.detect(USER_ID, FARM_ID, img_bytes, "image/jpeg")

    assert res.valid is True
    assert res.disease == "WHEAT_RUST"
    assert res.confidence == 0.88
    assert res.deterministic_status == "CONFIRMED_DISEASE"
    assert "Yellow Rust" in res.disease_name

@pytest.mark.asyncio
async def test_valid_healthy_crop(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "state": "Punjab",
            "location": {"type": "Point", "coordinates": [0,0]},
        }
    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.50, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={
        "valid": True,
        "image_type": "CROP_LEAF",
        "validation_confidence": 0.94
    })
    gemini.identify_crop = AsyncMock(return_value={
        "crop_type": "WHEAT",
        "crop_confidence": 0.95
    })
    gemini.detect_disease = AsyncMock(return_value={
        "disease": "HEALTHY",
        "confidence": 0.90
    })

    service = DiseaseDetectionService(db, gemini_client=gemini)
    img_bytes = make_detailed_image()
    res = await service.detect(USER_ID, FARM_ID, img_bytes, "image/jpeg")

    assert res.valid is True
    assert res.disease == "HEALTHY"
    assert res.deterministic_status == "HEALTHY"
    assert "Healthy Crop" in res.disease_name


@pytest.mark.asyncio
async def test_unknown_crop_rejection(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    async def fake_owned(_db, _farm_id, _user_id):
        return {"_id": ObjectId(FARM_ID), "state": "Punjab", "location": {"type": "Point", "coordinates": [0,0]}}
    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.50, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={
        "valid": True,
        "image_type": "CROP_LEAF",
        "validation_confidence": 0.94
    })
    gemini.identify_crop = AsyncMock(return_value={
        "crop_type": "WHEAT",
        "crop_confidence": 0.55
    })

    service = DiseaseDetectionService(db, gemini_client=gemini)
    img_bytes = make_detailed_image()
    res = await service.detect(USER_ID, FARM_ID, img_bytes, "image/jpeg")

    assert res.valid is True
    assert res.deterministic_status == "UNKNOWN"
    assert res.disease == "UNKNOWN"
    assert res.recommended_treatment is None


@pytest.mark.asyncio
async def test_low_confidence_disease(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()
    async def fake_owned(_db, _farm_id, _user_id):
        return {"_id": ObjectId(FARM_ID), "state": "Punjab", "location": {"type": "Point", "coordinates": [0,0]}}
    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.50, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={
        "valid": True,
        "image_type": "CROP_LEAF",
        "validation_confidence": 0.94
    })
    gemini.identify_crop = AsyncMock(return_value={
        "crop_type": "WHEAT",
        "crop_confidence": 0.95
    })
    gemini.detect_disease = AsyncMock(return_value={
        "disease": "WHEAT_RUST",
        "confidence": 0.60
    })

    service = DiseaseDetectionService(db, gemini_client=gemini)
    img_bytes = make_detailed_image()
    res = await service.detect(USER_ID, FARM_ID, img_bytes, "image/jpeg")

    assert res.valid is True
    assert res.deterministic_status == "LOW_CONFIDENCE"
    assert res.disease == "WHEAT_RUST"
    assert res.recommended_treatment is None


@pytest.mark.asyncio
async def test_unknown_disease_confidence(monkeypatch, tmp_path) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={"_id": CYCLE_ID, "crop_type": "WHEAT", "status": "ACTIVE"}
    )
    db.disease_reports.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.disease_reports.update_one = AsyncMock()
    async def fake_owned(_db, _farm_id, _user_id):
        return {"_id": ObjectId(FARM_ID), "state": "Punjab", "location": {"type": "Point", "coordinates": [0,0]}}
    monkeypatch.setattr("app.services.disease_detection_service.get_owned_farm", fake_owned)
    monkeypatch.setattr(
        "app.services.disease_detection_service.get_settings",
        lambda: MagicMock(disease_confidence_threshold=0.50, disease_upload_dir=str(tmp_path)),
    )

    gemini = MagicMock(spec=OpenRouterClient)
    gemini.validate_image = AsyncMock(return_value={
        "valid": True,
        "image_type": "CROP_LEAF",
        "validation_confidence": 0.94
    })
    gemini.identify_crop = AsyncMock(return_value={
        "crop_type": "WHEAT",
        "crop_confidence": 0.95
    })
    gemini.detect_disease = AsyncMock(return_value={
        "disease": "WHEAT_RUST",
        "confidence": 0.40
    })

    service = DiseaseDetectionService(db, gemini_client=gemini)
    img_bytes = make_detailed_image()
    res = await service.detect(USER_ID, FARM_ID, img_bytes, "image/jpeg")

    assert res.valid is True
    assert res.deterministic_status == "UNKNOWN"
    assert res.disease == "UNKNOWN"
    assert res.recommended_treatment is None
