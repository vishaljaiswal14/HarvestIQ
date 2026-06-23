from functools import lru_cache
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from app.core.config import get_settings
from app.core.constants.knowledge import CHROMA_COLLECTION_NAME

_chroma_client: Optional[ClientAPI] = None


def get_chroma_client() -> ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        settings = get_settings()
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(persist_dir))
    return _chroma_client


def get_agri_knowledge_collection() -> Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def reset_chroma_client() -> None:
    global _chroma_client
    _chroma_client = None


@lru_cache
def get_chroma_collection_name() -> str:
    return CHROMA_COLLECTION_NAME
