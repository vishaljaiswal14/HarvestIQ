from enum import StrEnum


class CropType(StrEnum):
    WHEAT = "WHEAT"
    RICE = "RICE"
    MAIZE = "MAIZE"
    COTTON = "COTTON"
    SUGARCANE = "SUGARCANE"
    SOYBEAN = "SOYBEAN"
    MUSTARD = "MUSTARD"
    POTATO = "POTATO"


_CROP_ALIASES: dict[str, CropType] = {
    "wheat": CropType.WHEAT,
    "rice": CropType.RICE,
    "maize": CropType.MAIZE,
    "corn": CropType.MAIZE,
    "cotton": CropType.COTTON,
    "sugarcane": CropType.SUGARCANE,
    "soybean": CropType.SOYBEAN,
    "mustard": CropType.MUSTARD,
    "potato": CropType.POTATO,
}


def normalize_crop_type(value: str) -> str:
    cleaned = value.strip().upper().replace(" ", "_")
    if cleaned in CropType.__members__:
        return cleaned
    alias = _CROP_ALIASES.get(value.strip().lower())
    if alias:
        return alias.value
    return cleaned
