from unittest.mock import MagicMock

import pytest

from app.core.constants.knowledge import normalize_topic
from app.models.day4_schemas import HybridSearchParams
from app.services.rag_service import RagService


@pytest.mark.asyncio
async def test_hybrid_search_returns_ranked_chunks(monkeypatch) -> None:
    db = MagicMock()

    async def fake_cursor():
        yield {"document_id": "icar-wheat-heat-stress-rajasthan"}

    db.knowledge_metadata.find = MagicMock(return_value=fake_cursor())

    collection = MagicMock()
    collection.count.return_value = 2
    collection.query.return_value = {
        "documents": [
            [
                "Wheat heat stress management in Rajasthan requires irrigation scheduling.",
                "Rice blast management in West Bengal.",
            ]
        ],
        "metadatas": [
            [
                {
                    "source": "ICAR",
                    "source_document": "icar-wheat-heat-stress-rajasthan",
                    "crop_type": "WHEAT",
                    "state": "RAJASTHAN",
                },
                {
                    "source": "State Agri Dept",
                    "source_document": "govt-rice-blast-west-bengal",
                    "crop_type": "RICE",
                    "state": "WEST_BENGAL",
                },
            ]
        ],
        "distances": [[0.15, 0.55]],
    }

    monkeypatch.setattr("app.services.rag_service.get_agri_knowledge_collection", lambda: collection)

    service = RagService(db)
    results = await service.hybrid_search(
        HybridSearchParams(
            query="wheat heat stress rajasthan",
            crop_type="WHEAT",
            state="RAJASTHAN",
            limit=2,
        )
    )

    assert len(results) >= 1
    assert "wheat" in results[0].text.lower()
    assert results[0].score > 0


def test_keyword_score_prefers_matching_terms() -> None:
    service = RagService(MagicMock())
    high = service._keyword_score("wheat heat stress", "Wheat heat stress management in Rajasthan")
    low = service._keyword_score("wheat heat stress", "Unrelated rice irrigation advisory")
    assert high > low


def test_normalize_topic_uppercases_and_underscores() -> None:
    assert normalize_topic("heat stress") == "HEAT_STRESS"
    assert normalize_topic("disease management") == "DISEASE_MANAGEMENT"


@pytest.mark.parametrize(
    "topic_input",
    ["heat_stress", "HEAT_STRESS", "Heat Stress"],
)
@pytest.mark.asyncio
async def test_topic_filter_accepts_mixed_case_queries(topic_input: str, monkeypatch) -> None:
    db = MagicMock()
    captured_mongo_query: dict = {}

    async def fake_cursor():
        yield {"document_id": "icar-wheat-heat-stress-rajasthan"}

    def capture_find(query, _projection):
        captured_mongo_query.update(query)
        return fake_cursor()

    db.knowledge_metadata.find = MagicMock(side_effect=capture_find)

    collection = MagicMock()
    collection.count.return_value = 1
    captured_query_kwargs: dict = {}

    def capture_query(**kwargs):
        captured_query_kwargs.update(kwargs)
        return {
            "documents": [["Wheat heat stress management in Rajasthan requires irrigation scheduling."]],
            "metadatas": [
                [
                    {
                        "source": "ICAR",
                        "source_document": "icar-wheat-heat-stress-rajasthan",
                        "crop_type": "WHEAT",
                        "state": "RAJASTHAN",
                        "topic": "HEAT_STRESS",
                    }
                ]
            ],
            "distances": [[0.15]],
        }

    collection.query = MagicMock(side_effect=capture_query)

    monkeypatch.setattr("app.services.rag_service.get_agri_knowledge_collection", lambda: collection)

    service = RagService(db)
    results = await service.hybrid_search(
        HybridSearchParams(
            query="wheat heat stress rajasthan",
            crop_type="WHEAT",
            state="RAJASTHAN",
            topic=topic_input,
            limit=3,
        )
    )

    assert captured_mongo_query["topic"] == "HEAT_STRESS"
    where_clauses = captured_query_kwargs["where"]["$and"]
    assert {"topic": "HEAT_STRESS"} in where_clauses
    assert len(results) >= 1
    assert results[0].metadata["topic"] == "HEAT_STRESS"
