import re
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.chroma import get_agri_knowledge_collection
from app.core.constants.knowledge import HYBRID_KEYWORD_WEIGHT, HYBRID_VECTOR_WEIGHT, normalize_topic
from app.models.day4_schemas import HybridSearchParams, KnowledgeChunkResult


class RagService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    async def hybrid_search(self, params: HybridSearchParams) -> list[KnowledgeChunkResult]:
        allowed_docs = await self._filter_document_ids(params)
        if allowed_docs is not None and not allowed_docs:
            return []

        collection = get_agri_knowledge_collection()
        where = self._build_chroma_where(params, allowed_docs)
        query_kwargs: dict[str, Any] = {
            "query_texts": [params.query],
            "n_results": min(params.limit * 3, 30),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where

        if collection.count() == 0:
            return []

        results = collection.query(**query_kwargs)
        return self._rank_results(params.query, results, params.limit)

    async def _filter_document_ids(self, params: HybridSearchParams) -> Optional[set[str]]:
        mongo_query: dict[str, Any] = {}
        if params.crop_type:
            mongo_query["$or"] = [
                {"crop_type": params.crop_type.upper()},
                {"crop_type": "ALL"},
            ]
        if params.state:
            state_filter = {"$or": [{"state": params.state.upper()}, {"state": "ALL"}]}
            mongo_query = {"$and": [mongo_query, state_filter]} if mongo_query else state_filter
        if params.district:
            district_filter = {
                "$or": [
                    {"district": params.district.upper()},
                    {"district": "ALL"},
                ]
            }
            mongo_query = {"$and": [mongo_query, district_filter]} if mongo_query else district_filter
        if params.season:
            season_filter = {"$or": [{"season": params.season.upper()}, {"season": "ALL"}]}
            mongo_query = {"$and": [mongo_query, season_filter]} if mongo_query else season_filter
        if params.topic:
            mongo_query["topic"] = normalize_topic(params.topic)

        if not mongo_query:
            return None

        cursor = self.db.knowledge_metadata.find(mongo_query, {"document_id": 1})
        return {doc["document_id"] async for doc in cursor}

    @staticmethod
    def _build_chroma_where(params: HybridSearchParams, allowed_docs: Optional[set[str]]) -> dict[str, Any]:
        clauses: list[dict[str, Any]] = []
        if params.crop_type:
            clauses.append(
                {
                    "$or": [
                        {"crop_type": params.crop_type.upper()},
                        {"crop_type": "ALL"},
                    ]
                }
            )
        if params.state:
            clauses.append(
                {
                    "$or": [
                        {"state": params.state.upper()},
                        {"state": "ALL"},
                    ]
                }
            )
        if params.district:
            clauses.append(
                {
                    "$or": [
                        {"district": params.district.upper()},
                        {"district": "ALL"},
                    ]
                }
            )
        if params.season:
            clauses.append(
                {
                    "$or": [
                        {"season": params.season.upper()},
                        {"season": "ALL"},
                    ]
                }
            )
        if params.topic:
            clauses.append({"topic": normalize_topic(params.topic)})
        if allowed_docs is not None:
            clauses.append({"source_document": {"$in": sorted(allowed_docs)}})

        if not clauses:
            return {}
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    @staticmethod
    def _keyword_score(query: str, text: str) -> float:
        tokens = {token for token in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(token) > 2}
        if not tokens:
            return 0.0
        lowered = text.lower()
        hits = sum(1 for token in tokens if token in lowered)
        return hits / len(tokens)

    def _rank_results(self, query: str, results: dict[str, Any], limit: int) -> list[KnowledgeChunkResult]:
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        ranked: list[KnowledgeChunkResult] = []
        for document, metadata, distance in zip(documents, metadatas, distances, strict=False):
            vector_score = max(0.0, 1.0 - float(distance))
            keyword_score = self._keyword_score(query, document)
            score = round(
                (HYBRID_VECTOR_WEIGHT * vector_score) + (HYBRID_KEYWORD_WEIGHT * keyword_score),
                4,
            )
            ranked.append(
                KnowledgeChunkResult(
                    text=document,
                    source=str(metadata.get("source", metadata.get("source_document", "unknown"))),
                    score=score,
                    metadata=metadata,
                )
            )

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:limit]
