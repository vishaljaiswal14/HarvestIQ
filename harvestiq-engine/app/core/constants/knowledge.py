from typing import Final

CHROMA_COLLECTION_NAME: Final[str] = "agri_knowledge"


def normalize_topic(value: str) -> str:
    return value.strip().upper().replace(" ", "_")
DEFAULT_CHUNK_SIZE: Final[int] = 500
DEFAULT_CHUNK_OVERLAP: Final[int] = 50
HYBRID_KEYWORD_WEIGHT: Final[float] = 0.35
HYBRID_VECTOR_WEIGHT: Final[float] = 0.65
