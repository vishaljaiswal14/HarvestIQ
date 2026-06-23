import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.chroma import get_agri_knowledge_collection
from app.core.constants.knowledge import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, normalize_topic
from app.models.day4_schemas import KnowledgeDocumentMeta


class KnowledgeIngestService:
    def __init__(self, db: AsyncIOMotorDatabase, kb_dir: Path | None = None) -> None:
        self.db = db
        root = Path(__file__).resolve().parents[2]
        self.kb_dir = kb_dir or (root / "data" / "agri_kb")

    async def ingest_all(self) -> int:
        if not self.kb_dir.exists():
            return 0

        indexed_documents = 0
        for path in sorted(self.kb_dir.glob("*.md")):
            await self.ingest_file(path)
            indexed_documents += 1
        return indexed_documents

    async def ingest_file(self, path: Path) -> KnowledgeDocumentMeta:
        raw = path.read_text(encoding="utf-8")
        frontmatter, body = self._parse_frontmatter(raw)
        meta = KnowledgeDocumentMeta(**frontmatter)
        topic = normalize_topic(meta.topic)
        chunks = self._chunk_text(body)

        collection = get_agri_knowledge_collection()
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for index, chunk in enumerate(chunks):
            chunk_id = f"{meta.document_id}:{index}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append(
                {
                    "source_document": meta.document_id,
                    "crop_type": meta.crop_type,
                    "state": meta.state,
                    "district": meta.district,
                    "season": meta.season,
                    "topic": topic,
                    "language": meta.language,
                    "title": meta.title,
                    "source": meta.source,
                    "chunk_index": index,
                }
            )

        if ids:
            collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

        indexed_at = datetime.now(timezone.utc)
        await self.db.knowledge_metadata.update_one(
            {"document_id": meta.document_id},
            {
                "$set": {
                    "document_id": meta.document_id,
                    "title": meta.title,
                    "source": meta.source,
                    "crop_type": meta.crop_type,
                    "state": meta.state,
                    "district": meta.district,
                    "season": meta.season,
                    "topic": topic,
                    "language": meta.language,
                    "chunk_count": len(chunks),
                    "indexed_at": indexed_at,
                }
            },
            upsert=True,
        )
        return meta

    @staticmethod
    def _parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
        if not raw.startswith("---"):
            return {}, raw.strip()

        _, remainder = raw.split("---", 1)
        frontmatter_block, body = remainder.split("---", 1)
        data: dict[str, Any] = {}
        for line in frontmatter_block.strip().splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
        return data, body.strip()

    @staticmethod
    def _chunk_text(text: str, size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: list[str] = []
        current = ""

        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 1 <= size:
                current = f"{current}\n\n{paragraph}".strip()
                continue
            if current:
                chunks.append(current)
            if len(paragraph) <= size:
                current = paragraph
                continue
            start = 0
            while start < len(paragraph):
                end = min(start + size, len(paragraph))
                chunks.append(paragraph[start:end])
                start = max(end - overlap, end)
            current = ""

        if current:
            chunks.append(current)
        return chunks
