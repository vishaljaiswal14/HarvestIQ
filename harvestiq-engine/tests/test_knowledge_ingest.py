from pathlib import Path

from app.services.knowledge_ingest_service import KnowledgeIngestService


def test_chunk_text_splits_long_paragraphs() -> None:
    text = "Paragraph one about wheat.\n\n" + ("Long advisory sentence. " * 80)
    chunks = KnowledgeIngestService._chunk_text(text, size=200, overlap=20)
    assert len(chunks) >= 2
    assert all(len(chunk) <= 200 for chunk in chunks)


def test_parse_frontmatter_extracts_metadata(tmp_path: Path) -> None:
    path = tmp_path / "sample.md"
    path.write_text(
        """---
document_id: sample-doc
title: Sample Advisory
source: ICAR
crop_type: WHEAT
state: RAJASTHAN
district: ALL
season: RABI
topic: fertilizer
language: en
---

Sample advisory body for wheat farmers.
""",
        encoding="utf-8",
    )
    raw = path.read_text(encoding="utf-8")
    frontmatter, body = KnowledgeIngestService._parse_frontmatter(raw)
    assert frontmatter["document_id"] == "sample-doc"
    assert "wheat farmers" in body
