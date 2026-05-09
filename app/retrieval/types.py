from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    title: str
    url: str
    anchor: str | None
    content: str
    score: float
    metadata: dict[str, Any]
    rerank_score: float | None = None


@dataclass(frozen=True)
class Citation:
    label: str
    url: str
    snippet: str
    section_path: str | None


@dataclass(frozen=True)
class RetrievalOutput:
    rewritten_query: str
    filters: dict[str, str]
    initial_results: list[RetrievedChunk]
    reranked_results: list[RetrievedChunk]
    citations: list[Citation]
    confidence: float
