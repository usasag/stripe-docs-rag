from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IndexedDocument:
    id: str
    source_url: str
    title: str
    h1: str
    product_area: str
    raw_text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class IndexedChunk:
    id: str
    document_id: str
    chunk_index: int
    section_path: str
    anchor: str | None
    content: str
    token_count: int
    embedding: list[float]
    metadata: dict[str, Any]


class InMemoryIndexer:
    def __init__(self) -> None:
        self.documents: list[IndexedDocument] = []
        self.chunks: list[IndexedChunk] = []

    def upsert_document(self, document: IndexedDocument) -> None:
        self.documents = [d for d in self.documents if d.source_url != document.source_url]
        self.documents.append(document)

    def upsert_chunks(self, chunks: list[IndexedChunk]) -> None:
        ids = {chunk.id for chunk in chunks}
        self.chunks = [c for c in self.chunks if c.id not in ids]
        self.chunks.extend(chunks)
