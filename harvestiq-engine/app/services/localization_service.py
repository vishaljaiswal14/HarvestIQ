from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.day5_schemas import LocalizationResponse


class LocalizationService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    async def get_labels(self, lang: str, fallback_lang: str = "en") -> LocalizationResponse:
        normalized = lang.strip().lower()
        labels = await self._fetch_lang(normalized)
        if not labels and normalized != fallback_lang:
            labels = await self._fetch_lang(fallback_lang)
        return LocalizationResponse(lang=normalized, labels=labels)

    async def _fetch_lang(self, lang: str) -> dict[str, str]:
        cursor = self.db.localization_dictionary.find({"lang": lang})
        labels: dict[str, str] = {}
        async for doc in cursor:
            labels[doc["key"]] = doc["value"]
        return labels

    async def upsert_label(self, key: str, lang: str, value: str) -> None:
        now = datetime.now(timezone.utc)
        await self.db.localization_dictionary.update_one(
            {"key": key, "lang": lang},
            {"$set": {"key": key, "lang": lang, "value": value, "updated_at": now}},
            upsert=True,
        )

    async def seed_defaults(self, entries: Optional[list[dict[str, str]]] = None) -> int:
        defaults = entries or _DEFAULT_ENTRIES
        count = 0
        for entry in defaults:
            await self.upsert_label(entry["key"], entry["lang"], entry["value"])
            count += 1
        return count


_DEFAULT_ENTRIES: list[dict[str, str]] = [
    {"key": "dashboard.title", "lang": "en", "value": "HarvestIQ"},
    {"key": "dashboard.subtitle", "lang": "en", "value": "Field intelligence dashboard"},
    {"key": "dashboard.advisory", "lang": "en", "value": "Ask Advisory"},
    {"key": "dashboard.disease", "lang": "en", "value": "Disease Detection"},
    {"key": "dashboard.radar", "lang": "en", "value": "Disease Radar"},
    {"key": "advisory.title", "lang": "en", "value": "Farm Advisory"},
    {"key": "advisory.placeholder", "lang": "en", "value": "Ask about your crop, soil, or weather..."},
    {"key": "advisory.send", "lang": "en", "value": "Send"},
    {"key": "voice.record", "lang": "en", "value": "Record voice"},
    {"key": "Query is required", "lang": "en", "value": "Query is required"},
    {"key": "Audio file is required", "lang": "en", "value": "Audio file is required"},
    {"key": "Image file is required", "lang": "en", "value": "Image file is required"},
    {"key": "No active crop cycle found", "lang": "en", "value": "No active crop cycle found"},
    {"key": "Farm location missing", "lang": "en", "value": "Farm location missing"},
    {"key": "HIGH_STRESS", "lang": "en", "value": "HIGH_STRESS"},
    {"key": "LOW_STRESS", "lang": "en", "value": "LOW_STRESS"},
    {"key": "NO_STRESS", "lang": "en", "value": "NO_STRESS"},
    {"key": "dashboard.title", "lang": "hi", "value": "हार्वेस्टआईक्यू"},
    {"key": "dashboard.subtitle", "lang": "hi", "value": "खेत खुफिया डैशबोर्ड"},
    {"key": "dashboard.advisory", "lang": "hi", "value": "सलाह पूछें"},
    {"key": "dashboard.disease", "lang": "hi", "value": "रोग पहचान"},
    {"key": "dashboard.radar", "lang": "hi", "value": "रोग रडार"},
    {"key": "advisory.title", "lang": "hi", "value": "खेत सलाह"},
    {"key": "advisory.placeholder", "lang": "hi", "value": "अपनी फसल, मिट्टी या मौसम के बारे में पूछें..."},
    {"key": "advisory.send", "lang": "hi", "value": "भेजें"},
    {"key": "voice.record", "lang": "hi", "value": "आवाज़ रिकॉर्ड करें"},
    {"key": "Query is required", "lang": "hi", "value": "प्रश्न आवश्यक है"},
    {"key": "Audio file is required", "lang": "hi", "value": "ऑडियो फ़ाइल आवश्यक है"},
    {"key": "Image file is required", "lang": "hi", "value": "छवि फ़ाइल आवश्यक है"},
    {"key": "No active crop cycle found", "lang": "hi", "value": "कोई सक्रिय फसल चक्र नहीं मिला"},
    {"key": "Farm location missing", "lang": "hi", "value": "खेत का स्थान गायब है"},
    {"key": "HIGH_STRESS", "lang": "hi", "value": "उच्च तनाव"},
    {"key": "LOW_STRESS", "lang": "hi", "value": "कम तनाव"},
    {"key": "NO_STRESS", "lang": "hi", "value": "कोई तनाव नहीं"},
]
